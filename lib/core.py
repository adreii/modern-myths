"""Core Blender helpers: scene setup, materials, primitives, animation, shot context.

Everything an episode's shots.py needs is reached through a `Shot` context:
each shot gets its own stage (a root empty far from the others), its own camera,
its own lights, and is only visible during its time range.
"""
import math

import bpy
from mathutils import Matrix, Vector

PALETTE = {
    "cream": (0.93, 0.86, 0.74), "wall": (0.96, 0.80, 0.66), "wall_blue": (0.62, 0.78, 0.86),
    "wood": (0.78, 0.52, 0.28), "wood_light": (0.90, 0.70, 0.45), "wood_dark": (0.45, 0.26, 0.13),
    "red": (0.86, 0.22, 0.17), "mustard": (0.93, 0.68, 0.18), "teal": (0.16, 0.56, 0.58),
    "green": (0.36, 0.62, 0.30), "blue": (0.22, 0.42, 0.78), "pink": (0.95, 0.55, 0.62),
    "purple": (0.52, 0.36, 0.68), "skin": (0.98, 0.80, 0.66), "white": (0.95, 0.95, 0.93),
    "black": (0.03, 0.03, 0.035), "grey": (0.55, 0.57, 0.60), "silver": (0.75, 0.78, 0.82),
    "hair": (0.32, 0.18, 0.09), "rug": (0.80, 0.40, 0.35), "night": (0.05, 0.07, 0.16),
    "gold": (0.95, 0.75, 0.25), "steam": (1, 1, 1),
}


# Brighter, more saturated plastic colours for the Roblox-like "brick" style.
BRICK_PALETTE = {
    "red": (0.80, 0.08, 0.06), "mustard": (0.98, 0.70, 0.05), "teal": (0.02, 0.55, 0.62),
    "green": (0.16, 0.62, 0.16), "blue": (0.05, 0.30, 0.85), "pink": (1.0, 0.40, 0.55),
    "purple": (0.40, 0.20, 0.75), "skin": (1.0, 0.80, 0.18), "wall": (0.95, 0.88, 0.75),
    "wall_blue": (0.55, 0.80, 0.98), "cream": (0.62, 0.80, 1.0), "rug": (0.85, 0.25, 0.25),
}

# Visual style switch: "toy" (wooden peg dolls) or "brick" (blocky plastic avatars).
STYLE = {"name": "toy"}


def set_style(name):
    STYLE["name"] = name
    if name == "brick":
        PALETTE.update(BRICK_PALETTE)


def rgb(c):
    return PALETTE[c] if isinstance(c, str) else c


# --- scene ------------------------------------------------------------------

def new_scene(fps=12, res=(1080, 1920), scale=100, engine="CYCLES", samples=24, style="toy"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    _meshes.clear()
    set_style(style)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = scale
    sc.render.engine = engine
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    if style == "brick":  # the user's art direction (2026-10-30): AgX, no look
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = -0.9
    else:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    if engine == "CYCLES":
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 4
        sc.cycles.device = "CPU"
    elif engine.startswith("BLENDER_EEVEE"):
        sc.eevee.taa_render_samples = samples
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    sc.world = world
    return sc


def world_key(frame, color, strength=1.0):
    """Ambient light/background, switched per shot (constant interpolation)."""
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*rgb(color), 1)
    bg.inputs[1].default_value = strength
    bg.inputs[0].keyframe_insert("default_value", frame=frame)
    bg.inputs[1].keyframe_insert("default_value", frame=frame)
    for fc in fcurves(bpy.context.scene.world.node_tree):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


# --- materials ----------------------------------------------------------------

_mats = {}


def mat(color, rough=0.55, emit=0.0, name=None):
    col = rgb(color)
    key = (col, rough, emit)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name or (color if isinstance(color, str) else "mat"))
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*col, 1)
    if STYLE["name"] == "brick":
        rough = min(rough, 0.35)  # smooth plastic
        if isinstance(color, str) and color.startswith("wood"):
            _wood_grain(m, col)
            rough = 0.6
    p.inputs["Roughness"].default_value = rough
    if emit:
        p.inputs["Emission Color"].default_value = (*col, 1)
        p.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*col, 1)
    _mats[key] = m
    return m


def _wood_grain(m, col):
    """Real wood among the plastic: stretched noise bands between two shades."""
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 12.0)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.72 for c in col], 1)
    ramp.color_ramp.elements[1].color = (*col, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])


def baseplate_mat(color):
    """Game-style floor: a faint grid of stud-sized tiles."""
    m = mat(color, 0.4, name="baseplate")
    if "grid" in m:
        return m
    m["grid"] = True
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = 4.0
    col = rgb(color)
    chk.inputs["Color1"].default_value = (*col, 1)
    chk.inputs["Color2"].default_value = (*[c * 0.9 for c in col], 1)
    nt.links.new(tc.outputs["Object"], chk.inputs["Vector"])
    nt.links.new(chk.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


# --- shot context ---------------------------------------------------------------

class Shot:
    """Build context for one shot. Times are in seconds relative to shot start."""

    def __init__(self, name, index, start, end, fps, lines, at_origin=False):
        self.name, self.fps, self.index = name, fps, index
        self.t0, self.t1 = start, end
        self.dur = end - start
        self.f0 = round(start * fps) + 1
        self.f1 = max(round(end * fps), self.f0)
        self.lines = [dict(l, start=l["start"] - start, end=l["end"] - start) for l in lines]
        self.after = []  # callables build.py runs once every shot exists (e.g. Cam.declip)
        self.coll = bpy.data.collections.new(f"{index:02d}_{name}")
        bpy.context.scene.collection.children.link(self.coll)
        self.root = self._link(bpy.data.objects.new(f"{name}_root", None))
        self.cam = None
        # extra lights for this shot only: anything put in here is shown just during the shot
        # (keyed by finish(), or by the key_shot_lights text in the .blend for lights added by hand)
        self.lights = bpy.data.collections.new(f"{name}_Lights")
        self.lights["shot"], self.lights["f0"], self.lights["f1"] = name, self.f0, self.f1
        self.coll.children.link(self.lights)
        # own stage far from the others, or the origin when every shot shares one town
        self.root.location = (0, 0, 0) if at_origin else (index * 60.0, 0, 0)

    # time helpers
    def f(self, t):
        """Seconds (shot-relative) -> absolute frame, never past the shot's last visible frame
        (so a move's end key, e.g. the camera's B point, sits on a frame you can see it on)."""
        return min(self.f0 + round(t * self.fps), self.f1)

    def line(self, i):
        return self.lines[i]

    def cue(self, i, word, after=False):
        """Estimated time a word is spoken in line i (by character position)."""
        ln = self.lines[i]
        text = ln["text"].lower()
        pos = text.find(word.lower())
        if pos < 0:
            raise ValueError(f"{word!r} not in line {i}: {ln['text']!r}")
        if after:
            pos += len(word)
        return ln["start"] + (ln["end"] - ln["start"]) * pos / max(len(text), 1)

    # object creation
    def _link(self, ob):
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        self.coll.objects.link(ob)
        return ob

    def adopt(self, ob, parent=None, loc=(0, 0, 0)):
        self._link(ob)
        ob.parent = parent or self.root
        ob.location = loc
        return ob

    def empty(self, name="empty", loc=(0, 0, 0), parent=None):
        return self.adopt(bpy.data.objects.new(name, None), parent, loc)

    def hide(self, ob, hidden=True):
        """Hide (or show) a shared object, e.g. a town wall, only during this shot."""
        for prop in ("hide_render", "hide_viewport"):
            for frame, val in ((self.f0 - 1, not hidden), (self.f0, hidden), (self.f1 + 1, not hidden)):
                setattr(ob, prop, val)
                ob.keyframe_insert(prop, frame=frame)

    def finish(self):
        """Hide every object of this shot (its lights collection too) outside its time range."""
        for ob in list(self.coll.objects) + list(self.lights.objects):  # (all_objects can be stale mid-build)
            key_shown(ob, self.f0, self.f1)


def key_shown(ob, f0, f1):
    """Key an object visible from frame f0 to f1 and hidden either side."""
    for prop in ("hide_render", "hide_viewport"):
        for frame, val in ((f0 - 1, True), (f0, False), (f1 + 1, True)):
            setattr(ob, prop, val)
            ob.keyframe_insert(prop, frame=frame)


# --- primitives (all return objects parented to the shot stage) -------------------

_meshes = {}


def _mesh(op, kw, smooth, size=None):
    """Mesh datablocks are cached and shared: the add-operator only runs once per shape,
    which keeps scene building fast as the object count grows."""
    k = (op.idname(), tuple(sorted(kw.items())), smooth, size)
    if k not in _meshes:
        op(**kw)
        tmp = bpy.context.active_object
        me = tmp.data
        bpy.data.objects.remove(tmp)
        if size:
            me.transform(Matrix.Diagonal((*size, 1)))
        me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
        me.materials.append(None)  # one slot; the material itself lives on each object
        _meshes[k] = me
    return _meshes[k]


def _prim(s, op, kw, color, loc, rot, parent, smooth, rough, emit, name, size=None):
    me = _mesh(op, kw, smooth, size)
    ob = s.adopt(bpy.data.objects.new(name or me.name, me), parent, loc)
    ob.rotation_euler = [math.radians(a) for a in rot]
    if color is not None:
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = mat(color, rough, emit)
    return ob


def box(s, size, color, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, bevel=0.04, rough=0.55, emit=0, name=None):
    ob = _prim(s, bpy.ops.mesh.primitive_cube_add, {"size": 1}, color, loc, rot, parent, bool(bevel), rough, emit,
               name, size=tuple(round(v, 5) for v in size))
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width, m.segments = bevel, 3
        ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    return ob


def ball(s, r, color, loc=(0, 0, 0), scale=(1, 1, 1), parent=None, rough=0.5, emit=0, name=None):
    ob = _prim(s, bpy.ops.mesh.primitive_uv_sphere_add, {"radius": r, "segments": 32, "ring_count": 16},
               color, loc, (0, 0, 0), parent, True, rough, emit, name)
    ob.scale = scale
    return ob


def cyl(s, r, h, color, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, r2=None, verts=32, rough=0.55, emit=0, bevel=0.0, name=None):
    if r2 is None:
        op, kw = bpy.ops.mesh.primitive_cylinder_add, {"radius": r, "depth": h, "vertices": verts}
    else:
        op, kw = bpy.ops.mesh.primitive_cone_add, {"radius1": r, "radius2": r2, "depth": h, "vertices": verts}
    ob = _prim(s, op, kw, color, loc, rot, parent, True, rough, emit, name)
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width, m.segments, m.limit_method = bevel, 3, "ANGLE"
    return ob


def ring(s, R, r, color, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, rough=0.4, name=None):
    return _prim(s, bpy.ops.mesh.primitive_torus_add,
                 {"major_radius": R, "minor_radius": r, "major_segments": 32, "minor_segments": 12},
                 color, loc, rot, parent, True, rough, 0, name)


def light(s, kind, loc, energy, color=(1, 0.95, 0.88), size=3.0, look=(0, 0, 0.8)):
    ld = bpy.data.lights.new(f"{s.name}_{kind}", kind)
    ld.energy, ld.color = energy, color
    if kind == "AREA":
        ld.size = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    ob = s.adopt(bpy.data.objects.new(ld.name, ld), None, loc)
    aim(ob, Vector(look) - Vector(loc))
    return ob


def aim(ob, direction):
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()


# --- animation ----------------------------------------------------------------------

def key(ob, path, value, frame, interp=None):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=frame)
    if interp:
        set_interp(ob, path, interp, frame)


def fcurves(owner):
    """An animated ID's F-curves, on Blender 4.2 (Action.fcurves) and 4.4+ (slotted actions)."""
    ad = owner.animation_data
    if not ad or not ad.action:
        return []
    if hasattr(ad.action, "fcurves"):
        return ad.action.fcurves
    from bpy_extras import anim_utils
    bag = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return bag.fcurves if bag else []


def set_interp(ob, path, interp, frame=None):
    for fc in fcurves(ob):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                if frame is None or abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interp


def move(s, ob, t0, t1, to, frm=None, interp=None):
    key(ob, "location", Vector(frm) if frm is not None else ob.location.copy(), s.f(t0), interp)
    key(ob, "location", Vector(to), s.f(t1), interp)


def turn(s, ob, t0, t1, to_deg, frm_deg=None, interp=None):
    if frm_deg is not None:
        ob.rotation_euler = [math.radians(a) for a in frm_deg]
    key(ob, "rotation_euler", ob.rotation_euler.copy(), s.f(t0), interp)
    key(ob, "rotation_euler", [math.radians(a) for a in to_deg], s.f(t1), interp)


def pop(s, ob, t, dur=0.35, size=1.0):
    """Scale in from nothing with a little overshoot."""
    base = Vector((size,) * 3) if isinstance(size, (int, float)) else Vector(size)
    key(ob, "scale", base * 0.001, s.f(t) - 1)
    key(ob, "scale", base * 0.001, s.f(t))
    key(ob, "scale", base * 1.18, s.f(t + dur * 0.6))
    key(ob, "scale", base, s.f(t + dur))


def vanish(s, ob, t, dur=0.25):
    base = ob.scale.copy()
    key(ob, "scale", base, s.f(t))
    key(ob, "scale", base * 0.001, s.f(t + dur))


def hop(s, ob, t0, t1, height=0.3, period=0.5, axis=2):
    """Repeated bounce, e.g. a toy that's 'alive'."""
    base = ob.location.copy()
    t = t0
    while t < t1:
        key(ob, "location", base, s.f(t))
        up = base.copy()
        up[axis] += height
        key(ob, "location", up, s.f(t + period / 2))
        t += period
    key(ob, "location", base, s.f(min(t, t1 + period)))


def wobble(s, ob, t0, t1, deg=8, period=0.5, axis=1, base_deg=None):
    """Rock back and forth around an axis."""
    base = ob.rotation_euler.copy() if base_deg is None else [math.radians(a) for a in base_deg]
    t, sign = t0, 1
    while t <= t1:
        r = list(base)
        r[axis] += math.radians(deg * sign)
        key(ob, "rotation_euler", r, s.f(t))
        t += period / 2
        sign = -sign
    key(ob, "rotation_euler", base, s.f(t))


# --- camera ----------------------------------------------------------------------------

def camera(s, pos, look, lens=40, to_pos=None, to_look=None, shake=0.0):
    """Shot camera bound to a timeline marker; optional slow dolly from pos to to_pos."""
    cd = bpy.data.cameras.new(f"{s.name}_cam")
    cd["shot"] = s.name
    cd.lens = lens
    cd.clip_end = 9000  # whole-town shots and the mountains behind
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 2.8
    cam = s.adopt(bpy.data.objects.new(cd.name, cd), None, pos)
    tgt = s.empty(f"{s.name}_look", look)
    cd.dof.focus_object = tgt
    c = cam.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    if to_pos is not None:
        move(s, cam, 0, s.dur, to_pos, frm=pos, interp="LINEAR")
    if to_look is not None:
        move(s, tgt, 0, s.dur, to_look, frm=look, interp="LINEAR")
    m = bpy.context.scene.timeline_markers.new(s.name, frame=s.f0)
    m.camera = cam
    s.cam = cam
    return cam, tgt
