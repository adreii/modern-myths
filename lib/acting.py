"""Acting for imported Roblox avatars (lib/imported.py rigs): poses, walking, stunts, props.

A port of roblox/StoryKit/Puppet.luau to keyframes. Every call keys the rig at shot time t
(seconds from the shot start), so call them in story order:

    acting.place(s, hero, (75, -71, 0.9), face=(75, -60))   # stand there, facing a point
    acting.pose(s, hero, "knock", 0.0, 0.2)                # blend into a pose
    acting.tap(s, hero, 0.2, 1.2)                          # knock-knock
    acting.walk_to(s, baker, (6, 66.5), 1.0, 3.0)          # walk there, facing the way
    acting.hold(s, hero, bag, "left", 0.0)                 # weld a prop to a hand
    acting.release(s, hero, bag, 2.4)                      # (or hold() it with another rig)
    acting.expression(s, hero, "surprised", 1.5)

Positions are in the rig root's parent space (town coordinates in town shots), z up.
Characters face -Y at yaw 0. "right"/"left" are the avatar's own sides, as in Puppet:
the avatar's right arm is rig.arm_l (screen left when it faces the camera).
R15 limbs move as one piece, so Puppet's elbow and knee bends are folded into the
shoulder and hip angles.
"""
import math

import bpy
from mathutils import Matrix, Vector

from .core import fcurves, key

# Joint angles in degrees. fwd: swing forward (on the neck: look up). side: lift the arm
# out to its own side. roll: tilt the head. "drop": lower the root, as a share of the
# hip height (crouch). Elbows/knees from Puppet are folded in at about half their bend.
POSES = {
    "idle": {},
    "look_up": {"neck": {"fwd": 28}},
    "look_down": {"neck": {"fwd": -25}},
    "shrug": {"right_arm": {"fwd": 40, "side": 25}, "left_arm": {"fwd": 40, "side": 25}, "neck": {"roll": 10}},
    "wave": {"right_arm": {"fwd": 10, "side": 155}},
    "flex": {"right_arm": {"side": 135}, "left_arm": {"side": 135}, "neck": {"fwd": 10}},
    # a lunge: no knees, so one leg reaches forward and the other back, and the root drops
    # until both feet touch the ground
    "crouch": {"right_leg": {"fwd": 45}, "left_leg": {"fwd": -35}, "right_arm": {"fwd": 65},
               "left_arm": {"fwd": 40}, "neck": {"fwd": -15}, "drop": None},
    "tuck": {"right_leg": {"fwd": 80}, "left_leg": {"fwd": 80}, "right_arm": {"fwd": 70}, "left_arm": {"fwd": 70}},
    "carry": {"right_arm": {"fwd": 50}},
    "phone": {"right_arm": {"fwd": 80, "side": -12}, "neck": {"fwd": -30}},
    "knock": {"right_arm": {"fwd": 120}, "left_arm": {"fwd": 30}},
    "give": {"left_arm": {"fwd": 85}},
    "hold_left": {"left_arm": {"fwd": 30}},
}
JOINTS = ("neck", "right_arm", "left_arm", "right_leg", "left_leg")
HANDS = {"right": "right_arm", "righthand": "right_arm", "left": "left_arm", "lefthand": "left_arm"}
WALK_RATE = 9.0  # Puppet's swing, sin(t * 9)


# --- rig state ----------------------------------------------------------------------

def _joint(rig, name):
    return {"neck": rig.neck, "right_arm": rig.arm_l, "left_arm": rig.arm_r,
            "right_leg": rig.leg_l, "left_leg": rig.leg_r}[name]


def _euler(name, a):
    """Pose angles -> the joint's rotation_euler (radians)."""
    fwd, side, roll = (math.radians(a.get(k, 0)) for k in ("fwd", "side", "roll"))
    if name == "neck":
        return Vector((-fwd, roll, 0))
    # right arm (rig.arm_l) hangs at -X, so lifting it outwards is +Y; the left arm is -Y
    return Vector((-fwd, side if name.startswith("right") else -side, 0))


def _state(rig):
    """Per-rig bookkeeping: ground height, current crouch drop, hands holding props."""
    if not hasattr(rig, "act"):
        rig.act = {"ground": rig.root.location.z, "drop": 0.0, "held": {}}
    return rig.act


def _hip(rig):
    """Hip height (= leg length) in studs."""
    return rig.leg_l.location.z * rig.root.scale.z


def _val(ob, path, frame):
    """A property's animated value at a frame (its current value where nothing is keyed)."""
    v = getattr(ob, path)
    vals = list(v) if hasattr(v, "__len__") else [v]
    for fc in fcurves(ob):
        if fc.data_path == path and fc.array_index < len(vals):
            vals[fc.array_index] = fc.evaluate(frame)
    return Vector(vals) if len(vals) > 1 else vals[0]


def _linear(ob, path, f0, f1):
    for fc in fcurves(ob):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                if f0 - 0.5 <= kp.co.x <= f1 + 0.5:
                    kp.interpolation = "LINEAR"


def _frames(s, t0, t1):
    """Every frame from t0 to t1 with its shot time."""
    f0, f1 = s.f(t0), max(s.f(t1), s.f(t0) + 1)
    return [(f, t0 + (t1 - t0) * (f - f0) / (f1 - f0)) for f in range(f0, f1 + 1)]


def _world(ob, frame):
    scene = bpy.context.scene
    keep = scene.frame_current
    scene.frame_set(frame)
    m = ob.matrix_world.copy()
    scene.frame_set(keep)
    return m


def _local_point(rig, p, frame):
    """A point (tuple, Vector or object) in the root's parent space."""
    if isinstance(p, bpy.types.Object):
        p = _world(p, frame).translation
        parent = rig.root.parent
        if parent is not None:
            p = _world(parent, frame).inverted() @ p
    return Vector((p[0], p[1], p[2] if len(p) > 2 else 0.0))


def _yaw_to(d):
    """Yaw (radians) that faces the rig (-Y at yaw 0) along horizontal direction d."""
    return math.atan2(d[0], -d[1])


def _near(a, ref):
    """Angle a moved by whole turns to be within half a turn of ref (shortest turn)."""
    return ref + (a - ref + math.pi) % (2 * math.pi) - math.pi


# --- poses --------------------------------------------------------------------------

def pose(s, rig, name, t, dur=0.25):
    """Blend from the current pose into a named pose (POSES) over dur seconds."""
    if name not in POSES:
        raise KeyError(f"no pose {name!r} (have {sorted(POSES)})")
    st = _state(rig)
    target = POSES[name]
    f0 = s.f(t)
    f0, f1 = (f0, max(s.f(t + dur), f0 + 1)) if dur > 0 else (f0 - 1, f0)  # dur 0 snaps
    for j in JOINTS:
        ob = _joint(rig, j)
        key(ob, "rotation_euler", _val(ob, "rotation_euler", f0), f0)
        key(ob, "rotation_euler", _euler(j, target.get(j, {})), f1)
    drop = 0.0
    if "drop" in target:  # lower the root until the splayed legs reach the ground
        legs = [abs(math.radians(target.get(k, {}).get("fwd", 0))) for k in ("right_leg", "left_leg")]
        drop = _hip(rig) * (1 - math.cos(max(legs)))
    if abs(drop - st["drop"]) > 1e-6:
        loc = _val(rig.root, "location", f0)
        key(rig.root, "location", loc, f0)
        key(rig.root, "location", Vector((loc.x, loc.y, st["ground"] - drop)), f1)
        st["drop"] = drop


def place(s, rig, at, t=0.0, face=None):
    """Stand the rig with its feet at `at` from time t (a cut, not a move), facing a point
    or a yaw in degrees (default: keep facing)."""
    st = _state(rig)
    f = s.f(t)
    p = _local_point(rig, at, f)
    if len(at) < 3 and not isinstance(at, bpy.types.Object):
        p.z = st["ground"]
    rot = _val(rig.root, "rotation_euler", f)
    yaw = rot.z if face is None else _face_yaw(rig, face, rot.z, f, p)
    if f > s.f0:  # hold the old spot until the cut
        key(rig.root, "location", _val(rig.root, "location", f - 1), f - 1)
        key(rig.root, "rotation_euler", _val(rig.root, "rotation_euler", f - 1), f - 1)
    key(rig.root, "location", Vector((p.x, p.y, p.z - st["drop"])), f)
    key(rig.root, "rotation_euler", Vector((0, 0, yaw)), f)
    _linear(rig.root, "location", f - 1, f)
    _linear(rig.root, "rotation_euler", f - 1, f)
    st["ground"] = p.z


def _face_yaw(rig, target, cur, frame, here=None):
    if isinstance(target, (int, float)):
        return _near(math.radians(target), cur)
    here = here if here is not None else _val(rig.root, "location", frame)
    d = _local_point(rig, target, frame) - here
    return _near(_yaw_to(d), cur) if d.xy.length > 1e-4 else cur


def turn_to(s, rig, target, t, dur=0.3):
    """Turn in place to face a point/object, or a yaw in degrees (0 faces -Y)."""
    f0 = s.f(t)
    rot = _val(rig.root, "rotation_euler", f0)
    key(rig.root, "rotation_euler", rot, f0)
    key(rig.root, "rotation_euler", Vector((rot.x, rot.y, _face_yaw(rig, target, rot.z, f0))),
        max(s.f(t + dur), f0 + 1))


# --- walking ------------------------------------------------------------------------

def walk_time(rig, dist):
    """Seconds to walk `dist` studs at Puppet's swing rate without the feet skating."""
    return dist * math.pi / (2 * _hip(rig) * math.sin(math.radians(30)) * WALK_RATE)


def walk_to(s, rig, to, t0, t1, arms=True):
    """Walk to a ground point (x, y[, z]) between t0 and t1, facing the way, legs ±30° and
    arms ±25° as in Puppet. The swing rate follows the speed so the feet don't skate
    (sin(t*9) at walk_time() pace); fast walks lengthen the stride up to ±45° first."""
    st = _state(rig)
    f0 = s.f(t0)
    start = _val(rig.root, "location", f0)
    start.z = st["ground"]
    end = _local_point(rig, to, f0)
    if len(to) < 3 and not isinstance(to, bpy.types.Object):
        end.z = st["ground"]
    dist = (end - start).xy.length
    speed = dist / max(t1 - t0, 1e-3)
    L = _hip(rig)
    amp = math.radians(30)
    rate = speed * math.pi / (2 * L * math.sin(amp))  # stance foot moves back as fast as we walk
    if rate > 14:  # Roblox walks run at ~16 studs/s: take longer strides before flailing
        amp = min(math.radians(45), math.asin(min(1.0, speed * math.pi / (2 * L * 14))))
        rate = speed * math.pi / (2 * L * math.sin(amp))
    # whole half-steps, so the legs end together
    steps = max(1, round(rate * (t1 - t0) / math.pi))
    rate = steps * math.pi / max(t1 - t0, 1e-3)
    arm_amp = amp * 25 / 30

    rot = _val(rig.root, "rotation_euler", f0)
    if dist > 1e-3:
        yaw = _near(_yaw_to(end - start), rot.z)
        key(rig.root, "rotation_euler", rot, f0)
        key(rig.root, "rotation_euler", Vector((rot.x, rot.y, yaw)), f0 + max(1, round(0.15 * s.fps)))

    limbs = {j: _val(_joint(rig, j), "rotation_euler", f0) for j in JOINTS[1:]}
    held = {j for j, p in st["held"].items() if p is not None}
    for f, t in _frames(s, t0, t1):
        u = (t - t0) / max(t1 - t0, 1e-3)
        sw = math.sin(rate * (t - t0))
        p = start.lerp(end, u)
        p.z -= st["drop"] + L * (1 - math.cos(amp * sw))  # the planted foot stays on the ground
        key(rig.root, "location", p, f)
        for j, sign, a in (("left_leg", 1, amp), ("right_leg", -1, amp),
                           ("left_arm", -1, arm_amp), ("right_arm", 1, arm_amp)):
            r = limbs[j].copy()
            if j.endswith("leg") or (arms and j not in held):
                r.x -= sign * a * sw  # +fwd is -X
            key(_joint(rig, j), "rotation_euler", r, f)
    f1 = _frames(s, t0, t1)[-1][0]
    key(rig.root, "location", Vector((end.x, end.y, end.z - st["drop"])), f1)
    for j in JOINTS[1:]:
        key(_joint(rig, j), "rotation_euler", limbs[j], f1)
        _linear(_joint(rig, j), "rotation_euler", f0, f1)
    _linear(rig.root, "location", f0, f1)
    st["ground"] = end.z


# --- gestures and stunts ------------------------------------------------------------

def tap(s, rig, t0, t1, deg=25):
    """Knock: bounce the right arm (Puppet's elbow tap) from t0 to t1."""
    arm = _joint(rig, "right_arm")
    f0 = s.f(t0)
    base = _val(arm, "rotation_euler", f0)
    for f, t in _frames(s, t0, t1):
        r = base.copy()
        r.x += math.radians(deg) * max(0.0, math.sin((t - t0) * 14))  # back from the door
        key(arm, "rotation_euler", r, f)
    key(arm, "rotation_euler", base, _frames(s, t0, t1)[-1][0])
    _linear(arm, "rotation_euler", f0, s.f(t1))


def backflip(s, rig, t, dur=1.0, height=6.0):
    """Jump `height` studs, flip backwards once around the body's middle and land on the
    same spot. Tucks the legs on the way up and stands back up at the end."""
    st = _state(rig)
    f0 = s.f(t)
    base = _val(rig.root, "location", f0)
    rot = _val(rig.root, "rotation_euler", f0)
    yaw = Matrix.Rotation(rot.z, 3, "Z")
    mid = rig.root.scale.z * 0.5  # spin around the waist, not the feet
    pose(s, rig, "tuck", t, dur * 0.2)
    for f, tt in _frames(s, t, t + dur):
        a = (tt - t) / dur
        ang = -2 * math.pi * a  # head goes back (+Y) first
        centre = base + Vector((0, 0, mid + math.sin(a * math.pi) * height))
        offset = yaw @ Matrix.Rotation(ang, 3, "X") @ Vector((0, 0, -mid))
        key(rig.root, "location", centre + offset, f)
        key(rig.root, "rotation_euler", Vector((ang if a < 1 else 0.0, rot.y, rot.z)), f)
    f1 = _frames(s, t, t + dur)[-1][0]
    _linear(rig.root, "location", f0, f1)
    _linear(rig.root, "rotation_euler", f0, f1)
    st["drop"] = 0.0
    pose(s, rig, "idle", t + dur * 0.8, dur * 0.2)


def lie(s, rig, t, on=True, at=None, head=None):
    """Lie on the back, face to the sky, from time t (a cut, as in Puppet), with the feet
    at `at` (default: where it stands) and the head towards `head` (a point/object or a
    yaw in degrees; default: falling backwards). on=False stands it back up there."""
    st = _state(rig)
    f = s.f(t)
    loc = _val(rig.root, "location", f)
    rot = _val(rig.root, "rotation_euler", f)
    p = _local_point(rig, at, f) if at is not None else Vector((loc.x, loc.y, st["ground"]))
    if at is not None and len(at) < 3 and not isinstance(at, bpy.types.Object):
        p.z = st["ground"]
    if on:
        st["stand"] = (Vector((loc.x, loc.y, st["ground"])), rot.z)
        back = max(v.co.y for v in rig.body.data.vertices) * rig.root.scale.y  # half the body's depth
        # the head ends up along local +Y turned by yaw; face that way for the default
        yaw = rot.z if head is None else _face_yaw(rig, head, rot.z, f, p) + math.pi
        new_loc, new_rot = p + Vector((0, 0, back)), Vector((math.radians(-90), 0, yaw))
    else:
        p0, yaw = st.get("stand", (p, rot.z))
        new_loc, new_rot = (p if at is not None else p0), Vector((0, 0, yaw))
    pose(s, rig, "idle", t, 0)
    if f > s.f0:
        key(rig.root, "location", loc, f - 1)
        key(rig.root, "rotation_euler", rot, f - 1)
    key(rig.root, "location", new_loc, f)
    key(rig.root, "rotation_euler", new_rot, f)
    _linear(rig.root, "location", f - 1, f)
    _linear(rig.root, "rotation_euler", f - 1, f)
    st["drop"] = 0.0


# --- props --------------------------------------------------------------------------

def _hand_tip(rig, hand):
    """The bottom of a hand in its shoulder joint's own space."""
    joint = _joint(rig, hand)
    pts = [c.matrix_basis @ v.co for c in joint.children if c.type == "MESH" for v in c.data.vertices]
    low = min(p.z for p in pts)
    x = sum(p.x for p in pts) / len(pts)
    y = sum(p.y for p in pts) / len(pts)
    return joint, Vector((x, y, low))


def _show(ob, frame, shown):
    for prop in ("hide_render", "hide_viewport"):
        setattr(ob, prop, not shown)
        ob.keyframe_insert(prop, frame=frame)


def _grip(s, rig, hand):
    """An empty at the bottom of a hand, riding its arm: what held props follow."""
    grips = _state(rig).setdefault("grips", {})
    if hand not in grips:
        joint, tip = _hand_tip(rig, hand)
        grips[hand] = s.empty(f"grip_{hand}", tuple(tip), joint)
    return grips[hand]


def hold(s, rig, prop, hand="right", t=0.0, offset=None, rigid=False, snap=True):
    """Hold `prop` in a hand from time t. The prop jumps so its top sits at the hand (plus
    `offset`, studs in world axes); snap=False grabs it where it is instead (hand-offs).
    It then follows the hand, hanging upright like a bag; rigid=True welds it to the hand
    so it turns with the arm (a phone). A prop another rig is holding is handed over.
    Uses a Child Of constraint whose influence is keyed."""
    hand = HANDS.get(hand.lower(), hand)
    f = s.f(t)
    seen = _world(prop, f)  # where it is now, still in the other hand
    for other in [o for o in _holders.get(prop.name, []) if o is not rig]:
        release(s, other, prop, t, keep=True)
    grip = _grip(s, rig, hand)
    gw = _world(grip, f)
    pw = _world(prop, f)  # its own (unheld) placement
    if snap:
        top = max((pw @ Vector(v)).z for v in prop.bound_box) - pw.translation.z
        want = Matrix.Translation(gw.translation - Vector((0, 0, top)) + Vector(offset or (0, 0, 0)))
        want = want @ pw.to_3x3().normalized().to_4x4() @ Matrix.Diagonal(pw.to_scale().to_4d())
    else:
        want = seen
    con = prop.constraints.new("CHILD_OF")
    con.name = f"hold_{rig.root.name}_{f}"
    con.target = grip
    if not rigid:  # follow the hand's position only
        for ax in "xyz":
            setattr(con, f"use_rotation_{ax}", False)
            setattr(con, f"use_scale_{ax}", False)
        gw = Matrix.Translation(gw.translation)
    con.inverse_matrix = gw.inverted() @ want @ pw.inverted()
    path = f'constraints["{con.name}"].influence'
    con.influence = 0.0
    prop.keyframe_insert(path, frame=s.f0 - 1)
    if f > s.f0:
        prop.keyframe_insert(path, frame=f - 1)
    con.influence = 1.0
    prop.keyframe_insert(path, frame=f)
    prop.keyframe_insert(path, frame=s.f1)
    con.influence = 0.0  # let go at the end of the shot, so shared town props stay put
    prop.keyframe_insert(path, frame=s.f1 + 1)
    _show(prop, f, True)
    _state(rig)["held"][hand] = prop
    _holders.setdefault(prop.name, []).append(rig)


_holders = {}  # prop name -> rigs that have held it


def release(s, rig, prop, t, at=None, keep=False):
    """Let go of a held prop at time t. With `at` (x, y, z in the prop's parent space) it is
    parked there; otherwise it disappears, as in Puppet (keep=True leaves it visible)."""
    f = s.f(t)
    for con in prop.constraints:
        if con.type == "CHILD_OF" and con.name.startswith(f"hold_{rig.root.name}_"):
            path = f'constraints["{con.name}"].influence'
            if _val_path(prop, path, f) > 0:
                con.influence = 1.0
                prop.keyframe_insert(path, frame=f - 1)
                con.influence = 0.0
                for fr in (f, s.f1):
                    if fr >= f:
                        prop.keyframe_insert(path, frame=fr)
    st = _state(rig)
    st["held"] = {h: p for h, p in st["held"].items() if p is not prop}
    if rig in _holders.get(prop.name, []):
        _holders[prop.name].remove(rig)
    if at is not None:
        key(prop, "location", _val(prop, "location", f - 1), f - 1)
        key(prop, "location", Vector(at), f)
        _linear(prop, "location", f - 1, f)
    elif not keep:
        _show(prop, f, False)
        _show(prop, s.f1 + 1, True)  # back for the next shot


def _val_path(ob, path, frame):
    for fc in fcurves(ob):
        if fc.data_path == path:
            return fc.evaluate(frame)
    return 0.0


# --- faces --------------------------------------------------------------------------

def expression(s, rig, name, t):
    """Change the face at time t. A bare name ("surprised") takes the age suffix of the
    rig's own faces, so the Baker gets surprised_old."""
    from . import imported
    if "_" not in name and rig.faces:
        first = next(iter(rig.faces))
        if "_" in first:
            name = f"{name}_{first.split('_', 1)[1]}"
    imported.face(s, rig, name, t)
