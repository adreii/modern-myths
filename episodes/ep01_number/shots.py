"""EP01 "Everyone Has a Number": the 18 shots, in the shared town.

A port of roblox/EP01_Shots.client.luau and ep01-shot-list.md (sets, positions, light,
camera kind and lens, number behaviour, acting). Positions are the Luau ones written in
Roblox space and mapped with R(x, y, z) (= town.rbx), so they can be checked against the
Luau line by line. Timing follows the voice: each shot's Roblox seconds are scaled to the
shot's spoken length with k(s), and the count-up lands on the spoken numbers.
"""
import math
import random
from pathlib import Path

import yaml

from lib import acting, cam, lighting, numbers
from lib import oldtown
from lib import town as T
from lib.core import key, mat
from lib.imported import roblox_avatar

STAGE_AT_ORIGIN = True  # every shot films in the one town
TOWN = None             # set by build.py from build_town()

R = T.rbx
H = 5.46                # avatar height in studs (R15)
HEAD = 4.7              # head centre above the feet, Roblox R15

PLAZA, SIDEWALK, STEP = 0.55, 0.9, 0.8
HERO_HOME = R(12, PLAZA, 14)
INFLUENCER_HOME = R(-8, PLAZA, 6)
KID_HOME = R(-8, PLAZA, 15)
BAKER_HOME = R(-71, STEP, -69.5)
BAKER_DOOR = R(75, STEP, -68.6)
ROW_CAM, ROW_LOOK = R(-66, 5, -63), R(0, 0.8, -69.5)  # shots 06 and 13: identical framing
CROWD = [f"crowd_{i}" for i in range(1, 8)]
ROBLOX_SECONDS = {"s01": 3.0, "s02": 3.0, "s03": 2.5, "s04": 3.0, "s05": 3.5, "s06": 3.0, "s07": 3.0,
                  "s08": 2.5, "s09": 3.0, "s10": 2.0, "s11": 4.5, "s12": 4.0, "s13": 3.5, "s14": 2.5,
                  "s15": 3.5, "s16": 4.0, "s17": 3.5, "s18": 6.0}
WARM = (1.0, 0.55, 0.22)
# hand-made light changes per shot, captured from Blender by pipeline/grab_looks.py
LOOKS_FILE = Path(__file__).with_name("looks.yaml")
HAND_LOOKS = (yaml.safe_load(LOOKS_FILE.read_text(encoding="utf-8")) or {}) if LOOKS_FILE.exists() else {}
# what each shot's world frame in EP01_World says after its number (the look and the setting)
LOOKS = {"s01": "dawn · square", "s02": "dawn · square crane", "s03": "dawn · square high angle",
         "s04": "pre-dawn · bakery close-up", "s05": "pre-dawn · lane wide", "s06": "dawn · doorstep push-in",
         "s07": "day · square orbit", "s08": "day · square", "s09": "day · square", "s10": "day · park bandstand",
         "s11": "day to dusk · square orbit", "s12": "dusk · square", "s13": "dawn · bare doorstep",
         "s14": "dawn · baker's bedroom", "s15": "dawn · lane POV", "s16": "dawn · baker's door",
         "s17": "dawn · baker's door", "s18": "dawn · crane over town", "card": "dawn · town wide"}
TAG = 9 / 16  # the Studio tags were sized for a landscape frame; 9:16 sees 56% of its width


def build_town():
    return oldtown.build_town()


# --- helpers ---------------------------------------------------------------------------

def mm(fov):
    """Roblox vertical FOV (degrees) -> lens mm on the 9:16 frame (36 mm on the long side)."""
    return 18 / math.tan(math.radians(fov) / 2)


def k(s):
    """Roblox seconds -> this shot's seconds."""
    return s.dur / ROBLOX_SECONDS[s.name]


def ring(center, radius, i, n):
    a = (i / n) * math.pi * 2 + 0.4
    return center + R(math.cos(a) * radius, 0, math.sin(a) * radius)


def head(at, scale=1.0):
    """Head centre of an avatar standing at `at` (Blender point)."""
    return at + R(0, HEAD * scale, 0)


def put(s, rig, at, toward=None, t=0.0):
    """Puppet.place: feet at `at`, facing along a Roblox direction vector."""
    acting.place(s, rig, at, t, face=(at + R(*toward)) if toward is not None else None)


def prop(s, name, shown=True, at=None):
    """A copy of a town prop for this shot (shared town objects stay untouched)."""
    src = TOWN.props[name]
    ob = src.copy()
    s.adopt(ob, None, tuple(at if at is not None else src.location))
    ob.rotation_euler = src.rotation_euler
    ob.hide_render = ob.hide_viewport = False
    if not shown:
        key(ob, "scale", (0, 0, 0), s.f0, "CONSTANT")
    return ob


def appear(s, ob, t, on=True):
    """Pop an object of this shot in (or out) at time t."""
    key(ob, "scale", (1, 1, 1) if on else (0, 0, 0), s.f(t), "CONSTANT")


def recolor(s, ob, material, t=0.0):
    """Swap a shared town object for a recoloured copy during this shot (from time t)."""
    c = ob.copy()
    c.data = ob.data.copy()
    c.data.materials.clear()
    c.data.materials.append(material)
    s.adopt(c, None, tuple(ob.matrix_world.translation))
    c.matrix_world = ob.matrix_world.copy()
    if t > 0:
        key(c, "scale", (0, 0, 0), s.f0, "CONSTANT")
        key(c, "scale", tuple(ob.scale), s.f(t), "CONSTANT")
        c.location.y -= 0.02  # just in front of the original it covers
    else:
        s.hide(ob)
    return c


def town_obj(name):
    return next(o for o in TOWN.objects if o.name == name)


def bakery_dark(s):
    s.hide(town_obj("Bakery.BakeryLight"))
    dark = mat((0.017, 0.026, 0.042), rough=0.2)
    for w in TOWN.windows("Bakery"):
        recolor(s, w, dark)


def windows_warm(s):
    warm = mat(WARM, rough=0.4, emit=3.0)
    for w in TOWN.windows():
        if not w.name.startswith("Bakery."):
            recolor(s, w, warm)


def stage(s, light, cast=("hero",), tags=True, untagged=(), tag_scale=1.0):
    """Light the shot and stand the cast at their homes with their numbers (stage() in Luau).
    Returns {role: rig} and {role: tag}."""
    lighting.preset(s, light, label=LOOKS.get(s.name), look=HAND_LOOKS.get(s.name))
    rigs, nums = {}, {}
    homes = {"hero": (HERO_HOME, (0, 0, 1)), "influencer": (INFLUENCER_HOME, (0, 0, 1)),
             "kid": (KID_HOME, (0, 0, -1)), "baker": (BAKER_HOME, (0, 0, 1))}
    for i, role in enumerate(CROWD, 1):
        spot = ring(R(0, PLAZA, 0), 22, i, len(CROWD))
        homes[role] = (spot, None)
    values = random.Random(7)
    crowd_values = {r: values.randint(40, 3000) for r in CROWD}
    for role in cast:
        rig = roblox_avatar(s, role, (0, 0, 0), h=H)
        at, toward = homes[role]
        put(s, rig, at, toward)
        if toward is None:  # the crowd faces the fountain
            acting.place(s, rig, at, 0.0, face=R(0, PLAZA, 0))
        rigs[role] = rig
        size = 6 * TAG * tag_scale
        if tags and role not in untagged:
            if role == "hero":
                nums[role] = numbers.tag(s, rig, 212, size=size)
            elif role == "baker":
                nums[role] = numbers.tag(s, rig, 9, size=size)
            elif role == "influencer":
                nums[role] = numbers.tag(s, rig, 50000, size=size * 7 / 6)
            elif role == "kid":
                nums[role] = numbers.tag(s, rig, 57, size=size * 4 / 6, height=2.4)
            else:
                nums[role] = numbers.tag(s, rig, crowd_values[role], size=size)
    return rigs, nums


# --- the shots ---------------------------------------------------------------------------

def s01(s):  # "In my town, everyone has a number floating over their head."
    rigs, nums = stage(s, "dawn", ("hero", "influencer", "kid", *CROWD[:4]))
    nums["hero"].fade_in(0.0, 1.6 * k(s))
    h = head(HERO_HOME)
    above = h + R(0, 1.8, 0)
    cam.push(s, h + R(0, -2, 14), h + R(0, -1, 9), above, mm=mm(40)).zoom(0, s.dur, mm(36))


def s02(s):  # "Nobody remembers who put it there."  24 mm crane down into the square
    stage(s, "day", ("hero", "influencer", "kid", *CROWD))
    cam.crane(s, R(0, 70, -40), R(6, 16, -26), R(0, 4, 30), R(0, 6, 40), mm=mm(70))


def s03(s):  # "Mine was two-twelve. Low. Embarrassing."  high angle: the myth makes him small
    rigs, _ = stage(s, "day", ("hero", *CROWD[:3]))
    hero = rigs["hero"]
    acting.pose(s, hero, "look_up", 0.3 * k(s), 0.4)
    acting.pose(s, hero, "shrug", 1.4 * k(s), 0.3)
    acting.expression(s, hero, "worried", 1.4 * k(s))
    h = head(HERO_HOME)
    cam.static(s, h + R(0, 7, 9), h + R(0, 0.5, 0), mm=mm(54))


def s04(s):  # "The baker had nine. Just nine."  85 mm close-up at her bakery, nearly still
    rigs, nums = stage(s, "pre_dawn_dark", ("baker",), tag_scale=0.55)
    baker = rigs["baker"]
    put(s, baker, BAKER_HOME, (0, 0, 1))
    basket = prop(s, "Basket")
    acting.hold(s, baker, basket, "right", 0.0)
    acting.pose(s, baker, "carry", 0.0, 0.0)
    acting.pose(s, baker, "look_down", 0.55 * s.dur, 0.6)  # "Just nine."
    h = head(BAKER_HOME)
    cam.push(s, h + R(1.6, 1.0, 14.5), h + R(1.5, 0.95, 14.0), h + R(0, 1.3, 0), mm=85, ease="linear",
             fstop=2.0, focus=baker)


def s05(s):  # "But every morning, before anyone woke up,"  wide: the empty lane, every window dark
    rigs, _ = stage(s, "pre_dawn_dark", ("baker",), tags=False)
    baker = rigs["baker"]
    start = R(-64, SIDEWALK, -67)
    put(s, baker, start, (1, 0, 0))
    basket = prop(s, "Basket")
    acting.hold(s, baker, basket, "right", 0.0)
    acting.pose(s, baker, "carry", 0.0, 0.0)
    acting.walk_to(s, baker, R(-36, SIDEWALK, -67), 0.0, s.dur)  # away from us, toward first light
    cam.static(s, R(-90, 3.0, -60.5), R(30, 9, -68), mm=26, fstop=8)


LOAF = R(-43.4, 1.5, -70.4)                       # Bread_1 on House_1's step
LOAF_CAM, LOAF_LOOK = R(-39.6, 2.1, -67.4), LOAF + R(0, 0.1, 0)  # where 06 ends and 13 sits


def s06(s):  # "she left bread on the doorsteps of houses with no lights on."  push in to one loaf
    stage(s, "dawn", ())
    prop(s, "Bread_1")
    c = cam.push(s, R(-22, 5.5, -60), LOAF_CAM, R(-46, 4.0, -71.5), mm=35, ease="inout",
                 fstop=2.8, focus=LOAF_LOOK)
    c.move(0.0, s.dur, look=LOAF_LOOK)
    c.zoom(0.0, s.dur, 85)


def s07(s):  # "The guy with fifty thousand never said hi to anyone."  low 24 mm orbit
    rigs, _ = stage(s, "day", ("influencer", "kid", *CROWD[:4]))
    inf = rigs["influencer"]
    put(s, inf, INFLUENCER_HOME, (-1, 0, 0))
    acting.pose(s, inf, "flex", 0.0, 0.4)
    cam.orbit(s, inf, r=7, h=-2.5, a0=-160, a1=-200, mm=mm(74))


def s08(s):  # "He was busy making his number go up."  over the kid's shoulder
    rigs, _ = stage(s, "day", ("influencer", "kid", *CROWD[:3]), untagged=("kid",))
    inf, kid = rigs["influencer"], rigs["kid"]
    phone = prop(s, "Phone")
    acting.hold(s, inf, phone, "right", 0.0, rigid=True)
    acting.pose(s, inf, "phone", 0.0, 0.0)
    acting.pose(s, kid, "wave", 0.2 * k(s), 0.3)
    kh = head(KID_HOME, 0.7)
    cam.static(s, kh + R(1.6, 1.2, 4.5), inf, mm=mm(40))


def s09(s):  # "So I did what everyone does."
    rigs, _ = stage(s, "day", ("hero", "influencer", "kid", *CROWD[:4]))
    hero = rigs["hero"]
    q = k(s)
    acting.turn_to(s, hero, rigs["influencer"].head, 0.0, 0.4)
    acting.turn_to(s, hero, HERO_HOME + R(0, 0, 10), 1.4 * q, 0.4)
    acting.pose(s, hero, "look_up", 1.4 * q, 0.4)
    acting.expression(s, hero, "smug", 1.4 * q)
    h = head(HERO_HOME)
    cam.push(s, h + R(0, -1, 14), h + R(0, -0.5, 9), h + R(0, 1.8, 0), mm=mm(40))


def s10(s):  # "I started performing."  on the park bandstand, crash zoom 24 -> 60 mm
    rigs, nums = stage(s, "day", ("hero", *CROWD[:3]), untagged=CROWD[:3])
    hero = rigs["hero"]
    at = TOWN.marker("Mark_Bandstand")
    put(s, hero, at, (0, 0, 1))
    acting.pose(s, hero, "flex", 0.0, 0.25)
    acting.expression(s, hero, "grin", 0.0)
    for i, role in enumerate(CROWD[:3]):  # a thin audience below the stage
        spot = at + R(-7 + i * 7, 0, 18 + (i % 2) * 3)
        spot.z = TOWN.marker("Mark_Bandstand").z - 3.2
        acting.place(s, rigs[role], spot, 0.0, face=at)
    h = head(at)
    cam.static(s, h + R(0, -0.6, 36), h + R(0, 0.6, 0), mm=24).snap_zoom(0.35 * k(s), 60)


def s11(s):  # "Nine hundred. Three thousand. Ten thousand."
    rigs, nums = stage(s, "day", ("hero", *CROWD))
    lighting.blend(s, "day", "dusk", 0.0, s.dur)
    q = k(s)
    hero = rigs["hero"]
    for i, role in enumerate(CROWD, 1):
        acting.walk_to(s, rigs[role], ring(HERO_HOME, 9, i, len(CROWD)), 0.0, 2.2 * q)
        acting.turn_to(s, rigs[role], HERO_HOME, 2.2 * q, 0.3)
    acting.backflip(s, hero, 0.0, 1.0 * q)
    acting.pose(s, hero, "flex", 1.0 * q, 0.3)
    acting.expression(s, hero, "grin", 0.0)
    acting.pose(s, hero, "wave", 2.7 * q, 0.3)
    for i, n in enumerate((900, 3000, 10000)):  # each number lands on its spoken line
        t = s.line(i)["start"]
        nums["hero"].count_to(t, n, dur=0.6)
        nums["hero"].pulse(t + 0.6)
    cam.orbit(s, hero, r=13, h=-1.5, a0=-60, a1=-150, mm=mm(70)).shake(0.25)  # r 9 in Studio ran into the crowd ring


def s12(s):  # "And the bigger it got, the fewer people actually knew my name."  135 mm, alone
    rigs, nums = stage(s, "dusk", ("hero", *CROWD), tags=True)
    nums["hero"].set(0.0, 10000)
    q = k(s)
    hero = rigs["hero"]
    put(s, hero, HERO_HOME, (-1, 0, 0))
    acting.expression(s, hero, "worried", 1.5 * q)
    for i, role in enumerate(CROWD, 1):
        spot = ring(HERO_HOME, 9, i, len(CROWD))
        acting.place(s, rigs[role], spot, 0.0, face=HERO_HOME)
        if i > 1:
            acting.walk_to(s, rigs[role], ring(HERO_HOME, 48, i, len(CROWD)), 0.1 * i * q, 0.1 * i * q + 2.0 * q)
    passer = rigs[CROWD[0]]  # crosses between us and the Hero early, half-waving
    start = HERO_HOME + R(-8, 0, -10)
    put(s, passer, start, (0, 0, 1))
    acting.pose(s, passer, "wave", 0.0, 0.3)
    acting.walk_to(s, passer, HERO_HOME + R(-8, 0, 14), 0.5 * q, 2.3 * q)
    h = head(HERO_HOME)
    c = R(-48, HEAD + PLAZA + 0.5, 14)
    cam.static(s, c, h + R(0, 1.2, 0), mm=mm(15), fstop=2.8, focus=hero)


def s13(s):  # "One morning, there was no bread."  where 06 ended: the same step, empty
    stage(s, "dawn", ())
    bakery_dark(s)
    cam.push(s, LOAF_CAM + R(0.6, 0.1, 0.5), LOAF_CAM, LOAF_LOOK, mm=85, ease="linear", fstop=2.8,
             focus=LOAF_LOOK)


def s14(s):  # "The baker was sick."
    rigs, nums = stage(s, "dawn", ("baker",))
    baker = rigs["baker"]
    mattress = town_obj("BakerBedroom.Mattress")
    top = mattress.matrix_world.translation + R(0.4, 0.3, 0)
    acting.lie(s, baker, 0.0, at=top + R(-2.6, 0, 0), head=top + R(3, 0, 0))
    acting.expression(s, baker, "sleepy_old", 0.0)
    nums["baker"].dim(0.0, 0.6, 0.0)
    cam.static(s, TOWN.marker("Cam_BakerWindow") + R(0, 2, 0), mattress.matrix_world.translation, mm=mm(45))


def s15(s):  # "And I realized no number in town could have told me that."  his POV, 135 mm
    rigs, _ = stage(s, "dawn", CROWD)
    bakery_dark(s)
    for i, role in enumerate(CROWD, 1):
        put(s, rigs[role], R(-36 + i * 11, SIDEWALK, -65), (0, 0, 1))
    cam.push(s, R(-80, 6.8, -62.5), R(-74, 6.8, -62.5), R(20, 6.5, -65), mm=mm(15)).zoom(0, s.dur, mm(13))


def s16(s):  # "So I brought her bread."  eye level 50 mm, then an 85 mm insert on the hand-off
    rigs, nums = stage(s, "dawn", ("hero", "baker"))
    nums["hero"].set(0.0, 10000)
    q = k(s)
    hero, baker = rigs["hero"], rigs["baker"]
    spot = R(75.9, STEP, -69.3)  # close enough to reach each other
    door = R(75, STEP, -71.3)
    acting.place(s, hero, spot, 0.0, face=R(75, STEP, -71.6))
    acting.place(s, baker, R(75, STEP, -90), 0.0)  # inside, out of sight until the door opens
    loaf = prop(s, "Bread_1")  # the same loaf model as the doorsteps
    acting.hold(s, hero, loaf, "left", 0.0, rigid=True)
    acting.pose(s, hero, "knock", 0.0, 0.2)
    acting.tap(s, hero, 0.0, 1.2 * q)
    acting.pose(s, hero, "hold_left", 1.2 * q, 0.2)
    recolor(s, town_obj("BakerHouse.Door"), mat((0.005, 0.004, 0.003), rough=0.6), t=1.4 * q)
    acting.place(s, baker, door, 1.4 * q, face=spot)
    acting.expression(s, baker, "surprised_old", 1.4 * q)
    acting.pose(s, hero, "give", 1.9 * q, 0.4)    # he holds it out
    acting.pose(s, baker, "give", 2.2 * q, 0.35)  # she reaches for it
    acting.hold(s, baker, loaf, "left", 2.6 * q, snap=False, rigid=True)  # it passes to her reaching hand
    acting.pose(s, baker, "hold_left", 2.9 * q, 0.35)  # and she brings it in to her
    acting.pose(s, hero, "idle", 2.8 * q, 0.4)
    acting.expression(s, baker, "smile_old", 3.0 * q)
    c = cam.static(s, R(67.5, 5.2, -60.5), R(76, 4.5, -70.5), mm=mm(40))
    # the hand-off from the side, across the two of them, framed on the loaf between their hands
    c.cut(2.0 * q, pos=R(82.0, 6.8, -70.3), look=R(75.4, 3.9, -70.3), mm=48)  # side-on, over the pots


def s17(s):  # "My number didn't move. Not even by one."  85 mm, the motif held still
    rigs, nums = stage(s, "dawn", ("hero",), tag_scale=0.55)
    nums["hero"].set(0.0, 10000)
    hero = rigs["hero"]
    at = BAKER_DOOR + R(0, 0, 1.5)
    put(s, hero, at, (0, 0, 1))
    acting.expression(s, hero, "smile", 0.0)
    h = head(at)
    cam.static(s, h + R(0, 1.6, 14), h + R(0, 1.6, 0), mm=mm(24), fstop=2.0, focus=hero)


def sky(s):
    """The 26 numbers floating over the town (shot 18 and the end card)."""
    values = random.Random(26)
    for i, p in enumerate(TOWN.sky_anchors):
        anchor = s.empty(f"{s.name}_sky{i}", tuple(p))
        numbers.tag(s, anchor, values.randint(3, 90000), size=9, height=0)


def s18(s):  # "Turns out the number never measured what we thought. It only measured who was watching."
    rigs, nums = stage(s, "dawn", ("hero",))
    nums["hero"].set(0.0, 10000)
    hero = rigs["hero"]
    at = BAKER_DOOR + R(0, 0, 1.5)
    put(s, hero, at, (0, 0, 1))
    acting.expression(s, hero, "smile", 0.0)
    sky(s)
    lighting.windows(s, 0.0, to=0.3, t0=0.3 * s.dur)  # as the crane rises, lights come on across town
    h = head(at)
    c = cam.crane(s, h + R(0, 0.3, 9), TOWN.marker("Cam_Town_Crane"), h, R(0, 0, -40), mm=mm(40)).zoom(0, s.dur, mm(45))
    c.declip()  # the crane rises through the lane's roofs: clip them while they're in the way


def card(s):  # end card: the warm town at dawn under the question
    stage(s, "dawn", ())
    sky(s)
    lighting.windows(s, 0.3)  # and stay on over the end card
    cam.static(s, TOWN.marker("Cam_Town_Crane"), R(0, 0, -40), mm=mm(45))


SHOTS = {f"s{i:02d}": globals()[f"s{i:02d}"] for i in range(1, 19)}
SHOTS["card"] = card
