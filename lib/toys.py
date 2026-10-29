"""The toy-world kit: peg-doll characters, rooms and props.

Convention: characters face -Y (toward a camera placed at negative Y).
Peg-doll height is `h` (kid ~1.0, grown-up ~1.5).
"""
import math
from dataclasses import dataclass

import bpy

from .core import STYLE, ball, baseplate_mat, box, cyl, key, light, mat, ring, world_key


# --- characters ------------------------------------------------------------------

@dataclass
class Rig:
    root: bpy.types.Object
    body: bpy.types.Object
    neck: bpy.types.Object
    head: bpy.types.Object
    arm_l: bpy.types.Object
    arm_r: bpy.types.Object
    h: float


def peg(s, loc=(0, 0, 0), h=1.0, shirt="red", hair="hair", style="kid", rot_z=0, parent=None, skin="skin"):
    """A character. style: kid | grandpa | baby | soldier. Look depends on the global STYLE."""
    if STYLE["name"] == "brick":
        from .imported import has_character, roblox_avatar
        if has_character(style):  # a real avatar exported from Roblox Studio
            return roblox_avatar(s, style, loc, h, rot_z, parent)
        return brick_avatar(s, loc, h, shirt, hair, style, rot_z, parent)
    root = s.empty(f"peg_{style}", loc, parent)
    root.rotation_euler.z = math.radians(rot_z)
    body = cyl(s, 0.30 * h, 0.58 * h, shirt, (0, 0, 0.29 * h), parent=root, r2=0.22 * h, bevel=0.03 * h)
    cyl(s, 0.31 * h, 0.06 * h, "wood_light", (0, 0, 0.03 * h), parent=root)  # base
    neck = s.empty("neck", (0, 0, 0.56 * h), root)
    head = ball(s, 0.24 * h, skin, (0, 0, 0.21 * h), parent=neck)
    # face
    for sx in (-1, 1):
        ball(s, 0.032 * h, "black", (sx * 0.085 * h, -0.21 * h, 0.03 * h), parent=head, rough=0.2)
        ball(s, 0.038 * h, "pink", (sx * 0.14 * h, -0.175 * h, -0.05 * h), scale=(1, 0.5, 0.8), parent=head)
    ball(s, 0.03 * h, "skin", (0, -0.235 * h, -0.01 * h), parent=head)  # nose
    # hair / hats
    if style == "kid":
        ball(s, 0.245 * h, hair, (0, 0.07 * h, 0.065 * h), parent=head)
    elif style == "grandpa":
        for sx in (-1, 1):
            ball(s, 0.08 * h, "white", (sx * 0.2 * h, 0.05 * h, 0.02 * h), parent=head)
            ring(s, 0.058 * h, 0.009 * h, "black", (sx * 0.085 * h, -0.225 * h, 0.03 * h), (90, 0, 0), parent=head)
        ball(s, 0.075 * h, "white", (0, -0.215 * h, -0.075 * h), scale=(1.3, 0.5, 0.45), parent=head)  # mustache
    elif style == "baby":
        ball(s, 0.26 * h, "pink", (0, 0.06 * h, 0.04 * h), scale=(1, 0.9, 1), parent=head)  # bonnet
    elif style == "soldier":
        cyl(s, 0.17 * h, 0.36 * h, "black", (0, 0, 0.32 * h), parent=head, r2=0.19 * h)
        box(s, (0.3 * h, 0.08 * h, 0.03 * h), "black", (0, -0.17 * h, 0.15 * h), parent=head, bevel=0.01)
        ball(s, 0.035 * h, "gold", (0, -0.17 * h, 0.4 * h), parent=head)
        for z in (0.2, 0.32, 0.44):
            ball(s, 0.03 * h, "gold", (0, -(0.30 - 0.138 * z) * h, z * h), parent=root)
    arms = []
    for sx in (-1, 1):
        sh = s.empty("shoulder", (sx * 0.27 * h, 0, 0.5 * h), root)
        cyl(s, 0.055 * h, 0.3 * h, shirt, (0, 0, -0.13 * h), parent=sh)
        ball(s, 0.07 * h, skin, (0, 0, -0.3 * h), parent=sh)
        sh.rotation_euler.y = math.radians(-sx * 12)
        arms.append(sh)
    return Rig(root, body, neck, head, arms[0], arms[1], h)


PANTS = {"kid": "blue", "grandpa": (0.35, 0.22, 0.12), "baby": "white", "soldier": "black"}


def brick_avatar(s, loc=(0, 0, 0), h=1.0, shirt="red", hair="hair", style="kid", rot_z=0, parent=None):
    """Blocky game avatar: box legs/torso/arms, rounded head, painted-on face.
    Proportions follow the classic 5-unit blocky rig (2 legs, 2 torso, ~1.2 head)."""
    u = h / 5.2
    root = s.empty(f"avatar_{style}", loc, parent)
    root.rotation_euler.z = math.radians(rot_z)
    pants = PANTS.get(style, "blue")
    bev = 0.06 * u
    for sx in (-1, 1):  # legs
        hip = s.empty("hip", (sx * 0.5 * u, 0, 2 * u), root)
        box(s, (0.98 * u, u, 2 * u), pants, (0, 0, -u), parent=hip, bevel=bev)
    body = box(s, (2 * u, u, 2 * u), shirt, (0, 0, 3 * u), parent=root, bevel=bev)
    if style == "soldier":
        box(s, (2.02 * u, 1.02 * u, 0.25 * u), "white", (0, 0, 2.3 * u), parent=root, bevel=0.02 * u)  # belt
        for z in (2.8, 3.3, 3.8):
            ball(s, 0.09 * u, "gold", (0, -0.52 * u, z * u), parent=root)
    arms = []
    for sx in (-1, 1):
        sh = s.empty("shoulder", (sx * 1.5 * u, 0, 3.75 * u), root)
        box(s, (0.98 * u, u, 1.2 * u), shirt, (0, 0, -0.35 * u), parent=sh, bevel=bev)
        box(s, (0.96 * u, 0.98 * u, 0.8 * u), "skin", (0, 0, -1.35 * u), parent=sh, bevel=bev)
        arms.append(sh)
    neck = s.empty("neck", (0, 0, 4 * u), root)
    head = cyl(s, 0.62 * u, 1.2 * u, "skin", (0, 0, 0.62 * u), parent=neck, bevel=0.22 * u)
    # face: dark oval eyes + smile, the classic blocky-avatar look
    for sx in (-1, 1):
        ball(s, 0.085 * u, "black", (sx * 0.2 * u, -0.6 * u, 0.12 * u), scale=(0.75, 0.4, 1.35), parent=head, rough=0.2)
    smile(s, 0.24 * u, 0.035 * u, (0, -0.605 * u, -0.08 * u), head, open_=style == "kid")
    if style == "kid":
        hair_cap(s, u, hair, head)
    elif style == "grandpa":
        for sx in (-1, 1):
            box(s, (0.3 * u, 0.9 * u, 0.6 * u), "white", (sx * 0.55 * u, 0.15 * u, 0.1 * u), parent=head, bevel=0.1 * u)
            ring(s, 0.13 * u, 0.025 * u, "black", (sx * 0.2 * u, -0.64 * u, 0.12 * u), (90, 0, 0), parent=head)
        box(s, (0.5 * u, 0.12 * u, 0.12 * u), "white", (0, -0.64 * u, -0.05 * u), parent=head, bevel=0.05 * u)
    elif style == "baby":
        hair_cap(s, u, "pink", head)
    elif style == "soldier":
        box(s, (1.1 * u, 1.1 * u, 1.0 * u), "black", (0, 0, 0.95 * u), parent=head, bevel=0.08 * u)
        box(s, (1.12 * u, 0.4 * u, 0.06 * u), "black", (0, -0.6 * u, 0.45 * u), parent=head, bevel=0.02 * u)
        ball(s, 0.12 * u, "gold", (0, -0.56 * u, 1.05 * u), parent=head)
    return Rig(root, body, neck, head, arms[0], arms[1], h)


def hair_cap(s, u, color, head):
    """Chunky accessory-style hair: a cap plus a back panel."""
    box(s, (1.36 * u, 1.36 * u, 0.42 * u), color, (0, 0.04 * u, 0.5 * u), parent=head, bevel=0.15 * u)
    box(s, (1.36 * u, 0.4 * u, 0.9 * u), color, (0, 0.5 * u, 0.15 * u), parent=head, bevel=0.12 * u)
    box(s, (0.5 * u, 0.25 * u, 0.25 * u), color, (-0.35 * u, -0.6 * u, 0.42 * u), parent=head, bevel=0.08 * u)  # fringe


def smile(s, r, thick, loc, parent, open_=False):
    """A curved line (bevelled curve) for the mouth."""
    cu = bpy.data.curves.new("smile", "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", thick, 3
    sp = cu.splines.new("POLY")
    n = 9
    sp.points.add(n - 1)
    for i, pt in enumerate(sp.points):
        a = math.radians(200 + 140 * i / (n - 1))
        pt.co = (r * math.cos(a), 0, r * 0.55 * math.sin(a), 1)
    cu.materials.append(mat("black", 0.3))
    return s.adopt(bpy.data.objects.new("smile", cu), parent, loc)


def wave(s, rig, t0, t1, arm="r", period=0.45):
    """Raise an arm and wave it."""
    a = rig.arm_r if arm == "r" else rig.arm_l
    sx = 1 if arm == "r" else -1
    key(a, "rotation_euler", (0, math.radians(-sx * 12), 0), s.f(t0))
    t, k = t0 + 0.2, 0
    while t < t1:
        key(a, "rotation_euler", (0, math.radians(-sx * (150 if k % 2 else 120)), 0), s.f(t))
        t += period / 2
        k += 1
    key(a, "rotation_euler", (0, math.radians(-sx * 12), 0), s.f(t + 0.2))


def reach(s, rig, t0, t1, deg=-80, arms="lr"):
    """Raise arm(s) forward (offering, holding, saluting)."""
    for a in ([rig.arm_l] if "l" in arms else []) + ([rig.arm_r] if "r" in arms else []):
        r0 = a.rotation_euler.copy()
        key(a, "rotation_euler", r0, s.f(t0))
        key(a, "rotation_euler", (math.radians(deg), r0.y, r0.z), s.f(t1))


def nod(s, rig, t, n=2, deg=12, period=0.3):
    for i in range(n):
        key(rig.neck, "rotation_euler", (0, 0, 0), s.f(t + i * period))
        key(rig.neck, "rotation_euler", (math.radians(deg), 0, 0), s.f(t + i * period + period / 2))
    key(rig.neck, "rotation_euler", (0, 0, 0), s.f(t + n * period))


def look(s, rig, t, yaw=0, pitch=0, dur=0.25):
    """Turn the head to yaw/pitch (degrees) at time t."""
    key(rig.neck, "rotation_euler", rig.neck.rotation_euler.copy(), s.f(t))
    key(rig.neck, "rotation_euler", (math.radians(pitch), 0, math.radians(yaw)), s.f(t + dur))


def talk(s, rig, t0, t1, period=0.28):
    """Small head bobs while speaking."""
    t = t0
    while t < t1:
        key(rig.neck, "rotation_euler", (math.radians(4), 0, 0), s.f(t))
        key(rig.neck, "rotation_euler", (0, 0, 0), s.f(t + period / 2))
        t += period


# --- sets -------------------------------------------------------------------------

def room(s, wall="wall", floor="wood", rug="rug", night=False, lamp=True):
    """Diorama corner: floor, back wall, baseboard, rug; plus lights and world."""
    brick = STYLE["name"] == "brick"
    from .imported import has_set, set_piece
    if brick and has_set("room"):  # a room built in Roblox Studio replaces the procedural one
        set_piece(s, "room")
        _lights(s, night, lamp)
        return
    fl = box(s, (14, 14, 0.2), floor, (0, 2, -0.1), bevel=0, rough=0.7)
    box(s, (14, 0.3, 9), wall, (0, 4.5, 4.5), bevel=0, rough=0.9)
    box(s, (14, 0.36, 0.3), "white", (0, 4.3, 0.15), bevel=0.02)
    if brick:
        fl.material_slots[0].material = baseplate_mat((0.62, 0.64, 0.66) if floor == "wood" else floor)
    else:  # floorboard lines
        for i in range(-6, 7):
            box(s, (0.02, 14, 0.005), "wood_dark", (i * 0.9, 2, 0.002), bevel=0)
    if rug:
        cyl(s, 2.4, 0.03, rug, (0, 0.6, 0.015), verts=64)
        ring(s, 2.3, 0.04, "cream", (0, 0.6, 0.03))
    _lights(s, night, lamp)


def _lights(s, night, lamp):
    if night:
        world_key(s.f0, "night", 0.35)
        light(s, "AREA", (3, -4, 6), 350, color=(0.55, 0.65, 1.0), size=4)  # moonlight
        if lamp:
            light(s, "POINT", (-2.2, 1.2, 1.6), 120, color=(1.0, 0.7, 0.35), size=0.3)  # nightlight
    else:
        world_key(s.f0, "cream", 0.55)
        light(s, "AREA", (-3, -4, 6), 900, size=5)  # key
        light(s, "AREA", (4, -2, 3), 180, color=(0.8, 0.88, 1.0), size=4)  # fill
        light(s, "AREA", (0, 3, 6), 250, size=4, look=(0, -1, 0))  # rim/top


def window(s, loc=(2.2, 4.3, 3.6), night=False):
    sky = "night" if night else (0.62, 0.82, 0.98)
    box(s, (2.2, 0.1, 1.8), sky, loc, bevel=0, emit=0.6 if not night else 0.3)
    box(s, (2.4, 0.15, 0.12), "white", (loc[0], loc[1] - 0.05, loc[2] + 0.95), bevel=0.02)
    box(s, (2.4, 0.15, 0.12), "white", (loc[0], loc[1] - 0.05, loc[2] - 0.95), bevel=0.02)
    box(s, (0.1, 0.15, 1.8), "white", (loc[0], loc[1] - 0.05, loc[2]), bevel=0.01)
    if night:
        ball(s, 0.25, (1, 0.95, 0.75), (loc[0] + 0.5, loc[1] - 0.1, loc[2] + 0.4), emit=4)


# --- props ------------------------------------------------------------------------

def block(s, loc=(0, 0, 0), size=0.4, color="wood_light", rot_z=0, parent=None, shape="cube"):
    """A wooden building block. shape: cube | long | arch-less | cone | cyl"""
    if shape == "long":
        ob = box(s, (size * 2, size, size), color, loc, (0, 0, rot_z), parent, bevel=0.035 * size / 0.4)
    elif shape == "cone":
        ob = cyl(s, size * 0.55, size, color, loc, (0, 0, rot_z), parent, r2=0.0)
    elif shape == "cyl":
        ob = cyl(s, size * 0.5, size, color, loc, (0, 0, rot_z), parent, bevel=0.02)
    else:
        ob = box(s, (size,) * 3, color, loc, (0, 0, rot_z), parent, bevel=0.035 * size / 0.4)
    return ob


def kitchen(s, loc=(0, 0, 0), parent=None):
    """Toy stove with a pot; returns (root, pot_lid, steam_origin)."""
    r = s.empty("kitchen", loc, parent)
    box(s, (1.6, 1.0, 1.4), "teal", (0, 0, 0.7), parent=r, bevel=0.06)
    box(s, (1.66, 1.06, 0.08), "white", (0, 0, 1.42), parent=r, bevel=0.02)
    box(s, (0.9, 0.04, 0.6), (0.1, 0.2, 0.22), (0, -0.51, 0.65), parent=r, bevel=0.02)  # oven door
    cyl(s, 0.05, 0.3, "silver", (0, -0.55, 1.05), (0, 90, 0), parent=r)  # handle
    for x in (-0.4, 0.4):
        ring(s, 0.22, 0.03, "black", (x, 0, 1.47), parent=r)
        cyl(s, 0.06, 0.08, "red", (x, -0.53, 1.25), (90, 0, 0), parent=r)  # knobs
    pot = cyl(s, 0.32, 0.38, "red", (-0.4, 0, 1.66), parent=r, bevel=0.02)
    lid = cyl(s, 0.34, 0.05, "silver", (-0.4, 0, 1.87), parent=r)
    ball(s, 0.06, "black", (0, 0, 0.05), parent=lid)
    steam = s.empty("steam", (-0.4, 0, 1.95), r)
    return r, lid, steam


def steam(s, origin, t0, t1, every=0.35, rise=1.4):
    """Puffs that rise and fade from an empty."""
    t, i = t0, 0
    while t < t1:
        p = ball(s, 0.12, "steam", (0.08 * ((i % 3) - 1), 0, 0), parent=origin, rough=1.0)
        key(p, "scale", (0.001,) * 3, s.f(t))
        key(p, "location", (0.08 * ((i % 3) - 1), 0, 0), s.f(t))
        key(p, "scale", (1.2,) * 3, s.f(t + 0.4))
        key(p, "scale", (0.001,) * 3, s.f(t + 1.0))
        key(p, "location", (0.15 * ((i % 3) - 1), 0, rise), s.f(t + 1.0))
        t += every
        i += 1


def car(s, loc=(0, 0, 0), color="blue", rot_z=0, parent=None):
    r = s.empty("car", loc, parent)
    r.rotation_euler.z = math.radians(rot_z)
    box(s, (1.1, 0.55, 0.32), color, (0, 0, 0.28), parent=r, bevel=0.1)
    box(s, (0.6, 0.5, 0.3), color, (-0.05, 0, 0.55), parent=r, bevel=0.1)
    box(s, (0.62, 0.52, 0.18), (0.75, 0.9, 1.0), (-0.05, 0, 0.58), parent=r, bevel=0.06, rough=0.1)
    for x in (-0.35, 0.35):
        for y in (-0.3, 0.3):
            cyl(s, 0.14, 0.1, "black", (x, y, 0.14), (90, 0, 0), parent=r)
            cyl(s, 0.06, 0.11, "silver", (x, y, 0.14), (90, 0, 0), parent=r)
    ball(s, 0.05, (1, 0.95, 0.6), (0.56, -0.17, 0.3), parent=r, emit=3)
    ball(s, 0.05, (1, 0.95, 0.6), (0.56, 0.17, 0.3), parent=r, emit=3)
    return r


def cradle(s, loc=(0, 0, 0), parent=None):
    r = s.empty("cradle", loc, parent)
    rock = s.empty("rock", (0, 0, 0.1), r)
    box(s, (1.1, 0.6, 0.35), "white", (0, 0, 0.3), parent=rock, bevel=0.08)
    for x in (-0.5, 0.5):
        cyl(s, 0.35, 0.06, "wood", (x, 0, 0.2), (0, 90, 0), parent=rock, verts=24)
    return r, rock


def desk(s, loc=(0, 0, 0), parent=None):
    """Toy office desk with a computer; returns (root, paper_spawn, screen)."""
    r = s.empty("desk", loc, parent)
    box(s, (1.8, 0.9, 0.1), "wood", (0, 0, 1.0), parent=r, bevel=0.03)
    for x in (-0.8, 0.8):
        box(s, (0.12, 0.8, 1.0), "wood_dark", (x, 0, 0.5), parent=r, bevel=0.02)
    box(s, (0.9, 0.08, 0.6), "grey", (0.3, 0.2, 1.45), parent=r, bevel=0.04)
    screen = box(s, (0.8, 0.02, 0.5), (0.4, 0.9, 0.7), (0.3, 0.155, 1.45), parent=r, bevel=0, emit=2.0)
    box(s, (0.12, 0.12, 0.2), "grey", (0.3, 0.25, 1.12), parent=r, bevel=0.02)
    stack = s.empty("papers", (-0.45, -0.1, 1.06), r)
    return r, stack, screen


def papers(s, origin, t0, t1, every=0.18):
    """Sheets that fly up off a stack and land in a growing 'done' pile."""
    t, i = t0, 0
    while t < t1:
        p = box(s, (0.35, 0.45, 0.01), "white", (0, 0, i * 0.015), parent=origin, bevel=0)
        key(p, "location", (0, 0, i * 0.015), s.f(t))
        key(p, "rotation_euler", (0, 0, 0), s.f(t))
        key(p, "location", (0.3, -0.2, 0.7), s.f(t + 0.2))
        key(p, "rotation_euler", (0.6, 0.3, 2.0), s.f(t + 0.2))
        key(p, "location", (-0.15 + 0.02 * (i % 3), 0.1, 0.02 + i * 0.012), s.f(t + 0.4))
        key(p, "rotation_euler", (0, 0, 0.1 * (i % 3)), s.f(t + 0.4))
        t += every
        i += 1


def robot(s, loc=(0, 0, 0), h=2.2, rot_z=0, parent=None):
    """A fancy toy robot; returns (root, head)."""
    r = s.empty("robot", loc, parent)
    r.rotation_euler.z = math.radians(rot_z)
    k = h / 2.2
    box(s, (0.9 * k, 0.6 * k, 1.0 * k), "silver", (0, 0, 0.8 * k), parent=r, bevel=0.08, rough=0.25)
    for x in (-0.25, 0.25):
        box(s, (0.25 * k, 0.3 * k, 0.4 * k), "grey", (x * k, 0, 0.2 * k), parent=r, bevel=0.04, rough=0.3)
        cyl(s, 0.09 * k, 0.04 * k, (0.3, 1.0, 0.6), (x * 0.6 * k, -0.31 * k, 0.95 * k), (90, 0, 0), parent=r, emit=3)
    head = s.empty("rhead", (0, 0, 1.3 * k), r)
    box(s, (0.7 * k, 0.55 * k, 0.5 * k), "silver", (0, 0, 0.25 * k), parent=head, bevel=0.08, rough=0.25)
    for x in (-0.15, 0.15):
        ball(s, 0.08 * k, (0.3, 0.8, 1.0), (x * k, -0.27 * k, 0.3 * k), parent=head, emit=5)
    box(s, (0.3 * k, 0.03 * k, 0.05 * k), "black", (0, -0.28 * k, 0.12 * k), parent=head, bevel=0)
    cyl(s, 0.02 * k, 0.3 * k, "grey", (0, 0, 0.65 * k), parent=head)
    ball(s, 0.06 * k, "red", (0, 0, 0.82 * k), parent=head, emit=3)
    return r, head


def gift(s, loc=(0, 0, 0), size=0.7, color="purple", ribbon="mustard", parent=None, lid_obj=False):
    r = s.empty("gift", loc, parent)
    box(s, (size, size, size * 0.8), color, (0, 0, size * 0.4), parent=r, bevel=0.03)
    lid = s.empty("lid", (0, 0, size * 0.8), r)
    box(s, (size * 1.06, size * 1.06, size * 0.16), color, (0, 0, 0.0), parent=lid, bevel=0.03)
    box(s, (size * 0.14, size * 1.08, size * 0.17), ribbon, (0, 0, 0), parent=lid, bevel=0.01)
    box(s, (size * 1.08, size * 0.14, size * 0.17), ribbon, (0, 0, 0), parent=lid, bevel=0.01)
    box(s, (size * 0.14, size * 1.02, size * 0.8), ribbon, (0, 0, -size * 0.4), parent=lid, bevel=0.01)
    for a in (-35, 35):
        ball(s, size * 0.13, ribbon, (0, 0, size * 0.14), scale=(1.8, 0.6, 0.8), parent=lid).rotation_euler.y = math.radians(a)
    return (r, lid) if lid_obj else r


def cake(s, loc=(0, 0, 0), parent=None):
    r = s.empty("cake", loc, parent)
    cyl(s, 0.7, 0.08, "white", (0, 0, 0.04), parent=r)
    cyl(s, 0.55, 0.4, "pink", (0, 0, 0.28), parent=r, bevel=0.03)
    cyl(s, 0.57, 0.08, "white", (0, 0, 0.48), parent=r, bevel=0.03)
    for i in range(7):
        a = i / 7 * math.tau
        x, y = 0.35 * math.cos(a), 0.35 * math.sin(a)
        cyl(s, 0.025, 0.25, ["teal", "mustard", "red"][i % 3], (x, y, 0.64), parent=r)
        ball(s, 0.045, (1, 0.7, 0.2), (x, y, 0.8), scale=(1, 1, 1.6), parent=r, emit=8)
    return r


def bed(s, loc=(0, 0, 0), parent=None):
    r = s.empty("bed", loc, parent)
    box(s, (2.6, 1.6, 0.5), "wood", (0, 0, 0.55), parent=r, bevel=0.05)
    box(s, (2.5, 1.5, 0.25), "blue", (0.1, 0, 0.92), parent=r, bevel=0.1)
    box(s, (0.6, 1.0, 0.2), "white", (-0.9, 0, 1.12), parent=r, bevel=0.08)
    box(s, (0.12, 1.6, 1.4), "wood_dark", (-1.3, 0, 0.7), parent=r, bevel=0.04)
    for x in (-1.2, 1.2):
        for y in (-0.7, 0.7):
            box(s, (0.15, 0.15, 0.3), "wood_dark", (x, y, 0.15), parent=r, bevel=0.02)
    return r


def shark(s, loc=(0, 0, 0), rot_z=0, hat="black", parent=None):
    """A tiny shark wearing a top hat."""
    r = s.empty("shark", loc, parent)
    r.rotation_euler.z = math.radians(rot_z)
    ball(s, 0.18, "grey", (0, 0, 0), scale=(2.0, 0.8, 0.8), parent=r)
    ball(s, 0.17, "white", (0.02, 0, -0.04), scale=(1.8, 0.7, 0.55), parent=r)
    cyl(s, 0.1, 0.22, "grey", (-0.02, 0, 0.17), (0, -20, 0), parent=r, r2=0.0, verts=3)
    cyl(s, 0.08, 0.16, "grey", (-0.38, 0, 0.04), (0, 90, 0), parent=r, r2=0.0, verts=3)
    ball(s, 0.03, "black", (0.22, -0.11, 0.04), parent=r)
    ball(s, 0.03, "black", (0.22, 0.11, 0.04), parent=r)
    cyl(s, 0.11, 0.02, hat, (0.1, 0, 0.13), parent=r)
    cyl(s, 0.07, 0.15, hat, (0.1, 0, 0.21), parent=r)
    cyl(s, 0.072, 0.03, "red", (0.1, 0, 0.16), parent=r)
    return r


def dragon(s, loc=(0, 0, 0), parent=None, k=0.6):
    r = s.empty("dragon", loc, parent)
    box(s, (0.7 * k, 0.4 * k, 0.4 * k), "green", (0, 0, 0.2 * k), parent=r, bevel=0.03)
    box(s, (0.35 * k, 0.35 * k, 0.35 * k), "green", (0.35 * k, 0, 0.5 * k), parent=r, bevel=0.03)
    for y in (-0.08, 0.08):
        ball(s, 0.04 * k, "black", (0.53 * k, y * k, 0.56 * k), parent=r)
    for x in (-0.2, 0, 0.2):
        cyl(s, 0.07 * k, 0.18 * k, "mustard", (x * k, 0, 0.47 * k), parent=r, r2=0.0, verts=4)
    for sy in (-1, 1):
        w = cyl(s, 0.3 * k, 0.04 * k, "teal", (0, sy * 0.35 * k, 0.45 * k), (sy * 60, 0, 0), parent=r, verts=3)
    cyl(s, 0.1 * k, 0.45 * k, "green", (-0.5 * k, 0, 0.25 * k), (0, -70, 0), parent=r, r2=0.0, verts=4)
    return r
