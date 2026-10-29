"""ep01 "The Toys That Play Themselves": one function per shot name in script.yaml.

Each function receives a Shot context `s` (see lib/core.py): build the set in
local coordinates, add a camera, and animate using seconds relative to the shot.
`s.dur` is the shot length; `s.cue(line_index, "word")` is when a word is spoken.
"""
import math

from lib.core import (ball, box, camera, cyl, hop, key, light, move, pop, turn, vanish, wobble, world_key)
from lib.toys import (bed, block, cake, car, cradle, desk, dragon, gift, kitchen, look, nod, papers, peg,
                      reach, robot, room, shark, steam, talk, wave, window)

WOOD = ["wood_light", "wood", "wood_light", (0.85, 0.62, 0.38)]


def orbit(s, ob, center, radius, t0, t1, z=0.0, rps=0.4, phase=0.0, step=1 / 6):
    """Drive an object around a circle, facing along its path."""
    t = t0
    while t <= t1 + 1e-6:
        a = phase + (t - t0) * rps * math.tau
        key(ob, "location", (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), z), s.f(t), "LINEAR")
        key(ob, "rotation_euler", (0, 0, a + math.pi / 2), s.f(t), "LINEAR")
        t += step


def castle(s, loc, t_wall=None, t_tower=None, t_door=None, t_dragon=None, t_moat=None, t_sharks=None, spin_until=None):
    """The kid's creation. With times given, each part pops in on its cue; otherwise it's all there."""
    root = s.empty("castle", loc)
    sz = 0.32
    parts = {"wall": [], "tower": [], "door": [], "dragon": [], "moat": [], "sharks": []}
    for i, x in enumerate((-2, -1, 1, 2)):  # wall either side of the tower
        for z in range(2):
            parts["wall"].append(block(s, (x * sz, 0, sz / 2 + z * sz), sz, WOOD[(i + z) % 4], parent=root))
    for z in range(5):
        parts["tower"].append(block(s, (0, 0, sz / 2 + z * sz), sz, WOOD[z % 4], parent=root))
    parts["door"].append(box(s, (0.18, 0.04, 0.3), "wood_dark", (0, -sz / 2 - 0.01, 0.15), parent=root, bevel=0.02))
    parts["dragon"].append(dragon(s, (0, 0, 5 * sz), parent=root, k=0.75))
    parts["moat"].append(cyl(s, 1.35, 0.03, (0.25, 0.55, 0.9), (0, 0, 0.02), parent=root, verts=64, rough=0.1))
    sharks = s.empty("sharks", (0, 0, 0.12), root)
    for i in range(3):
        a = i / 3 * math.tau
        parts["sharks"].append(shark(s, (1.1 * math.cos(a), 1.1 * math.sin(a), 0), rot_z=math.degrees(a) + 90, parent=sharks))
    if spin_until:
        key(sharks, "rotation_euler", (0, 0, 0), s.f(0), "LINEAR")
        key(sharks, "rotation_euler", (0, 0, spin_until * 0.8), s.f(spin_until), "LINEAR")
    for name, t in (("wall", t_wall), ("tower", t_tower), ("door", t_door), ("dragon", t_dragon),
                    ("moat", t_moat), ("sharks", t_sharks)):
        if t is None:
            continue
        for j, ob in enumerate(parts[name]):
            pop(s, ob, t + j * 0.07, size=tuple(ob.scale))
    return root


# --- shots ----------------------------------------------------------------------

def hook(s):
    room(s)
    window(s)
    kid = peg(s, (0, 0.6, 0), shirt="red")
    c = car(s, (0, 0, 0), "mustard")
    c.scale = (0.6,) * 3
    orbit(s, c, (0, 0.6), 1.3, 0, s.dur + 0.5, rps=0.45)
    sol = peg(s, (-1.5, 1.8, 0), h=0.7, shirt="red", style="soldier", rot_z=20)
    hop(s, sol.root, 0, s.dur, 0.12, 0.35)
    wave(s, sol, 0.2, s.dur, "r", 0.3)
    b = ball(s, 0.25, "teal", (1.5, 1.5, 0.25))
    hop(s, b, 0, s.dur, 0.8, 0.55)
    for t, yaw in ((0.0, 30), (0.7, -40), (1.4, 40), (2.1, -30)):
        look(s, kid, t, yaw)
    camera(s, (0.3, -5.5, 2.6), (0, 0.6, 0.7), lens=32, to_pos=(0.1, -4.4, 2.0))


def kitchen_shot(s, kid=True):
    k, lid, st = kitchen(s, (0, 1.2, 0))
    steam(s, st, 0, s.dur + 0.5)
    hop(s, lid, 0, s.dur, 0.06, 0.25)
    return k


def kitchen_(s):
    room(s, wall="wall_blue")
    kitchen_shot(s)
    spoon = cyl(s, 0.03, 0.6, "wood", (-0.4, 1.2, 2.0), (0, 20, 0))
    t = 0
    while t < s.dur:  # the spoon stirs by itself
        key(spoon, "location", (-0.55, 1.2, 2.05), s.f(t))
        key(spoon, "location", (-0.25, 1.2, 2.05), s.f(t + 0.25))
        t += 0.5
    kid = peg(s, (1.6, 0.2, 0), shirt="red", rot_z=-30)
    look(s, kid, 0.1, 50)
    camera(s, (1.2, -3.8, 2.4), (0.2, 1.0, 1.2), lens=30, to_pos=(0.9, -3.2, 2.2))


def dolls(s):
    room(s, wall="pink")
    cr, rock = cradle(s, (0, 1, 0))
    wobble(s, rock, 0, s.dur + 0.4, deg=7, period=0.8, axis=0)
    baby = peg(s, (0, 0, 0.35), h=0.55, shirt="white", style="baby", rot_z=0)
    baby.root.parent = rock
    baby.root.location = (0, 0, 0.35)
    # a tidy stack of nappies, one flies into the cradle by itself
    for i in range(4):
        box(s, (0.35, 0.3, 0.1), "white", (1.1, 0.9, 0.05 + i * 0.11), bevel=0.04)
    d = box(s, (0.35, 0.3, 0.1), "white", (1.1, 0.9, 0.49), bevel=0.04)
    key(d, "location", (1.1, 0.9, 0.49), s.f(0.5))
    key(d, "location", (0.5, 0.9, 1.6), s.f(0.9))
    key(d, "location", (0.0, 1.0, 0.6), s.f(1.3))
    vanish(s, d, 1.35, 0.15)
    out = box(s, (0.3, 0.25, 0.1), (0.9, 0.85, 0.6), (0, 1, 0.6), bevel=0.04)
    pop(s, out, 1.4, 0.15)
    key(out, "location", (0, 1, 0.6), s.f(1.55))
    key(out, "location", (-0.6, 1.0, 1.7), s.f(1.85))
    key(out, "location", (-1.2, 1.0, 0.55), s.f(2.2))
    cyl(s, 0.3, 0.6, "grey", (-1.2, 1.0, 0.3), r2=0.35)  # bin
    camera(s, (0.3, -2.4, 1.7), (0.1, 1.0, 0.6), lens=35, to_pos=(0.2, -2.0, 1.5))


def cars(s):
    room(s, wall="wall_blue", rug=None)
    box(s, (12, 1.6, 0.02), (0.22, 0.22, 0.25), (0, 0.6, 0.01), bevel=0)  # road mat
    for i in range(-7, 8):
        box(s, (0.4, 0.08, 0.01), "white", (i * 0.8, 0.6, 0.025), bevel=0)
    colors = ["red", "mustard", "teal", "blue", "green", "purple"]
    honk = s.cue(0, "honk")
    for i, c in enumerate(colors):
        x = -4.0 + i * 1.3
        ob = car(s, (x, 0.6, 0.02), c)
        ob.scale = (0.8,) * 3
        # inch forward, stop, inch forward (traffic)
        key(ob, "location", (x, 0.6, 0.02), s.f(0))
        key(ob, "location", (x + 0.4, 0.6, 0.02), s.f(0.8))
        key(ob, "location", (x + 0.4, 0.6, 0.02), s.f(1.5))
        key(ob, "location", (x + 0.7, 0.6, 0.02), s.f(2.0))
        key(ob, "location", (x + 0.7, 0.6, 0.02), s.f(honk + 0.08 * i))
        key(ob, "location", (x + 0.7, 0.6, 0.25), s.f(honk + 0.08 * i + 0.12))
        key(ob, "location", (x + 0.7, 0.6, 0.02), s.f(honk + 0.08 * i + 0.25))
        key(ob, "location", (x + 0.7, 0.6, 0.15), s.f(honk + 0.08 * i + 0.45))
        key(ob, "location", (x + 0.7, 0.6, 0.02), s.f(honk + 0.08 * i + 0.6))
    # a tiny briefcase on one roof: they're going to work
    box(s, (0.3, 0.12, 0.2), "wood_dark", (-0.6 + 1.3 * 2 - 0.05, 0.6, 0.8), bevel=0.02)
    camera(s, (2.0, -3.5, 2.2), (-0.4, 0.6, 0.4), lens=28, to_pos=(1.0, -3.0, 2.0), to_look=(0.2, 0.6, 0.4))


def watch(s):
    room(s)
    window(s)
    kid = peg(s, (0, 1.4, 0), shirt="red")
    friend = peg(s, (1.1, 1.6, 0), shirt="teal", hair=(0.9, 0.7, 0.3), rot_z=-10)
    for i, yaw in enumerate((-35, 35, -35, 35, -35)):
        look(s, kid, i * 0.6, yaw, 10, 0.2)
        look(s, friend, i * 0.6 + 0.1, yaw, 10, 0.2)
    # toys zip past in the foreground
    for i, c in enumerate(("mustard", "blue", "green")):
        ob = car(s, (-3, -0.2 - 0.4 * i, 0), c)
        ob.scale = (0.7,) * 3
        move(s, ob, 0.2 + i * 0.8, 1.0 + i * 0.8, (3, -0.2 - 0.4 * i, 0), frm=(-3, -0.2 - 0.4 * i, 0))
        if i % 2:
            ob.rotation_euler.z = math.pi
            move(s, ob, 0.2 + i * 0.8, 1.0 + i * 0.8, (-3, -0.2 - 0.4 * i, 0), frm=(3, -0.2 - 0.4 * i, 0))
    camera(s, (0.4, -3.5, 1.0), (0.5, 1.5, 0.8), lens=35, to_pos=(0.4, -3.0, 0.95))


def rich(s):
    room(s, wall="purple", rug="mustard")
    window(s)
    kid = peg(s, (0.5, 0.5, 0), shirt="white", hair=(0.95, 0.85, 0.4))
    r, head = robot(s, (-0.9, 1.4, 0), h=2.6, rot_z=-15)
    # a second fancy toy: gilded rocking horse stand-in
    ball(s, 0.35, "gold", (1.6, 1.8, 0.6), rough=0.2)
    t_watch = s.cue(0, "their toys")
    hop(s, r, 0, t_watch - 0.4, 0.05, 0.6)
    turn(s, head, t_watch - 0.1, t_watch + 0.3, (25, 0, -55), frm_deg=(0, 0, 0))  # robot leans to stare at kid
    turn(s, r, t_watch - 0.1, t_watch + 0.4, (0, 0, -40), frm_deg=(0, 0, -15))
    look(s, kid, t_watch + 0.6, 55, 20, 0.3)  # kid notices… uneasily
    key(kid.root, "location", (0.5, 0.5, 0), s.f(t_watch + 1.0))
    key(kid.root, "location", (0.8, 0.4, 0), s.f(t_watch + 1.3))
    camera(s, (0.6, -4.6, 2.2), (0, 1.0, 1.1), lens=30, to_pos=(0.4, -3.4, 1.8))


def birthday(s):
    room(s, wall="wall")
    window(s)
    box(s, (1.8, 1.0, 0.5), "white", (0, 1.2, 0.25), bevel=0.05)
    cake(s, (0, 1.2, 0.5))
    kid = peg(s, (0, 0.1, 0), shirt="red")
    hop(s, kid.root, 0.3, s.dur, 0.25, 0.4)
    for i, (x, y, c, r) in enumerate(((-1.4, 0.5, "purple", "mustard"), (1.4, 0.6, "teal", "red"),
                                      (-1.1, -0.4, "red", "white"), (1.2, -0.3, "mustard", "teal"),
                                      (-1.4, 0.5, "blue", "pink"))):
        g = gift(s, (x, y, 0 if i < 4 else 0.62), 0.6, c, r)
        pop(s, g, 0.2 + 0.35 * i)
    camera(s, (0.2, -4.2, 2.3), (0, 0.6, 0.8), lens=30, to_pos=(0.1, -3.6, 2.1))


def office(s):
    room(s, wall="wall_blue", rug=None)
    window(s)
    d, stack, screen = desk(s, (0, 1, 0))
    for i in range(10):
        box(s, (0.35, 0.45, 0.01), "white", (-0.45, 0.9, 1.07 + i * 0.012), bevel=0)
    papers(s, stack, 0.1, s.dur)
    # the empty swivel chair spins on its own
    ch = s.empty("chair", (0, 0.1, 0))
    cyl(s, 0.05, 0.6, "black", (0, 0, 0.3), parent=ch)
    cyl(s, 0.4, 0.06, "black", (0, 0, 0.03), parent=ch, verts=5)
    seat = s.empty("seat", (0, 0, 0.6), ch)
    box(s, (0.7, 0.7, 0.12), "red", (0, 0, 0.05), parent=seat, bevel=0.05)
    box(s, (0.7, 0.12, 0.8), "red", (0, -0.35, 0.45), parent=seat, bevel=0.05)
    key(seat, "rotation_euler", (0, 0, 0), s.f(0), "LINEAR")
    key(seat, "rotation_euler", (0, 0, math.tau * 1.5), s.f(s.dur + 0.3), "LINEAR")
    # "TAX" stamp thumps
    stamp = cyl(s, 0.08, 0.25, "red", (0.75, 0.8, 1.25))
    hop(s, stamp, 0, s.dur, 0.25, 0.35)
    camera(s, (-0.8, -3.2, 2.6), (0, 0.8, 1.1), lens=30, to_pos=(-0.5, -2.7, 2.4))


def soldier(s):
    room(s, wall="wall")
    sol = peg(s, (0, 1.0, 0), h=1.3, shirt="red", style="soldier")
    kid = peg(s, (1.2, 0.0, 0), shirt="teal", rot_z=-35)
    # instant crisp salute
    key(sol.arm_r, "rotation_euler", (0, math.radians(-12), 0), s.f(0.2))
    key(sol.arm_r, "rotation_euler", (0, math.radians(-150), math.radians(-20)), s.f(0.35))
    hop(s, sol.root, 0.15, 0.4, 0.15, 0.25)
    # kid tries, too late and wrong arm
    key(kid.arm_l, "rotation_euler", (0, math.radians(12), 0), s.f(1.2))
    key(kid.arm_l, "rotation_euler", (0, math.radians(120), 0), s.f(1.6))
    look(s, kid, 0.3, 40, 15)
    camera(s, (0.6, -3.4, 0.8), (0.3, 1.0, 1.0), lens=30, to_pos=(0.5, -3.0, 0.7))


def grandpa(s):
    room(s, wall="wall")
    window(s)
    gp = peg(s, (-0.8, 0.9, 0), h=1.5, shirt="green", style="grandpa", rot_z=-25)
    kid = peg(s, (0.9, 0.5, 0), shirt="red", rot_z=25)
    bx = box(s, (0.55, 0.45, 0.4), (0.72, 0.55, 0.36), (-0.35, 0.55, 0.75), bevel=0.02, rough=0.9)  # cardboard
    reach(s, gp, 0.0, 0.3, -70)
    move(s, bx, 0.4, 1.2, (0.45, 0.4, 0.62))
    reach(s, kid, 0.9, 1.2, -70)
    look(s, kid, 0.2, 0, -15)
    camera(s, (0.2, -3.8, 1.6), (0, 0.6, 1.0), lens=32, to_pos=(0.1, -3.3, 1.5))


def blocks(s):
    room(s, wall="wall", rug="rug")
    # open cardboard box, seen from above
    bx = s.empty("box", (0, 0.6, 0))
    card = (0.72, 0.55, 0.36)
    box(s, (1.4, 1.0, 0.05), card, (0, 0, 0.025), parent=bx, bevel=0)
    for (x, y, sx, sy) in ((0, -0.5, 1.4, 0.04), (0, 0.5, 1.4, 0.04), (-0.7, 0, 0.04, 1.0), (0.7, 0, 0.04, 1.0)):
        box(s, (sx, sy, 0.5), card, (x, y, 0.25), parent=bx, bevel=0, rough=0.9)
    for (x, y, rx) in ((0, -0.75, -110), (0, 0.75, 110)):  # flaps
        box(s, (1.4, 0.5, 0.03), card, (x, y, 0.5), (rx, 0, 0), parent=bx, bevel=0, rough=0.9)
    i = 0
    for x in (-0.45, -0.05, 0.35):
        for y in (-0.25, 0.2):
            block(s, (x, y, 0.22), 0.36, WOOD[i % 4], rot_z=(i * 7) % 15 - 7, parent=bx)
            i += 1
    block(s, (0.15, 0.0, 0.5), 0.36, "wood_light", rot_z=20, parent=bx, shape="cyl")
    camera(s, (0.0, -0.8, 4.2), (0, 0.6, 0.2), lens=35, to_pos=(0.0, -0.3, 3.0))


def broken(s):
    room(s, wall="wall")
    window(s)
    gp = peg(s, (-0.7, 1.0, 0), h=1.5, shirt="green", style="grandpa", rot_z=-20)
    kid = peg(s, (0.8, 0.6, 0), shirt="red", rot_z=20)
    for (x, y) in ((0.3, -0.1), (0.7, -0.2), (0.5, 0.1)):
        block(s, (x, y, 0.18), 0.36, "wood_light", rot_z=x * 40)
    l0, l1 = s.line(0), s.line(1)
    look(s, kid, l0["start"], 25, -10)
    talk(s, kid, l0["start"], l0["end"])
    key(kid.arm_r, "rotation_euler", (0, math.radians(-12), 0), s.f(l0["start"]))
    key(kid.arm_r, "rotation_euler", (math.radians(-60), math.radians(-12), 0), s.f(l0["start"] + 0.3))
    key(kid.arm_r, "rotation_euler", (0, math.radians(-12), 0), s.f(l0["end"] + 0.2))
    nod(s, gp, l1["start"], 1, 15, 0.5)
    talk(s, gp, s.cue(1, "no"), l1["end"])
    look(s, gp, l1["end"] - 0.4, 0, 20)  # leans in on "waiting"
    camera(s, (0.1, -3.6, 1.7), (0, 0.8, 1.0), lens=32, to_pos=(0.05, -3.0, 1.55))


def underbed(s):
    room(s, wall="wall_blue", rug=None)
    bed(s, (0.2, 1.4, 0))
    kid = peg(s, (-1.0, 0.1, 0), shirt="red", rot_z=-60)
    bx = box(s, (0.55, 0.45, 0.3), (0.72, 0.55, 0.36), (-0.9, 0.5, 0.15), bevel=0.02, rough=0.9)
    reach(s, kid, 0.2, 0.5, -60)
    move(s, bx, 0.5, 1.6, (0.0, 1.4, 0.15))
    t_q = s.cue(0, "waiting")
    look(s, kid, t_q, -60, -20, 0.3)  # glances back at the bed
    camera(s, (-0.2, -3.0, 0.6), (-0.2, 1.0, 0.45), lens=28, to_pos=(-0.2, -2.6, 0.55))


def night(s):
    room(s, wall="wall_blue", night=True)
    window(s, night=True)
    t_k, t_o, t_s = s.cue(0, "kitchen"), s.cue(0, "office"), s.cue(0, "soldier")
    k, lid, st = kitchen(s, (-2.8, 1.5, 0))
    steam(s, st, 0, s.dur + 0.5)
    hop(s, lid, 0, s.dur, 0.06, 0.25)
    d, stack, screen = desk(s, (0, 1.5, 0))
    papers(s, stack, t_o, s.dur + 0.5, every=0.25)
    sol = peg(s, (2.6, 0.8, 0), h=1.1, shirt="red", style="soldier", rot_z=-90)
    move(s, sol.root, t_s + 0.3, s.dur + 0.5, (5.5, 0.8, 0))
    hop(s, sol.root, t_s + 0.3, s.dur + 0.5, 0.1, 0.3)
    key(sol.arm_r, "rotation_euler", (math.radians(-30), 0, 0), s.f(t_s))
    flag = box(s, (0.02, 0.4, 0.25), "white", (0, -0.3, 1.0), parent=sol.root, bevel=0)  # tiny bindle-flag
    cam, tgt = camera(s, (-2.6, -2.8, 2.2), (-2.8, 1.5, 1.4), lens=32)
    for t, x in ((0, -2.6), (t_k + 0.3, -2.6), (t_o - 0.1, -1.0), (t_o + 0.6, 0.1), (t_s - 0.1, 0.1),
                 (t_s + 0.6, 2.4), (s.dur, 2.9)):
        key(cam, "location", (x, -2.8, 2.2), s.f(t))
        key(tgt, "location", (x - 0.1, 1.3, 1.2), s.f(t))


def bored(s):
    room(s, wall="wall_blue", night=True)
    kid = peg(s, (0, 0.5, 0.3), shirt="red")
    kid.root.rotation_euler = (math.radians(-90), 0, math.radians(10))
    for i, a in enumerate((0, 25, -20, 30)):
        key(kid.neck, "rotation_euler", (0, 0, math.radians(a)), s.f(i * 0.6))
    key(kid.arm_l, "rotation_euler", (0, math.radians(110), 0), s.f(0))
    key(kid.arm_r, "rotation_euler", (0, math.radians(-110), 0), s.f(0))
    for (x, y) in ((1.0, 1.2), (-1.1, 0.9)):
        block(s, (x, y, 0.18), 0.36, "wood_light", rot_z=x * 30)
    camera(s, (0.05, 0.0, 4.5), (0, 0.6, 0), lens=35, to_pos=(0.05, 0.25, 3.6))


def build(s):
    room(s, wall="wall_blue", night=True)
    kid = peg(s, (1.9, -0.2, 0), shirt="red", rot_z=-55)
    l1 = 1
    b1 = block(s, (-0.3, -1.1, 0.16), 0.32, "wood_light")
    b2 = block(s, (0.1, -1.1, 0.16), 0.32, "wood")
    pop(s, b1, s.cue(0, "one"))
    pop(s, b2, s.cue(0, "another"))
    vanish(s, b1, s.line(1)["start"] - 0.1)
    vanish(s, b2, s.line(1)["start"] - 0.1)
    castle(s, (0, 0.3, 0), t_wall=s.cue(l1, "wall"), t_tower=s.cue(l1, "tower"), t_door=s.cue(l1, "door"),
           t_dragon=s.cue(l1, "dragon"), t_moat=s.cue(l1, "moat"), t_sharks=s.cue(l1, "sharks"),
           spin_until=s.dur + 0.5)
    hop(s, kid.root, s.cue(l1, "hats"), s.dur, 0.15, 0.35)
    look(s, kid, 0.2, -20, 15)
    # slow orbit around the build
    cam, tgt = camera(s, (1.2, -4.2, 2.2), (0, 0.3, 0.9), lens=32)
    n = 8
    for i in range(n + 1):
        t = s.dur * i / n
        a = math.radians(-70 + 50 * i / n)
        r = 4.3 - 0.9 * i / n
        key(cam, "location", (r * math.cos(a), 0.3 + r * math.sin(a), 2.2 - 0.3 * i / n), s.f(t), "LINEAR")


def creator(s):
    room(s, wall="wall_blue", night=True, lamp=False)
    light(s, "POINT", (1.5, -0.8, 2.0), 160, color=(1.0, 0.75, 0.4), size=0.4)
    castle(s, (0, 0.6, 0), spin_until=s.dur + 0.5)
    kid = peg(s, (1.5, -0.3, 0), shirt="red", rot_z=-20)
    t_me = s.cue(0, "me.")
    hop(s, kid.root, t_me, t_me + 0.8, 0.4, 0.4)
    wave(s, kid, t_me, s.dur, "r", 0.35)
    camera(s, (0.6, -2.6, 0.35), (0.4, 0.6, 1.1), lens=24, to_pos=(0.8, -2.2, 0.3))


def morning(s):
    room(s, wall="wall_blue")
    window(s)
    kitchen_shot(s)
    camera(s, (0.3, -3.6, 2.2), (-0.1, 1.2, 1.4), lens=35)  # deadpan, locked-off


def rocket(s):
    room(s, wall="wall_blue")
    window(s)
    kid = peg(s, (1.4, -0.2, 0), shirt="red", rot_z=-30)
    rk = s.empty("rocket", (-0.2, 0.6, 0))
    sz = 0.34
    for z in range(4):
        block(s, (0, 0, sz / 2 + 0.25 + z * sz), sz, WOOD[z % 4], parent=rk, shape="cyl")
    block(s, (0, 0, 0.25 + 4 * sz + sz / 2), sz * 1.1, "red", parent=rk, shape="cone")
    for a in (0, 120, 240):
        f = box(s, (0.05, 0.35, 0.45), "red", (0.2 * math.cos(math.radians(a)), 0.2 * math.sin(math.radians(a)), 0.4),
                (0, 0, a + 90), parent=rk, bevel=0.02)
    ball(s, 0.06, (0.6, 0.85, 1.0), (0, -sz / 2, 0.25 + 2.6 * sz), parent=rk, emit=2)  # porthole
    t_sp = s.cue(0, "spaceship")
    flame = cyl(s, 0.16, 0.5, (1.0, 0.55, 0.15), (0, 0, 0.0), (180, 0, 0), parent=rk, r2=0.0, emit=12)
    pop(s, flame, t_sp)
    key(rk, "location", (-0.2, 0.6, 0), s.f(t_sp + 0.1))
    key(rk, "location", (-0.2, 0.6, 0.6), s.f(s.dur + 0.4))
    wobble(s, rk, t_sp, s.dur + 0.4, deg=3, period=0.15, axis=0)
    look(s, kid, t_sp, 30, 35)
    camera(s, (0.2, -3.6, 1.0), (-0.1, 0.6, 1.3), lens=28, to_pos=(0.1, -3.2, 0.9))


def ending(s):
    room(s, wall="wall")
    window(s)
    # the fancy toys, idle on a shelf
    box(s, (3.2, 0.5, 0.08), "wood", (0, 4.0, 2.6), bevel=0.02)
    robot(s, (-1.0, 4.0, 2.64), h=0.9)
    car(s, (0.2, 4.0, 2.64), "mustard").scale = (0.6,) * 3
    kitchen(s, (1.1, 4.0, 2.64))[0].scale = (0.35,) * 3
    kid = peg(s, (0.7, 0.2, 0), shirt="red", rot_z=-35)
    gp = peg(s, (-1.4, 0.4, 0), h=1.5, shirt="green", style="grandpa", rot_z=30)
    i = 0
    for z in range(3):
        for x in (-0.5, -0.1, 0.3):
            if z == 2 and x != -0.1:
                continue
            b = block(s, (x, 0.9, 0.17 + z * 0.34), 0.34, WOOD[i % 4])
            if z == 2:
                pop(s, b, s.cue(0, "show"))  # last block lands as the line ends
            i += 1
    reach(s, kid, s.cue(0, "wait,") - 0.3, s.cue(0, "show"), -70, "l")
    nod(s, gp, s.cue(0, "show") + 0.3, 2, 12, 0.4)
    look(s, gp, 0, -20, 15)
    camera(s, (0.0, -2.3, 1.2), (-0.1, 1.2, 1.0), lens=30, to_pos=(0.0, -4.4, 2.0), to_look=(0, 1.6, 1.4))


def card(s):
    world_key(s.f0, (0.02, 0.02, 0.03), 0.0)
    box(s, (20, 20, 0.1), (0.04, 0.035, 0.04), (0, 0, -0.05), bevel=0, rough=0.9)
    b = block(s, (0, 0, 0.3), 0.6, "wood_light")
    turn(s, b, 0, s.dur, (0, 0, 40), frm_deg=(0, 0, -10), interp="LINEAR")
    light(s, "SPOT", (0, -1.0, 4.0), 300, size=0.3, look=(0, 0, 0.3)).data.spot_size = math.radians(30)
    camera(s, (0, -6.0, 2.5), (0, 0, 2.3), lens=35)


# script.yaml shot names -> functions
SHOTS = {
    "hook": hook, "kitchen": kitchen_, "dolls": dolls, "cars": cars, "watch": watch, "rich": rich,
    "birthday": birthday, "office": office, "soldier": soldier, "grandpa": grandpa, "blocks": blocks,
    "broken": broken, "underbed": underbed, "night": night, "bored": bored, "build": build,
    "creator": creator, "morning": morning, "rocket": rocket, "ending": ending, "card": card,
}
