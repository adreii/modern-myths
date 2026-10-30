"""The EP01 town, ported from the Roblox Studio builders in roblox/Build/.

- BuildEP01Map:         ground, plaza, fountain, benches, trees, bakery street, markers
- BuildEP01Extras:      props (Bread_1..4, Basket, BreadBag, Phone), BakerBedroom, sky anchors
- BuildTownPhase1:      building shells, roads, sidewalks, 36 street lamps, park
- BuildInteriorsPhase2: Hero's house, garage and school interiors, their markers

Coordinates, names and sizes are the Luau ones, written in Roblox space and mapped once:
1 Blender unit = 1 stud, Roblox (x, y, z) -> Blender (x, -z, y) (`rbx`). A part's CFrame `cf`
becomes the object matrix `_C @ cf`, so its local axes stay the Roblox ones (a cylinder's
axis is local X) and a `Cam_*` empty is oriented like a Blender camera (looks down -Z, +Y up).

Everything lives in one `Town` collection. Objects carry custom properties:
`building` (owner name), `cutaway=1` + `cutaway_group` on street-facing pieces shots hide to
film inside, `window=1` on window glass, `light=1` on practical lights.

    town = build_town()
    town.marker("Cam_Town_Crane")      # Vector, Blender space
    town.camera_matrix("Cam_Square_A") # 4x4 to put a camera on the mount
    town.cutaway("HeroHouse")          # front-wall pieces, signs, steps
    town.windows(), town.props["Phone"], town.sky_anchors
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

from . import core

FONT = r"C:\Windows\Fonts\ariblk.ttf"

# Roblox -> Blender axes: x stays, Roblox up (y) becomes +Z, Roblox front (-z) becomes +Y.
_C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def rbx(x, y=None, z=None):
    """Roblox position (x, y, z) or Vector -> Blender Vector."""
    if y is None:
        x, y, z = x
    return Vector((x, -z, y))


# --- Roblox-space CFrame helpers (4x4 matrices in Roblox axes) ----------------------------

def V3(x, y, z):
    return Vector((x, y, z))


def CF(x=0.0, y=0.0, z=0.0):
    if not isinstance(x, (int, float)):
        x, y, z = x
    return Matrix.Translation((x, y, z))


def ANG(rx, ry, rz):
    """CFrame.Angles: X, then Y, then Z rotation (R = Rx * Ry * Rz)."""
    return Matrix.Rotation(rx, 4, "X") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rz, 4, "Z")


def LOOK(pos, at):
    """CFrame.lookAt: local -Z points at `at`, +Y stays as close to world up as it can."""
    pos, at = Vector(pos), Vector(at)
    f = (at - pos).normalized()
    r = f.cross(Vector((0, 1, 0)))
    if r.length < 1e-6:
        r = Vector((1, 0, 0))
    r.normalize()
    u = r.cross(f)
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2], m[i][3] = r[i], u[i], -f[i], pos[i]
    return m


def P(cf):
    """CFrame.Position."""
    return cf.to_translation()


def rgb(r, g, b):
    return (r, g, b)


def lerp_color(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


WHITE = (255, 255, 255)


# --- meshes (shared unit shapes, scaled per object) ----------------------------------------

def _unit_mesh(kind):
    name = f"town_{kind}"
    me = bpy.data.meshes.get(name)
    if me:
        return me
    me = bpy.data.meshes.new(name)
    sharp = None
    if kind == "Block":
        v = [(x, y, z) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        smooth = [False] * 6
    elif kind == "Cylinder":  # axis along local X, radius 0.5, length 1
        n = 24
        ring = [(math.cos(2 * math.pi * i / n) * 0.5, math.sin(2 * math.pi * i / n) * 0.5) for i in range(n)]
        v = [(-0.5, a, b) for a, b in ring] + [(0.5, a, b) for a, b in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        f += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        smooth = [True] * n + [False, False]
        sharp = True
    else:  # Ball, diameter 1
        segs, rings = 24, 12
        v = [(0, 0, -0.5)]
        for j in range(1, rings):
            th = math.pi * j / rings - math.pi / 2
            v += [(math.cos(2 * math.pi * i / segs) * math.cos(th) * 0.5,
                   math.sin(2 * math.pi * i / segs) * math.cos(th) * 0.5, math.sin(th) * 0.5) for i in range(segs)]
        v.append((0, 0, 0.5))
        top = len(v) - 1
        f = [(0, 1 + (i + 1) % segs, 1 + i) for i in range(segs)]
        for j in range(rings - 2):
            a, b = 1 + j * segs, 1 + (j + 1) * segs
            f += [(a + i, a + (i + 1) % segs, b + (i + 1) % segs, b + i) for i in range(segs)]
        last = 1 + (rings - 2) * segs
        f += [(last + i, last + (i + 1) % segs, top) for i in range(segs)]
        smooth = [True] * len(f)
    me.from_pydata(v, [], f)
    me.polygons.foreach_set("use_smooth", smooth)
    if sharp:  # flat caps: mark the rim edges sharp so the smooth sides don't bend their normals
        attr = me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
        n = len(v) // 2
        attr.data.foreach_set("value", [not (e.vertices[0] % n == e.vertices[1] % n) for e in me.edges])
    me.materials.append(None)  # one slot; the material lives on each object
    me.update()
    return me


# --- materials ------------------------------------------------------------------------------

def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(color):
    """Roblox Color3 (sRGB 0-255) -> linear RGB for Blender."""
    return tuple(round(_lin(c), 5) for c in color)


_mats = {}


def _texcoord(nt):
    """Wall-friendly 2D coordinates from world position: (along the wall, up) on walls and
    (x, y) on floors, so one brick/plank pattern works on every face of a box."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    pos = nt.nodes.new("ShaderNodeSeparateXYZ")
    nrm = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], pos.inputs[0])
    nt.links.new(geo.outputs["Normal"], nrm.inputs[0])
    flat = nt.nodes.new("ShaderNodeMath")
    flat.operation = "ABSOLUTE"
    nt.links.new(nrm.outputs["Z"], flat.inputs[0])
    wall = nt.nodes.new("ShaderNodeMath")
    wall.operation = "SUBTRACT"
    wall.inputs[0].default_value = 1.0
    nt.links.new(flat.outputs[0], wall.inputs[1])

    def mul(a, b):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = "MULTIPLY"
        nt.links.new(a, n.inputs[0])
        nt.links.new(b, n.inputs[1])
        return n.outputs[0]

    def add(a, b):
        n = nt.nodes.new("ShaderNodeMath")
        nt.links.new(a, n.inputs[0])
        nt.links.new(b, n.inputs[1])
        return n.outputs[0]

    u = add(pos.outputs["X"], mul(pos.outputs["Y"], wall.outputs[0]))
    v = add(mul(pos.outputs["Z"], wall.outputs[0]), mul(pos.outputs["Y"], flat.outputs[0]))
    out = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(u, out.inputs[0])
    nt.links.new(v, out.inputs[1])
    return out.outputs[0]


def _bricks(m, col, mortar, w, h, mortar_size, bias=0.0):
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexBrick")
    tex.offset = 0.5
    tex.inputs["Scale"].default_value = 1.0
    tex.inputs["Brick Width"].default_value = w
    tex.inputs["Row Height"].default_value = h
    tex.inputs["Mortar Size"].default_value = mortar_size
    tex.inputs["Bias"].default_value = bias
    tex.inputs["Color1"].default_value = (*col, 1)
    tex.inputs["Color2"].default_value = (*[c * 0.86 for c in col], 1)
    tex.inputs["Mortar"].default_value = (*mortar, 1)
    nt.links.new(_texcoord(nt), tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])


def _new_mat(name, col, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*col, 1)
    return m


def surface(color, material="SmoothPlastic", transparency=0.0):
    """One material per (Roblox colour, Roblox material, transparency)."""
    col = lin(color)
    if material == "Neon":
        return core.mat(col, 0.35, emit=3.0, name="Neon")
    if material == "Glass":
        key = ("Glass", col, transparency)
        if key not in _mats:
            m = _new_mat("Glass", col, 0.05)
            p = m.node_tree.nodes["Principled BSDF"]
            p.inputs["Alpha"].default_value = max(0.0, 1.0 - transparency)
            p.inputs["Specular IOR Level"].default_value = 0.8
            m.use_transparent_shadow = True
            m.surface_render_method = "BLENDED" if transparency else "DITHERED"
            _mats[key] = m
        return _mats[key]
    if material in ("Brick", "WoodPlanks", "Wood", "Cobblestone"):
        key = (material, col)
        if key not in _mats:
            if material == "Brick":
                m = _new_mat("Brick", col, 0.7)
                _bricks(m, col, tuple(min(1.0, c * 1.25 + 0.08) for c in col), 0.9, 0.4, 0.04)
            elif material == "Cobblestone":
                m = _new_mat("Cobblestone", col, 0.8)
                _bricks(m, col, tuple(c * 0.6 for c in col), 1.6, 1.3, 0.08, bias=0.3)
            elif material == "WoodPlanks":
                m = _new_mat("WoodPlanks", col, 0.6)
                _bricks(m, col, tuple(c * 0.55 for c in col), 6.0, 0.8, 0.03, bias=-0.2)
            else:
                m = _new_mat("Wood", col, 0.6)
                core._wood_grain(m, col)
            _mats[key] = m
        return _mats[key]
    rough = {"Metal": 0.3, "DiamondPlate": 0.3}.get(material, 0.35)
    return core.mat(col, rough, name=material)


# --- builder ---------------------------------------------------------------------------------

class Town:
    """What build_town() returns: lookups into the built town."""

    def __init__(self, coll):
        self.coll = coll
        self.markers = {}  # name -> empty
        self.props = {}  # name -> object
        self.sky_anchors = []  # Vectors (Blender space)
        self.objects = []
        self._by_building = {}
        self.build_seconds = 0.0

    def marker(self, name):
        return self.markers[name].matrix_world.translation.copy()

    def camera_matrix(self, name):
        """A Cam_* mount as a camera world matrix (looks down local -Z, +Y up)."""
        return self.markers[name].matrix_world.copy()

    def building(self, name):
        return list(self._by_building.get(name, []))

    def buildings(self):
        return sorted(self._by_building)

    def cutaway(self, name, group="FrontWall"):
        return [o for o in self._by_building.get(name, []) if o.get("cutaway") and o.get("cutaway_group") == group]

    def windows(self, name=None):
        obs = self._by_building.get(name, []) if name else self.objects
        return [o for o in obs if o.get("window")]

    def lights(self, name=None):
        obs = self._by_building.get(name, []) if name else self.objects
        return [o for o in obs if o.get("light")]


class _Builder:
    def __init__(self, town):
        self.town = town
        self.owner = "Town"
        self.tags = {}
        self.signs = []  # text objects fitted to their boards once the depsgraph has them

    def into(self, owner, **tags):
        b = _Builder.__new__(_Builder)
        b.town, b.owner, b.signs = self.town, owner, self.signs
        b.tags = tags
        return b

    def _link(self, ob, name=None):
        self.town.coll.objects.link(ob)
        ob["building"] = self.owner
        for k, v in self.tags.items():
            ob[k] = v
        self.town.objects.append(ob)
        self.town._by_building.setdefault(self.owner, []).append(ob)
        return ob

    def part(self, name, size, cf, color, material="SmoothPlastic", shape="Block", transparency=0.0, **tags):
        sx, sy, sz = size
        if shape == "Cylinder":
            d = min(sy, sz)
            scale = (sx, d, d)
        elif shape == "Ball":
            d = min(sx, sy, sz)
            scale = (d, d, d)
        else:
            scale = (sx, sy, sz)
        ob = bpy.data.objects.new(name if name in _EXACT else f"{self.owner}.{name}", _unit_mesh(shape))
        ob.matrix_basis = _C @ cf @ Matrix.Diagonal((*scale, 1))
        self._link(ob)
        ob["rbx_name"] = name
        for k, v in tags.items():
            ob[k] = v
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = surface(color, material, transparency)
        if transparency >= 1:
            ob.hide_render = ob.hide_viewport = True
        return ob

    def light(self, at_cf, brightness, rng, color=(255, 228, 190), kind="POINT", angle=None, name="Light"):
        """A Roblox PointLight/SpotLight: energy from brightness and range, cut off at the range."""
        ld = bpy.data.lights.new(f"{self.owner}.{name}", kind)
        ld.color = lin(color)
        ld.energy = brightness * rng * rng * 2.0
        ld.shadow_soft_size = 0.4
        ld.use_shadow = False  # many practicals; the key light casts the shadows
        ld.use_custom_distance = True
        ld.cutoff_distance = rng
        if kind == "SPOT":
            ld.spot_size = math.radians(angle or 45)
            ld.spot_blend = 0.3
        ob = bpy.data.objects.new(ld.name, ld)
        ob.matrix_basis = _C @ at_cf
        self._link(ob)
        ob["light"] = 1
        return ob

    def sign_text(self, board, size, cf, text, color, flip=False):
        """SurfaceGui TextLabel (TextScaled) on the board's Front (-Z) face, in Arial Black."""
        cu = bpy.data.curves.new(f"{self.owner}.Text", "FONT")
        cu.body = text
        cu.font = _font()
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.extrude = 0.01
        ob = bpy.data.objects.new(cu.name, cu)
        self._link(ob)
        ob["sign"] = text
        for k in ("cutaway", "cutaway_group"):
            if k in board:
                ob[k] = board[k]
        ob.data.materials.append(surface(color, "SmoothPlastic"))
        # flip=True puts the text on the +Z face instead (the bakery sign's street side)
        face = CF(0, 0, size[2] / 2 + 0.03) if flip else CF(0, 0, -size[2] / 2 - 0.03) @ ANG(0, math.pi, 0)
        self.signs.append((ob, cf @ face, size[0], size[1]))
        return ob

    def marker(self, name, pos, look_at=None):
        ob = bpy.data.objects.new(name, None)
        ob.empty_display_type = "ARROWS" if look_at is not None else "PLAIN_AXES"
        if look_at is not None:
            ob.matrix_basis = _C @ LOOK(pos, look_at)
        else:
            ob.location = rbx(pos)
        self._link(ob)
        ob["marker"] = 1
        self.town.markers[name] = ob
        return ob


_EXACT = {f"Bread_{i}" for i in range(1, 5)} | {"Basket", "BreadBag", "Phone"}


def _font():
    f = bpy.data.fonts.get("ariblk")
    if f:
        return f
    try:
        f = bpy.data.fonts.load(FONT, check_existing=True)
        f.name = "ariblk"
        return f
    except (RuntimeError, OSError):
        return None  # Blender's built-in font


def _fit_signs(b):
    bpy.context.view_layer.update()
    for ob, cf, w, h in b.signs:
        dx, dy = ob.dimensions.x, ob.dimensions.y
        if dx < 1e-4:
            dx, dy = 0.8 * len(ob.data.body), 1.0
        k = min(w * 0.9 / dx, h * 0.78 / dy)
        ob.matrix_basis = _C @ cf @ Matrix.Diagonal((k, k, k, 1))


# --- BuildEP01Map ------------------------------------------------------------------------------

PALETTE = {
    "plaza": rgb(196, 190, 178), "road": rgb(70, 72, 80), "sidewalk": rgb(170, 170, 165),
    "grass": rgb(110, 170, 90),
    "houses": [rgb(214, 120, 100), rgb(120, 160, 205), rgb(235, 205, 120), rgb(150, 195, 150), rgb(205, 160, 200)],
    "bakery": rgb(240, 220, 185), "roof": rgb(80, 60, 55), "door": rgb(110, 70, 45),
    "windowDark": rgb(35, 45, 60), "windowLit": rgb(255, 200, 120), "stone": rgb(150, 150, 155),
    "water": rgb(80, 160, 220), "wood": rgb(140, 100, 65),
}


def _ep01_map(b):
    pal = PALETTE
    g = b.into("Ground")
    # BuildTownPhase1 grows the grass to 520 x 520 at z = 40 for the outer ring
    g.part("Grass", (520, 1, 520), CF(0, -0.45, 40), pal["grass"], "Grass")
    g.part("Plaza", (90, 1, 90), CF(0, 0.05, 0), pal["plaza"], "Cobblestone")
    g.part("Road", (260, 1, 14), CF(0, 0.05, -57), pal["road"], "Asphalt")
    g.part("Sidewalk", (260, 1.4, 8), CF(0, 0.2, -66), pal["sidewalk"], "Concrete")
    g.part("PlazaPath", (12, 1, 10), CF(0, 0.05, -50), pal["plaza"], "Cobblestone")

    sq = b.into("TownSquare")
    up = ANG(0, 0, math.radians(90))
    sq.part("FountainBase", (3, 16, 16), CF(0, 1.5, 0) @ up, pal["stone"], "Slate", "Cylinder")
    sq.part("FountainWater", (0.4, 14, 14), CF(0, 2.9, 0) @ up, pal["water"], "Glass", "Cylinder", transparency=0.3)
    sq.part("FountainPillar", (7, 2.5, 2.5), CF(0, 6, 0) @ up, pal["stone"], "Slate", "Cylinder")
    sq.part("FountainBowl", (1, 6, 6), CF(0, 9.5, 0) @ up, pal["stone"], "Slate", "Cylinder")
    for i, x in enumerate((-26, 26), 1):
        for j, z in enumerate((-18, 18), 1):
            n = f"Bench_{i}{j}"
            facing = LOOK(V3(x, 0, z), V3(0, 0, 0))
            sq.part(f"{n}.Seat", (8, 0.6, 2.5), facing @ CF(0, 2, 0), pal["wood"], "WoodPlanks")
            sq.part(f"{n}.Back", (8, 2.5, 0.5), facing @ CF(0, 3.4, 1.1), pal["wood"], "WoodPlanks")
            sq.part(f"{n}.LegL", (0.6, 2, 2), facing @ CF(-3.3, 1, 0), pal["stone"])
            sq.part(f"{n}.LegR", (0.6, 2, 2), facing @ CF(3.3, 1, 0), pal["stone"])
    for i, pos in enumerate((V3(-40, 0, -40), V3(40, 0, -40), V3(-40, 0, 40), V3(40, 0, 40)), 1):
        sq.part(f"TreeTrunk_{i}", (2, 8, 2), CF(pos + V3(0, 4, 0)), pal["wood"], "Wood")
        sq.part(f"TreeTop_{i}", (9, 9, 9), CF(pos + V3(0, 11, 0)), rgb(80, 150, 70), "Grass", "Ball")

    def house(name, x, z, color, w=None, h=None):
        """A solid house facing +Z (toward the road). Returns the doorstep position."""
        hb = b.into(name)
        width, height, depth = w or 22, h or 16, 18
        front = z + depth / 2
        hb.part("Body", (width, height, depth), CF(x, height / 2, z), color, "Brick")
        hb.part("Roof", (width + 2, 1.5, depth + 2), CF(x, height + 0.75, z), pal["roof"], "Slate")
        hb.part("Door", (4.5, 7.5, 0.4), CF(x, 3.75, front + 0.2), pal["door"], "Wood")
        hb.part("Step", (7, 0.8, 3), CF(x, 0.4, front + 1.5), pal["stone"], "Concrete")
        for i, wx in enumerate((x - width / 4 - 1, x + width / 4 + 1), 1):
            hb.part(f"Window_{i}", (4.5, 4.5, 0.3), CF(wx, height * 0.62, front + 0.15), pal["windowDark"], "Glass",
                    window=1)
        return V3(x, 0.8, front + 2.5)

    bakery_step = house("Bakery", -75, -81, pal["bakery"], 26, 18)
    bk = b.into("Bakery")
    size, cf = (14, 3, 0.4), CF(-75, 15, -71.6)
    sign = bk.part("Sign", size, cf, pal["wood"], "Wood")
    # The Luau puts the label on the board's Front (-Z) face, which faces the bakery wall;
    # here it goes on the street side so it reads.
    bk.sign_text(sign, size, cf, "BAKERY", rgb(255, 240, 215), flip=True)
    # warm light at Window_1 (on for most shots, off for shot 13); 1 stud out from the glass,
    # since the body behind it is solid and a light inside the pane leaves a ring on it
    bk.light(CF(-75 - 26 / 4 - 1, 18 * 0.62, -72 + 1.15), 2, 18, pal["windowLit"], name="BakeryLight")
    doorsteps = [house(f"House_{i}", x, -81, pal["houses"][i - 1]) for i, x in enumerate((-45, -15, 15, 45), 1)]
    baker_step = house("BakerHouse", 75, -81, pal["houses"][4], 20, 15)

    # Markers (names match ep01-shot-list.md); the Hero stands off-centre of the fountain.
    hero = V3(12, 3, 14)
    b.marker("Mark_Fountain", V3(hero.x, 0.5, hero.z))
    b.marker("Mark_Crowd", V3(0, 0.5, 26))
    b.marker("Mark_Bakery", bakery_step)
    for i, step in enumerate(doorsteps, 1):
        b.marker(f"Door_{i}", step)
    b.marker("Door_Baker", baker_step)
    head = hero + V3(0, 2, 0)
    b.marker("Cam_Square_A", V3(12, 3, 32), head)
    b.marker("Cam_Square_B", V3(40, 12, 34), head)
    b.marker("Cam_Square_Crane", V3(0, 70, 60), V3(0, 0, 0))
    b.marker("Cam_Street_A", V3(-55, 5, -66), doorsteps[0])
    b.marker("Cam_Street_B", V3(55, 5, -66), doorsteps[3])
    b.marker("Cam_Street_Top", V3(0, 55, -72), V3(0, 0, -76))
    # Cam_BakerWindow: BuildEP01Extras re-aims it at the bedroom set (see _ep01_extras)
    b.marker("Cam_Town_Crane", V3(0, 140, 140), V3(0, 0, -40))
    return bakery_step, baker_step


# --- BuildEP01Extras ---------------------------------------------------------------------------

def _ep01_extras(b):
    pr = b.into("Props")
    bread = rgb(196, 140, 80)
    for i, x in enumerate((-45, -15, 15, 45), 1):  # invisible until a shot shows them
        b.town.props[f"Bread_{i}"] = pr.part(f"Bread_{i}", (2.6, 1.3, 1.4), CF(x + 1.6, 1.45, -70.6), bread, "Sand",
                                             "Cylinder", transparency=1)
    # parked under the map until a shot uses them
    b.town.props["Basket"] = pr.part("Basket", (1.8, 1, 1.3), CF(0, -60, 0), rgb(150, 105, 60), "WoodPlanks")
    b.town.props["BreadBag"] = pr.part("BreadBag", (1.2, 1.6, 0.8), CF(0, -60, 2), rgb(215, 185, 140), "Fabric")
    b.town.props["Phone"] = pr.part("Phone", (0.2, 1, 0.55), CF(0, -60, 4), rgb(20, 20, 25), "Glass")

    # Baker's bedroom: an open set far east of town, seen through its front window (shot 14).
    rm = b.into("BakerBedroom")
    wall, inside = rgb(205, 160, 200), rgb(235, 225, 210)
    cx, cz = 150, -84
    rm.part("Floor", (20, 1, 16), CF(cx, 0.05, cz), rgb(150, 110, 75), "WoodPlanks")
    rm.part("BackWall", (20, 14, 1), CF(cx, 7, cz - 7.5), inside)
    rm.part("LeftWall", (1, 14, 16), CF(cx - 9.5, 7, cz), inside)
    rm.part("RightWall", (1, 14, 16), CF(cx + 9.5, 7, cz), inside)
    rm.part("Ceiling", (20, 1, 16), CF(cx, 14.5, cz), inside)
    fz = cz + 7.5  # front wall with a 7 x 5 window opening (x 146.5..153.5, y 4..9)
    rm.part("FrontLeft", (6.5, 14, 1), CF(cx - 6.75, 7, fz), wall, "Brick")
    rm.part("FrontRight", (6.5, 14, 1), CF(cx + 6.75, 7, fz), wall, "Brick")
    rm.part("FrontBelow", (7, 4, 1), CF(cx, 2, fz), wall, "Brick")
    rm.part("FrontAbove", (7, 5, 1), CF(cx, 11.5, fz), wall, "Brick")
    rm.part("WindowSill", (7.6, 0.4, 1.6), CF(cx, 4.1, fz + 0.2), rgb(240, 240, 240))
    rm.part("BedFrame", (7, 1.4, 4), CF(cx, 1.2, cz - 2.5), rgb(120, 85, 60), "Wood")
    rm.part("Mattress", (6.6, 0.6, 3.6), CF(cx, 2.2, cz - 2.5), rgb(245, 245, 250), "Fabric")
    rm.part("Pillow", (1.4, 0.5, 2.6), CF(cx - 2.5, 2.7, cz - 2.5), rgb(255, 255, 255), "Fabric")
    rm.part("Blanket", (3.6, 0.3, 3.7), CF(cx + 1.2, 3.1, cz - 2.5), rgb(110, 140, 200), "Fabric")
    rm.part("Lamp", (0.8, 0.8, 0.8), CF(cx + 5, 3, cz - 5), rgb(255, 220, 150), "Neon")
    rm.light(CF(cx + 5, 3, cz - 5), 1.2, 14, rgb(255, 200, 140), name="LampGlow")
    b.marker("Cam_BakerWindow", V3(cx + 1, 6.5, fz + 9), V3(cx - 0.5, 3, cz - 2.5))

    # Floating number anchors over the rooftops and the square (shot 18). Same spread as the
    # Luau's Random.new(18); Python's RNG gives different values.
    rng = random.Random(18)
    sky = b.into("SkyNumbers")
    for i in range(1, 27):
        if i <= 16:
            pos = V3(rng.uniform(-85, 85), rng.uniform(19, 27), rng.uniform(-96, -76))
        else:
            pos = V3(rng.uniform(-40, 40), rng.uniform(12, 20), rng.uniform(-40, 40))
        sky.marker(f"Sky_{i}", pos)
        b.town.sky_anchors.append(rbx(pos))


# --- BuildTownPhase1 ---------------------------------------------------------------------------

GROUND = 0.55  # road / plaza top
STOREY = 12
ASPHALT = rgb(70, 72, 80)
PAVEMENT = rgb(170, 170, 165)
GLASS = rgb(170, 210, 235)
DOOR = rgb(110, 70, 45)
TRIM = rgb(240, 238, 232)
DARK = rgb(40, 40, 46)


def wall_with_openings(b, bottom, width, height, color, material, openings):
    """A wall built from solid pieces around rectangular openings. `bottom` is the CFrame at the
    wall's bottom centre (local X along the wall). Openings are (x0, x1, y0, y1, kind) with kind
    "window" | "door" | "store" | "open". Returns the objects."""
    obs = []
    xs = [-width / 2, width / 2]
    for o in openings:
        xs += [min(max(o[0], -width / 2), width / 2), min(max(o[1], -width / 2), width / 2)]
    cuts = []
    for x in sorted(xs):
        if not cuts or x - cuts[-1] > 1e-3:
            cuts.append(x)
    for a, c in zip(cuts, cuts[1:]):
        holes = sorted((o[2], o[3]) for o in openings if o[0] <= a + 1e-3 and o[1] >= c - 1e-3)
        y = 0

        def fill(y0, y1):
            if y1 - y0 > 1e-3:
                obs.append(b.part("Wall", (c - a, y1 - y0, 1), bottom @ CF((a + c) / 2, (y0 + y1) / 2, 0), color,
                                  material))

        for h0, h1 in holes:
            fill(y, h0)
            y = max(y, h1)
        fill(y, height)
    for o in openings:  # glass for windows and shop fronts, a panel for doors
        w, h = o[1] - o[0], o[3] - o[2]
        cf = bottom @ CF((o[0] + o[1]) / 2, (o[2] + o[3]) / 2, 0)
        if o[4] in ("window", "store"):
            obs.append(b.part("Glass", (w, h, 0.2), cf, GLASS, "Glass", transparency=0.55, window=1))
            obs.append(b.part("Sill", (w + 0.6, 0.3, 1.4), bottom @ CF((o[0] + o[1]) / 2, o[2], 0), TRIM))
        elif o[4] == "door":
            obs.append(b.part("Door", (w, h, 0.4), cf, DOOR, "Wood"))
    return obs


def window_row(lst, wall_width, storey_base, avoid_half_width=None):
    """Evenly spaced windows on one storey of a wall."""
    n = max(1, math.floor(wall_width / 8))
    spacing = wall_width / n
    for i in range(1, n + 1):
        cx = -wall_width / 2 + spacing * (i - 0.5)
        if not (avoid_half_width and abs(cx) < avoid_half_width + 2.5):
            lst.append((cx - 2, cx + 2, storey_base + 4, storey_base + 8.5, "window"))


def building(b, name, x, z, front, W, D, floors, color, storeyH=STOREY, material="Brick", roof=None,
             storefront=False, doorW=5, doorH=8, sign=None, signColor=None, signBoard=None, awning=None):
    """One hollow building shell; its front faces `front` (a Roblox unit vector at the street).
    Returns (builder for the building, L(x, y, z) -> CFrame in building space, height)."""
    mb = b.into(name)
    fw = b.into(name, cutaway=1, cutaway_group="FrontWall")
    sh = storeyH
    H = floors * sh + 2.5
    origin = V3(x, GROUND, z)
    base = LOOK(origin, origin + Vector(front))

    def L(lx, ly, lz):
        return base @ CF(lx, ly, lz)

    fo = []
    if storefront:
        fo.append((-W / 2 + 2.5, -doorW / 2, 0.8, 8.5, "store"))
        fo.append((doorW / 2, W / 2 - 2.5, 0.8, 8.5, "store"))
        fo.append((-doorW / 2, doorW / 2, 0, doorH, "door"))
    else:
        fo.append((-doorW / 2, doorW / 2, 0, doorH, "door"))
        window_row(fo, W - 2, 0, doorW / 2)
    for f in range(2, floors + 1):
        window_row(fo, W - 2, (f - 1) * sh)
    wall_with_openings(fw, L(0, 0, -D / 2 + 0.5), W, H, color, material, fo)

    bo, so = [], []
    for f in range(1, floors + 1):
        window_row(bo, W - 2, (f - 1) * sh)
        window_row(so, D - 4, (f - 1) * sh)
    wall_with_openings(mb, L(0, 0, D / 2 - 0.5) @ ANG(0, math.pi, 0), W, H, color, material, bo)
    wall_with_openings(mb, L(-W / 2 + 0.5, 0, 0) @ ANG(0, math.pi / 2, 0), D - 2, H, color, material, so)
    wall_with_openings(mb, L(W / 2 - 0.5, 0, 0) @ ANG(0, -math.pi / 2, 0), D - 2, H, color, material, so)

    for f in range(1, floors + 1):
        mb.part(f"Floor{f}", (W - 2, 0.7, D - 2), L(0, (f - 1) * sh, 0), rgb(180, 170, 155), "WoodPlanks")
    mb.part("Roof", (W - 2, 0.7, D - 2), L(0, floors * sh, 0), roof or rgb(85, 80, 80), "Slate")
    fw.part("Coping", (W + 0.6, 0.5, 0.8), L(0, H + 0.25, -D / 2 + 0.4), TRIM)

    if sign:
        y = 9.9 if storefront else doorH + 1.6
        size, cf = (min(W - 3, 20), 2.4, 0.4), L(0, y, -D / 2 - 0.25)
        board = fw.part("Sign", size, cf, signBoard or DARK)
        fw.sign_text(board, size, cf, sign, signColor or rgb(255, 240, 210))
    if awning:
        fw.part("Awning", (W - 3, 0.4, 3.4), L(0, 8.9, -D / 2 - 1.7) @ ANG(math.radians(10), 0, 0), awning, "Fabric")
    fw.part("Step", (doorW + 2, 0.35, 2), L(0, 0.17, -D / 2 - 1), PAVEMENT, "Concrete")
    for ob in b.town.building(name):
        ob["storeys"], ob["storey_height"] = floors, sh
    return mb, L, H


def _town_phase1(b):
    st = b.into("Streets")

    def road(name, cx, cz, sx, sz):
        st.part(name, (sx, 1, sz), CF(cx, 0.05, cz), ASPHALT, "Asphalt")

    def walk(name, cx, cz, sx, sz):
        st.part(name, (sx, 1.4, sz), CF(cx, 0.2, cz), PAVEMENT, "Concrete")

    road("RingWest", -54, 2, 12, 104)
    road("RingEast", 54, 2, 12, 104)
    road("SquareRoadSouth", 0, 54, 212, 12)
    road("SchoolRoad", 0, 100, 300, 12)
    road("AvenueWest", -100, 21.5, 12, 169)
    road("AvenueEast", 100, 21.5, 12, 169)
    walk("WalkSquareNorth", 0, -48, 90, 4)
    walk("WalkSquareWest", -46.5, 2, 3, 94)
    walk("WalkSquareEast", 46.5, 2, 3, 94)
    walk("WalkSquareSouth", 0, 46.5, 90, 3)
    walk("WalkWestShops", -61.5, 2, 3, 104)
    walk("WalkEastShops", 61.5, 2, 3, 104)
    walk("WalkSouthRow", 0, 61.5, 182, 3)  # sidewalks stop at crossings
    for z in (92.5, 107.5):
        walk("WalkSchool", -122, z, 32, 3)
        walk("WalkSchool", 0, z, 188, 3)
        walk("WalkSchool", 122, z, 32, 3)
    for x in (-107.5, -92.5, 92.5, 107.5):
        walk("WalkAvenue", x, -1, 3, 98)
        walk("WalkAvenue", x, 77, 3, 34)

    lb = b.into("Lamps")

    def lamp(pos):
        lb.part("Pole", (0.5, 10, 0.5), CF(pos + V3(0, 5.9, 0)), DARK, "Metal")
        lb.part("Head", (1.4, 0.7, 1.4), CF(pos + V3(0, 11.2, 0)), rgb(255, 230, 180), "Neon")
        lb.light(CF(pos + V3(0, 11.2, 0)), 0.7, 20, rgb(255, 215, 160), name="LampLight")

    for z in range(-40, 41, 20):
        lamp(V3(-61.5, 0.9, z))
        lamp(V3(61.5, 0.9, z))
    for x in range(-40, 41, 20):
        lamp(V3(x, 0.9, 61.5))
    for x in range(-140, 141, 35):
        lamp(V3(x, 0.9, 92.5))
    for z in range(-30, 81, 22):
        lamp(V3(-92.5, 0.9, z))
        lamp(V3(92.5, 0.9, z))

    west, east, north = V3(-1, 0, 0), V3(1, 0, 0), V3(0, 0, -1)
    # East side of the square: Market Street shops, facing west onto the square.
    for n, z, sign, color, awning in (
            ("SneakerShop", -36, "SNEAKERS", rgb(235, 120, 90), rgb(240, 90, 70)),
            ("Cafe", -18, "CAFE", rgb(150, 200, 170), rgb(70, 140, 100)),
            ("CornerShop", 0, "CORNER SHOP", rgb(240, 210, 130), rgb(60, 110, 190)),
            ("Restaurant", 18, "PIZZA", rgb(230, 150, 150), rgb(200, 50, 50)),
            ("Laundromat", 36, "LAUNDRY", rgb(170, 200, 235), rgb(90, 150, 220))):
        building(b, n, 73, z, west, 17.5, 20, 2, color, storefront=True, sign=sign, awning=awning)

    # West side: apartment block and library, facing east onto the square.
    building(b, "ApartmentBlock", -73, -20, east, 50, 20, 3, rgb(205, 175, 150), doorW=6, doorH=9,
             sign="MAPLE COURT", signBoard=rgb(60, 60, 70))
    building(b, "Library", -73, 27, east, 36, 20, 2, rgb(190, 200, 215), storeyH=13, material="Concrete", doorW=6,
             doorH=9, sign="LIBRARY", signBoard=rgb(40, 60, 100))

    # South side: toy shop, Town Hall with clock tower, music shop, facing north onto the square.
    building(b, "ToyShop", -34, 73, north, 22, 20, 2, rgb(250, 200, 110), storefront=True, sign="TOYS",
             awning=rgb(240, 110, 160))
    building(b, "MusicShop", 34, 73, north, 22, 20, 2, rgb(160, 140, 200), storefront=True, sign="MUSIC",
             awning=rgb(110, 80, 170))
    hall, L, H = building(b, "TownHall", 0, 75, north, 40, 24, 2, rgb(225, 215, 195), storeyH=13,
                          material="Concrete", doorW=7, doorH=10, sign="TOWN HALL", signBoard=rgb(120, 40, 40))
    hall.part("Tower", (10, 20, 10), L(0, H + 10, -4), rgb(215, 205, 185), "Concrete")
    hall.part("Cap", (12, 1.5, 12), L(0, H + 20.75, -4), rgb(120, 40, 40), "Slate")
    hall.part("Spire", (6, 4, 6), L(0, H + 23.5, -4), rgb(120, 40, 40), "Slate")
    hall.part("ClockFace", (0.4, 7, 7), L(0, H + 13, -9.2) @ ANG(0, math.pi / 2, 0), rgb(250, 248, 235),
              "SmoothPlastic", "Cylinder")
    hall.part("HourHand", (0.4, 2.2, 0.2), L(0, H + 13.9, -9.5), DARK)
    hall.part("MinuteHand", (0.3, 3.2, 0.2), L(0.9, H + 13, -9.5) @ ANG(0, 0, math.radians(-70)), DARK)
    hf = b.into("TownHall", cutaway=1, cutaway_group="FrontWall")
    for x in (-6, 6):  # cylinder length runs along X: turned upright
        hf.part("Column", (11, 1.4, 1.4), L(x, 5.5, -13.2) @ ANG(0, 0, math.pi / 2), TRIM, "Marble", "Cylinder")
    hf.part("Portico", (16, 1, 4), L(0, 11.3, -13.4), TRIM, "Marble")

    # Outer ring: school (south), Hero's house + garage (south-east), arena (east), park (south-west).
    school, L, _ = building(b, "School", 0, 155, north, 80, 30, 2, rgb(225, 140, 95), doorW=8, doorH=9,
                            sign="SCHOOL", signBoard=rgb(40, 70, 120))
    yd = b.into("School", group="Schoolyard")
    yd.part("Yard", (80, 0.4, 30), CF(0, 0.6, 124), rgb(150, 150, 155), "Concrete")
    yd.part("Court", (40, 0.1, 22), CF(0, 0.85, 124), rgb(60, 120, 180))
    yd.part("CentreLine", (0.3, 0.05, 22), CF(0, 0.92, 124), WHITE)
    for x in (-19, 19):
        yd.part("HoopPole", (0.5, 9, 0.5), CF(x + (-1.5 if x < 0 else 1.5), 5, 124), DARK, "Metal")
        yd.part("Backboard", (0.3, 3, 4.5), CF(x, 9, 124), WHITE)
        yd.part("Hoop", (0.2, 1.6, 1.6), CF(x + (1 if x < 0 else -1), 8, 124) @ ANG(0, 0, math.pi / 2),
                rgb(230, 90, 30), "Metal", "Cylinder")
    for x in range(-40, 41, 4):
        if abs(x) > 5:
            yd.part("FencePost", (0.3, 4, 0.3), CF(x, 2.6, 110), DARK, "Metal")
    yd.part("FenceRailWest", (35, 0.3, 0.2), CF(-22.5, 4.2, 110), DARK, "Metal")
    yd.part("FenceRailEast", (35, 0.3, 0.2), CF(22.5, 4.2, 110), DARK, "Metal")
    yd.part("Flagpole", (0.4, 16, 0.4), CF(28, 8.6, 136), rgb(200, 200, 205), "Metal")
    yd.part("Flag", (4, 2.6, 0.1), CF(30.2, 15, 136), rgb(230, 70, 60), "Fabric")

    building(b, "HeroHouse", 122, 127, north, 24, 22, 2, rgb(200, 215, 235), material="WoodPlanks", doorW=4.5,
             doorH=8, roof=rgb(110, 60, 55))
    building(b, "Garage", 142.5, 129, north, 13, 18, 1, rgb(200, 215, 235), storeyH=10, material="WoodPlanks",
             doorW=9, doorH=7.5)
    for ob in b.town.cutaway("Garage"):
        if ob["rbx_name"] == "Door":
            ob.name, ob["rbx_name"] = "Garage.GarageDoor", "GarageDoor"
            ob.material_slots[0].material = surface(rgb(225, 225, 225), "DiamondPlate")
    gd = b.into("HeroHouse", group="Garden")
    for x in range(108, 151, 3):
        if abs(x - 122) > 2 and abs(x - 142.5) > 5:
            gd.part("Picket", (0.4, 2.6, 0.4), CF(x, 1.9, 112.5), WHITE, "Wood")
    gd.part("Path", (3, 0.2, 3.5), CF(122, 0.65, 114.3), PAVEMENT, "Concrete")
    gd.part("Drive", (9, 0.2, 9), CF(142.5, 0.65, 115), PAVEMENT, "Concrete")
    gd.part("MailboxPost", (0.4, 3.4, 0.4), CF(118.5, 2.2, 112), DARK)
    gd.part("Mailbox", (1.4, 1, 0.9), CF(118.5, 4, 112), rgb(60, 110, 190), "Metal")

    _, L, _ = building(b, "Arena", 145, -10, west, 60, 50, 1, rgb(120, 130, 165), storeyH=20, material="Concrete",
                       doorW=10, doorH=10, sign="ARENA", signBoard=rgb(200, 50, 60))
    af = b.into("Arena", cutaway=1, cutaway_group="FrontWall")
    size, cf = (30, 4, 0.6), L(0, 17, -25.4)
    marquee = af.part("Marquee", size, cf, rgb(30, 30, 40))
    af.sign_text(marquee, size, cf, "FRIDAY NIGHT RUMBLE", rgb(255, 210, 74))

    pk = b.into("Park")
    sand = rgb(200, 185, 150)
    yellow = rgb(240, 200, 60)
    pk.part("PathNS", (4, 0.2, 60), CF(-128, 0.65, 140), sand, "Sand")
    pk.part("PathEW", (36, 0.2, 4), CF(-128, 0.65, 135), sand, "Sand")
    pk.part("Pond", (0.3, 16, 16), CF(-138, 0.6, 160) @ ANG(0, 0, math.pi / 2), rgb(70, 150, 210), "SmoothPlastic",
            "Cylinder")
    for p in (V3(-117, 0, 122), V3(-113, 0, 122), V3(-117, 0, 126), V3(-113, 0, 126)):
        pk.part("SlidePost", (0.4, 5, 0.4), CF(p + V3(0, 3, 0)), yellow, "Metal")
    pk.part("SlideDeck", (4.4, 0.4, 4.4), CF(-115, 5.6, 124), rgb(230, 90, 80))
    pk.part("Slide", (3, 0.3, 8), CF(-115, 3.2, 130.5) @ ANG(math.radians(-38), 0, 0), rgb(60, 150, 230))
    for x in (-124, -116):
        pk.part("SwingPost", (0.4, 7, 0.4), CF(x, 4, 146), yellow, "Metal")
    pk.part("SwingBar", (8.4, 0.4, 0.4), CF(-120, 7.5, 146), yellow, "Metal")
    for x in (-122, -118):
        pk.part("Chain", (0.1, 4.5, 0.1), CF(x - 0.6, 5.2, 146), DARK)
        pk.part("Chain", (0.1, 4.5, 0.1), CF(x + 0.6, 5.2, 146), DARK)
        pk.part("Seat", (1.6, 0.2, 0.8), CF(x, 3, 146), rgb(230, 90, 80))
    for i, pos in enumerate((V3(-140, 0, 120), V3(-145, 0, 140), V3(-120, 0, 165), V3(-115, 0, 112),
                             V3(-148, 0, 165)), 1):
        pk.part(f"TreeTrunk{i}", (2, 8, 2), CF(pos + V3(0, 4.5, 0)), rgb(140, 100, 65), "Wood")
        pk.part(f"TreeTop{i}", (9, 9, 9), CF(pos + V3(0, 11.5, 0)), rgb(80, 150, 70), "Grass", "Ball")
    bench = LOOK(V3(-131, 0.55, 150), V3(-138, 0.55, 160))
    pk.part("BenchSeat", (6, 0.5, 2), bench @ CF(0, 2, 0), rgb(140, 100, 65), "WoodPlanks")
    pk.part("BenchBack", (6, 2, 0.4), bench @ CF(0, 3.2, 0.9), rgb(140, 100, 65), "WoodPlanks")
    pk.part("BenchLegs", (5, 1.8, 1.6), bench @ CF(0, 0.9, 0), DARK, "Metal")


# --- BuildInteriorsPhase2 ---------------------------------------------------------------------

WOOD = rgb(150, 105, 70)
CREAM = rgb(240, 230, 210)


def wall_with_gaps(b, name, bottom, width, height, color, gaps):
    """A plain wall with empty doorways; gaps are (x0, x1, y0, y1) in wall space."""
    xs = [-width / 2, width / 2]
    for o in gaps:
        xs += [o[0], o[1]]
    cuts = []
    for x in sorted(xs):
        if not cuts or x - cuts[-1] > 1e-3:
            cuts.append(x)
    for a, c in zip(cuts, cuts[1:]):
        y = 0
        for o in gaps:
            if o[0] <= a + 1e-3 and o[1] >= c - 1e-3:
                if o[2] > y:
                    b.part(name, (c - a, o[2] - y, 1), bottom @ CF((a + c) / 2, (y + o[2]) / 2, 0), color)
                y = max(y, o[3])
        if height > y:
            b.part(name, (c - a, height - y, 1), bottom @ CF((a + c) / 2, (y + height) / 2, 0), color)


def slab_with_hole(b, slab_name, L, y, iw, id_, hole):
    """Replace a building's floor slab with one that has a stairwell hole (x0, x1, z0, z1)."""
    town = b.town
    for ob in town.building(b.owner):
        if ob.get("rbx_name") == slab_name:
            town.objects.remove(ob)
            town._by_building[b.owner].remove(ob)
            bpy.data.objects.remove(ob)
    color = rgb(180, 170, 155)
    x0, x1, z0, z1 = hole

    def piece(ax, bx, az, bz):
        if bx - ax > 1e-3 and bz - az > 1e-3:
            b.part(slab_name, (bx - ax, 0.7, bz - az), L((ax + bx) / 2, y, (az + bz) / 2), color, "WoodPlanks")

    piece(-iw / 2, x0, -id_ / 2, id_ / 2)
    piece(x1, iw / 2, -id_ / 2, id_ / 2)
    piece(x0, x1, -id_ / 2, z0)
    piece(x0, x1, z1, id_ / 2)


def stairs(b, start, width, count, rise, depth, color):
    """Solid stairs; `start` is the bottom of the first step's front edge, looking up the stairs."""
    h = rise / count
    for k in range(1, count + 1):
        b.part("Step", (width, k * h, depth), start @ CF(0, k * h / 2, -(k - 0.5) * depth), color, "WoodPlanks")


def railing(b, frm, to, color):
    length = (to - frm).length
    mid = (frm + to) / 2
    b.part("Rail", (0.3, 0.3, length), LOOK(mid, to) @ CF(0, 3.2, 0), color, "Wood")
    n = max(2, math.floor(length / 2))
    for i in range(n + 1):
        b.part("Baluster", (0.2, 3.2, 0.2), CF(frm.lerp(to, i / n)) @ CF(0, 1.6, 0), color, "Wood")


def table4(b, name, base, w, d, h, color):
    b.part(f"{name}.Top", (w, 0.4, d), base @ CF(0, h - 0.2, 0), color, "Wood")
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.part(f"{name}.Leg", (0.35, h - 0.4, 0.35), base @ CF(sx * (w / 2 - 0.4), (h - 0.4) / 2, sz * (d / 2 - 0.4)),
                   color, "Wood")


def chair(b, base, color, s=1):
    """A chair looking along base's -Z (back on its +Z side); `s` scales it (kids' chairs)."""
    k = s
    b.part("Chair.Seat", (2 * k, 0.3, 2 * k), base @ CF(0, 2 * k, 0), color, "Wood")
    b.part("Chair.Back", (2 * k, 2.4 * k, 0.3), base @ CF(0, 3.3 * k, 0.85 * k), color, "Wood")
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.part("Chair.Leg", (0.25, 1.85 * k, 0.25), base @ CF(sx * 0.8 * k, 0.93 * k, sz * 0.8 * k), color, "Wood")


def bed(b, base, blanket):
    """base: floor point at the bed's centre, headboard toward +Z."""
    b.part("Bed.Frame", (5.6, 1.3, 8.5), base @ CF(0, 0.65, 0), WOOD, "Wood")
    b.part("Bed.Headboard", (6, 4, 0.5), base @ CF(0, 2, 4.2), WOOD, "Wood")
    b.part("Bed.Mattress", (5.2, 0.6, 8), base @ CF(0, 1.6, -0.1), TRIM, "Fabric")
    b.part("Bed.Pillow", (3.8, 0.6, 1.5), base @ CF(0, 2.2, 3.1), WHITE, "Fabric")
    b.part("Bed.Blanket", (5.4, 0.3, 5), base @ CF(0, 2, -1.6), blanket, "Fabric")


def sofa(b, base, color, length):
    """Sits facing base's -Z."""
    b.part("Sofa.Base", (length, 1.5, 3), base @ CF(0, 0.75, 0), color, "Fabric")
    b.part("Sofa.Back", (length, 3.2, 0.9), base @ CF(0, 1.6, 1.9), color, "Fabric")
    b.part("Sofa.ArmL", (0.9, 2.3, 3.9), base @ CF(-length / 2 - 0.45, 1.15, 0.45), color, "Fabric")
    b.part("Sofa.ArmR", (0.9, 2.3, 3.9), base @ CF(length / 2 + 0.45, 1.15, 0.45), color, "Fabric")
    cushion = lerp_color(color, WHITE, 0.15)
    b.part("Sofa.CushionL", (length / 2 - 0.1, 0.5, 2.7), base @ CF(-length / 4, 1.75, -0.1), cushion, "Fabric")
    b.part("Sofa.CushionR", (length / 2 - 0.1, 0.5, 2.7), base @ CF(length / 4, 1.75, -0.1), cushion, "Fabric")


def ceiling_lamp(b, cf, brightness=1.4, rng=26):
    b.part("CeilingLamp", (2.4, 0.3, 2.4), cf, rgb(255, 242, 215), "Neon")
    b.light(cf, brightness, rng, name="CeilingLight")


def _hero_house(b):
    """Shell: centre (122, 127), front faces -Z, 24 x 22, two storeys of 12. Inner x -11..11, z -10..10."""
    hb = b.into("HeroHouse")
    it = b.into("HeroHouse", group="Interior")

    def L(x, y, z):
        return CF(122 + x, 0.55 + y, 127 + z)

    def F(x, y, z):  # ground floor, y from the floor top
        return L(x, 0.35 + y, z)

    def U(x, y, z):  # upstairs
        return L(x, 12.35 + y, z)

    # Stairs along the east wall: up from z = -9 to z = 4, landing in a hole in the upstairs floor.
    slab_with_hole(hb, "Floor2", L, 12, 22, 20, (8.3, 11, -9.5, 4.5))
    stairs(it, F(9.7, 0, -9) @ ANG(0, math.pi, 0), 2.4, 13, 12, 1, rgb(170, 125, 85))
    railing(it, P(U(8.1, 0, -9.5)), P(U(8.1, 0, 4.5)), TRIM)
    railing(it, P(U(8.3, 0, -9.7)), P(U(11, 0, -9.7)), TRIM)

    # Partition between kitchen (west) and living room (east), leaving an entry strip at the front.
    wall_with_gaps(it, "Partition", F(0, 0, 1.5) @ ANG(0, math.pi / 2, 0), 17, 11.3, CREAM, [])

    # Kitchen (x -11..0)
    it.part("BaseCabinets", (7.5, 3.4, 2.4), F(-6.75, 1.7, 8.6), TRIM, "Wood")
    it.part("Worktop", (7.9, 0.4, 2.8), F(-6.75, 3.6, 8.5), rgb(70, 72, 78), "Granite")
    it.part("Sink", (2.4, 0.1, 1.6), F(-5.5, 3.82, 8.5), rgb(170, 175, 180), "Metal")
    it.part("Tap", (0.25, 1.1, 0.25), F(-5.5, 4.35, 9.4), rgb(190, 195, 200), "Metal")
    for ox, oy in ((-0.6, -0.5), (0.6, -0.5), (-0.6, 0.5), (0.6, 0.5)):
        it.part("Burner", (0.1, 0.9, 0.9), F(-8.9 + ox, 3.85, 8.5 + oy) @ ANG(0, 0, math.pi / 2), DARK, "Metal",
                "Cylinder")
    it.part("OvenDoor", (2.4, 1.8, 0.1), F(-8.9, 1.6, 7.35), rgb(30, 30, 35), "Glass")
    it.part("WallCabinet", (2.8, 3, 1.4), F(-9.4, 8.6, 9.2), TRIM, "Wood")
    it.part("Fridge", (3, 8, 2.8), F(-1.8, 4, 8.5), rgb(205, 210, 215), "Metal")
    it.part("FridgeHandle", (0.2, 2.4, 0.2), F(-3, 5, 7), DARK, "Metal")
    table4(it, "KitchenTable", F(-5.5, 0, -2), 5, 3.5, 3.2, WOOD)
    for cx, cz, a in ((-8.5, -2, -math.pi / 2), (-2.5, -2, math.pi / 2), (-5.5, -4.6, math.pi), (-5.5, 0.6, 0)):
        chair(it, F(cx, 0, cz) @ ANG(0, a, 0), rgb(200, 90, 70))
    it.part("FruitBowl", (0.5, 1.4, 1.4), F(-5.5, 3.45, -2) @ ANG(0, 0, math.pi / 2), TRIM, "SmoothPlastic",
            "Cylinder")
    it.part("Apple", (0.6, 0.6, 0.6), F(-5.7, 3.85, -1.9), rgb(210, 40, 40), "SmoothPlastic", "Ball")
    it.part("Orange", (0.6, 0.6, 0.6), F(-5.2, 3.85, -2.2), rgb(245, 150, 30), "SmoothPlastic", "Ball")
    it.part("PendantShade", (1.6, 0.7, 1.6), F(-5.5, 8.6, -2), rgb(255, 235, 200), "Neon")
    it.light(F(-5.5, 8.6, -2), 1, 14, name="PendantLight")
    it.part("PendantCord", (0.1, 2.4, 0.1), F(-5.5, 10.1, -2), DARK)
    ceiling_lamp(it, F(-5.5, 11.1, 4))

    # Living room (x 0..11): TV on the partition, sofa facing it, stairs along the east wall
    it.part("TVStand", (1.6, 2.2, 5), F(1.3, 1.1, -3), WOOD, "Wood")
    it.part("TV", (0.3, 3.4, 5.4), F(0.85, 4.4, -3), DARK)
    it.part("TVScreen", (0.1, 3, 5), F(1.05, 4.4, -3), rgb(20, 30, 45), "Glass", screen="Right")
    sofa(it, F(5.6, 0, -3) @ ANG(0, math.pi / 2, 0), rgb(200, 110, 90), 5.2)  # faces -X, toward the TV
    table4(it, "CoffeeTable", F(3.3, 0, -3), 2.2, 3.4, 1.5, WOOD)
    it.part("Rug", (7, 0.1, 7.5), F(4, 0.05, -3), rgb(220, 200, 150), "Fabric")
    it.part("Bookshelf", (4.4, 8, 1.4), F(4.5, 4, 9.2), WOOD, "Wood")
    books = (rgb(200, 60, 60), rgb(60, 120, 200), rgb(240, 190, 60), rgb(90, 170, 100))
    for row in range(3):
        for i in range(4):
            it.part("Book", (0.7, 1.6, 1), F(3.2 + i * 0.9, 1.3 + row * 2.6, 8.7), books[(i + row) % 4])
    it.part("LampPole", (0.3, 5.6, 0.3), F(1.5, 2.8, 7.8), DARK, "Metal")
    it.part("LampShade", (1.4, 1, 1.4), F(1.5, 6, 7.8), rgb(255, 235, 200), "Neon")
    it.light(F(1.5, 6, 7.8), 0.8, 11, name="FloorLampLight")
    it.part("PlantPot", (1.4, 1.4, 1.4), F(6.5, 0.7, -8.6) @ ANG(0, 0, math.pi / 2), rgb(190, 110, 70),
            "SmoothPlastic", "Cylinder")
    it.part("Plant", (2.4, 2.4, 2.4), F(6.5, 2.4, -8.6), rgb(80, 150, 70), "Grass", "Ball")
    ceiling_lamp(it, F(4, 11.1, -1))

    # Bedroom upstairs (whole floor apart from the stairwell)
    bed(it, U(-5.5, 0, 5.5), rgb(240, 150, 90))
    it.part("Nightstand", (2, 2.2, 1.8), U(-9.6, 1.1, 8.8), WOOD, "Wood")
    it.part("LampBase", (0.5, 1, 0.5), U(-9.6, 2.7, 8.8), DARK, "Metal")
    it.part("LampShade", (1.2, 0.9, 1.2), U(-9.6, 3.6, 8.8), rgb(255, 230, 180), "Neon")
    it.light(U(-9.6, 3.6, 8.8), 0.7, 9, name="BedsideLight")
    it.part("Wardrobe", (2.4, 8.5, 5), U(-9.6, 4.25, -4), rgb(235, 225, 205), "Wood")
    table4(it, "Desk", U(5, 0, 8.6), 4.5, 2.4, 3.2, rgb(235, 225, 205))
    it.part("Laptop", (1.6, 0.1, 1.2), U(5, 3.25, 8.6), DARK, "Metal")
    chair(it, U(5, 0, 6.4) @ ANG(0, math.pi, 0), rgb(90, 140, 200))  # faces the desk (+Z)
    it.part("Rug", (7, 0.1, 5), U(0, 0.05, 0.5), rgb(120, 170, 140), "Fabric")
    it.part("Poster", (3, 4, 0.2), U(0, 6.2, 9.4), rgb(255, 200, 60))
    ceiling_lamp(it, U(0, 10.9, 0))
    it.part("Ceiling", (22, 0.1, 20), L(0, 23.6, 0), rgb(245, 242, 235))  # hides the roof's underside

    # Camera mounts (outside the front, i.e. through the cutaway wall) and character spots
    b.marker("Cam_House_Kitchen", P(L(-5.5, 6, -24)), P(F(-5.5, 3, 2)))
    b.marker("Cam_House_Living", P(L(5, 6, -24)), P(F(4, 3, -1)))
    b.marker("Cam_House_Bedroom", P(L(0, 18.5, -25)), P(U(-1, 3, 3)))
    b.marker("Cam_House_Dollhouse", P(L(0, 13, -40)), P(L(0, 11, 0)))
    b.marker("Mark_House_FrontDoor", P(L(0, 0.35, -13)))
    b.marker("Mark_House_Kitchen", P(F(-5.5, 0, -6.5)))
    b.marker("Mark_House_Sofa", P(F(5.4, 1.9, -3)))
    b.marker("Mark_House_TV", P(F(3, 0, 3)))
    b.marker("Mark_House_Bed", P(U(-5.5, 1.9, 5)))
    b.marker("Mark_House_Desk", P(U(5, 0, 6)))


def _garage(b):
    """Shell: centre (142.5, 129), front faces -Z, 13 x 18, one storey of 10. Inner x -5.5..5.5, z -8..8."""
    it = b.into("Garage", group="Interior")
    kt = b.into("Garage", group="GoKart")

    def G(x, y, z):
        return CF(142.5 + x, 0.9 + y, 129 + z)

    table4(it, "Workbench", G(0, 0, 7), 8, 2.2, 3.4, WOOD)
    it.part("Pegboard", (8, 3.2, 0.2), G(0, 5.6, 7.9), rgb(200, 170, 120), "Wood")
    it.part("HammerHandle", (0.25, 1.8, 0.2), G(-2.5, 5.4, 7.7), WOOD, "Wood")
    it.part("HammerHead", (1, 0.4, 0.3), G(-2.5, 6.3, 7.7), DARK, "Metal")
    it.part("Wrench", (0.3, 2, 0.15), G(-1, 5.6, 7.7) @ ANG(0, 0, math.radians(20)), rgb(180, 185, 190), "Metal")
    it.part("SawBlade", (2.6, 0.8, 0.1), G(1.6, 6, 7.7), rgb(190, 195, 200), "Metal")
    it.part("SawHandle", (0.8, 0.9, 0.2), G(3.2, 6, 7.7), rgb(200, 60, 50))
    it.part("Shelf", (2, 0.3, 7), G(-5, 4, -1), WOOD, "Wood")
    it.part("PaintCan", (1, 1.1, 1.1), G(-5, 4.7, -3) @ ANG(0, 0, math.pi / 2), rgb(60, 120, 200), "Metal", "Cylinder")
    it.part("PaintCan", (1, 1.1, 1.1), G(-5, 4.7, -1.5) @ ANG(0, 0, math.pi / 2), rgb(230, 190, 50), "Metal",
            "Cylinder")
    it.part("Box", (1.8, 1.4, 2), G(-5, 4.85, 1.5), rgb(190, 150, 100), "Cardboard")
    # Half-built go-kart (the episode 7 project)
    kt.part("Chassis", (3, 0.4, 5.5), G(0, 0.9, -1), rgb(220, 60, 50), "Metal")
    for ox, oz in ((-1.7, -2.8), (1.7, -2.8), (-1.7, 0.8)):
        kt.part("Wheel", (0.8, 1.6, 1.6), G(ox, 0.8, -1 + oz), DARK, "Rubber", "Cylinder")
    kt.part("LooseWheel", (0.8, 1.6, 1.6), G(2.8, 0.4, 3) @ ANG(0, 0, math.pi / 2), DARK, "Rubber", "Cylinder")
    kt.part("Seat", (2, 1.4, 1.6), G(0, 1.8, 0.3), DARK, "Fabric")
    kt.part("SteeringColumn", (0.2, 1.4, 0.2), G(0, 1.8, -2.4) @ ANG(math.radians(-30), 0, 0), rgb(180, 185, 190), "Metal")
    kt.part("SteeringWheel", (0.2, 1.4, 1.4), G(0, 2.5, -2.8) @ ANG(0, math.pi / 2, math.radians(60)), DARK, "Rubber",
            "Cylinder")
    ceiling_lamp(it, G(0, 8.6, 0), 1.3, 20)
    b.marker("Cam_Garage", P(G(0, 5, -22)), P(G(0, 2, 1)))
    b.marker("Mark_Garage_Bench", P(G(0, 0, 4.8)))
    b.marker("Mark_Garage_Kart", P(G(-2.6, 0, -1)))


def _school(b):
    """Shell: centre (0, 155), front faces -Z, 80 x 30, two storeys of 12. Inner x -39..39, z -14..14.
    Ground floor: hallway (z -14..-8, lockers, stairs) | cafeteria (west) and hall with stage (east).
    Upstairs: Classroom A (west) and Classroom B (east)."""
    sb = b.into("School")
    it = b.into("School", group="Interior")

    def S(x, y, z):
        return CF(x, 0.55 + y, 155 + z)

    def F(x, y, z):
        return S(x, 0.35 + y, z)

    def U(x, y, z):
        return S(x, 12.35 + y, z)

    # Stairs in the hallway's west end, rising east; hole in the upstairs floor above them.
    slab_with_hole(sb, "Floor2", S, 12, 78, 28, (-38.5, -24, -14, -10))
    stairs(it, F(-38, 0, -12) @ ANG(0, -math.pi / 2, 0), 3, 13, 12, 1, rgb(150, 150, 155))
    railing(it, P(U(-38.5, 0, -9.8)), P(U(-24, 0, -9.8)), rgb(60, 110, 190))

    # Hallway back wall (cutaway, so the rooms behind can be filmed), with doorways to both rooms.
    hw = b.into("School", group="Interior", cutaway=1, cutaway_group="HallwayWall")
    wall_with_gaps(hw, "HallwayWall", F(0, 0, -8), 78, 11.3, CREAM, [(-20, -15, 0, 8.5), (15, 20, 0, 8.5)])
    locker_colors = (rgb(60, 110, 190), rgb(70, 125, 205))

    def locker_run(x0, x1):
        i, x = 0, x0
        while x <= x1 - 1.9 + 1e-9:
            i += 1
            hw.part("Locker", (1.9, 7, 1.4), F(x + 0.95, 3.5, -9.2), locker_colors[(i % 2)], "Metal")
            hw.part("Vent", (1.2, 0.8, 0.1), F(x + 0.95, 6, -9.95), DARK, "Metal")
            hw.part("Handle", (0.15, 0.6, 0.15), F(x + 1.6, 3.6, -9.95), rgb(200, 200, 205), "Metal")
            x += 2

    locker_run(-14, 14)
    locker_run(21, 38)
    it.part("HallFloorStripe", (60, 0.05, 0.6), F(0, 0.03, -11), rgb(240, 200, 60))
    for x in (-12, 12, 30):
        ceiling_lamp(it, F(x, 11.1, -11), 1.2, 20)

    wall_with_gaps(it, "Divider", F(0, 0, 3) @ ANG(0, math.pi / 2, 0), 22, 11.3, CREAM, [])

    # Cafeteria (x -39..0)
    it.part("ServingCounter", (20, 3.4, 2.4), F(-20, 1.7, 12.6), rgb(200, 205, 210), "Metal")
    it.part("CounterTop", (20.4, 0.3, 2.8), F(-20, 3.55, 12.5), rgb(170, 175, 180), "Metal")
    foods = (rgb(240, 200, 80), rgb(110, 170, 80), rgb(200, 90, 60), rgb(240, 240, 230))
    for i in range(6):
        it.part("FoodTray", (2.4, 0.3, 1.6), F(-27.5 + i * 3, 3.85, 12.5), rgb(150, 155, 160), "Metal")
        it.part("Food", (1.8, 0.4, 1.1), F(-27.5 + i * 3, 4.1, 12.5), foods[i % 4])
    size, cf = (10, 3, 0.2), F(-20, 7.5, 13.85)
    menu = it.part("MenuBoard", size, cf, rgb(40, 60, 50))
    it.sign_text(menu, size, cf, "LUNCH: PIZZA FRIDAY!", rgb(250, 245, 220))
    for z in (-3.5, 3.5):
        table4(it, "LunchTable", F(-20, 0, z), 20, 3.2, 2.8, rgb(230, 225, 210))
        it.part("Bench", (20, 0.4, 1.1), F(-20, 1.7, z - 2.4), rgb(60, 110, 190))
        it.part("Bench", (20, 0.4, 1.1), F(-20, 1.7, z + 2.4), rgb(60, 110, 190))
        it.part("BenchLegs", (18, 1.5, 0.4), F(-20, 0.75, z - 2.4), DARK, "Metal")
        it.part("BenchLegs", (18, 1.5, 0.4), F(-20, 0.75, z + 2.4), DARK, "Metal")
    for i in range(4):
        it.part("LunchTrayOnTable", (1.8, 0.2, 1.3), F(-28 + i * 5, 2.9, -3.5 + (-0.8 if i % 2 == 0 else 0.8)),
                rgb(240, 120, 90))
    for x in (-30, -10):
        ceiling_lamp(it, F(x, 11.1, 3), 1.3, 26)

    # Hall with a stage (x 0..39)
    hl = b.into("School", group="Hall")
    hl.part("Stage", (36, 2.5, 7), F(20, 1.25, 10.5), rgb(150, 105, 70), "WoodPlanks")
    hl.part("StageLip", (36, 0.4, 0.4), F(20, 2.45, 6.9), rgb(240, 200, 60))
    hl.part("Backdrop", (36, 8.8, 0.4), F(20, 6.9, 13.7), rgb(120, 30, 40), "Fabric")
    hl.part("CurtainL", (3, 8.8, 0.6), F(3.5, 6.9, 7.6), rgb(170, 30, 40), "Fabric")
    hl.part("CurtainR", (3, 8.8, 0.6), F(36.5, 6.9, 7.6), rgb(170, 30, 40), "Fabric")
    size, cf = (16, 2.4, 0.2), F(20, 9.4, 13.4)
    banner = hl.part("Banner", size, cf, rgb(250, 245, 230))
    hl.sign_text(banner, size, cf, "SCIENCE FAIR", rgb(40, 70, 140))
    hl.part("Podium", (2.4, 3.4, 1.8), F(20, 4.2, 9.5), WOOD, "Wood")
    hl.part("Microphone", (0.2, 1, 0.2), F(20, 6.4, 9.1), DARK, "Metal")
    for z in (-5, -2, 1):
        for x in range(8, 33, 3):
            chair(hl, F(x, 0, z) @ ANG(0, math.pi, 0), rgb(60, 110, 190), 0.85)
    spot = LOOK(P(F(20, 10.8, -2)), P(F(20, 4, 9.5)))
    hl.part("Spotlight", (1, 1, 1.4), spot, DARK, "Metal")
    hl.light(spot, 3, 30, rgb(255, 240, 210), kind="SPOT", angle=35, name="StageSpot")
    for x in (10, 30):
        ceiling_lamp(hl, F(x, 11.1, 0), 1.2, 26)

    # Upstairs classrooms
    wall_with_gaps(it, "ClassDivider", U(0, 0, 0) @ ANG(0, math.pi / 2, 0), 28, 11.3, CREAM, [])

    def classroom(cx, name, board_text, desk_color):
        rm = b.into("School", group=name)
        size, cf = (14, 4.6, 0.2), U(cx, 5.6, 13.4)
        board = rm.part("Whiteboard", size, cf, WHITE)
        rm.sign_text(board, size, cf, board_text, rgb(40, 70, 160))
        rm.part("BoardFrame", (14.6, 5.2, 0.15), U(cx, 5.6, 13.5), rgb(150, 150, 155), "Metal")
        rm.part("BoardTray", (14, 0.25, 0.6), U(cx, 3.2, 13.2), rgb(150, 150, 155), "Metal")
        table4(rm, "TeacherDesk", U(cx + 9, 0, 9), 5, 2.6, 3.2, WOOD)
        rm.part("Apple", (0.6, 0.6, 0.6), U(cx + 10.5, 3.5, 9), rgb(210, 40, 40), "SmoothPlastic", "Ball")
        rm.part("Clock", (0.2, 2, 2), U(cx - 11, 9, 13.6) @ ANG(0, math.pi / 2, 0), WHITE, "SmoothPlastic", "Cylinder")
        for z in (-6, -1, 4):
            for dx in (-13, -6.5, 0, 6.5, 13):
                x = cx + dx
                if not (x < -23 and z < -9):  # the stairwell
                    table4(rm, "StudentDesk", U(x, 0, z), 2.6, 2, 2.8, desk_color)
                    chair(rm, U(x, 0, z - 1.8) @ ANG(0, math.pi, 0), rgb(60, 110, 190), 0.85)
        for dx in (-9, 9):
            ceiling_lamp(rm, U(cx + dx, 10.9, 0), 1.2, 24)

    classroom(-20, "ClassroomA", "2 + 2 = ?", rgb(235, 225, 205))
    classroom(20, "ClassroomB", "Be kind :)", rgb(210, 230, 210))

    # Camera mounts from the schoolyard, through the cutaway front wall
    b.marker("Cam_School_Hallway", P(S(0, 6, -30)), P(F(0, 3, -10)))
    b.marker("Cam_School_Cafeteria", P(S(-20, 7, -30)), P(F(-20, 3, 4)))
    b.marker("Cam_School_Hall", P(S(20, 8, -30)), P(F(20, 3, 8)))
    b.marker("Cam_School_ClassroomA", P(S(-20, 18.5, -30)), P(U(-20, 3, 6)))
    b.marker("Cam_School_ClassroomB", P(S(20, 18.5, -30)), P(U(20, 3, 6)))
    b.marker("Mark_School_Lockers", P(F(0, 0, -11.5)))
    b.marker("Mark_School_CafeTable", P(F(-20, 0, -6.4)))
    b.marker("Mark_School_Stage", P(F(20, 2.5, 8.5)))
    b.marker("Mark_School_Podium", P(F(20, 2.5, 8.2)))
    b.marker("Mark_School_ClassA_Front", P(U(-20, 0, 10)))
    b.marker("Mark_School_ClassB_Front", P(U(20, 0, 10)))


# --- entry point -------------------------------------------------------------------------------

def build_town():
    """Build the whole town into a `Town` collection (call once per episode build)."""
    import time
    t0 = time.perf_counter()
    _mats.clear()
    coll = bpy.data.collections.new("Town")
    bpy.context.scene.collection.children.link(coll)
    town = Town(coll)
    b = _Builder(town)
    _ep01_map(b)
    _ep01_extras(b)
    _town_phase1(b)
    _hero_house(b)
    _garage(b)
    _school(b)
    _fit_signs(b)
    town.build_seconds = time.perf_counter() - t0
    return town
