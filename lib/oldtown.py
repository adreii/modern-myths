"""The Old Town: a small old European town built from lib/town_layout.yaml.

Plaster houses with clay-tile roofs, a church with a spire on Church Hill, a keep and belfry on
Castle Ridge, a wooden quarter by the river, Linden Park with its bandstand, trees everywhere.
The terrain, forest and mountains around it come from lib/backdrop.py.

It returns the same `Town` object lib/town.py does, so shots keep using:

    town.marker("Cam_Town_Crane"), town.windows("Bakery"), town.props["Bread_1"],
    town.objects (names like "BakerHouse.Door", "Bakery.BakeryLight", "BakerBedroom.Mattress"),
    town.sky_anchors

Coordinates are the layout's plan studs: Roblox-style (x, y, z), mapped with town.rbx
(x, -z, y). Textures come from assets/ext (Poly Haven, CC0); a model dropped into
assets/ext/<folder>/ as .glb (the Sketchfab picks in assets/ext/LICENSES.md) replaces the
matching stand-in: loaf, linden, oak, cypress, fountain, gazebo.
"""
import math
import random
import time
import zlib
from pathlib import Path

import bmesh
import bpy
import yaml
from mathutils import Matrix, Vector, noise

from . import core
from .town import LOOK, V3, Town, _Builder, _font, lin, rbx, rgb

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "assets" / "ext"
LAYOUT = Path(__file__).with_name("town_layout.yaml")

UP = Vector((0, 0, 1))
FACING = {  # front normal and the along-facade axis (U, Up, N right-handed), in plan (x, z)
    "S": ((0, 1), (1, 0)), "N": ((0, -1), (-1, 0)), "E": ((1, 0), (0, -1)), "W": ((-1, 0), (0, 1)),
}


def P(x, y, z):
    return rbx(x, y, z)


def plan(x, z):
    """Plan (x, z) as a horizontal Blender vector."""
    return Vector((x, -z, 0))


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# --- terrain height (shared with lib/backdrop.py) ------------------------------------------------

GRASS = 0.05  # flat ground top in town


def ground(x, z, L=None):
    """Terrain height (Roblox y) at plan (x, z)."""
    L = L or layout()
    h = GRASS
    for hill in L["hills"]:
        dx = (x - hill["x"]) / hill.get("sx", 1)
        dz = (z - hill["z"]) / hill.get("sz", 1)
        d = math.hypot(dx, dz)
        lump = 1 + 0.08 * noise.noise(Vector((x * 0.02, z * 0.02, 3.1))) if d > hill["r0"] else 1
        h = max(h, GRASS + hill["h"] * lump * smooth(1 - (d - hill["r0"]) / (hill["r1"] - hill["r0"])))
    # wooded hills rising to the north, past the castle
    north = smooth((-z - 300) / 420)
    if north > 0:
        h = max(h, GRASS + north * (34 + 22 * noise.noise(Vector((x * 0.004, z * 0.004, 1.7)))))
    # gentle swells outside the town
    r = math.hypot(x, z * 0.8)
    out = smooth((r - 240) / 160)
    if out > 0:
        h += out * 4 * (1 + noise.noise(Vector((x * 0.01, z * 0.01, 0.4))))
    # rolling farmland and wooded hills on every other side, rising the further out they go,
    # so the land never stops at a hard edge (the south was empty before)
    far = smooth((r - 650) / 1400) * (1 - north)
    if far > 0:
        h += far * (55 + 45 * noise.noise(Vector((x * 0.0025, z * 0.0025, 6.2)))
                    + 12 * noise.noise(Vector((x * 0.012, z * 0.012, 2.9))))
    # the river
    rv = L["river"]
    dr = abs(x - rv["x"] - 6 * math.sin(z * 0.012))
    cut = smooth(1 - (dr - rv["width"] * 0.35) / (rv["width"] * 0.65))
    if cut > 0:
        h -= cut * rv["depth"]
    return h


_layout = None


def layout():
    global _layout
    if _layout is None:
        _layout = yaml.safe_load(LAYOUT.read_text(encoding="utf-8"))
    return _layout


# --- materials -----------------------------------------------------------------------------------

_mats = {}


def _img(path, color=True):
    im = bpy.data.images.load(str(path), check_existing=True)
    if not color:
        im.colorspace_settings.name = "Non-Color"
    return im


def _tex_files(folder):
    d = EXT / folder / "textures"
    if not d.is_dir():
        return {}
    out = {}
    for f in d.iterdir():
        for k in ("diff", "rough", "nor_gl", "alpha"):
            if f"_{k}_" in f.name:
                out[k] = f
    return out


def _sock(socks, name, kind="RGBA"):
    """Mix nodes have one socket per data type under each name; pick the colour one."""
    return next(x for x in socks if x.name == name and x.type == kind)


def _principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def tex_mat(name, folder, tile, tint=(1, 1, 1), rough=0.85, fallback=(0.6, 0.6, 0.6), bump=1.0, detail=False):
    """A Poly Haven texture set on the mesh's stud-unit UVs, `tile` studs per repeat, tinted.
    detail=True keeps only the texture's light and dark (grime, patches) over the tint colour, so
    one dirty plaster scan paints clean walls of any colour. Falls back to a flat colour when the
    textures are missing."""
    key = (name, folder, tile, tint, detail)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    files = _tex_files(folder)
    p.inputs["Roughness"].default_value = rough
    if not files:
        p.inputs["Base Color"].default_value = (*[a * b for a, b in zip(fallback, tint)], 1)
        _mats[key] = m
        return m
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    diff = nt.nodes.new("ShaderNodeTexImage")
    diff.image = _img(files["diff"])
    nt.links.new(mp.outputs["Vector"], diff.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if detail:
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.12, 0.42
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.72, 1.08
        nt.links.new(diff.outputs["Color"], bw.inputs[0])
        nt.links.new(bw.outputs[0], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], _sock(mix.inputs, "A"))
    else:
        nt.links.new(diff.outputs["Color"], _sock(mix.inputs, "A"))
    _sock(mix.inputs, "B").default_value = (*tint, 1)
    nt.links.new(_sock(mix.outputs, "Result"), p.inputs["Base Color"])
    if "rough" in files:
        r = nt.nodes.new("ShaderNodeTexImage")
        r.image = _img(files["rough"], color=False)
        nt.links.new(mp.outputs["Vector"], r.inputs["Vector"])
        nt.links.new(r.outputs["Color"], p.inputs["Roughness"])
    if "nor_gl" in files and bump > 0:
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = _img(files["nor_gl"], color=False)
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*tint, 1)
    _mats[key] = m
    return m


def flat(name, col, rough=0.7, emit=0.0):
    key = ("flat", name, col, rough, emit)
    if key not in _mats:
        m = core.mat(col, rough, emit=emit, name=name)
        _mats[key] = m
    return _mats[key]


def noisy(name, a, b, scale=0.4, rough=0.8, detail=4.0, coords="Object"):
    """Two colours mixed by noise: bark, grass, stone, leaves."""
    key = ("noisy", name, a, b, scale)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = _principled(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coords], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.35, 0.65
    ramp.color_ramp.elements[0].color = (*a, 1)
    ramp.color_ramp.elements[1].color = (*b, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*a, 1)
    _mats[key] = m
    return m


def leaves(name, a, b, c):
    """Foliage: three greens by noise, darker toward the bottom of the crown, a little
    light through the leaves."""
    key = ("leaf", name)
    if key in _mats:
        return _mats[key]
    m = noisy(name, a, b, scale=0.18, rough=0.9, detail=6.0)
    nt = m.node_tree
    p = _principled(m)
    ramp = next(n for n in nt.nodes if n.type == "VALTORGB")
    e = ramp.color_ramp.elements.new(0.85)
    e.color = (*c, 1)
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 4, 26
    mr.inputs["To Min"].default_value = 0.45
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], _sock(mul.inputs, "A"))
    nt.links.new(mr.outputs["Result"], _sock(mul.inputs, "B"))
    nt.links.new(_sock(mul.outputs, "Result"), p.inputs["Base Color"])
    p.inputs["Subsurface Weight"].default_value = 0.15
    p.inputs["Subsurface Radius"].default_value = (0.6, 1.0, 0.3)
    _mats[key] = m
    return m


def window_glass():
    """Window glass that lights up by time of day: each window carries a random number
    (`win_rand`, per face) and glows warm when it is below the `LitFraction` value, which
    lib/lighting.py keys per shot (0 by day and at dawn, some at dusk, more at night)."""
    key = ("windowglass",)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("WindowGlass")
    m.use_nodes = True
    nt = m.node_tree
    n, L = nt.nodes, nt.links.new
    p = _principled(m)
    p.inputs["Base Color"].default_value = (0.02, 0.028, 0.04, 1)
    p.inputs["Roughness"].default_value = 0.15
    p.inputs["Emission Color"].default_value = (1.0, 0.58, 0.26, 1)
    att = n.new("ShaderNodeAttribute")
    att.attribute_type, att.attribute_name = "GEOMETRY", "win_rand"
    frac = n.new("ShaderNodeValue")
    frac.name = frac.label = "LitFraction"
    frac.outputs[0].default_value = 0.0
    lt = n.new("ShaderNodeMath")
    lt.operation = "LESS_THAN"
    L(att.outputs["Fac"], lt.inputs[0])
    L(frac.outputs[0], lt.inputs[1])
    k = n.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 6.0
    L(lt.outputs[0], k.inputs[0])
    L(k.outputs[0], p.inputs["Emission Strength"])
    m.diffuse_color = (0.02, 0.028, 0.04, 1)
    _mats[key] = m
    return m


def plank_mat(name, col, plank=0.85):
    """Painted plank wood: vertical boards (each a slightly different shade), dark gaps between
    them, grain running along the boards, worn a little lighter at random."""
    key = ("planks", name, col)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    n, L = nt.nodes, nt.links.new
    p = _principled(m)
    uv = n.new("ShaderNodeUVMap")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(uv.outputs["UV"], sep.inputs[0])
    sc = n.new("ShaderNodeMath")
    sc.operation, sc.inputs[1].default_value = "DIVIDE", plank
    L(sep.outputs["X"], sc.inputs[0])
    idx = n.new("ShaderNodeMath")
    idx.operation = "FLOOR"
    L(sc.outputs[0], idx.inputs[0])
    fr = n.new("ShaderNodeMath")
    fr.operation = "FRACT"
    L(sc.outputs[0], fr.inputs[0])
    wn = n.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = "1D"
    L(idx.outputs[0], wn.inputs["W"])
    shade = n.new("ShaderNodeMapRange")
    shade.inputs["To Min"].default_value, shade.inputs["To Max"].default_value = 0.78, 1.12
    L(wn.outputs["Value"], shade.inputs["Value"])
    # grain: noise stretched along the boards
    comb = n.new("ShaderNodeCombineXYZ")
    gx = n.new("ShaderNodeMath")
    gx.operation, gx.inputs[1].default_value = "MULTIPLY", 9.0
    L(sep.outputs["X"], gx.inputs[0])
    gy = n.new("ShaderNodeMath")
    gy.operation, gy.inputs[1].default_value = "MULTIPLY", 0.7
    L(sep.outputs["Y"], gy.inputs[0])
    L(gx.outputs[0], comb.inputs["X"])
    L(gy.outputs[0], comb.inputs["Y"])
    L(idx.outputs[0], comb.inputs["Z"])
    grain = n.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 1.5
    grain.inputs["Detail"].default_value = 6
    L(comb.outputs[0], grain.inputs["Vector"])
    gr = n.new("ShaderNodeMapRange")
    gr.inputs["To Min"].default_value, gr.inputs["To Max"].default_value = 0.82, 1.08
    L(grain.outputs["Fac"], gr.inputs["Value"])
    # gaps: dark at each board's edges
    edge = n.new("ShaderNodeMapRange")
    edge.interpolation_type = "SMOOTHSTEP"
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.0, 0.06
    edge.inputs["To Min"].default_value = 0.25
    L(fr.outputs[0], edge.inputs["Value"])
    edge2 = n.new("ShaderNodeMapRange")
    edge2.interpolation_type = "SMOOTHSTEP"
    edge2.inputs["From Min"].default_value, edge2.inputs["From Max"].default_value = 1.0, 0.94
    edge2.inputs["To Min"].default_value = 0.25
    L(fr.outputs[0], edge2.inputs["Value"])
    k = n.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    L(shade.outputs["Result"], k.inputs[0])
    L(gr.outputs["Result"], k.inputs[1])
    k2 = n.new("ShaderNodeMath")
    k2.operation = "MULTIPLY"
    L(k.outputs[0], k2.inputs[0])
    L(edge.outputs["Result"], k2.inputs[1])
    k3 = n.new("ShaderNodeMath")
    k3.operation = "MULTIPLY"
    L(k2.outputs[0], k3.inputs[0])
    L(edge2.outputs["Result"], k3.inputs[1])
    tint = n.new("ShaderNodeMix")
    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    _sock(tint.inputs, "A").default_value = (*col, 1)
    comb2 = n.new("ShaderNodeCombineColor")
    for c in ("Red", "Green", "Blue"):
        L(k3.outputs[0], comb2.inputs[c])
    L(comb2.outputs[0], _sock(tint.inputs, "B"))
    L(_sock(tint.outputs, "Result"), p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.65
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    L(k3.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], p.inputs["Normal"])
    m.diffuse_color = (*col, 1)
    _mats[key] = m
    return m


DOOR_COLORS = [(96, 56, 34), (52, 78, 60), (62, 78, 104), (118, 42, 34), (70, 52, 40), (40, 66, 74)]


def palette(L):
    return [lin(c) for c in L["plaster"]]


class M:
    """The town's materials (built on first use)."""

    def __init__(self, L):
        self.L = L
        pl = palette(L)
        self.plaster = [tex_mat(f"Plaster_{i}", "white_plaster_rough_01" if i % 2 == 0 else "yellow_plaster", 14,
                                tint=col, rough=0.9, fallback=(1, 1, 1), bump=0.6, detail=True)
                        for i, col in enumerate(pl)]
        self.roof = tex_mat("RoofTiles", "clay_roof_tiles", 9, tint=(1.0, 0.92, 0.88), rough=0.8,
                            fallback=lin((180, 80, 50)))
        self.roof_dark = tex_mat("RoofTilesDark", "clay_roof_tiles", 9, tint=(0.55, 0.5, 0.5), rough=0.8,
                                 fallback=lin((120, 60, 45)))
        self.cobble = tex_mat("Cobbles", "cobblestone_square", 10, rough=0.85, fallback=lin((170, 160, 145)))
        self.stone = tex_mat("Stone", "white_plaster_rough_01", 10, tint=lin((168, 160, 146)), rough=0.9,
                             fallback=(1, 1, 1), bump=1.2, detail=True)
        self.ochre_stone = tex_mat("OchreStone", "yellow_plaster", 16, tint=lin((222, 178, 118)), rough=0.9,
                                   fallback=(1, 1, 1), detail=True)
        self.trim = flat("Trim", lin((236, 232, 220)), 0.6)
        self.wood = noisy("Wood", lin((98, 66, 42)), lin((72, 46, 30)), scale=1.2, rough=0.7)
        self.wood_dark = noisy("WoodDark", lin((60, 42, 30)), lin((42, 30, 22)), scale=1.2, rough=0.75)
        self.doors = [plank_mat(f"DoorPlanks_{i}", lin(c)) for i, c in enumerate(DOOR_COLORS)]
        self.door = self.doors[0]
        self.brass = flat("Brass", (0.78, 0.55, 0.22), 0.3)
        self.brass.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
        self.glass = window_glass()
        self.shutters = [noisy(f"Shutter_{i}", lin(c), tuple(x * 0.8 for x in lin(c)), scale=2.0, rough=0.6)
                         for i, c in enumerate(L["shutters"])]
        self.flowers = noisy("Flowers", lin((205, 40, 60)), lin((240, 140, 160)), scale=3.0, rough=0.8)
        self.slate = noisy("Slate", lin((70, 88, 92)), lin((52, 66, 70)), scale=0.3, rough=0.6)
        self.copper = noisy("Copper", lin((96, 140, 120)), lin((70, 110, 96)), scale=0.25, rough=0.5)
        self.gravel = noisy("Gravel", lin((196, 186, 165)), lin((168, 156, 134)), scale=2.0, rough=0.95)
        self.planks = noisy("Planks", lin((120, 92, 64)), lin((90, 66, 44)), scale=0.8, rough=0.85)
        self.log = noisy("Logs", lin((110, 80, 54)), lin((78, 55, 36)), scale=0.6, rough=0.85)
        self.water = flat("Water", lin((60, 90, 100)), 0.05)
        self.metal = flat("Iron", lin((30, 30, 32)), 0.4)
        self.lamp = flat("LampGlass", (1.0, 0.62, 0.3), 0.3, emit=6.0)
        self.hedge = leaves("Hedge", lin((52, 82, 38)), lin((70, 104, 46)), lin((88, 120, 56)))
        self.cloth = {}

    def awning(self, col):
        key = tuple(col)
        if key not in self.cloth:
            m = bpy.data.materials.new("Awning")
            m.use_nodes = True
            nt = m.node_tree
            p = _principled(m)
            tc = nt.nodes.new("ShaderNodeUVMap")
            w = nt.nodes.new("ShaderNodeTexWave")
            w.wave_profile = "SAW"
            w.inputs["Scale"].default_value = 0.6
            w.inputs["Distortion"].default_value = 0
            nt.links.new(tc.outputs["UV"], w.inputs["Vector"])
            rp = nt.nodes.new("ShaderNodeValToRGB")
            rp.color_ramp.interpolation = "CONSTANT"
            rp.color_ramp.elements[0].color = (*lin(col), 1)
            rp.color_ramp.elements[1].position = 0.5
            rp.color_ramp.elements[1].color = (0.85, 0.82, 0.75, 1)
            nt.links.new(w.outputs["Fac"], rp.inputs["Fac"])
            nt.links.new(rp.outputs["Color"], p.inputs["Base Color"])
            p.inputs["Roughness"].default_value = 0.9
            self.cloth[key] = m
        return self.cloth[key]


# --- mesh building -------------------------------------------------------------------------------

class MB:
    """Collects faces (Blender coordinates) with stud-unit UVs and a material each, then makes one
    mesh object. UVs are projected on each face's own plane, so textures keep their size."""

    def __init__(self):
        self.verts, self.faces = [], []

    def poly(self, pts, mat, uv_axes=None, rand=None):
        """rand: a per-face number (e.g. which windows light up), stored as `win_rand`."""
        pts = [Vector(p) for p in pts]
        if len(pts) < 3:
            return
        if rand is not None:
            self.rand = getattr(self, "rand", {})
            self.rand[len(self.faces)] = rand
        base = len(self.verts)
        self.verts += pts
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if n.length < 1e-9:
            n = UP.copy()
        n.normalize()
        if uv_axes is None:
            # u: horizontal along the face (or x on floors), v: up the face
            u = UP.cross(n)
            if u.length < 1e-4:
                u = Vector((1, 0, 0))
            u.normalize()
            v = n.cross(u)
        else:
            u, v = uv_axes
        uvs = [((p - pts[0]).dot(u), (p - pts[0]).dot(v)) for p in pts]
        # anchor UVs in world space so neighbouring faces line up
        o = pts[0]
        uvs = [(a + o.dot(u), b + o.dot(v)) for a, b in uvs]
        self.faces.append((list(range(base, base + len(pts))), uvs, mat))

    def box(self, c, ax, half, mat, mats=None):
        """A box at centre c with orthonormal axes ax (3 Vectors) and half sizes. mats: optional
        per-face materials {'+x','-x','+y','-y','+z','-z'}."""
        a, b, cz = (Vector(x) for x in ax)
        if a.cross(b).dot(cz) < 0:  # keep it right-handed so the faces point outward
            cz = -cz
        hx, hy, hz = half

        def V(i, j, k):
            return c + a * (i * hx) + b * (j * hy) + cz * (k * hz)
        faces = {
            "+x": [V(1, -1, -1), V(1, 1, -1), V(1, 1, 1), V(1, -1, 1)],
            "-x": [V(-1, -1, -1), V(-1, -1, 1), V(-1, 1, 1), V(-1, 1, -1)],
            "+y": [V(-1, 1, -1), V(-1, 1, 1), V(1, 1, 1), V(1, 1, -1)],
            "-y": [V(-1, -1, -1), V(1, -1, -1), V(1, -1, 1), V(-1, -1, 1)],
            "+z": [V(-1, -1, 1), V(1, -1, 1), V(1, 1, 1), V(-1, 1, 1)],
            "-z": [V(-1, -1, -1), V(-1, 1, -1), V(1, 1, -1), V(1, -1, -1)],
        }
        for k, pts in faces.items():
            self.poly(pts, (mats or {}).get(k, mat))

    def abox(self, lo, hi, mat):
        """Axis-aligned box between two Blender corners."""
        lo, hi = Vector(lo), Vector(hi)
        lo, hi = Vector(map(min, lo, hi)), Vector(map(max, lo, hi))
        self.box((lo + hi) / 2, (Vector((1, 0, 0)), Vector((0, 1, 0)), UP), (hi - lo) / 2, mat)

    def prism(self, c, r, h, n, mat, top=None, r_top=None, cap=True):
        """An n-sided upright prism (or frustum/pyramid with r_top) standing on c."""
        r_top = r if r_top is None else r_top
        lo = [c + Vector((math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r, 0)) for i in range(n)]
        hi = [c + Vector((math.cos(2 * math.pi * i / n) * r_top, math.sin(2 * math.pi * i / n) * r_top, h))
              for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            if r_top > 1e-4:
                self.poly([lo[i], lo[j], hi[j], hi[i]], mat)
            else:
                self.poly([lo[i], lo[j], c + Vector((0, 0, h))], top or mat)
        if cap:
            self.poly(list(reversed(lo)), mat)
            if r_top > 1e-4:
                self.poly(hi, top or mat)

    def build(self, name, smooth=False, centred=False):
        """centred: put the object's origin at the middle of its bounds (for parts a shot aims at)."""
        shift = Vector()
        if centred and self.verts:
            lo = Vector(map(min, *self.verts))
            hi = Vector(map(max, *self.verts))
            shift = (lo + hi) / 2
            self.verts = [v - shift for v in self.verts]
        me = bpy.data.meshes.new(name)
        mats = []
        idx = {}
        for _, _, m in self.faces:
            if m.name not in idx:
                idx[m.name] = len(mats)
                mats.append(m)
        me.from_pydata([tuple(v) for v in self.verts], [], [f for f, _, _ in self.faces])
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", [idx[m.name] for _, _, m in self.faces])
        if getattr(self, "rand", None):
            wr = me.attributes.new("win_rand", "FLOAT", "FACE")
            wr.data.foreach_set("value", [self.rand.get(i, 1.0) for i in range(len(self.faces))])
        uvl = me.uv_layers.new(name="UVMap")
        data = []
        for _, uvs, _ in self.faces:
            for u in uvs:
                data += u
        uvl.data.foreach_set("uv", data)
        me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        ob.location = shift
        return ob


# --- the building frame --------------------------------------------------------------------------

class Frame:
    """A building's local frame: u along the front (to the right seen from the street), h up from
    its base, k out of the front wall (negative = inside). Origin: centre of the front wall at the
    base. Converts to Blender points."""

    def __init__(self, spec, base):
        n, u = FACING[spec.get("face", "S")]
        self.n = plan(*n)
        self.u = plan(*u)
        self.w, self.d = spec["w"], spec["d"]
        cx, cz = spec["x"], spec["z"]
        self.o = plan(cx, cz) + self.n * (self.d / 2) + Vector((0, 0, base))

    def __call__(self, u, h, k=0.0):
        return self.o + self.u * u + UP * h + self.n * k

    def axes(self):
        return (self.u, UP, self.n)


def _quad(f, mb, u0, u1, h0, h1, k, mat):
    mb.poly([f(u0, h0, k), f(u1, h0, k), f(u1, h1, k), f(u0, h1, k)], mat)


def window_slots(length, floor_h0, avoid=None):
    """Window centres along a wall of the given length (avoid: (u0, u1) kept clear for a door)."""
    n = max(1, int((length - 3) // 7))
    step = length / n
    us = [-length / 2 + step * (i + 0.5) for i in range(n)]
    if avoid:
        us = [u for u in us if not (avoid[0] - 2.4 < u < avoid[1] + 2.4)]
    return us


class House:
    """A plaster town house: plinth, storeys of shuttered windows, a door with a stone step, a
    clay-tile gable roof with a chimney. Pieces the shots need stay separate objects: the glass
    (`<name>.Windows`, window=1) and the door (`<name>.Door`)."""

    WIN_W, WIN_H = 3.4, 5.0

    def __init__(self, ctx, spec):
        self.ctx, self.s = ctx, spec
        self.L = ctx.L
        self.m = ctx.m
        self.name = spec["name"]
        self.base = ground(spec["x"], spec["z"], self.L)
        self.f = Frame(spec, self.base)
        self.rng = random.Random(zlib.crc32(self.name.encode()))  # same town every build
        self.mb, self.glass, self.door = MB(), MB(), MB()

    @property
    def H(self):
        return 1.2 + self.s.get("floors", 2) * self.L["storey"]

    def wall_mat(self):
        return self.m.plaster[self.s.get("color", 0) % len(self.m.plaster)]

    def shell(self):
        f, mb, w, d, H = self.f, self.mb, self.s["w"], self.s["d"], self.H
        wall = self.wall_mat()
        mb.box(f(0, H / 2, -d / 2), f.axes(), (w / 2, H / 2, d / 2), wall,
               mats={"-y": self.m.stone})
        # plinth and cornice bands
        mb.box(f(0, 0.7, -d / 2), f.axes(), (w / 2 + 0.25, 0.75, d / 2 + 0.25), self.m.stone)
        mb.box(f(0, H - 0.3, -d / 2), f.axes(), (w / 2 + 0.3, 0.3, d / 2 + 0.3), self.m.trim)
        for i in range(1, self.s.get("floors", 2)):  # string course between floors
            mb.box(f(0, 1.2 + i * self.L["storey"], -d / 2), f.axes(), (w / 2 + 0.12, 0.15, d / 2 + 0.12), self.m.trim)

    def roof(self, pitch=40, overhang=1.2):
        f, mb, w, d, H = self.f, self.mb, self.s["w"], self.s["d"], self.H
        across = self.s.get("roof", "along") == "front"  # ridge runs front-to-back: gable faces the street
        t = math.tan(math.radians(pitch))
        mat = self.m.roof
        if not across:
            half = d / 2 + overhang
            rise = (d / 2) * t
            ridge_k, ridge_h = -d / 2, H + rise
            for sgn in (1, -1):  # front slope, back slope
                eave_k = -d / 2 + sgn * half
                eave_h = H - overhang * t
                a = f(-w / 2 - overhang, eave_h, eave_k)
                b = f(w / 2 + overhang, eave_h, eave_k)
                c = f(w / 2 + overhang, ridge_h, ridge_k)
                e = f(-w / 2 - overhang, ridge_h, ridge_k)
                self._slab(a, b, c, e, mat, sgn)
            for su in (-1, 1):  # gable walls
                mb.poly([f(su * w / 2, H, 0), f(su * w / 2, H, -d), f(su * w / 2, ridge_h, ridge_k)] if su > 0 else
                        [f(su * w / 2, H, -d), f(su * w / 2, H, 0), f(su * w / 2, ridge_h, ridge_k)], self.wall_mat())
            ridge = (f(0, ridge_h, ridge_k), self.f.u, w / 2 + overhang)
        else:
            half = w / 2 + overhang
            rise = (w / 2) * t
            ridge_h = H + rise
            for sgn in (1, -1):
                eave_u = sgn * half
                eave_h = H - overhang * t
                a = f(eave_u, eave_h, overhang)
                b = f(eave_u, eave_h, -d - overhang)
                c = f(0, ridge_h, -d - overhang)
                e = f(0, ridge_h, overhang)
                self._slab(a, b, c, e, mat, sgn)
            for kk in (0, -d):
                mb.poly([f(-w / 2, H, kk), f(w / 2, H, kk), f(0, ridge_h, kk)], self.wall_mat())
            # a round attic window in the street gable
            disc(self.glass, f(0, H + rise * 0.45, 0.04), f.u, 1.1, self.m.glass)
            ridge = (f(0, ridge_h, -d / 2), self.f.n, d / 2 + overhang)
        # ridge cap and a chimney
        c, ax, half_len = ridge
        mb.box(c + UP * 0.25, (ax, UP, ax.cross(UP)), (half_len, 0.3, 0.45), self.m.roof_dark)
        cu = self.rng.uniform(-0.3, 0.3) * (w if not across else d) * 0.5
        ck = -d * self.rng.uniform(0.3, 0.45) if not across else -d * self.rng.uniform(0.25, 0.75)
        cu = cu if not across else self.rng.choice((-1, 1)) * w * 0.22
        top = H + (rise if not across else rise * 0.6) + 3
        mb.box(f(cu, top - 4, ck), f.axes(), (1.1, 4.5, 1.1), self.m.plaster[0])
        mb.box(f(cu, top + 0.6, ck), f.axes(), (1.4, 0.3, 1.4), self.m.stone)
        self.roof_top = H + rise

    def _slab(self, a, b, c, e, mat, sgn):
        """A roof plane 0.6 thick, tiles running down the slope."""
        n = (b - a).cross(e - a).normalized()
        if n.z < 0:
            n = -n
        th = n * 0.6
        down = (a - e).normalized()
        along = (b - a).normalized()
        self.mb.poly([a + th, b + th, c + th, e + th] if sgn > 0 else [b + th, a + th, e + th, c + th], mat,
                     uv_axes=(along, -down))
        self.mb.poly([a, e, c, b], self.m.wood_dark)  # underside
        self.mb.poly([a, b, b + th, a + th], self.m.wood_dark)  # fascia
        self.mb.poly([b, c, c + th, b + th], self.m.wood_dark)
        self.mb.poly([e, a, a + th, e + th], self.m.wood_dark)

    def window(self, side, u, h0, wide=None, tall=None, shutters=True, box=False):
        """A window on a side ('front', 'back', 'left', 'right'): frame, sill, glass, shutters."""
        f, w, d = self.f, self.s["w"], self.s["d"]
        ww, wh = wide or self.WIN_W, tall or self.WIN_H
        # local axes for this wall: a = along the wall, k = out of it
        if side == "front":
            o, a, nrm = f(u, h0, 0), f.u, f.n
        elif side == "back":
            o, a, nrm = f(-u, h0, -d), -f.u, -f.n
        elif side == "left":
            o, a, nrm = f(-w / 2, h0, -d / 2 + u), f.n, -f.u
        else:
            o, a, nrm = f(w / 2, h0, -d / 2 - u), -f.n, f.u
        ax = (a, UP, nrm)
        # glass, set back into the wall
        g = o + nrm * 0.02 + UP * (wh / 2)
        self.glass.poly([g - a * ww / 2 - UP * wh / 2, g + a * ww / 2 - UP * wh / 2,
                         g + a * ww / 2 + UP * wh / 2, g - a * ww / 2 + UP * wh / 2], self.m.glass,
                        rand=self.rng.random())
        # frame (4 bars + a mullion and transom)
        tr = self.m.trim
        c = o + UP * (wh / 2) + nrm * 0.12
        self.mb.box(c + UP * (wh / 2 + 0.25), ax, (ww / 2 + 0.45, 0.25, 0.14), tr)
        self.mb.box(c - a * (ww / 2 + 0.22), ax, (0.22, wh / 2, 0.14), tr)
        self.mb.box(c + a * (ww / 2 + 0.22), ax, (0.22, wh / 2, 0.14), tr)
        self.mb.box(c, ax, (0.07, wh / 2, 0.06), tr)
        self.mb.box(c + UP * (wh * 0.18), ax, (ww / 2, 0.07, 0.06), tr)
        self.mb.box(o + UP * (-0.15) + nrm * 0.35, ax, (ww / 2 + 0.6, 0.15, 0.35), self.m.stone)  # sill
        if shutters and "shutters" in self.s:
            sm = self.m.shutters[self.s["shutters"] % len(self.m.shutters)]
            for sg in (-1, 1):
                ang = self.rng.uniform(0, 0.5) if self.rng.random() < 0.3 else 0.0
                hinge = o + a * sg * (ww / 2 + 0.45) + UP * (wh / 2) + nrm * 0.15
                dirv = (a * sg * math.cos(ang) + nrm * math.sin(ang)).normalized()
                sc = hinge + dirv * (ww / 4 + 0.05)
                self.mb.box(sc, (dirv, UP, UP.cross(dirv)),
                            (ww / 4, wh / 2 + 0.2, 0.08), sm)
        if box:  # flower box with flowers
            bc = o + nrm * 0.75 - UP * 0.6
            self.mb.box(bc, ax, (ww / 2 + 0.3, 0.45, 0.45), self.m.wood)
            for i in range(9):
                p = bc + a * self.rng.uniform(-ww / 2, ww / 2) + UP * (0.5 + self.rng.uniform(0, 0.4)) \
                    + nrm * self.rng.uniform(-0.25, 0.25)
                self.mb.prism(p, self.rng.uniform(0.35, 0.55), 0.6, 6, self.m.flowers, r_top=0.2)

    def windows(self, door_u=(-2.4, 2.4)):
        f, w, d, Ls = self.f, self.s["w"], self.s["d"], self.L["storey"]
        floors = self.s.get("floors", 2)
        flowers = self.s.get("flowers", False)
        for i in range(floors):
            h0 = 1.2 + i * Ls + (2.2 if i == 0 else 1.8)
            for u in window_slots(w, h0, door_u if i == 0 else None):
                self.window("front", u, h0, box=flowers and i == 1)
            for u in window_slots(w, h0):
                self.window("back", u, h0)
            if d >= 12:
                for u in window_slots(d * 0.8, h0):
                    self.window("left", u, h0)
                    self.window("right", u, h0)

    def entrance(self, u=0.0, step=True):
        f, mb = self.f, self.mb
        dw, dh = 4.0, 7.6
        h0 = (1.15 if step else 0.55) - self.base  # door sill on the step (or the street)
        self.door_leaf(u, h0, dw, dh)
        # stone surround and lintel
        mb.box(f(u - dw / 2 - 0.4, h0 + dh / 2, 0.2), f.axes(), (0.45, dh / 2 + 0.3, 0.25), self.m.stone)
        mb.box(f(u + dw / 2 + 0.4, h0 + dh / 2, 0.2), f.axes(), (0.45, dh / 2 + 0.3, 0.25), self.m.stone)
        mb.box(f(u, h0 + dh + 0.5, 0.25), f.axes(), (dw / 2 + 0.9, 0.5, 0.3), self.m.stone)
        if step:
            top = 1.15 - self.base
            mb.box(f(u, top / 2, 1.5), f.axes(), (3.4, top / 2, 1.5), self.m.stone)
        # a little lamp over the door
        return f(u, 0, 3.0)

    def door_leaf(self, u, h0, dw, dh, k=0.08):
        """The door: painted planks with two cross rails, iron hinge straps, a brass knob on a
        round rose and a keyhole plate. All one object (`<name>.Door`), so a shot can swap it."""
        f, d = self.f, self.door
        wood = self.m.doors[self.rng.randrange(len(self.m.doors))]
        d.box(f(u, h0 + dh / 2, k), f.axes(), (dw / 2, dh / 2, 0.1), wood)
        for hh in (dh * 0.22, dh * 0.78):  # cross rails
            d.box(f(u, h0 + hh, k + 0.14), f.axes(), (dw / 2 - 0.15, 0.28, 0.05), wood)
        for hh in (dh * 0.2, dh * 0.8):  # hinge straps on the left
            d.box(f(u - dw / 2 + 0.95, h0 + hh, k + 0.2), f.axes(), (0.85, 0.11, 0.03), self.m.metal)
            d.prism(f(u - dw / 2 + 1.75, h0 + hh, k + 0.2), 0.12, 0.06, 8, self.m.metal)
        kn = f(u + dw / 2 - 0.55, h0 + dh * 0.47, k + 0.12)
        out = f.n
        for i in range(10):  # the rose, a flat brass disc on the door
            a0, a1 = 2 * math.pi * i / 10, 2 * math.pi * (i + 1) / 10
            r = 0.22
            d.poly([kn, kn + (f.u * math.cos(a0) + UP * math.sin(a0)) * r,
                    kn + (f.u * math.cos(a1) + UP * math.sin(a1)) * r], self.m.brass)
        d.box(kn + out * 0.12, (f.u, UP, out), (0.05, 0.05, 0.12), self.m.brass)  # shank
        ball = kn + out * 0.3
        for i in range(8):  # the knob: a small faceted ball
            for j in range(4):
                a0, a1 = 2 * math.pi * i / 8, 2 * math.pi * (i + 1) / 8
                b0, b1 = math.pi * (j / 4 - 0.5), math.pi * ((j + 1) / 4 - 0.5)

                def pt(a, b):
                    return ball + (f.u * (math.cos(a) * math.cos(b)) + UP * (math.sin(a) * math.cos(b))
                                   + out * math.sin(b)) * 0.17
                d.poly([pt(a0, b0), pt(a1, b0), pt(a1, b1), pt(a0, b1)], self.m.brass)
        d.box(kn - UP * 0.42, (f.u, UP, out), (0.09, 0.2, 0.02), self.m.brass)  # keyhole plate
        d.box(kn - UP * 0.45 + out * 0.025, (f.u, UP, out), (0.025, 0.06, 0.01), self.m.metal)

    def awning(self, col, u0, u1):
        f = self.f
        a = f(u0, 9.0, 0.1)
        b = f(u1, 9.0, 0.1)
        c = f(u1, 7.2, 3.6)
        e = f(u0, 7.2, 3.6)
        self.mb.poly([e, c, b, a], self.m.awning(col), uv_axes=(f.u, (a - e).normalized()))
        self.mb.poly([a, b, c, e], self.m.awning(col), uv_axes=(f.u, (a - e).normalized()))
        # valance
        self.mb.poly([e, c, c - UP * 0.8, e - UP * 0.8], self.m.awning(col))

    def finish(self):
        b = self.ctx.b.into(self.name)
        body = self.mb.build(f"{self.name}.Body")
        b._link(body)
        if self.glass.faces:
            g = self.glass.build(f"{self.name}.Windows")
            b._link(g)
            g["window"] = 1
        if self.door.faces:
            dr = self.door.build(f"{self.name}.Door")
            b._link(dr)
        return body

    def build(self):
        self.shell()
        self.roof()
        self.windows()
        self.entrance()
        if "awning" in self.s:
            self.awning(self.s["awning"], -self.s["w"] / 2 + 0.6, self.s["w"] / 2 - 0.6)
        return self.finish()


class Bakery(House):
    """The bakery: a shop front with two wide display windows, an awning, the BAKERY sign and a
    warm light by the window (bakery_dark() switches it off)."""

    def windows(self, door_u=None):
        f, w, Ls = self.f, self.s["w"], self.L["storey"]
        for u in (-w / 4 - 1, w / 4 + 1):  # display windows (Window_1 sat at -w/4 - 1)
            self.window("front", u, 1.6, wide=7.5, tall=5.6, shutters=False)
        for u in window_slots(w, 0):
            self.window("front", u, 1.2 + Ls + 1.8, box=True)
            self.window("back", u, 1.2 + Ls + 1.8)
            self.window("back", u, 4.0)
        for u in window_slots(self.s["d"] * 0.8, 0):
            self.window("left", u, 1.2 + Ls + 1.8)
            self.window("right", u, 1.2 + Ls + 1.8)

    def build(self):
        super().build()
        f, w = self.f, self.s["w"]
        self.awning((150, 70, 45), -w / 2 + 0.8, -2.6)
        self.awning((150, 70, 45), 2.6, w / 2 - 0.8)
        b = self.ctx.b.into(self.name)
        # hanging sign on an iron bracket, perpendicular to the wall so it reads down the lane
        board_c = f(-w / 2 + 1.5, 13.0, 3.2)
        mb = MB()
        mb.box(f(-w / 2 + 1.5, 15.0, 1.7), f.axes(), (0.12, 0.12, 1.8), self.m.metal)
        mb.box(board_c, (f.n, UP, -f.u), (2.6, 1.3, 0.12), self.m.wood_dark)
        sign = mb.build("Bakery.Sign")
        b._link(sign)
        for sg in (1, -1):
            cu = bpy.data.curves.new("Bakery.Text", "FONT")
            cu.body = "BAKERY"
            cu.font = _font()
            cu.align_x, cu.align_y = "CENTER", "CENTER"
            cu.size = 0.95
            cu.extrude = 0.02
            t = bpy.data.objects.new("Bakery.Text", cu)
            t.data.materials.append(flat("SignText", lin((250, 225, 170)), 0.5))
            side = -f.u * sg  # each face of the board, read by someone looking at it
            t.matrix_basis = Matrix.Translation(board_c + side * 0.14) @ _basis(UP.cross(side), side)
            b._link(t)
        # the warm light in the shop (1 stud out from the left display window)
        lp = f(-w / 4 - 1, 4.4, 1.2)
        b.light(_cf_at(lp), 2, 18, (255, 200, 120), name="BakeryLight")
        # a bread table under the awning, loaves in rows
        tb = MB()
        u = w / 4 + 1
        top = 4.05 - self.base
        tb.box(f(u, top, 1.4), f.axes(), (3.4, 0.15, 1.0), self.m.wood)
        for su in (-3.1, 3.1):
            tb.box(f(u + su, (top + 1.15 - self.base) / 2, 1.4), f.axes(), (0.15, (top - 1.15 + self.base) / 2, 0.9),
                   self.m.wood)
        b._link(tb.build("Bakery.Table"))
        for i in range(10):
            loaf = self.ctx.loaf_copy("Bakery.Display")
            loaf.matrix_basis = Matrix.Translation(f(u - 2.6 + (i % 5) * 1.3, top + 0.15, 0.95 + (i // 5) * 0.9)) @ \
                Matrix.Rotation(math.radians(90 + self.rng.uniform(-15, 15)), 4, "Z") @ Matrix.Scale(0.48, 4)
            b._link(loaf)
        return self


def disc(mb, c, along, r, mat, n=16):
    """A flat round face standing upright on a wall: `along` runs across it, UP is up."""
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        mb.poly([c, c + (along * math.cos(a0) + UP * math.sin(a0)) * r,
                 c + (along * math.cos(a1) + UP * math.sin(a1)) * r], mat)


def _basis(x, z):
    """A 4x4 rotation whose local X is x and local Z is z (text faces +Z)."""
    x = Vector(x).normalized()
    z = Vector(z).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed().to_4x4()


def _cf_at(p):
    """Blender point -> the Roblox-space CFrame _Builder.light expects."""
    from .town import CF
    return CF(p.x, p.z, -p.y)


class TownHall(House):
    def build(self):
        super().build()
        f, w, d, H = self.f, self.s["w"], self.s["d"], self.H
        mb = MB()
        top = self.roof_top
        mb.box(f(0, top + 5, -d / 2), f.axes(), (4.5, 9, 4.5), self.m.plaster[1])
        mb.box(f(0, top + 14.3, -d / 2), f.axes(), (5.0, 0.4, 5.0), self.m.trim)
        mb.prism(f(0, top + 14.6, -d / 2), 6.2, 9, 4, self.m.copper, r_top=0.0)
        b = self.ctx.b.into(self.name)
        b._link(mb.build(f"{self.name}.ClockTower"))
        clock = MB()  # the clock face toward the square
        c = f(0, top + 9, -d / 2 + 4.6)
        disc(clock, c, f.u, 3.0, self.m.trim, n=24)
        clock.box(c + UP * 1.2 + f.n * 0.1, f.axes(), (0.12, 1.3, 0.05), self.m.metal)
        clock.box(c + f.u * 0.8 + f.n * 0.1, f.axes(), (0.9, 0.12, 0.05), self.m.metal)
        b._link(clock.build(f"{self.name}.Clock"))
        # columns either side of the door
        for u in (-4.2, 4.2):
            mb2 = MB()
            mb2.prism(f(u, 0.55 - self.base, 1.0), 0.6, 9, 12, self.m.trim)
            b._link(mb2.build(f"{self.name}.Column"))
        return self


class Church:
    """Nave with a steep roof and a front tower with belfry openings and a tall copper spire."""

    def __init__(self, ctx, spec):
        self.ctx, self.s, self.m = ctx, spec, ctx.m
        self.base = ground(spec["x"], spec["z"], ctx.L)
        self.f = Frame(spec, self.base)

    def build(self):
        f, s, m = self.f, self.s, self.m
        w, d = s["w"], s["d"]
        mb, glass = MB(), MB()
        wall = m.plaster[0]
        Hn = 22
        mb.box(f(0, Hn / 2, -d / 2 - 4), f.axes(), (w / 2, Hn / 2, d / 2 - 4), wall)
        mb.box(f(0, 0.8, -d / 2 - 4), f.axes(), (w / 2 + 0.3, 0.8, d / 2 - 3.7), m.stone)
        # steep nave roof
        t = math.tan(math.radians(52))
        rise = (w / 2) * t
        for sg in (1, -1):
            a = f(sg * (w / 2 + 1.2), Hn - 1.2 * t, -8)
            b = f(sg * (w / 2 + 1.2), Hn - 1.2 * t, -d - 1)
            c = f(0, Hn + rise, -d - 1)
            e = f(0, Hn + rise, -8)
            pts = [a, b, c, e] if sg > 0 else [b, a, e, c]
            mb.poly(pts, m.slate, uv_axes=((b - a).normalized(), (e - a).normalized()))
        mb.poly([f(-w / 2, Hn, -d), f(w / 2, Hn, -d), f(0, Hn + rise, -d)], wall)
        # tall arched windows along the nave
        for k in range(4):
            kk = -12 - k * 8.5
            for sg in (-1, 1):
                c = f(sg * (w / 2 + 0.02), 11, kk)
                nrm = f.u * sg
                along = f.n
                glass.poly([c - along * 1.4 - UP * 5, c + along * 1.4 - UP * 5, c + along * 1.4 + UP * 4,
                            c + UP * 5.4, c - along * 1.4 + UP * 4], m.glass)
                mb.box(c - UP * 5.3 + nrm * 0.3, (along, UP, nrm), (1.9, 0.2, 0.3), m.stone)
        # the tower
        tw = 11
        Ht = 48
        mb.box(f(0, Ht / 2, -tw / 2), f.axes(), (tw / 2, Ht / 2, tw / 2), wall)
        mb.box(f(0, 1, -tw / 2), f.axes(), (tw / 2 + 0.4, 1, tw / 2 + 0.4), m.stone)
        for hh in (16, 30, Ht):
            mb.box(f(0, hh - 0.3, -tw / 2), f.axes(), (tw / 2 + 0.35, 0.35, tw / 2 + 0.35), m.trim)
        # belfry openings on all four sides
        for side in range(4):
            ang = side * math.pi / 2
            nrm = (f.n * math.cos(ang) + f.u * math.sin(ang))
            along = UP.cross(nrm) * -1
            c = f(0, 0, -tw / 2) + nrm * (tw / 2 + 0.03) + UP * 38
            for off in (-2.2, 2.2):
                glass.poly([c + along * (off - 1.2) - UP * 4, c + along * (off + 1.2) - UP * 4,
                            c + along * (off + 1.2) + UP * 3.2, c + along * off + UP * 4.4,
                            c + along * (off - 1.2) + UP * 3.2], m.glass)
            disc(mb, f(0, 0, -tw / 2) + nrm * (tw / 2 + 0.05) + UP * 24, along, 2.6, m.trim)  # clock
        # the spire: octagonal drum, small onion, then a tall needle
        top = f(0, Ht, -tw / 2)
        mb.prism(top, tw * 0.62, 3, 8, m.copper, r_top=tw * 0.45)
        mb.prism(top + UP * 3, tw * 0.38, 5, 8, m.copper, r_top=tw * 0.5)
        mb.prism(top + UP * 8, tw * 0.5, 4, 8, m.copper, r_top=tw * 0.22)
        mb.prism(top + UP * 12, tw * 0.22, 3, 8, wall, r_top=tw * 0.22)
        mb.prism(top + UP * 15, tw * 0.3, 24, 8, m.copper, r_top=0.0)
        mb.prism(top + UP * 39, 0.12, 3.5, 6, flat("Gold", lin((230, 180, 70)), 0.3))
        # main door
        door = MB()
        door.box(f(0, 4.5, 0.1), f.axes(), (2.6, 4.5, 0.1), m.doors[0])
        for hh in (2.0, 7.0):
            door.box(f(0, hh, 0.24), f.axes(), (2.45, 0.3, 0.05), m.doors[0])
            door.box(f(-1.6, hh, 0.3), f.axes(), (0.9, 0.12, 0.03), m.metal)
            door.box(f(1.6, hh, 0.3), f.axes(), (0.9, 0.12, 0.03), m.metal)
        door.box(f(0, 4.5, 0.25), f.axes(), (0.04, 4.4, 0.04), m.metal)  # the meeting line of a double door
        mb.box(f(0, 9.6, 0.3), f.axes(), (3.6, 0.6, 0.35), m.stone)
        b = self.ctx.b.into(s["name"])
        b._link(mb.build("Church.Body"))
        g = glass.build("Church.Windows")
        g["window"] = 1
        b._link(g)
        b._link(door.build("Church.Door"))
        # steps down the front of the plateau are the stair alley (built by the town)
        return self


class Keep:
    """The castle keep (crenellated) or a belfry tower (pyramid tile roof), warm ochre stone."""

    def __init__(self, ctx, spec):
        self.ctx, self.s, self.m = ctx, spec, ctx.m
        self.base = ground(spec["x"], spec["z"], ctx.L) - 2
        self.f = Frame(spec, self.base)

    def build(self):
        f, s, m = self.f, self.s, self.m
        w, d = s["w"], s["d"]
        mb, glass = MB(), MB()
        tower = s.get("kind") == "tower"
        H = 46 if tower else 34
        mb.box(f(0, H / 2, -d / 2), f.axes(), (w / 2, H / 2, d / 2), m.ochre_stone)
        mb.box(f(0, 3, -d / 2), f.axes(), (w / 2 + 1, 3, d / 2 + 1), m.stone)
        if tower:
            mb.box(f(0, H, -d / 2), f.axes(), (w / 2 + 0.6, 0.5, d / 2 + 0.6), m.trim)
            mb.prism(f(0, H + 0.5, -d / 2), w * 0.78, 14, 4, m.roof, r_top=0.0)
        else:
            n = 5
            for side in range(4):
                for i in range(n):
                    t = -w / 2 + w * (i + 0.5) / n
                    if side == 0:
                        p = f(t, H + 1.3, 0)
                    elif side == 1:
                        p = f(t, H + 1.3, -d)
                    elif side == 2:
                        p = f(-w / 2, H + 1.3, -d / 2 + t)
                    else:
                        p = f(w / 2, H + 1.3, -d / 2 + t)
                    mb.box(p, f.axes(), (1.4, 1.3, 1.4), m.ochre_stone)
        # slit windows
        for hh in (12, 22, H - 6):
            for side, (a, nrm) in enumerate(((f.u, f.n), (-f.u, -f.n))):
                c = f(0, hh, 0 if side == 0 else -d) + nrm * 0.03
                glass.poly([c - a * 0.6 - UP * 2, c + a * 0.6 - UP * 2, c + a * 0.6 + UP * 2, c - a * 0.6 + UP * 2],
                           m.glass)
        b = self.ctx.b.into(s["name"])
        b._link(mb.build(f"{s['name']}.Body"))
        g = glass.build(f"{s['name']}.Windows")
        g["window"] = 1
        b._link(g)
        return self


class LogHouse(House):
    """A log house: horizontal log walls, corner log ends, a steep shingle roof."""

    def wall_mat(self):
        return self.m.log

    def shell(self):
        f, mb, w, d = self.f, self.mb, self.s["w"], self.s["d"]
        H = self.H
        # stacked logs: thin boxes so the walls read as courses
        n = int(H // 1.2)
        for i in range(n):
            h = 0.6 + i * 1.2
            r = 0.62
            mb.box(f(0, h, 0), f.axes(), (w / 2 + 0.8, r, r), self.m.log)
            mb.box(f(0, h, -d), f.axes(), (w / 2 + 0.8, r, r), self.m.log)
            mb.box(f(-w / 2, h + 0.6, -d / 2), f.axes(), (r, r, d / 2 + 0.8), self.m.log)
            mb.box(f(w / 2, h + 0.6, -d / 2), f.axes(), (r, r, d / 2 + 0.8), self.m.log)
        mb.box(f(0, H / 2, -d / 2), f.axes(), (w / 2 - 0.3, H / 2, d / 2 - 0.3), self.m.wood_dark)
        mb.box(f(0, 0.2, -d / 2), f.axes(), (w / 2 + 1.2, 0.6, d / 2 + 1.2), self.m.stone)

    @property
    def H(self):
        return 10.0

    def roof(self, pitch=48, overhang=1.8):
        keep = self.m.roof
        self.m.roof = self.m.wood_dark
        super().roof(pitch, overhang)
        self.m.roof = keep

    def windows(self, door_u=(-2.4, 2.4)):
        for u in (-self.s["w"] / 3, self.s["w"] / 3):
            self.window("front", u, 3.0, wide=2.6, tall=3.0, shutters=False, box=True)
        for u in window_slots(self.s["d"] * 0.7, 0):
            self.window("left", u, 3.0, wide=2.6, tall=3.0, shutters=False)
            self.window("right", u, 3.0, wide=2.6, tall=3.0, shutters=False)

    def entrance(self, u=0.0, step=True):
        f = self.f
        self.door_leaf(0, 0.0, 3.6, 7.2, k=0.65)
        self.mb.box(f(0, 0.8, 2.2), f.axes(), (3.2, 0.25, 1.8), self.m.planks)


KINDS = {"bakery": Bakery, "townhall": TownHall, "church": Church, "keep": Keep, "tower": Keep, "log": LogHouse}


# --- trees ---------------------------------------------------------------------------------------

TREES = {  # height, crown centre, crown radii (x, y, z), blobs, blob radius, trunk radius, greens
    "linden": dict(h=34, cz=21, cr=(12, 12, 12), n=12, br=5.5, tr=1.3,
                   g=((40, 72, 26), (62, 98, 36), (98, 128, 52))),
    "oak": dict(h=28, cz=17, cr=(15, 15, 9), n=13, br=5.2, tr=1.6, g=((38, 64, 24), (58, 88, 32), (90, 112, 46))),
    "cypress": dict(h=30, cz=15, cr=(3.2, 3.2, 14), n=10, br=3.0, tr=0.6, g=((24, 44, 22), (34, 60, 30), (52, 80, 40)),
                    column=True),
    "pine": dict(h=26, cz=22, cr=(11, 11, 3.5), n=9, br=4.0, tr=0.9, g=((30, 52, 30), (44, 70, 38), (66, 92, 50))),
    "birch": dict(h=24, cz=16, cr=(6, 6, 8), n=9, br=3.4, tr=0.6, g=((70, 104, 40), (100, 136, 56), (140, 168, 80)),
                  bark=((220, 220, 210), (60, 56, 52))),
    "willow": dict(h=22, cz=13, cr=(12, 12, 8), n=12, br=4.8, tr=1.4, g=((84, 112, 44), (112, 140, 58), (150, 170, 80)),
                   droop=True),
    "fruit": dict(h=12, cz=8, cr=(5.5, 5.5, 4), n=8, br=3.0, tr=0.6, g=((54, 88, 34), (78, 116, 46), (110, 140, 60))),
    "small": dict(h=13, cz=9, cr=(4.5, 4.5, 5), n=7, br=2.8, tr=0.55, g=((50, 84, 32), (74, 110, 44), (104, 136, 58))),
    "far": dict(h=18, cz=11, cr=(5, 5, 7), n=3, br=4.5, tr=0.8, g=((36, 58, 30), (50, 76, 38), (70, 96, 50)), low=True),
}
EXT_TREES = {"linden": "linden", "oak": "oak", "cypress": "cypress"}

# Game-style card trees: a bark trunk and branches carrying alpha leaf cards (sprites made by
# pipeline/make_leaf_cards.py from Poly Haven's shrub_03 leaves). Per kind: the leaf sprite, how
# many cards, card size (studs), branch count, and how the cards sit.
CARDS = {
    "linden": dict(tex="broad", n=320, size=5.6, branches=9),
    "oak": dict(tex="broad", n=340, size=6.0, branches=11),
    "small": dict(tex="broad", n=80, size=4.5, branches=6),
    "fruit": dict(tex="small", n=90, size=4.5, branches=7),
    "birch": dict(tex="small", n=120, size=4.5, branches=8),
    "willow": dict(tex="willow", n=300, size=5.8, branches=10, droop=True),
    "cypress": dict(tex="needle", n=280, size=4.0, branches=0, column=True),
    "pine": dict(tex="needle", n=260, size=5.0, branches=8, flat=True),
}
GEN = EXT / "generated"


def _blob(bm, center, r, seed, sub=2, droop=False):
    m = Matrix.Translation(center) @ Matrix.Diagonal((r, r, r * (1.35 if droop else 0.85), 1))
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0, matrix=m)
    for v in res["verts"]:
        d = v.co - center
        k = 1 + 0.32 * noise.noise(v.co * 0.28 + Vector((seed, seed * 0.7, 0)))
        v.co = center + d * k
    return res["verts"]


def leaf_mat(tex):
    """Alpha leaf cards: the sprite's colour (each tree a little different, from its random
    number), light through the leaves, fully transparent outside the leaves."""
    key = ("leafcard", tex)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"LeafCards_{tex}")
    m.use_nodes = True
    nt = m.node_tree
    n, L = nt.nodes, nt.links.new
    p = _principled(m)
    out = next(x for x in n if x.type == "OUTPUT_MATERIAL")
    img = n.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(str(GEN / f"leaf_{tex}.png"), check_existing=True)
    img.image.alpha_mode = "STRAIGHT"
    oi = n.new("ShaderNodeObjectInfo")
    hue = n.new("ShaderNodeHueSaturation")
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.47, 0.53
    L(oi.outputs["Random"], mr.inputs["Value"])
    L(mr.outputs["Result"], hue.inputs["Hue"])
    vr = n.new("ShaderNodeMapRange")
    vr.inputs["To Min"].default_value, vr.inputs["To Max"].default_value = 0.8, 1.1
    L(oi.outputs["Random"], vr.inputs["Value"])
    L(vr.outputs["Result"], hue.inputs["Value"])
    L(img.outputs["Color"], hue.inputs["Color"])
    L(hue.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.7
    tl = n.new("ShaderNodeBsdfTranslucent")
    L(hue.outputs["Color"], tl.inputs["Color"])
    lit = n.new("ShaderNodeMixShader")
    lit.inputs[0].default_value = 0.3
    L(p.outputs[0], lit.inputs[1])
    L(tl.outputs[0], lit.inputs[2])
    tr = n.new("ShaderNodeBsdfTransparent")
    cut = n.new("ShaderNodeMixShader")
    L(img.outputs["Alpha"], cut.inputs[0])
    L(tr.outputs[0], cut.inputs[1])
    L(lit.outputs[0], cut.inputs[2])
    L(cut.outputs[0], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    m.use_backface_culling = False
    _mats[key] = m
    return m


def _card_tree_mesh(kind, variant, m):
    """A game-style tree: tapered trunk and branches, and leaf cards spread over the crown."""
    p, c = TREES[kind], CARDS[kind]
    rng = random.Random(f"card{kind}{variant}")
    bm = bmesh.new()
    cx, cy, cz = p["cr"]
    top = p["h"] - (0 if c.get("column") else cz * 0.6)
    bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=p["tr"], radius2=p["tr"] * 0.35,
                          depth=top, matrix=Matrix.Translation((0, 0, top / 2)))
    tips = []
    for i in range(c["branches"]):  # main branches out to the crown
        a = 2 * math.pi * i / max(c["branches"], 1) + rng.uniform(-0.3, 0.3)
        h0 = p["cz"] - cz * rng.uniform(0.2, 0.75)
        out = Vector((math.cos(a) * cx, math.sin(a) * cy, rng.uniform(-0.1, 0.7) * cz)) * rng.uniform(0.55, 0.85)
        base = Vector((0, 0, h0))
        tip = Vector((0, 0, p["cz"])) + out
        d = tip - base
        rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=p["tr"] * 0.4, radius2=p["tr"] * 0.08,
                              depth=d.length, matrix=Matrix.Translation(base + d / 2) @ rot)
        tips.append(tip)
    for f in bm.faces:
        f.material_index = 0
        f.smooth = True
    nb = len(bm.faces)
    for i in range(c["n"]):  # leaf cards
        if c.get("column"):
            t = rng.random()
            a = rng.uniform(0, 2 * math.pi)
            r = cx * 1.3 * (1.1 - 0.75 * t) * rng.uniform(0.3, 1.0)
            pos = Vector((math.cos(a) * r, math.sin(a) * r, 2 + t * (p["h"] - 3)))
            outward = Vector((math.cos(a), math.sin(a), 0.35))
        else:
            while True:
                v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                if 0.15 < v.length <= 1:
                    break
            v = v.normalized() * (v.length ** 0.35)  # mostly towards the crown's surface
            if c.get("flat"):
                v.z *= 0.9
            pos = Vector((v.x * cx, v.y * cy, p["cz"] + v.z * cz))
            outward = v.normalized() if v.length > 1e-3 else Vector((0, 0, 1))
        size = c["size"] * rng.uniform(0.75, 1.2)
        if c.get("droop"):
            up = (Vector((0, 0, -1)) + outward * 0.3).normalized()  # hanging curtains
        elif c.get("flat"):
            up = (outward + Vector((0, 0, -0.2))).normalized()
        else:
            up = (outward + Vector((rng.uniform(-.4, .4), rng.uniform(-.4, .4), rng.uniform(-.2, .5)))).normalized()
        side = up.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized())
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        base = pos - up * size * 0.45  # the sprite's twig end points back into the crown
        verts = [bm.verts.new(base - side * size / 2), bm.verts.new(base + side * size / 2),
                 bm.verts.new(base + side * size / 2 + up * size), bm.verts.new(base - side * size / 2 + up * size)]
        f = bm.faces.new(verts)
        f.material_index = 1
    uv = bm.loops.layers.uv.new("UVMap")
    bm.faces.ensure_lookup_table()
    for f in bm.faces[nb:]:
        for loop, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = co
    me = bpy.data.meshes.new(f"CardTree_{kind}_{variant}")
    bm.to_mesh(me)
    bm.free()
    bark = p.get("bark", ((86, 66, 48), (54, 40, 30)))
    me.materials.append(noisy(f"Bark_{kind}", lin(bark[0]), lin(bark[1]), scale=1.5, rough=0.9))
    me.materials.append(leaf_mat(c["tex"]))
    return me


def _tree_mesh(kind, variant, m):
    """A stand-in tree: a tapered trunk with a few branches and a lumpy crown of blobs."""
    p = TREES[kind]
    rng = random.Random(f"{kind}{variant}")
    bm = bmesh.new()
    lw = 1 if p.get("low") else 2
    # trunk
    seg = 6 if p.get("low") else 10
    trunk_top = p["cz"] - (0 if p.get("column") else p["cr"][2] * 0.3)
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=p["tr"], radius2=p["tr"] * 0.45,
                                depth=trunk_top, matrix=Matrix.Translation((0, 0, trunk_top / 2)))
    for f in bm.faces:
        f.material_index = 0
    nb = len(bm.faces)
    # branches
    if not p.get("low") and not p.get("column"):
        for i in range(4):
            a = rng.uniform(0, 2 * math.pi)
            h0 = p["cz"] - p["cr"][2] * rng.uniform(0.3, 0.6)
            ln = p["cr"][0] * 0.6
            dirv = Vector((math.cos(a), math.sin(a), 0.8)).normalized()
            mid = Vector((0, 0, h0)) + dirv * ln / 2
            rot = dirv.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=p["tr"] * 0.45, radius2=p["tr"] * 0.15,
                                  depth=ln, matrix=Matrix.Translation(mid) @ rot)
    nb = len(bm.faces)
    # crown
    cx, cy, cz = p["cr"]
    for i in range(p["n"]):
        if p.get("column"):
            t = i / max(p["n"] - 1, 1)
            c = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), 3 + t * (p["h"] - 6)))
            r = p["br"] * (1.15 - 0.75 * t)
        else:
            while True:
                v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                if v.length <= 1:
                    break
            c = Vector((v.x * cx, v.y * cy, p["cz"] + v.z * cz))
            r = p["br"] * rng.uniform(0.8, 1.15)
            if p.get("droop"):
                c.z -= abs(v.x + v.y) * 2
        _blob(bm, c, r, i + variant * 10, sub=lw, droop=p.get("droop", False))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[nb:]:
        f.material_index = 1
        f.smooth = True
    me = bpy.data.meshes.new(f"Tree_{kind}_{variant}")
    bm.to_mesh(me)
    bm.free()
    bark = p.get("bark", ((86, 66, 48), (54, 40, 30)))
    me.materials.append(noisy(f"Bark_{kind}", lin(bark[0]), lin(bark[1]), scale=1.5, rough=0.9))
    me.materials.append(leaves(f"Leaves_{kind}", *[lin(c) for c in p["g"]]))
    return me


def _proto_collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        c.use_fake_user = True
    return c


def ext_model(folder, size, axis="height"):
    """Import assets/ext/<folder>/*.glb once into an unlinked collection, scaled so its height
    (or length) is `size` studs and standing on the origin. None when the file isn't there."""
    d = EXT / folder
    files = sorted(d.glob("**/*.glb")) + sorted(d.glob("**/*.gltf")) if d.is_dir() else []
    if not files:
        return None
    cname = f"EXT_{folder}"
    if cname in bpy.data.collections:
        return bpy.data.collections[cname]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(files[0]))
    new = [o for o in bpy.data.objects if o not in before]
    coll = _proto_collection(cname)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ext = hi - lo
    span = ext.z if axis == "height" else max(ext.x, ext.y)
    k = size / max(span, 1e-6)
    root = bpy.data.objects.new(f"{cname}_root", None)
    coll.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.matrix_world = Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation(
        (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    return coll


class Ctx:
    def __init__(self, town, L):
        self.town, self.L = town, L
        self.b = _Builder(town)
        self.m = M(L)
        self.tree_protos = {}
        self._loaf_me = None

    def tree(self, kind, variant):
        key = (kind, variant)
        if key not in self.tree_protos:
            ext = EXT_TREES.get(kind)
            coll = ext_model(ext, TREES[kind]["h"]) if ext else None
            if coll is None:
                cards = kind in CARDS and (GEN / f"leaf_{CARDS[kind]['tex']}.png").exists()
                make = _card_tree_mesh if cards else _tree_mesh  # card trees once the sprites exist
                coll = _proto_collection(f"Tree_{kind}_{variant}")
                ob = bpy.data.objects.new(f"Tree_{kind}_{variant}", make(kind, variant, self.m))
                coll.objects.link(ob)
            self.tree_protos[key] = coll
        return self.tree_protos[key]

    def place_tree(self, kind, x, z, scale=1.0, rot=None, owner="Trees", seed=0):
        rng = random.Random(f"{x:.1f},{z:.1f}")
        coll = self.tree(kind, rng.randrange(2))
        ob = bpy.data.objects.new(f"{owner}.{kind}", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = coll
        s = scale * rng.uniform(0.88, 1.12)
        ob.matrix_basis = Matrix.Translation(P(x, ground(x, z, self.L) - 0.3, z)) @ \
            Matrix.Rotation(rot if rot is not None else rng.uniform(0, 2 * math.pi), 4, "Z") @ Matrix.Scale(s, 4)
        self.b.into(owner)._link(ob)
        ob["tree"] = kind
        return ob

    def loaf_mesh(self):
        """The loaf: the Sketchfab model in assets/ext/loaf when present, else a scored crusty
        stand-in. 2.6 studs long, resting on its origin."""
        if self._loaf_me is not None:
            return self._loaf_me
        coll = ext_model("loaf", 2.6, axis="length")
        if coll is not None:
            obs = [o for o in coll.objects if o.type == "MESH"]
            dg = bpy.context.evaluated_depsgraph_get()
            bm = bmesh.new()
            for o in obs:
                tmp = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
                tmp.transform(o.matrix_world)
                bm.from_mesh(tmp)
                bpy.data.meshes.remove(tmp)
            me = bpy.data.meshes.new("Loaf")
            bm.to_mesh(me)
            bm.free()
            for mt in obs[0].data.materials:
                me.materials.append(mt)
            self._loaf_me = me
            return me
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
        for v in bm.verts:
            x, y, z = v.co
            z = max(z, -0.55)  # flat bottom
            score = 0.0
            if z > 0.2:  # three diagonal cuts across the top
                for c in (-0.5, 0.0, 0.5):
                    t = (x * 0.8 + y * 0.6) - c
                    score += math.exp(-(t / 0.07) ** 2) * 0.12
            k = 1 + 0.04 * noise.noise(Vector((x * 3, y * 3, z * 3)))
            v.co = Vector((x * 1.3 * k, y * 0.68 * k, (z + 0.55) * 0.62 * k - score))
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new("Loaf")
        bm.to_mesh(me)
        bm.free()
        m = bpy.data.materials.new("Crust")
        m.use_nodes = True
        nt = m.node_tree
        p = _principled(m)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 6
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "MULTIPLY_ADD"
        add.inputs[1].default_value = 0.35
        nt.links.new(nz.outputs["Fac"], add.inputs[0])
        nt.links.new(sep.outputs["Z"], add.inputs[2])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp
        cr.elements[0].position, cr.elements[0].color = 0.15, (*lin((214, 170, 110)), 1)
        cr.elements[1].position, cr.elements[1].color = 0.75, (*lin((120, 62, 26)), 1)
        e = cr.elements.new(0.5)
        e.color = (*lin((176, 104, 44)), 1)
        nt.links.new(add.outputs[0], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.65
        p.inputs["Subsurface Weight"].default_value = 0.1
        me.materials.append(m)
        self._loaf_me = me
        return me

    def loaf_copy(self, name):
        return bpy.data.objects.new(name, self.loaf_mesh())


# --- grounds, stairs, props ----------------------------------------------------------------------

def build_grounds(ctx):
    m = ctx.m
    mats = {"cobble": m.cobble, "gravel": m.gravel, "planks": m.planks}
    b = ctx.b.into("Ground")
    for name, kind, x0, z0, x1, z1, top in ctx.L["grounds"]:
        mb = MB()
        lo = P(min(x0, x1), -0.6, max(z0, z1))
        hi = P(max(x0, x1), top, min(z0, z1))
        mb.abox(lo, hi, mats[kind])
        ob = mb.build(f"Ground.{name}")
        b._link(ob)
    for st in ctx.L["stairs"]:
        mb = MB()
        n = 20
        z0, z1 = st["z0"], st["z1"]
        top0 = 0.55
        for i in range(n):
            za = z0 + (z1 - z0) * i / n
            zb = z0 + (z1 - z0) * (i + 1) / n
            h = top0 + st["rise"] * (i + 1) / n
            mb.abox(P(st["x"] - st["w"] / 2, -0.5, za), P(st["x"] + st["w"] / 2, h, zb), m.stone)
        # low walls either side
        for sx in (-1, 1):
            xw = st["x"] + sx * (st["w"] / 2 + 0.6)
            mb.abox(P(xw - 0.6, -0.5, z0), P(xw + 0.6, st["rise"] + 1.5, z1), m.stone)
        b._link(mb.build("Ground.ChurchStairs"))


def build_props(ctx):
    L, m = ctx.L, ctx.m
    pr = L["props"]
    # fountain (stand-in unless assets/ext/fountain has the Sketchfab model)
    fx, fz = pr["fountain"]
    b = ctx.b.into("TownSquare")
    ext = ext_model("fountain", 11)
    if ext is not None:
        ob = bpy.data.objects.new("TownSquare.Fountain", None)
        ob.instance_type, ob.instance_collection = "COLLECTION", ext
        ob.location = P(fx, 0.55, fz)
        b._link(ob)
    else:
        fountain(ctx, b, P(fx, 0.55, fz))
    # benches: the Poly Haven bench, else planks
    bench = _polyhaven_model("painted_wooden_bench")
    for i, (x, z, ang) in enumerate(pr["benches"]):
        if bench is not None:
            ob = bpy.data.objects.new(f"Props.Bench_{i}", None)
            ob.instance_type, ob.instance_collection = "COLLECTION", bench
            ob.matrix_basis = Matrix.Translation(P(x, 0.55 if abs(x) < 50 else ground(x, z, L) + 0.3, z)) @ \
                Matrix.Rotation(math.radians(ang), 4, "Z") @ Matrix.Scale(3.2, 4)
        else:
            mb = MB()
            mb.abox(P(x - 3.5, 1.6, z - 1), P(x + 3.5, 2.1, z + 1), m.wood)
            ob = mb.build(f"Props.Bench_{i}")
        ctx.b.into("Props")._link(ob)
    # market stalls
    for i, (x, z, col) in enumerate(pr["stalls"]):
        mb = MB()
        c = P(x, 0.55, z)
        for dx in (-3.2, 3.2):
            for dz in (-2.2, 2.2):
                mb.abox(c + Vector((dx - 0.2, dz - 0.2, 0)), c + Vector((dx + 0.2, dz + 0.2, 7.5)), m.wood)
        mb.abox(c + Vector((-3.4, -2.4, 3.0)), c + Vector((3.4, 2.4, 3.5)), m.wood)
        a, bb = c + Vector((-4, -3.2, 7.0)), c + Vector((4, -3.2, 7.0))
        cc, e = c + Vector((4, 3.0, 8.6)), c + Vector((-4, 3.0, 8.6))
        mb.poly([a, bb, cc, e], m.awning(col), uv_axes=(Vector((1, 0, 0)), (e - a).normalized()))
        mb.poly([bb, a, e, cc], m.awning(col), uv_axes=(Vector((1, 0, 0)), (e - a).normalized()))
        for j in range(4):  # crates of produce
            q = c + Vector((-2.4 + j * 1.6, 0.6, 3.5))
            mb.abox(q + Vector((-0.7, -0.9, 0)), q + Vector((0.7, 0.9, 0.7)), m.planks)
            mb.prism(q + Vector((0, 0, 0.7)), 0.6, 0.35, 8,
                     flat(f"Produce{j}", lin(((200, 60, 40), (230, 170, 50), (110, 150, 50), (180, 90, 140))[j])),
                     r_top=0.3)
        ctx.b.into("Props")._link(mb.build(f"Props.Stall_{i}"))
    # wall lanterns along the lane, street lamps around the square and park
    for i, (x, z) in enumerate(pr["lanterns"]):
        north = z < -60  # north-row facades look south (Blender -Y), south-row ones north
        out = Vector((0, -1, 0)) if north else Vector((0, 1, 0))
        base = P(x, 11.0, z)
        mb = MB()
        mb.abox(base - Vector((0.1, 0.1, 0)), base + Vector((0.1, 0.1, 0.15)) + out * 1.5, m.metal)
        lc = base + out * 1.5 - UP * 1.2
        mb.prism(lc, 0.55, 1.4, 4, m.lamp, r_top=0.7)
        mb.prism(lc + UP * 1.4, 0.8, 0.6, 4, m.metal, r_top=0.0)
        ob = mb.build(f"Props.Lantern_{i}")
        lb = ctx.b.into("Lanterns")
        lb._link(ob)
        lb.light(_cf_at(lc + UP * 0.7 + out * 0.3), 0.8, 16, (255, 190, 120), name=f"Lantern_{i}")
    for i, (x, z) in enumerate(pr["lamps"]):
        y = 0.55 if abs(x) < 50 and -30 < z < 48 else ground(x, z, L)
        c = P(x, y, z)
        mb = MB()
        mb.prism(c, 0.5, 0.8, 8, m.metal, r_top=0.35)
        mb.prism(c, 0.22, 11, 8, m.metal, r_top=0.16)
        mb.prism(c + UP * 11, 0.45, 1.6, 4, m.lamp, r_top=0.65)
        mb.prism(c + UP * 12.6, 0.8, 0.8, 4, m.metal, r_top=0.0)
        lb = ctx.b.into("Lamps")
        lb._link(mb.build(f"Props.Lamp_{i}"))
        lb.light(_cf_at(c + UP * 11.8), 0.7, 20, (255, 215, 160), name=f"LampLight_{i}")
    # the bandstand in Linden Park (shot 10)
    bx, bz = pr["bandstand"]
    ext = ext_model("gazebo", 16)
    gb = ctx.b.into("Bandstand")
    c = P(bx, ground(bx, bz, L), bz)
    mb = MB()
    mb.prism(c, 11, 3.2, 8, m.stone, top=m.planks, r_top=11)
    for i in range(3):  # steps toward the south (the camera side)
        mb.abox(c + Vector((-3, -11 - 1.4 * (i + 1), 0)), c + Vector((3, -11 - 1.4 * i, 3.2 - 1.05 * (i + 1))),
                m.stone)
    if ext is not None:
        ob = bpy.data.objects.new("Bandstand.Gazebo", None)
        ob.instance_type, ob.instance_collection = "COLLECTION", ext
        ob.location = c + UP * 3.2
        gb._link(ob)
    else:
        for i in range(8):
            a = 2 * math.pi * (i + 0.5) / 8
            p = c + Vector((math.cos(a) * 9.6, math.sin(a) * 9.6, 3.2))
            mb.prism(p, 0.45, 11, 8, m.trim, r_top=0.4)
            q = c + Vector((math.cos(a + math.pi / 8) * 9.6, math.sin(a + math.pi / 8) * 9.6, 3.2))
            if i != 5:  # leave the front (south, toward the steps) open
                rail_dir = Vector((-math.sin(a + math.pi / 8), math.cos(a + math.pi / 8), 0))
                mb.box(q + UP * 2.4, (rail_dir, UP, rail_dir.cross(UP)), (3.6, 0.15, 0.15), m.trim)
        mb.prism(c + UP * 14.2, 11.6, 0.6, 8, m.trim, r_top=11.6)
        mb.prism(c + UP * 14.8, 11.6, 6.5, 8, m.copper, r_top=0.0)
        mb.prism(c + UP * 21.3, 0.25, 2.0, 6, flat("Gold", lin((230, 180, 70)), 0.3))
    gb._link(mb.build("Bandstand.Body"))
    # pond and well
    px, pz, rx, rz = pr["pond"]
    mb = MB()
    c = P(px, ground(px, pz, L), pz)
    n = 24
    ring = [c + Vector((math.cos(2 * math.pi * i / n) * rx, math.sin(2 * math.pi * i / n) * rz, 0.15)) for i in range(n)]
    mb.poly(ring, m.water)
    for i in range(n):
        a, bb = ring[i], ring[(i + 1) % n]
        mid = (a + bb) / 2
        d = (bb - a)
        mb.box(mid + UP * 0.2 + (mid - c).normalized() * 0.6, (d.normalized(), UP, d.normalized().cross(UP)),
               (d.length / 2 + 0.4, 0.4, 0.6), m.stone)
    ctx.b.into("Park")._link(mb.build("Park.Pond"))
    wx, wz = pr["well"]
    mb = MB()
    c = P(wx, ground(wx, wz, L), wz)
    mb.prism(c, 2.4, 2.6, 12, m.stone, top=m.water, r_top=2.4)
    for sx in (-2.2, 2.2):
        mb.abox(c + Vector((sx - 0.2, -0.2, 2.6)), c + Vector((sx + 0.2, 0.2, 7.5)), m.wood)
    mb.box(c + UP * 8.2 + Vector((0, 0.9, 0)), (Vector((1, 0, 0)), Vector((0, 0.6, 0.8)).normalized(),
                                                Vector((0, -0.8, 0.6))), (3.0, 1.4, 0.15), m.wood_dark)
    mb.box(c + UP * 8.2 + Vector((0, -0.9, 0)), (Vector((1, 0, 0)), Vector((0, -0.6, 0.8)).normalized(),
                                                 Vector((0, -0.8, -0.6))), (3.0, 1.4, 0.15), m.wood_dark)
    ctx.b.into("WoodenQuarter")._link(mb.build("WoodenQuarter.Well"))
    # hedges
    for i, (x, z, w, d) in enumerate(pr["hedges"]):
        mb = MB()
        y = ground(x + w / 2, z + d / 2, L)
        mb.abox(P(x, y, z + d), P(x + w, y + 3.2, z), m.hedge)
        ctx.b.into("Park")._link(mb.build(f"Park.Hedge_{i}"))
    # Poly Haven shrubs along house fronts on the square and in the park
    shrub = _polyhaven_model("shrub_03")
    if shrub is not None:
        rng = random.Random(3)
        spots = [(-44, -26), (44, -26), (-44, 45), (44, 45), (85, 30), (160, 40), (100, -10), (-50, 34), (50, 2),
                 (130, 60), (-2, -88), (88, -60)]
        for i, (x, z) in enumerate(spots):
            ob = bpy.data.objects.new(f"Props.Shrub_{i}", None)
            ob.instance_type, ob.instance_collection = "COLLECTION", shrub
            ob.matrix_basis = Matrix.Translation(P(x, ground(x, z, L) + (0.5 if abs(x) < 50 else 0), z)) @ \
                Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Scale(rng.uniform(2.4, 3.4), 4)
            ctx.b.into("Props")._link(ob)


def water_mat():
    key = ("fountainwater",)
    if key not in _mats:
        m = bpy.data.materials.new("FountainWater")
        m.use_nodes = True
        p = _principled(m)
        p.inputs["Base Color"].default_value = (0.55, 0.75, 0.78, 1)
        p.inputs["Roughness"].default_value = 0.04
        p.inputs["IOR"].default_value = 1.33
        p.inputs["Transmission Weight"].default_value = 0.9
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
        _mats[key] = m
    return _mats[key]


def ring(mb, c, r_out, r_in, h0, h1, mat, n=32):
    """A round wall (basin rim): outer and inner faces and a flat top."""
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        o0 = Vector((math.cos(a0), math.sin(a0), 0))
        o1 = Vector((math.cos(a1), math.sin(a1), 0))
        mb.poly([c + o0 * r_out + UP * h0, c + o1 * r_out + UP * h0, c + o1 * r_out + UP * h1,
                 c + o0 * r_out + UP * h1], mat)
        mb.poly([c + o1 * r_in + UP * h0, c + o0 * r_in + UP * h0, c + o0 * r_in + UP * h1,
                 c + o1 * r_in + UP * h1], mat)
        mb.poly([c + o0 * r_out + UP * h1, c + o1 * r_out + UP * h1, c + o1 * r_in + UP * h1,
                 c + o0 * r_in + UP * h1], mat)


def fountain(ctx, b, c):
    """A round town fountain: a stone basin with a moulded rim, a pedestal with two bowls and a
    finial, water standing in the basin and bowls, and thin sheets of water falling from the bowls."""
    m, mb, wt = ctx.m, MB(), MB()
    ring(mb, c, 9.0, 8.0, 0.0, 1.9, m.stone)
    ring(mb, c, 9.4, 7.7, 1.9, 2.3, m.trim)  # rim moulding
    mb.prism(c, 8.0, 0.4, 32, m.stone)  # basin floor
    mb.prism(c + UP * 0.4, 1.8, 0.8, 16, m.stone, r_top=1.5)
    mb.prism(c + UP * 1.2, 1.1, 4.2, 16, m.stone, r_top=0.8)  # pedestal
    for h, r in ((5.4, 3.6), (8.6, 1.9)):  # the bowls, wide and shallow
        mb.prism(c + UP * (h - 0.9), 0.7, 0.9, 16, m.stone, r_top=r)
        ring(mb, c, r + 0.25, r - 0.2, h, h + 0.35, m.trim, n=24)
        wt.prism(c + UP * (h + 0.15), r - 0.2, 0.05, 24, water_mat())
        # water falling from the bowl's rim into what is below it
        below = 1.5 if h < 6 else 5.75
        n = 32
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            p0 = Vector((math.cos(a0), math.sin(a0), 0)) * (r + 0.3)
            p1 = Vector((math.cos(a1), math.sin(a1), 0)) * (r + 0.3)
            q0 = Vector((math.cos(a0), math.sin(a0), 0)) * (r + 0.75)
            q1 = Vector((math.cos(a1), math.sin(a1), 0)) * (r + 0.75)
            wt.poly([c + q0 + UP * below, c + q1 + UP * below, c + p1 + UP * (h + 0.3), c + p0 + UP * (h + 0.3)],
                    water_mat())
    mb.prism(c + UP * 8.95, 0.35, 1.2, 12, m.stone, r_top=0.25)
    mb.prism(c + UP * 10.15, 0.55, 0.7, 12, m.trim, r_top=0.0)
    wt.prism(c + UP * 1.5, 7.95, 0.05, 32, water_mat())  # basin water, just under the rim
    b._link(mb.build("TownSquare.Fountain"))
    b._link(wt.build("TownSquare.FountainWater"))


def pot(ctx, owner, x, z, size=1.0, kind=0):
    """A terracotta pot with a leafy plant and flowers on top."""
    m = ctx.m
    y = ground(x, z, ctx.L)
    y = max(y, 0.55 if abs(x) < 100 and -72 < z < 48 else y)
    if -72 <= z <= -62 and abs(x) <= 100:
        y = 0.9  # the lane's raised sidewalk
    c = P(x, y, z)
    mb = MB()
    clay = noisy("Terracotta", lin((176, 92, 56)), lin((150, 76, 46)), scale=2, rough=0.8)
    mb.prism(c, 0.9 * size, 1.6 * size, 12, clay, r_top=1.2 * size, cap=True)
    ring(mb, c, 1.32 * size, 1.05 * size, 1.6 * size, 1.85 * size, clay, n=12)
    mb.prism(c + UP * 1.5 * size, 1.05 * size, 0.1, 12, noisy("Soil", lin((60, 44, 30)), lin((44, 32, 22))))
    rng = random.Random(f"pot{x},{z}")
    cols = ((205, 40, 60), (240, 140, 170), (150, 70, 170), (250, 210, 80), (245, 245, 235))
    flower = noisy(f"Bloom{kind % 5}", lin(cols[kind % 5]), tuple(v * 0.85 for v in lin(cols[kind % 5])), scale=4)
    for i in range(7):
        p_ = c + Vector((rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), 0)) * size + UP * (1.9 + rng.uniform(0, 1.2)) * size
        mb.prism(p_, rng.uniform(0.3, 0.5) * size, 0.45 * size, 6, flower, r_top=0.15 * size)
    ob = mb.build(f"{owner}.Pot")
    ctx.b.into(owner)._link(ob)
    # a little leafy bush from the leaf cards
    if (GEN / "leaf_small.png").exists():
        lm = MB()
        for i in range(10):
            a = rng.uniform(0, 2 * math.pi)
            up = Vector((math.cos(a) * 0.6, math.sin(a) * 0.6, 1)).normalized()
            side = Vector((-math.sin(a), math.cos(a), 0))
            s = rng.uniform(1.6, 2.4) * size
            base = c + UP * 1.4 * size
            lm.poly([base - side * s / 2, base + side * s / 2, base + side * s / 2 + up * s, base - side * s / 2 + up * s],
                    leaf_mat("small"), uv_axes=None)
        lo = lm.build(f"{owner}.PotLeaves")
        _square_uvs(lo)
        ctx.b.into(owner)._link(lo)


def _square_uvs(ob):
    """0-1 UVs per quad (leaf cards built with MB)."""
    uvl = ob.data.uv_layers.active
    for poly in ob.data.polygons:
        for li, co in zip(poly.loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
            uvl.data[li].uv = co


def bike(ctx, x, z, ang):
    """A town bicycle leaning on its stand: two spoked wheels, a diamond frame, saddle, bars."""
    m = ctx.m
    y = 0.9 if -72 <= z <= -62 and abs(x) <= 100 else (0.55 if abs(x) < 100 and -72 < z < 48 else ground(x, z, ctx.L))
    rng = random.Random(f"bike{x}{z}")
    paint = flat(f"BikePaint{int(ang) % 4}", lin(((40, 70, 120), (130, 30, 30), (40, 90, 60), (30, 30, 34))[int(ang) % 4]), 0.35)
    mb = MB()
    R, wb = 1.25, 3.4  # wheel radius and wheelbase, studs
    rot = Matrix.Rotation(math.radians(ang), 3, "Z") @ Matrix.Rotation(math.radians(8), 3, "X")  # leaning a little
    o = P(x, y, z)

    def W(px, pz):  # bike-local (along, up) -> world
        return o + rot @ Vector((px, 0, pz))
    for cx_ in (-wb / 2, wb / 2):
        hub = (cx_, R)
        n = 20
        for i in range(n):  # tyre
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            p0 = W(hub[0] + math.cos(a0) * R, hub[1] + math.sin(a0) * R)
            p1 = W(hub[0] + math.cos(a1) * R, hub[1] + math.sin(a1) * R)
            d = (p1 - p0)
            mb.box((p0 + p1) / 2, (d.normalized(), rot @ Vector((0, 1, 0)), d.normalized().cross(rot @ Vector((0, 1, 0)))),
                   (d.length / 2 + 0.02, 0.09, 0.09), m.metal)
        for i in range(8):  # spokes
            a = math.pi * i / 8
            p0 = W(hub[0] - math.cos(a) * R, hub[1] - math.sin(a) * R)
            p1 = W(hub[0] + math.cos(a) * R, hub[1] + math.sin(a) * R)
            d = p1 - p0
            mb.box((p0 + p1) / 2, (d.normalized(), rot @ Vector((0, 1, 0)), d.normalized().cross(rot @ Vector((0, 1, 0)))),
                   (d.length / 2, 0.02, 0.02), flat("Spoke", (0.6, 0.6, 0.62), 0.3))

    def tube(a, b_, r=0.07, mat=paint):
        pa, pb = W(*a), W(*b_)
        d = pb - pa
        mb.box((pa + pb) / 2, (d.normalized(), rot @ Vector((0, 1, 0)), d.normalized().cross(rot @ Vector((0, 1, 0)))),
               (d.length / 2, r, r), mat)
    bb, seat, head = (-0.2, R), (-0.6, 2.6), (1.1, 2.55)
    tube((-wb / 2, R), bb)
    tube((-wb / 2, R), seat)
    tube(bb, seat)
    tube(bb, head)
    tube(seat, head)
    tube(head, (wb / 2, R))
    tube(seat, (-0.65, 3.0), 0.05, m.metal)
    mb.box(W(-0.7, 3.05), (rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, 1))), (0.45, 0.2, 0.08),
           flat("Saddle", (0.05, 0.03, 0.02), 0.6))
    tube(head, (1.0, 3.3), 0.05, m.metal)
    mb.box(W(1.0, 3.3), (rot @ Vector((0, 1, 0)), rot @ Vector((1, 0, 0)), rot @ Vector((0, 0, 1))), (0.8, 0.05, 0.05), m.metal)
    if rng.random() < 0.6:  # a front basket
        mb.box(W(1.7, 3.0), (rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), rot @ Vector((0, 0, 1))), (0.45, 0.4, 0.35),
               m.planks)
    ctx.b.into("Props")._link(mb.build("Props.Bike"))


def hang_sign(ctx, spec, text, height=11.0, color=(70, 52, 36)):
    """A board on an iron bracket, out from a building's front at its right corner, lettered on
    both faces so it reads from either way along the street."""
    f = Frame(spec, ground(spec["x"], spec["z"], ctx.L))
    m, w = ctx.m, spec["w"]
    u = w / 2 - 1.2
    board_c = f(u, height, 2.9)
    mb = MB()
    mb.box(f(u, height + 2.0, 1.6), f.axes(), (0.1, 0.1, 1.7), m.metal)
    mb.box(board_c, (f.n, UP, -f.u), (2.3, 1.1, 0.1), flat(f"SignBoard{color}", lin(color), 0.6))
    b = ctx.b.into(spec["name"])
    b._link(mb.build(f"{spec['name']}.Sign"))
    for sg in (1, -1):
        cu = bpy.data.curves.new(f"{spec['name']}.SignText", "FONT")
        cu.body = text
        cu.font = _font()
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.size = min(0.95, 3.6 / max(len(text), 1))
        cu.extrude = 0.02
        t = bpy.data.objects.new(f"{spec['name']}.SignText", cu)
        t.data.materials.append(flat("SignText", lin((250, 225, 170)), 0.5))
        side = -f.u * sg
        t.matrix_basis = Matrix.Translation(board_c + side * 0.12) @ _basis(UP.cross(side), side)
        b._link(t)


def wall_sign(ctx, spec, text, height=None, color=(40, 50, 60)):
    """Lettering on a board flat on the front wall, above the door (TOWN HALL, shop names)."""
    f = Frame(spec, ground(spec["x"], spec["z"], ctx.L))
    h = height or 9.6
    mb = MB()
    width = min(spec["w"] - 3, 1.0 * len(text) + 2)
    mb.box(f(0, h, 0.15), f.axes(), (width / 2, 0.85, 0.12), flat(f"WallSign{color}", lin(color), 0.5))
    b = ctx.b.into(spec["name"])
    b._link(mb.build(f"{spec['name']}.WallSign"))
    cu = bpy.data.curves.new(f"{spec['name']}.WallText", "FONT")
    cu.body = text
    cu.font = _font()
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.size = min(1.1, (width - 1) / max(len(text) * 0.62, 1))
    cu.extrude = 0.02
    t = bpy.data.objects.new(f"{spec['name']}.WallText", cu)
    t.data.materials.append(flat("SignGold", lin((230, 190, 100)), 0.35))
    t.matrix_basis = Matrix.Translation(f(0, h, 0.3)) @ _basis(f.u, f.n)
    b._link(t)


def build_details(ctx):
    """Flower pots, bicycles, shop signs, more lamps: the lived-in layer (layout `details:`)."""
    L = ctx.L
    d = L.get("details", {})
    specs = {s["name"]: s for s in L["buildings"]}
    for i, it in enumerate(d.get("pots", [])):
        pot(ctx, "Details", it[0], it[1], it[2] if len(it) > 2 else 1.0, kind=i)
    for x, z, ang in d.get("bikes", []):
        bike(ctx, x, z, ang)
    for name, text in d.get("hang_signs", {}).items():
        hang_sign(ctx, specs[name], text)
    for name, text in d.get("wall_signs", {}).items():
        wall_sign(ctx, specs[name], text)
    m = ctx.m
    for i, (x, z) in enumerate(d.get("lamps", [])):
        y = 0.9 if -72 <= z <= -62 and abs(x) <= 100 else (0.55 if abs(x) < 100 and -72 < z < 48 else ground(x, z, L))
        c = P(x, y, z)
        mb = MB()
        mb.prism(c, 0.5, 0.8, 8, m.metal, r_top=0.35)
        mb.prism(c, 0.22, 11, 8, m.metal, r_top=0.16)
        mb.prism(c + UP * 11, 0.45, 1.6, 4, m.lamp, r_top=0.65)
        mb.prism(c + UP * 12.6, 0.8, 0.8, 4, m.metal, r_top=0.0)
        lb = ctx.b.into("Lamps")
        lb._link(mb.build(f"Props.LaneLamp_{i}"))
        lb.light(_cf_at(c + UP * 11.8), 0.7, 20, (255, 215, 160), name=f"LaneLampLight_{i}")


_ph = {}


def _polyhaven_model(name):
    """Append a Poly Haven model's objects from its .blend into an unlinked collection."""
    if name in _ph:
        return _ph[name]
    f = EXT / name / f"{name}_2k.blend"
    if not f.exists():
        _ph[name] = None
        return None
    with bpy.data.libraries.load(str(f), link=False) as (src, dst):
        dst.objects = list(src.objects)
    coll = _proto_collection(f"PH_{name}")
    for o in dst.objects:
        if o is not None and o.type in ("MESH", "EMPTY"):
            coll.objects.link(o)
    for im in bpy.data.images:  # re-point textures that were relative to the .blend we appended from
        if im.filepath and not Path(bpy.path.abspath(im.filepath)).exists():
            cand = EXT / name / "textures" / Path(im.filepath.replace("\\", "/")).name
            if cand.exists():
                im.filepath = str(cand)
    _ph[name] = coll
    return coll


# --- EP01 extras: props, the Baker's bedroom set, sky anchors, markers ---------------------------

BEDROOM = (700, 520)  # an open set far from town (shot 14 films it through its window)


def build_extras(ctx):
    from .town import CF
    b, t = ctx.b, ctx.town
    pr = b.into("Props")
    for i, x in enumerate((-45, -15, 15, 45), 1):  # on the doorsteps; hidden until a shot shows them
        ob = ctx.loaf_copy(f"Bread_{i}")
        ob.matrix_basis = Matrix.Translation(P(x + 1.6, 1.15, -70.4)) @ Matrix.Rotation(math.radians(80 + 9 * i), 4,
                                                                                        "Z")
        pr._link(ob)
        ob.hide_render = ob.hide_viewport = True
        t.props[f"Bread_{i}"] = ob
    parked = P(0, -60, 0)
    basket = MB()
    basket.prism(Vector((0, 0, 0)), 0.9, 0.9, 12, ctx.m.planks, r_top=1.1)
    bo = basket.build("Basket")
    bo.location = parked
    pr._link(bo)
    for i in range(3):  # loaves in the basket
        lo = ctx.loaf_copy("Basket.Loaf")
        lo.parent = bo
        lo.matrix_parent_inverse = Matrix.Identity(4)
        lo.matrix_basis = Matrix.Translation((-0.4 + i * 0.4, 0, 0.75)) @ Matrix.Rotation(1.57 + i * 0.4, 4, "Z") @ \
            Matrix.Scale(0.42, 4)
        pr._link(lo)
    t.props["Basket"] = bo
    # the bread for shot 16: a loaf in a paper sleeve, carried in one hand
    bag = MB()
    bag.box(Vector((0, 0, 0.6)), (Vector((1, 0, 0)), Vector((0, 1, 0)), UP), (0.45, 0.35, 0.6),
            flat("Paper", lin((222, 200, 160)), 0.85))
    bgo = bag.build("BreadBag")
    bgo.location = parked + Vector((0, 2, 0))
    pr._link(bgo)
    lo = ctx.loaf_copy("BreadBag.Loaf")
    lo.parent = bgo
    lo.matrix_basis = Matrix.Translation((0, 0, 0.75)) @ Matrix.Rotation(math.radians(80), 4, "Y") @ \
        Matrix.Scale(0.5, 4)
    pr._link(lo)
    t.props["BreadBag"] = bgo
    ph = MB()
    ph.box(Vector((0, 0, 0)), (Vector((1, 0, 0)), Vector((0, 1, 0)), UP), (0.1, 0.275, 0.5),
           flat("PhoneGlass", (0.01, 0.01, 0.012), 0.1))
    pho = ph.build("Phone")
    pho.location = parked + Vector((0, 4, 0))
    pr._link(pho)
    t.props["Phone"] = pho

    # the Baker's bedroom (same set as before, moved off the map)
    cx, cz = BEDROOM
    rm = b.into("BakerBedroom")
    m = ctx.m

    def part(name, lo, hi, mat):
        mb = MB()
        mb.abox(P(lo[0], lo[1], hi[2]), P(hi[0], hi[1], lo[2]), mat)
        ob = mb.build(f"BakerBedroom.{name}", centred=True)
        rm._link(ob)
        return ob
    inside = m.plaster[0]
    gy = ground(cx, cz, ctx.L)
    floor_y = gy
    part("Floor", (cx - 10, floor_y - 0.5, cz - 8), (cx + 10, floor_y + 0.5, cz + 8), m.planks)
    part("BackWall", (cx - 10, floor_y, cz - 8), (cx + 10, floor_y + 14, cz - 7), inside)
    part("LeftWall", (cx - 10, floor_y, cz - 8), (cx - 9, floor_y + 14, cz + 8), inside)
    part("RightWall", (cx + 9, floor_y, cz - 8), (cx + 10, floor_y + 14, cz + 8), inside)
    part("Ceiling", (cx - 10, floor_y + 14, cz - 8), (cx + 10, floor_y + 15, cz + 8), inside)
    fz = cz + 7.5
    wall = m.plaster[4]
    part("FrontLeft", (cx - 10, floor_y, fz - 0.5), (cx - 3.5, floor_y + 14, fz + 0.5), wall)
    part("FrontRight", (cx + 3.5, floor_y, fz - 0.5), (cx + 10, floor_y + 14, fz + 0.5), wall)
    part("FrontBelow", (cx - 3.5, floor_y, fz - 0.5), (cx + 3.5, floor_y + 4, fz + 0.5), wall)
    part("FrontAbove", (cx - 3.5, floor_y + 9, fz - 0.5), (cx + 3.5, floor_y + 14, fz + 0.5), wall)
    part("WindowSill", (cx - 3.8, floor_y + 3.9, fz - 0.6), (cx + 3.8, floor_y + 4.3, fz + 1.0), m.trim)
    part("BedFrame", (cx - 3.5, floor_y + 0.5, cz - 4.5), (cx + 3.5, floor_y + 1.9, cz - 0.5), m.wood)
    part("Mattress", (cx - 3.3, floor_y + 1.9, cz - 4.3), (cx + 3.3, floor_y + 2.5, cz - 0.7),
         flat("Linen", lin((245, 242, 235)), 0.9))
    part("Pillow", (cx - 3.2, floor_y + 2.5, cz - 3.8), (cx - 1.8, floor_y + 3.0, cz - 1.2),
         flat("Linen", lin((245, 242, 235)), 0.9))
    part("Blanket", (cx - 0.6, floor_y + 2.5, cz - 4.35), (cx + 3.4, floor_y + 2.8, cz - 0.65),
         noisy("Quilt", lin((110, 140, 200)), lin((170, 120, 150)), scale=3))
    part("Lamp", (cx + 4.6, floor_y + 2.6, cz - 5.4), (cx + 5.4, floor_y + 3.4, cz - 4.6), m.lamp)
    rm.light(CF(cx + 5, floor_y + 3, cz - 5), 1.2, 14, (255, 200, 140), name="LampGlow")
    b.marker("Cam_BakerWindow", V3(cx + 1, floor_y + 6.5, fz + 9), V3(cx - 0.5, floor_y + 3, cz - 2.5))

    # floating numbers over the rooftops and the square (shot 18, the end card)
    rng = random.Random(18)
    sky = b.into("SkyNumbers")
    for i in range(1, 27):
        if i <= 16:
            pos = V3(rng.uniform(-85, 85), rng.uniform(36, 46), rng.uniform(-96, -76))
        else:
            pos = V3(rng.uniform(-40, 40), rng.uniform(14, 22), rng.uniform(-40, 40))
        sky.marker(f"Sky_{i}", pos)
        t.sky_anchors.append(rbx(pos))


def build_markers(ctx):
    b = ctx.b
    hero = V3(12, 3, 14)
    b.marker("Mark_Fountain", V3(hero.x, 0.5, hero.z))
    b.marker("Mark_Crowd", V3(0, 0.5, 26))
    b.marker("Mark_Bakery", V3(-75, 1.15, -69.5))
    for i, x in enumerate((-45, -15, 15, 45), 1):
        b.marker(f"Door_{i}", V3(x, 1.15, -69.5))
    b.marker("Door_Baker", V3(75, 1.15, -69.5))
    head = hero + V3(0, 2, 0)
    b.marker("Cam_Square_A", V3(12, 3, 32), head)
    b.marker("Cam_Square_B", V3(40, 12, 34), head)
    b.marker("Cam_Square_Crane", V3(0, 70, 60), V3(0, 0, 0))
    b.marker("Cam_Street_A", V3(-55, 5, -66), V3(-45, 1, -69.5))
    b.marker("Cam_Street_B", V3(55, 5, -66), V3(45, 1, -69.5))
    b.marker("Cam_Street_Top", V3(0, 55, -72), V3(0, 0, -76))
    b.marker("Cam_Town_Crane", V3(0, 140, 140), V3(0, 0, -40))
    bx, bz = ctx.L["props"]["bandstand"]
    top = ground(bx, bz, ctx.L) + 3.2
    b.marker("Mark_Bandstand", V3(bx, top, bz))
    b.marker("Cam_Park", V3(bx, top + 4, bz + 34), V3(bx, top + 4, bz))


# --- entry point ---------------------------------------------------------------------------------

def build_trees(ctx):
    for group, items in ctx.L["trees"].items():
        for it in items:
            kind, x, z = it[:3]
            ctx.place_tree(kind, x, z, it[3] if len(it) > 3 else 1.0, owner=f"Trees_{group}")


def build_town(backdrop=True):
    """Build the Old Town into a `Town` collection (once per episode build)."""
    t0 = time.perf_counter()
    _mats.clear()
    _ph.clear()
    L = layout()
    coll = bpy.data.collections.new("Town")
    bpy.context.scene.collection.children.link(coll)
    town = Town(coll)
    ctx = Ctx(town, L)
    for spec in L["buildings"]:
        KINDS.get(spec.get("kind"), House)(ctx, spec).build()
    build_grounds(ctx)
    build_props(ctx)
    build_trees(ctx)
    build_details(ctx)
    build_extras(ctx)
    build_markers(ctx)
    if backdrop:
        from . import backdrop as bd
        bd.build(ctx)
    town.build_seconds = time.perf_counter() - t0
    town.ctx = ctx
    return town
