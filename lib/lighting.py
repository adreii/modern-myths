"""Time-of-day looks (port of roblox/StoryKit/LightingPresets.luau).

    lighting.preset(s, "dawn")                    # snap at the shot start
    lighting.blend(s, "day", "dusk", 0, s.dur)    # shot 11: day -> dusk over the shot

Every shot has its own sun (`s01_Sun` in the shot's collection) and its own world group, both
set once and not keyed, so they can be grabbed and changed in Blender like any light. The
compositor grade and exposure are shared and keyed at each shot's first frame (constant).
Changes made in Blender are kept by pipeline/grab_looks.py, which writes them to the episode's
looks.yaml; preset() applies that file on every build. The world is one `EP01_World` with a node
group per shot (`WG_S04` ...), each in a labelled frame, laid out left to right in shot order; a
selector driven by the active scene's `ep_shot` (keyed per shot) picks which one renders. So a
shot's sky can be tuned in its own group without touching any other shot, and a look-dev scene
just sets its own `ep_shot`. What maps to what:

    clockTime        -> sun elevation/azimuth (latitude 41.73, Roblox's default; the moon at night)
    brightness       -> sun strength
    outdoorAmbient   -> world light colour (what lights the scene); ambient tints it
    atmosphere       -> sky the camera sees: an HDRI (assets/ext, per look) mixed with a gradient
                        (colour at the horizon, decay above) + distance fog from the mist pass in
                        the compositor (density, haze), which also fades the far mountains
    grade            -> compositor tint (multiply), saturation, contrast, brightness
    bloom            -> compositor Glare (Bloom)
    exposure         -> view_settings.exposure, on top of the style's base exposure

Everything is keyed, the compositor too (its node group is an ID with its own action).
Don't call core.world_key in the same file: it sets every world key to constant and would
flatten blend().
"""
import math

import bpy
from mathutils import Vector

from . import core


def _c(r, g, b):
    """Roblox Color3.fromRGB -> linear RGB."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


def _g(r, g, b):
    """Roblox Color3.fromRGB taken as-is (no linearising): Roblox mixes ambient light and
    the colour-correction tint closer to display space, so these read right un-converted."""
    return (r / 255, g / 255, b / 255)


# Roblox values, verbatim (LightingPresets.luau:36-72).
PRESETS = {
    "pre_dawn_dark": dict(
        clock=6.0, brightness=1.1, exposure=-0.05,
        ambient=_g(85, 95, 130), outdoor=_g(110, 120, 160),
        atmo=dict(density=0.35, haze=1.5, color=_c(130, 145, 185), decay=_c(70, 80, 120)),
        grade=dict(tint=_g(195, 210, 255), saturation=-0.25, contrast=0.1, brightness=-0.02),
        bloom=dict(intensity=0.9, size=28, threshold=0.9)),
    "dawn": dict(
        clock=6.4, brightness=1.6, exposure=0,
        ambient=_g(90, 80, 90), outdoor=_g(140, 120, 120),
        atmo=dict(density=0.33, haze=2, color=_c(255, 205, 170), decay=_c(140, 120, 150)),
        grade=dict(tint=_g(255, 236, 220), saturation=0.05, contrast=0.08, brightness=0),
        bloom=dict(intensity=0.6, size=30, threshold=0.85)),
    "day": dict(
        clock=13, brightness=2.4, exposure=0,
        ambient=_g(110, 110, 120), outdoor=_g(150, 150, 160),
        atmo=dict(density=0.25, haze=0.5, color=_c(200, 220, 255), decay=_c(110, 130, 160)),
        grade=dict(tint=_g(255, 255, 255), saturation=0.15, contrast=0.1, brightness=0),
        bloom=dict(intensity=0.35, size=24, threshold=0.95)),
    "dusk": dict(
        clock=18.5, brightness=1.4, exposure=-0.1,
        ambient=_g(95, 70, 80), outdoor=_g(140, 100, 100),
        atmo=dict(density=0.32, haze=2.2, color=_c(255, 170, 120), decay=_c(120, 80, 120)),
        grade=dict(tint=_g(255, 225, 205), saturation=0.1, contrast=0.12, brightness=-0.02),
        bloom=dict(intensity=0.7, size=32, threshold=0.85)),
    "night": dict(
        clock=21, brightness=0.4, exposure=-0.4,
        ambient=_g(30, 35, 60), outdoor=_g(45, 50, 85),
        atmo=dict(density=0.36, haze=1, color=_c(80, 95, 140), decay=_c(40, 45, 80)),
        grade=dict(tint=_g(190, 205, 255), saturation=-0.2, contrast=0.15, brightness=-0.04),
        bloom=dict(intensity=1.1, size=30, threshold=0.8)),
}

# Blender-side tuning the Roblox engine did implicitly (sun colour, how bright a low sun is).
TUNE = {
    "pre_dawn_dark": dict(sun_color=(0.55, 0.65, 1.0), sun_mult=0.35),
    "dawn": dict(sun_color=(1.0, 0.70, 0.48), sun_mult=0.9),
    "day": dict(sun_color=(1.0, 0.96, 0.90), sun_mult=1.0),
    "dusk": dict(sun_color=(1.0, 0.62, 0.40), sun_mult=0.9),
    "night": dict(sun_color=(0.55, 0.65, 1.0), sun_mult=1.8),
}

# share of house windows lit (the WindowGlass material's LitFraction): nobody is up at dawn,
# lamps go on at dusk; the bakery has its own light
WINDOWS_LIT = {"pre_dawn_dark": 0.0, "dawn": 0.0, "day": 0.0, "dusk": 0.4, "night": 0.65}

LATITUDE = 41.73      # Roblox Lighting.GeographicLatitude default
NORTH = 0.0           # degrees to turn the whole sky around Z, to suit the town's layout
MIN_ELEVATION = 5.0   # a sun just under the horizon still rakes the street (Roblox dusk does)
SUN_K = 1.6           # Roblox brightness -> sun strength
AMBIENT_K = 0.55      # world light strength
SKY_K = 1.0           # strength of the sky the camera sees
FOG_START, FOG_DEPTH = 100.0, 6000.0   # studs; the far peaks sit 2,300-3,600 out
FOG_K = 1.2           # more haze than Roblox's, so the mountain ranges separate in depth

# the sky photo behind each look (Poly Haven, CC0, in assets/ext): file, strength, how much of
# it shows against the gradient, rotation (degrees)
HDRI = {
    "pre_dawn_dark": ("kloofendal_misty_morning", 0.25, 0.55, 140),
    "dawn": ("misty_dawn", 0.9, 0.75, 200),
    "day": ("kloofendal_misty_morning", 1.0, 0.8, 30),
    "dusk": ("misty_dawn", 0.7, 0.7, 20),
    "night": ("kloofendal_misty_morning", 0.05, 0.4, 0),
}
EXT = __import__("pathlib").Path(__file__).resolve().parents[1] / "assets" / "ext"


def _sun_dir(clock):
    """Unit vector towards the sun (or the moon at night) for a Roblox clock time."""
    lat = math.radians(LATITUDE)
    h = math.radians((clock - 12) * 15)
    up = math.cos(lat) * math.cos(h)
    if up < math.sin(math.radians(-15)):      # well after sunset: use the moon, opposite
        h += math.pi
        up = math.cos(lat) * math.cos(h)
    east = -math.sin(h)
    south = math.sin(lat) * math.cos(h)
    el = max(math.asin(max(-1, min(1, up))), math.radians(MIN_ELEVATION))
    horiz = Vector((east, -south, 0))
    horiz = horiz.normalized() if horiz.length > 1e-6 else Vector((0, -1, 0))
    d = horiz * math.cos(el) + Vector((0, 0, math.sin(el)))
    rot = math.radians(NORTH)
    return Vector((d.x * math.cos(rot) - d.y * math.sin(rot), d.x * math.sin(rot) + d.y * math.cos(rot), d.z))


def _values(name):
    """A preset flattened to the numbers the scene gets keyed with."""
    p, k = PRESETS[name], TUNE[name]
    a, g, b = p["atmo"], p["grade"], p["bloom"]
    light = tuple(o * 0.75 + i * 0.25 for o, i in zip(p["outdoor"], p["ambient"]))
    return dict(
        clock=p["clock"],
        sun_strength=p["brightness"] * SUN_K * k["sun_mult"],
        sun_color=k["sun_color"],
        world_color=light,
        horizon=a["color"], zenith=a["decay"],
        fog=min(0.92, FOG_K * a["density"] * (0.8 + 0.25 * a["haze"])),
        tint=g["tint"], saturation=1 + g["saturation"],
        contrast=g["contrast"] * 100, brightness=g["brightness"] * 100,
        bloom_strength=b["intensity"] * 0.5,
        bloom_threshold=b["threshold"] * 1.1,
        bloom_size=min(1.0, b["size"] / 40),
        exposure=p["exposure"],
        hdri_strength=HDRI[name][1], hdri_mix=HDRI[name][2],
        windows=WINDOWS_LIT[name],
    )


def _lerp(a, b, x):
    out = {}
    for k, va in a.items():
        vb = b[k]
        out[k] = tuple(p + (q - p) * x for p, q in zip(va, vb)) if isinstance(va, tuple) else va + (vb - va) * x
    return out


# --- shared rig ---------------------------------------------------------------------------

def _rig():
    """Build (once) the sun, the world nodes and the compositor grade; return their handles."""
    sc = bpy.context.scene
    sun = bpy.data.objects.get("StoryKit_Sun")
    if sun is not None:
        return sun, sc.world.node_tree.nodes, sc.compositing_node_group.nodes

    coll = bpy.data.collections.new("StoryKit_Light")
    sc.collection.children.link(coll)
    ld = bpy.data.lights.new("StoryKit_Sun", "SUN")
    ld.energy = 0.0  # unused: each shot has its own sun now (shot_sun)
    sun = bpy.data.objects.new("StoryKit_Sun", ld)
    sun.hide_render = True
    coll.objects.link(sun)

    # world: one group per shot (added by preset()), a selector picks the active shot's
    w = sc.world
    w.name = "EP01_World"
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    sel = nt.nodes.new("ShaderNodeValue")
    sel.name = sel.label = "Shot"
    fc = sel.outputs[0].driver_add("default_value")
    var = fc.driver.variables.new()
    var.name, var.type = "shot", "CONTEXT_PROP"
    var.targets[0].context_property = "ACTIVE_SCENE"
    var.targets[0].data_path = '["ep_shot"]'
    fc.driver.expression = "shot"
    sc["ep_shot"] = 0
    w.mist_settings.start, w.mist_settings.depth = FOG_START, FOG_DEPTH
    w.mist_settings.falloff = "LINEAR"

    # compositor: fog -> tint -> saturation -> contrast -> bloom
    bpy.context.view_layer.use_pass_mist = True
    ng = sc.compositing_node_group
    if ng is None:
        ng = bpy.data.node_groups.new("StoryKit_Grade", "CompositorNodeTree")
        sc.compositing_node_group = ng
    ng.nodes.clear()
    if not any(i.item_type == "SOCKET" and i.in_out == "OUTPUT" for i in ng.interface.items_tree):
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    n = ng.nodes
    rl = n.new("CompositorNodeRLayers")
    fogf = n.new("ShaderNodeMath")
    fogf.name, fogf.operation = "FogAmount", "MULTIPLY"
    fog = n.new("ShaderNodeMix")
    fog.name, fog.data_type = "Fog", "RGBA"
    tint = n.new("ShaderNodeMix")
    tint.name, tint.data_type, tint.blend_type = "Tint", "RGBA", "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    hs = n.new("CompositorNodeHueSat")
    hs.name = "Saturation"
    bc = n.new("CompositorNodeBrightContrast")
    bc.name = "Contrast"
    gl = n.new("CompositorNodeGlare")
    gl.name = "Bloom"
    gl.inputs["Type"].default_value = "Bloom"
    gl.inputs["Quality"].default_value = "Medium"
    go = n.new("NodeGroupOutput")
    L = ng.links.new
    L(rl.outputs["Mist"], fogf.inputs[0])
    L(fogf.outputs[0], fog.inputs["Factor"])
    L(rl.outputs["Image"], fog.inputs["A"])
    L(fog.outputs["Result"], tint.inputs["A"])
    L(tint.outputs["Result"], hs.inputs["Image"])
    L(hs.outputs["Image"], bc.inputs["Image"])
    L(bc.outputs["Image"], gl.inputs["Image"])
    L(gl.outputs["Image"], go.inputs[0])
    sc["storykit_exposure"] = sc.view_settings.exposure   # the style's base exposure
    return sun, nt.nodes, ng.nodes


# --- the per-shot world groups -------------------------------------------------------------------

GROUP_INPUTS = (("Ambient Color", "NodeSocketColor"), ("Ambient Strength", "NodeSocketFloat"),
                ("Horizon", "NodeSocketColor"), ("Zenith", "NodeSocketColor"),
                ("HDRI Strength", "NodeSocketFloat"), ("HDRI Mix", "NodeSocketFloat"),
                ("HDRI Rotation", "NodeSocketFloat"), ("Sky Strength", "NodeSocketFloat"))
SPACING = 420


def _world_group(name, hdri):
    """WG_<shot>: the sky the camera sees (HDRI over a horizon-to-zenith gradient) and the light
    everything else gets (ambient colour, coloured by the same HDRI)."""
    ng = bpy.data.node_groups.new(name, "ShaderNodeTree")
    for nm, kind in GROUP_INPUTS:
        ng.interface.new_socket(nm, in_out="INPUT", socket_type=kind)
    ng.interface.new_socket("World", in_out="OUTPUT", socket_type="NodeSocketShader")
    n, L = ng.nodes, ng.links.new
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    gi.location, go.location = (-900, 0), (700, 0)
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ")
    rng = n.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = -0.05, 0.6
    grad = n.new("ShaderNodeMix")
    grad.data_type = "RGBA"
    L(tc.outputs["Generated"], sep.inputs[0])
    L(sep.outputs["Z"], rng.inputs["Value"])
    L(rng.outputs["Result"], grad.inputs["Factor"])
    L(gi.outputs["Horizon"], _socket(grad, "A", "RGBA"))
    L(gi.outputs["Zenith"], _socket(grad, "B", "RGBA"))
    sky_col = _socket_out(grad)
    amb_col = gi.outputs["Ambient Color"]
    f = EXT / hdri / f"{hdri}_2k.hdr"
    if f.exists():
        rad = n.new("ShaderNodeMath")
        rad.operation = "RADIANS"
        L(gi.outputs["HDRI Rotation"], rad.inputs[0])
        rot = n.new("ShaderNodeCombineXYZ")
        L(rad.outputs[0], rot.inputs["Z"])
        mp = n.new("ShaderNodeMapping")
        L(tc.outputs["Generated"], mp.inputs["Vector"])
        L(rot.outputs[0], mp.inputs["Rotation"])
        env = n.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(str(f), check_existing=True)
        L(mp.outputs["Vector"], env.inputs["Vector"])
        bright = n.new("ShaderNodeMix")
        bright.data_type, bright.blend_type = "RGBA", "MULTIPLY"
        bright.inputs["Factor"].default_value = 1.0
        L(env.outputs["Color"], _socket(bright, "A", "RGBA"))
        hs = n.new("ShaderNodeCombineColor")
        for c in ("Red", "Green", "Blue"):
            L(gi.outputs["HDRI Strength"], hs.inputs[c])
        L(hs.outputs[0], _socket(bright, "B", "RGBA"))
        over = n.new("ShaderNodeMix")  # the photo over the gradient
        over.data_type = "RGBA"
        L(gi.outputs["HDRI Mix"], over.inputs["Factor"])
        L(sky_col, _socket(over, "A", "RGBA"))
        L(_socket_out(bright), _socket(over, "B", "RGBA"))
        sky_col = _socket_out(over)
        tint = n.new("ShaderNodeMix")  # light from the photo, coloured by the ambient
        tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
        L(gi.outputs["HDRI Mix"], tint.inputs["Factor"])
        L(gi.outputs["Ambient Color"], _socket(tint, "A", "RGBA"))
        norm = n.new("ShaderNodeMix")
        norm.data_type = "RGBA"
        norm.inputs["Factor"].default_value = 0.5
        L(env.outputs["Color"], _socket(norm, "A", "RGBA"))
        _socket(norm, "B", "RGBA").default_value = (1, 1, 1, 1)
        L(_socket_out(norm), _socket(tint, "B", "RGBA"))
        amb_col = _socket_out(tint)
    amb = n.new("ShaderNodeBackground")
    sky = n.new("ShaderNodeBackground")
    L(amb_col, amb.inputs["Color"])
    L(gi.outputs["Ambient Strength"], amb.inputs["Strength"])
    L(sky_col, sky.inputs["Color"])
    L(gi.outputs["Sky Strength"], sky.inputs["Strength"])
    lp = n.new("ShaderNodeLightPath")
    mix = n.new("ShaderNodeMixShader")
    L(lp.outputs["Is Camera Ray"], mix.inputs[0])
    L(amb.outputs[0], mix.inputs[1])
    L(sky.outputs[0], mix.inputs[2])
    L(mix.outputs[0], go.inputs[0])
    for i, node in enumerate(x for x in n if x not in (gi, go)):
        node.location = (-600 + (i % 6) * 220, 300 - (i // 6) * 260)
    return ng


def _socket_out(node):
    return next(o for o in node.outputs if o.name == "Result" and o.type == "RGBA")


def shot_world(s, look, label=None):
    """The group node in EP01_World for shot s (made on first use), placed and labelled in shot
    order, and the selector re-wired to include it. Returns the group node."""
    _rig()
    nt = bpy.context.scene.world.node_tree
    key = f"WG_{s.name.upper()}"
    node = nt.nodes.get(key)
    if node is None:
        hdri = HDRI.get(look, HDRI["day"])
        frame = nt.nodes.new("NodeFrame")
        frame.name = f"Frame_{key}"
        frame.label = f"{s.name.upper()} · {label or look.replace('_', ' ')}"
        frame.label_size = 28
        frame.shrink = True
        node = nt.nodes.new("ShaderNodeGroup")
        node.name = key
        node.node_tree = _world_group(key, hdri[0])
        node.label = frame.label
        node.parent = frame
        node.location = (s.index * SPACING, 0)
        node["shot_index"] = s.index
        node["look"] = look
        node.width = 300
        _wire_selector(nt)
    # this shot renders this group: key the scene's ep_shot at the shot start
    sc = bpy.context.scene
    sc["ep_shot"] = s.index
    sc.keyframe_insert('["ep_shot"]', frame=s.f0)
    for fc in core.fcurves(sc):
        if fc.data_path == '["ep_shot"]':
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"
    return node


def _wire_selector(nt):
    """Chain the shot groups left to right through Mix Shaders, each switched on by
    (Shot == its index), into the World Output on the far right."""
    for n in list(nt.nodes):
        if n.name.startswith("Pick_") or n.name.startswith("Is_"):
            nt.nodes.remove(n)
    groups = sorted((n for n in nt.nodes if n.type == "GROUP" and n.name.startswith("WG_")),
                    key=lambda n: n["shot_index"])
    sel = nt.nodes["Shot"]
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    prev = groups[0].outputs[0]
    for g in groups[1:]:
        x = g["shot_index"] * SPACING
        cmp = nt.nodes.new("ShaderNodeMath")
        cmp.name, cmp.operation = f"Is_{g.name}", "COMPARE"
        cmp.inputs[1].default_value = g["shot_index"]
        cmp.inputs[2].default_value = 0.5
        cmp.location = (x, -520)
        nt.links.new(sel.outputs[0], cmp.inputs[0])
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.name = f"Pick_{g.name}"
        mx.location = (x + 180, -420)
        nt.links.new(cmp.outputs[0], mx.inputs[0])
        nt.links.new(prev, mx.inputs[1])
        nt.links.new(g.outputs[0], mx.inputs[2])
        prev = mx.outputs[0]
    nt.links.new(prev, out.inputs["Surface"])
    last = groups[-1]["shot_index"] * SPACING
    out.location = (last + SPACING + 200, -420)
    sel.location = (-SPACING, -520)


def _socket(node, name, kind):
    """Mix nodes have one socket per data type under the same name; pick the right one."""
    return next(i for i in node.inputs if i.name == name and i.type == kind)


def shot_sun(s):
    """The shot's own sun: an ordinary sun lamp in the shot's collection, above the town."""
    name = f"{s.name}_Sun"
    sun = bpy.data.objects.get(name)
    if sun is None:
        ld = bpy.data.lights.new(name, "SUN")
        ld.angle = math.radians(3)
        sun = s.adopt(bpy.data.objects.new(name, ld), None, (0, 0, 80))
        sun.empty_display_size = 6
    return sun


def _apply(frame, v, interp, wg, sun, key_shot=True):
    """Set every value at frame and key the shared ones. interp is the interpolation of the
    segment after it. wg / sun: the shot's world group node and sun; they are keyed only when
    key_shot (a blend), so a still shot's sun and sky stay free to edit by hand."""
    sc = bpy.context.scene
    _, wn, cn = _rig()
    d = _sun_dir(v["clock"])
    prev = sun.rotation_euler.copy()
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler("XYZ", prev)
    sun.data.energy = v["sun_strength"]
    sun.data.color = v["sun_color"]
    gin = wg.inputs
    gin["Ambient Color"].default_value = (*v["world_color"], 1)
    gin["Ambient Strength"].default_value = AMBIENT_K
    gin["Horizon"].default_value = (*v["horizon"], 1)
    gin["Zenith"].default_value = (*v["zenith"], 1)
    gin["HDRI Strength"].default_value = v["hdri_strength"]
    gin["HDRI Mix"].default_value = v["hdri_mix"]
    gin["Sky Strength"].default_value = SKY_K
    cn["FogAmount"].inputs[1].default_value = v["fog"]
    _socket(cn["Fog"], "B", "RGBA").default_value = (*v["horizon"], 1)
    _socket(cn["Tint"], "B", "RGBA").default_value = (*v["tint"], 1)
    cn["Saturation"].inputs["Saturation"].default_value = v["saturation"]
    cn["Contrast"].inputs["Contrast"].default_value = v["contrast"]
    cn["Contrast"].inputs["Brightness"].default_value = v["brightness"]
    gl = cn["Bloom"]
    gl.inputs["Strength"].default_value = v["bloom_strength"]
    gl.inputs["Threshold"].default_value = v["bloom_threshold"]
    gl.inputs["Size"].default_value = v["bloom_size"]
    sc.view_settings.exposure = sc["storykit_exposure"] + v["exposure"]

    if key_shot:
        sun.keyframe_insert("rotation_euler", frame=frame)
        sun.data.keyframe_insert("energy", frame=frame)
        sun.data.keyframe_insert("color", frame=frame)
        for nm in ("Ambient Color", "Ambient Strength", "Horizon", "Zenith", "HDRI Strength", "HDRI Mix"):
            gin[nm].keyframe_insert("default_value", frame=frame)
    for sock in (cn["FogAmount"].inputs[1], _socket(cn["Fog"], "B", "RGBA"), _socket(cn["Tint"], "B", "RGBA"),
                 cn["Saturation"].inputs["Saturation"], cn["Contrast"].inputs["Contrast"],
                 cn["Contrast"].inputs["Brightness"], gl.inputs["Strength"], gl.inputs["Threshold"], gl.inputs["Size"]):
        sock.keyframe_insert("default_value", frame=frame)
    sc.keyframe_insert("view_settings.exposure", frame=frame)
    glass = bpy.data.materials.get("WindowGlass")
    lit = glass.node_tree.nodes.get("LitFraction") if glass and glass.node_tree else None
    if lit is not None:  # shared by every shot, so keyed like the grade
        lit.outputs[0].default_value = v["windows"]
        lit.outputs[0].keyframe_insert("default_value", frame=frame)
        for fc in core.fcurves(glass.node_tree):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp
    for owner in (sun, sun.data, sc.world.node_tree, sc.compositing_node_group, sc):
        for fc in core.fcurves(owner):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp


SUN_KEYS = ("rotation", "strength", "color", "angle")
WORLD_KEYS = [n for n, _ in GROUP_INPUTS]


def read_look(sun, wg):
    """The hand-editable values of a shot's look: its sun and its world group inputs."""
    sun_v = {"rotation": [round(math.degrees(a), 2) for a in sun.rotation_euler],
             "strength": round(sun.data.energy, 4), "color": [round(c, 4) for c in sun.data.color],
             "angle": round(math.degrees(sun.data.angle), 2)}
    world = {}
    for n in WORLD_KEYS:
        v = wg.inputs[n].default_value
        world[n] = [round(c, 4) for c in v] if hasattr(v, "__len__") else round(v, 4)
    return {"sun": sun_v, "world": world}


def apply_look(sun, wg, look):
    """Apply a looks.yaml entry ({sun: {...}, world: {...}}) on top of the preset."""
    sv = (look or {}).get("sun", {})
    if "rotation" in sv:
        sun.rotation_euler = [math.radians(a) for a in sv["rotation"]]
    if "strength" in sv:
        sun.data.energy = sv["strength"]
    if "color" in sv:
        sun.data.color = sv["color"]
    if "angle" in sv:
        sun.data.angle = math.radians(sv["angle"])
    for n, v in (look or {}).get("world", {}).items():
        wg.inputs[n].default_value = v


def windows(s, lit, to=None, t0=0.0, t1=None):
    """Override how many house windows are lit in this shot (0-1). With `to`, they come on one by
    one from `lit` to `to` between t0 and t1 (each window has its own threshold)."""
    glass = bpy.data.materials.get("WindowGlass")
    node = glass.node_tree.nodes.get("LitFraction") if glass and glass.node_tree else None
    if node is None:
        return
    sock = node.outputs[0]
    t1 = s.dur if t1 is None else t1
    keys = [(s.f0, lit, "CONSTANT")] if to is None else [(s.f0, lit, "CONSTANT"), (s.f(t0), lit, "LINEAR"),
                                                         (s.f(t1), to, "CONSTANT")]
    for frame, v, interp in keys:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=frame)
        for fc in core.fcurves(glass.node_tree):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp


def preset(s, name, label=None, look=None):
    """Light this shot with a preset: its own sun and world group get the values (not keyed,
    so they can be changed by hand), the shared grade and exposure are keyed at its first frame.
    label: what the shot's world frame says after the shot number (default: the preset name).
    look: this shot's entry in the episode's looks.yaml (hand-made changes, see grab_looks.py)."""
    wg = shot_world(s, name, label)
    sun = shot_sun(s)
    wg.inputs["HDRI Rotation"].default_value = HDRI[name][3]
    _apply(s.f0, _values(name), "CONSTANT", wg, sun, key_shot=False)
    import json
    base = read_look(sun, wg)  # what the preset gives, so grab_looks.py writes only real changes
    sun["preset_look"] = json.dumps(base["sun"])
    wg["preset_look"] = json.dumps(base["world"])
    apply_look(sun, wg, look)


def blend(s, a, b, t0=0.0, t1=None, label=None):
    """Hold preset a until t0, ease (sine in-out) to b by t1, then hold b.
    Sampled every 2 frames, so the sun travels its real arc instead of cutting across the sky."""
    t1 = s.dur if t1 is None else t1
    wg = shot_world(s, a, label)
    sun = shot_sun(s)
    wg.inputs["HDRI Rotation"].default_value = HDRI[a][3]
    va, vb = _values(a), _values(b)
    if vb["clock"] < va["clock"]:   # time always moves forward
        vb["clock"] += 24
    f0, f1 = s.f(t0), s.f(t1)
    if f0 > s.f0:
        _apply(s.f0, va, "CONSTANT", wg, sun)
    for f in range(f0, f1, 2):
        x = (f - f0) / max(f1 - f0, 1)
        _apply(f, _lerp(va, vb, 0.5 - 0.5 * math.cos(math.pi * x)), "LINEAR", wg, sun)
    _apply(f1, vb, "CONSTANT", wg, sun)
