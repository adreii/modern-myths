"""Use real models exported from Roblox Studio (right-click → Export Selection → .obj).

- Characters: an R6 or R15 avatar export (parts named Head / Torso / Left Arm … or
  Head / UpperTorso / LeftUpperArm / LeftHand …; accessories ride on the nearest part)
  becomes a posable Rig, so every shot helper (wave, reach, nod, look, talk…) works on it
  unchanged. R15 limbs move as one piece from the shoulder or hip.
- Avatars: one exported body (`body:` in cast.yaml) is repainted per character from
  `avatars.json`, the body colours and scale read out of Studio by
  roblox/Tools/DumpAvatars.luau. A cast entry that isn't a file path names an avatar there.
- Faces: a face image from assets/faces/ is stuck on the front of the head (`faces:` in
  cast.yaml sets each role's default); `face(s, rig, "surprised", t)` changes expression.
- Sets: any exported build (a bedroom, a kitchen, a whole map) can be placed in a shot.

Files are listed per episode in `cast.yaml` (see episodes/ep01_toys/cast.yaml).
Each file is imported once; every use is a cheap copy sharing the same meshes.
"""
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from .toys import Rig

ROOT = Path(__file__).resolve().parent.parent
CAST = {"characters": {}, "sets": {}, "faces": {}, "turn": 0.0, "stud": 1 / 5.2,
        "body": None, "avatars": "assets/roblox/avatars.json"}
FACES = ROOT / "assets" / "faces"

# body part -> name fragments (lowercase, spaces/underscores removed), R6 and R15;
# limbs come before torso/head so "LeftUpperArm" never counts as anything else
PARTS = {
    "arm_l": ("leftarm", "leftupperarm", "leftlowerarm", "lefthand"),
    "arm_r": ("rightarm", "rightupperarm", "rightlowerarm", "righthand"),
    "leg_l": ("leftleg", "leftupperleg", "leftlowerleg", "leftfoot"),
    "leg_r": ("rightleg", "rightupperleg", "rightlowerleg", "rightfoot"),
    "torso": ("torso",),  # Torso, UpperTorso, LowerTorso
    "head": ("head",),
}
_cache = {}


def load_cast(path):
    import yaml
    if Path(path).exists():
        CAST.update({k: v for k, v in (yaml.safe_load(Path(path).read_text()) or {}).items() if v is not None})
    CAST.setdefault("characters", {})
    CAST.setdefault("sets", {})
    CAST.setdefault("faces", {})
    CAST.pop("_avatars", None)


def has_character(style):
    return bool(CAST["characters"].get(style))


def has_set(name):
    return bool(CAST["sets"].get(name))


def _import(path, normalize_height=None):
    """Import an OBJ once. Meshes are baked into a clean frame: Z up, facing -Y,
    centred on the origin with feet/floor at z=0, and (optionally) a given height."""
    path = (ROOT / path).resolve()
    key = (str(path), normalize_height)
    if key in _cache:
        return _cache[key]
    if not path.exists():
        raise FileNotFoundError(f"cast file missing: {path}")
    before = set(bpy.data.objects)
    # Studio writes each part as a group (g), not an object (o): split on both
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y", use_split_groups=True)
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    turn = Matrix.Rotation(float(CAST.get("turn", 0)) * 3.14159265 / 180, 4, "Z")
    for o in objs:  # bake transforms so every part lives in one shared space
        o.data.transform(turn @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    pts = [v.co for o in objs for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    k = normalize_height / (hi.z - lo.z) if normalize_height else float(CAST.get("stud", 1 / 5.2))
    shift = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for o in objs:
        o.data.transform(Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation(-shift))
        for c in list(o.users_collection):
            c.objects.unlink(o)  # keep the originals out of the scene; shots get copies
    _cache[key] = objs
    return objs


def _drop_eyes(o):
    """Remove the export's eye ovals from a head mesh (once; copies share it): the small loose
    pieces on the front of the face at eye height. The face plane draws the eyes instead. The
    mouth and the rest of the head stay. Frame from _import: height 1, facing -Y."""
    if o.get("eyes_dropped"):
        return
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    seen, drop = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        comp, stack = [], [v]
        seen.add(v)
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        ys = [c.co.y for c in comp]
        zs = [c.co.z for c in comp]
        if len(comp) < 100 and max(ys) < -0.09 and min(zs) > 0.88 and max(zs) < 0.99:
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="VERTS")
        bm.to_mesh(o.data)
        o.data.update()
    bm.free()
    o["eyes_dropped"] = len(drop)


def _part_of(o):
    """Which body part a mesh is, "skip" for the invisible root, None for accessories."""
    n = o.name.split(".")[0].lower().replace(" ", "").replace("_", "")
    if "rootpart" in n:
        return "skip"
    return next((k for k, frags in PARTS.items() if any(f in n for f in frags)), None)


def _parts_by_position(objs):
    """Body parts from where the meshes sit, for exports whose names say nothing
    (Studio names R15 groups Hero1, Hero2 …). Needs the baked frame from _import:
    height 1, feet at z=0, facing -Y, so the avatar's own left is +X."""
    centre = {o: (lambda b: (b[0] + b[1]) / 2)(_bounds(o)) for o in objs}
    head = max(objs, key=lambda o: centre[o].z)
    kind = {}
    for o in objs:
        c = centre[o]
        if o is head:
            kind[o] = "head"
        elif abs(c.x) > 0.18:  # arms hang outside the torso (~±0.27; legs ~±0.09)
            kind[o] = "arm_l" if c.x > 0 else "arm_r"
        elif c.z < 0.36:  # below the hip
            kind[o] = "leg_l" if c.x > 0 else "leg_r"
        else:
            kind[o] = "torso"
    return kind


def avatar(name):
    """One avatar's entry in avatars.json: {"colors": {part: [r, g, b]}, "scale": …}."""
    import json
    if "_avatars" not in CAST:
        path = ROOT / CAST["avatars"]
        CAST["_avatars"] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if name not in CAST["_avatars"]:
        raise KeyError(f"avatar {name!r} not in {CAST['avatars']} (rerun roblox/Tools/DumpAvatars.luau)")
    return CAST["_avatars"][name]


def _linear(c):  # Roblox colours are sRGB; Blender materials want linear
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def _bounds(o):
    xs, ys, zs = zip(*(v.co for v in o.data.vertices))
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def roblox_avatar(s, style, loc=(0, 0, 0), h=1.0, rot_z=0, parent=None):
    """An imported R6/R15 avatar as a Rig (root scaled to height h, times the avatar's
    own scale when it comes from avatars.json)."""
    import math
    from .core import mat
    entry = CAST["characters"][style]
    look = None
    if not str(entry).lower().endswith(".obj"):  # an avatar name: shared body, own colours
        look = avatar(entry)
        h *= look.get("scale", 1.0)
        entry = CAST["body"]
        if not entry:
            raise ValueError(f"{style}: avatar {CAST['characters'][style]!r} needs `body:` in cast.yaml")
    src = _import(entry, normalize_height=1.0)
    kind = {o: _part_of(o) for o in src}
    if not any(k in ("head", "torso") for k in kind.values()):  # unnamed parts
        kind = _parts_by_position(src)
    groups = {k: [o for o in src if kind[o] == k] for k in PARTS}
    missing = [k for k, g in groups.items() if not g]
    if missing:
        raise ValueError(f"{entry}: no parts for {missing} (meshes: {[o.name for o in src]})")

    def bounds(objs):
        bs = [_bounds(o) for o in objs]
        return (Vector([min(b[0][i] for b in bs) for i in range(3)]),
                Vector([max(b[1][i] for b in bs) for i in range(3)]))

    b = {k: bounds(g) for k, g in groups.items()}
    torso_top = b["torso"][1].z

    def shoulder(k):
        lo, hi = b[k]
        return Vector(((lo.x + hi.x) / 2, 0, hi.z - min(hi.x - lo.x, hi.z - lo.z) / 2))

    pivots = {  # joint positions derived from the part boxes
        "neck": Vector((0, 0, torso_top)),
        "arm_l": shoulder("arm_l"),
        "arm_r": shoulder("arm_r"),
        "leg_l": Vector(((b["leg_l"][0].x + b["leg_l"][1].x) / 2, 0, b["leg_l"][1].z)),
        "leg_r": Vector(((b["leg_r"][0].x + b["leg_r"][1].x) / 2, 0, b["leg_r"][1].z)),
    }
    # rig convention: arm_l is at -X. Colours stay with the avatar's own parts (kind).
    for l, r in (("arm_l", "arm_r"), ("leg_l", "leg_r")):
        if pivots[l].x > pivots[r].x:
            pivots[l], pivots[r] = pivots[r], pivots[l]
            groups[l], groups[r] = groups[r], groups[l]

    root = s.empty(f"roblox_{style}", loc, parent)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (h, h, h)
    joints = {j: s.empty(j, p, root) for j, p in pivots.items()}
    owner = {"head": "neck", "arm_l": "arm_l", "arm_r": "arm_r", "leg_l": "leg_l", "leg_r": "leg_r"}

    def attach(o, joint):
        c = o.copy()  # shares mesh + materials with the imported original
        if look and kind[o] in look["colors"]:
            c.data = o.data.copy()  # own mesh so its material can change
            c.data.materials.clear()
            c.data.materials.append(mat(_linear(look["colors"][kind[o]]), rough=0.35))
        if joint is None:
            s.adopt(c, root)
        else:
            s.adopt(c, joints[joint], tuple(-pivots[joint]))
        return c

    for o in groups["head"]:  # the face plane does the eyes
        _drop_eyes(o)
    made = {k: [attach(o, owner.get(k)) for o in g] for k, g in groups.items()}
    # accessories (hair, hats, faces as separate meshes): ride on the closest part
    for o in src:
        if kind[o] is not None:
            continue
        lo, hi = _bounds(o)
        attach(o, "neck" if (lo.z + hi.z) / 2 > torso_top else None)
    rig = Rig(root, made["torso"][0], joints["neck"], made["head"][0], joints["arm_l"], joints["arm_r"], h)
    rig.leg_l, rig.leg_r = joints["leg_l"], joints["leg_r"]  # hip joints, for lib/acting.py
    # face decals hang on the neck joint, just in front of the head (characters face -Y)
    lo, hi = b["head"]
    size = min(hi.x - lo.x, hi.z - lo.z) * 0.9
    rig.face_at = (joints["neck"], Vector(((lo.x + hi.x) / 2, lo.y - 0.004, (lo.z + hi.z) / 2)) - pivots["neck"], size)
    rig.faces = {}
    # the head mesh's origin sits at the feet, so cameras aim at this point instead
    rig.head_centre = s.empty(f"{root.name}_head", tuple((lo + hi) / 2 - pivots["neck"]), joints["neck"])
    default = CAST["faces"].get(style) or (look or {}).get("face") or ("neutral" if look else None)
    if default:
        face(s, rig, default)
    return rig


def _face_plane(s, rig, name):
    """A square, image-textured plane for one expression, parented to the neck joint."""
    path = FACES / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"no face {name!r}: add {path} (or run pipeline/make_faces.py)")
    joint, loc, size = rig.face_at
    d = size / 2
    me = bpy.data.meshes.new(f"face_{name}")
    me.from_pydata([(-d, 0, -d), (d, 0, -d), (d, 0, d), (-d, 0, d)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for li, co in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = co
    key = f"face_{name}"
    m = bpy.data.materials.get(key)
    if m is None:
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        nt = m.node_tree
        p = nt.nodes["Principled BSDF"]
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(path), check_existing=True)
        tex.interpolation = "Cubic"
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
        nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
        p.inputs["Roughness"].default_value = 0.6
    me.materials.append(m)
    ob = s.adopt(bpy.data.objects.new(f"face_{name}", me), joint, tuple(loc))
    ob.scale = (0, 0, 0)  # hidden until face() shows it
    ob.visible_shadow = False  # a face card never casts a shadow
    return ob


def face(s, rig, name, t=0.0):
    """Show expression `name` (assets/faces/<name>.png) from shot time t on."""
    from .core import key
    frame = s.f(t)
    if name not in rig.faces:
        rig.faces[name] = _face_plane(s, rig, name)
        if frame > s.f0:  # a face that only appears later is hidden until then
            key(rig.faces[name], "scale", (0, 0, 0), s.f0, "CONSTANT")
    for n, ob in rig.faces.items():
        key(ob, "scale", (1, 1, 1) if n == name else (0, 0, 0), frame, "CONSTANT")


def set_piece(s, name, loc=(0, 0, 0), rot_z=0, scale=1.0):
    """Place an imported build (cast.yaml `sets:`) in a shot, in stud units."""
    import math
    root = s.empty(f"set_{name}", loc)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (scale,) * 3
    for o in _import(CAST["sets"][name]):
        s.adopt(o.copy(), root)
    return root
