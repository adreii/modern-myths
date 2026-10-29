"""Use real models exported from Roblox Studio (right-click → Export Selection → .obj).

- Characters: an R6 avatar export (parts named Head / Torso / Left Arm / Right Arm /
  Left Leg / Right Leg; accessories ride on the nearest part) becomes a posable Rig,
  so every shot helper (wave, reach, nod, look, talk…) works on it unchanged.
- Sets: any exported build (a bedroom, a kitchen, a whole map) can be placed in a shot.

Files are listed per episode in `cast.yaml` (see episodes/ep01_toys/cast.yaml).
Each file is imported once; every use is a cheap copy sharing the same meshes.
"""
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from .toys import Rig

ROOT = Path(__file__).resolve().parent.parent
CAST = {"characters": {}, "sets": {}, "turn": 0.0, "stud": 1 / 5.2}

R6 = {"head": "head", "torso": "torso", "arm_l": "left arm", "arm_r": "right arm",
      "leg_l": "left leg", "leg_r": "right leg"}
_cache = {}


def load_cast(path):
    import yaml
    if Path(path).exists():
        CAST.update({k: v for k, v in (yaml.safe_load(Path(path).read_text()) or {}).items() if v is not None})
    CAST.setdefault("characters", {})
    CAST.setdefault("sets", {})


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
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
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


def _bounds(o):
    xs, ys, zs = zip(*(v.co for v in o.data.vertices))
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def roblox_avatar(s, style, loc=(0, 0, 0), h=1.0, rot_z=0, parent=None):
    """An imported R6 avatar as a Rig (root scaled to height h)."""
    import math
    src = _import(CAST["characters"][style], normalize_height=1.0)
    parts = {k: None for k in R6}
    for o in src:
        n = o.name.lower().replace("_", " ")
        for k, label in R6.items():
            if label in n and parts[k] is None:
                parts[k] = o
    missing = [R6[k] for k, o in parts.items() if o is None]
    if missing:
        raise ValueError(f"{CAST['characters'][style]}: no parts named {missing} (is it an R6 rig?)")
    b = {k: _bounds(o) for k, o in parts.items()}
    torso_top = b["torso"][1].z
    pivots = {  # joint positions derived from the part boxes
        "neck": Vector((0, 0, torso_top)),
        "arm_l": Vector(((b["arm_l"][0].x + b["arm_l"][1].x) / 2, 0, b["arm_l"][1].z - (b["arm_l"][1].x - b["arm_l"][0].x) / 2)),
        "arm_r": Vector(((b["arm_r"][0].x + b["arm_r"][1].x) / 2, 0, b["arm_r"][1].z - (b["arm_r"][1].x - b["arm_r"][0].x) / 2)),
        "leg_l": Vector(((b["leg_l"][0].x + b["leg_l"][1].x) / 2, 0, b["leg_l"][1].z)),
        "leg_r": Vector(((b["leg_r"][0].x + b["leg_r"][1].x) / 2, 0, b["leg_r"][1].z)),
    }
    if pivots["arm_l"].x > pivots["arm_r"].x:  # rig convention: arm_l is at -X
        pivots["arm_l"], pivots["arm_r"] = pivots["arm_r"], pivots["arm_l"]
        parts["arm_l"], parts["arm_r"] = parts["arm_r"], parts["arm_l"]

    root = s.empty(f"roblox_{style}", loc, parent)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (h, h, h)
    joints = {j: s.empty(j, p, root) for j, p in pivots.items()}
    owner = {"head": "neck", "arm_l": "arm_l", "arm_r": "arm_r", "leg_l": "leg_l", "leg_r": "leg_r"}

    def attach(o, joint):
        c = o.copy()  # shares mesh + materials with the imported original
        if joint is None:
            s.adopt(c, root)
        else:
            s.adopt(c, joints[joint], tuple(-pivots[joint]))
        return c

    made = {k: attach(o, owner.get(k)) for k, o in parts.items()}
    # accessories (hair, hats, faces as separate meshes): ride on the closest part
    for o in src:
        if o in parts.values():
            continue
        lo, hi = _bounds(o)
        z = (lo.z + hi.z) / 2
        attach(o, "neck" if z > torso_top else None)
    return Rig(root, made["torso"], joints["neck"], made["head"], joints["arm_l"], joints["arm_r"], h)


def set_piece(s, name, loc=(0, 0, 0), rot_z=0, scale=1.0):
    """Place an imported build (cast.yaml `sets:`) in a shot, in stud units."""
    import math
    root = s.empty(f"set_{name}", loc)
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (scale,) * 3
    for o in _import(CAST["sets"][name]):
        s.adopt(o.copy(), root)
    return root
