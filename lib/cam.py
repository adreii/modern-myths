"""Camera moves with real lenses (port of roblox/StoryKit/CameraRig.luau).

    c = cam.push(s, pos=(0, -20, 6), to_pos=(0, -9, 6), look=hero.head, mm=50)
    c = cam.orbit(s, hero.head, r=9, h=-2.5, a0=-60, a1=-150, mm=24).shake(0.25)
    c = cam.static(s, (0, -30, 5), hero.head, mm=135, fstop=2.8)
    c.cut(1.2, pos=(4, -6, 5)).snap_zoom(1.2, 50)

Lenses are millimetres on a 36 mm sensor fitted to the frame's long side, which in 9:16 is
the height, so they match the shot list's Roblox FOV key (24 mm = 74°, 50 = 40°, 135 = 15°).

Positions and look targets are a point (relative to the shot root), an object, or
(object, offset): objects are followed, so the camera can track a walker. A Rig counts as
its head. Moves ease in-out (sine) unless ease="linear" (or "in", "out").

Rig: <shot>_rig (position) > <shot>_aimer (Track To the look point) > <shot>_cam (roll, shake).
The camera comes from core.camera, so it is bound to the shot's timeline marker.
"""
import math
import zlib

import bpy
from mathutils import Vector

from . import core
from . import numbers

STUD = 0.28           # metres per stud: real f-stops are scaled by this so DOF reads at true size
# Cameras the user set up by hand (e.g. with the Lens Optics add-on), by shot: build.py fills
# this from the episode's cameras.blend. Such a shot keeps that camera data as it is: its lens,
# focus and the add-on's settings are never written or keyed here (the add-on drives `lens`
# from its own focal_mm, and keys on `lens` would be overwritten anyway). Rig moves still apply.
HAND = {}

RIG_COLOR = (0.55, 0.2, 1.0)   # violet: the camera's sphere
LOOK_COLOR = (0.2, 0.9, 0.3)   # green: where it looks
EASES = {"inout": ("SINE", "EASE_IN_OUT"), "linear": ("LINEAR", "AUTO"),
         "in": ("QUAD", "EASE_IN"), "out": ("QUAD", "EASE_OUT")}


def _is_point(p):
    return not isinstance(p, bpy.types.Object) and not hasattr(p, "head") and not (
        isinstance(p, tuple) and len(p) == 2 and not isinstance(p[0], (int, float)))


def _ease(owner, path, frame, ease, index=-1):
    interp, easing = EASES[ease]
    for fc in core.fcurves(owner):
        if fc.data_path == path and (index < 0 or fc.array_index == index):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation, kp.easing = interp, easing


class Track:
    """An empty whose position moves between points and followed objects.

    Points are keyed on its location; each followed object is a Copy Location constraint
    whose influence is keyed. Only the current target is ever at full influence."""

    def __init__(self, s, name, start):
        self.s = s
        self.ob = s.empty(name)
        self.cons = {}
        self.cur = None
        self._goto(s.f0, start)

    def _target(self, p):
        """An object (or Rig head, or (object, offset)) -> the empty to copy."""
        off = Vector((0, 0, 0))
        if isinstance(p, tuple):
            p, off = p[0], Vector(p[1])
        if not isinstance(p, bpy.types.Object):  # a Rig: its head centre (the mesh origin is at the feet)
            p = getattr(p, "head_centre", None) or getattr(p, "head", p)
        if off.length == 0:
            return p
        key = (p.name, tuple(off))
        if key not in self.cons:
            e = self.s.empty(f"{self.ob.name}_pt")
            e.parent = None
            c = e.constraints.new("COPY_LOCATION")
            c.target, c.use_offset = p, True
            e.location = off
            self.cons[key] = e
        return self.cons[key]

    def _con(self, ob):
        c = self.ob.constraints.get(ob.name)
        if c is None:
            c = self.ob.constraints.new("COPY_LOCATION")
            c.name, c.target, c.influence = ob.name, ob, 0.0
            c.keyframe_insert("influence", frame=self.s.f0 - 1)
        return c

    def _key_loc(self, frame, p, ease="inout"):
        core.key(self.ob, "location", Vector(p), frame)
        _ease(self.ob, "location", frame, ease)

    def _key_inf(self, c, frame, v, ease="inout"):
        c.influence = v
        c.keyframe_insert("influence", frame=frame)
        path = f'constraints["{c.name}"].influence'
        _ease(self.ob, path, frame, ease)

    def _goto(self, frame, p):
        """Jump (constant) to p at frame."""
        self.move(frame, frame, p, "linear")

    def move(self, f0, f1, p, ease="inout"):
        """Travel from the current target to p between frames f0 and f1 (a cut if f0 >= f1)."""
        cut = f1 <= f0
        f1 = max(f1, f0)
        cur = self.cur
        inf = lambda c: f'constraints["{c.name}"].influence'
        if _is_point(p):
            p = Vector(p)
            if cur is None or isinstance(cur, Vector):  # point -> point: plain location keys
                if cur is not None and not cut:
                    self._key_loc(f0, cur, ease)
                self._key_loc(f1, p, ease)
                if cut:
                    self._const_before(self.ob, "location", f1)
            else:  # object -> point: the point waits under the object, then the object lets go
                self._key_loc(f0, p, ease)
                self._const_before(self.ob, "location", f0)
                c = self._con(cur)
                if not cut:
                    self._key_inf(c, f0, 1.0, ease)
                self._key_inf(c, f1, 0.0, ease)
                if cut:
                    self._const_before(self.ob, inf(c), f1)
            self.cur = p
            return
        ob = self._target(p)
        c = self._con(ob)
        if cur is None or isinstance(cur, Vector):  # point -> object: blend the object in
            if not cut:
                self._key_inf(c, f0, 0.0, ease)
            self._key_inf(c, f1, 1.0, ease)
            if cut:
                self._const_before(self.ob, inf(c), f1)
        elif cur is not ob:
            old = self._con(cur)
            names = [k.name for k in self.ob.constraints]
            if cut or names.index(c.name) > names.index(old.name):
                # the new one is on top: blend it in, then let the old one go
                if not cut:
                    self._key_inf(c, f0, 0.0, ease)
                self._key_inf(c, f1, 1.0, ease)
                if cut:
                    self._const_before(self.ob, inf(c), f1)
                if f1 > f0:
                    self._key_inf(old, f1 - 1, 1.0, "linear")
                self._key_inf(old, f1, 0.0, "linear")
                self._const_before(self.ob, inf(old), f1)
            else:  # the new one is underneath: switch it on, then fade the old one out
                self._key_inf(c, f0, 1.0, "linear")
                self._const_before(self.ob, inf(c), f0)
                self._key_inf(old, f0, 1.0, ease)
                self._key_inf(old, f1, 0.0, ease)
        self.cur = ob

    @staticmethod
    def _const_before(ob, path, frame):
        """Make the key just before frame hold (constant), so the change at frame is a jump."""
        for fc in core.fcurves(ob):
            if fc.data_path == path:
                before = [kp for kp in fc.keyframe_points if kp.co.x < frame - 0.5]
                if before:
                    before[-1].interpolation = "CONSTANT"


class Cam:
    def __init__(self, s, pos, look, mm=50, fstop=None, focus=None):
        self.s = s
        cam, tgt = core.camera(s, (0, 0, 0), (0, 0, 0), lens=mm)
        # replace core's Track To and look empty with the rig below
        for c in list(cam.constraints):
            cam.constraints.remove(c)
        bpy.data.objects.remove(tgt)
        self.pos = Track(s, f"{s.name}_rig", pos)
        self.look = Track(s, f"{s.name}_lookat", look)
        # spheres you can grab in the viewport to direct the shot: the big one moves the camera,
        # the small one is where it looks (both drawn through walls)
        for tr, size, col in ((self.pos, 1.5, RIG_COLOR), (self.look, 0.7, LOOK_COLOR)):
            tr.ob.empty_display_type, tr.ob.empty_display_size = "SPHERE", size
            tr.ob.show_in_front = True
            # the "Empty Color" add-on (colored_empties) reads these; harmless without it
            tr.ob["use_empty_color"], tr.ob["empty_color"] = True, col
        self.aim = s.empty(f"{s.name}_aim", parent=self.look.ob)   # look shake lives here
        self.aimer = s.empty(f"{s.name}_aimer", parent=self.pos.ob)
        c = self.aimer.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = self.aim, "TRACK_NEGATIVE_Z", "UP_Y"
        cam.parent = self.aimer
        cam.location = (0, 0, 0)
        cam.data.sensor_fit = "AUTO"
        cam.data.sensor_width = 36
        cam.data.show_passepartout, cam.data.passepartout_alpha = True, 1.0  # viewport: only the frame shows
        self.hand = s.name in HAND
        if self.hand:  # the user's own camera for this shot, untouched
            made = cam.data
            cam.data = HAND[s.name]
            bpy.data.cameras.remove(made)
        self.cam = cam
        self.dof(fstop, focus)
        numbers.bind(s, cam)

    # --- lens -----------------------------------------------------------------------

    def dof(self, fstop=None, focus=None):
        """Real f-stop (scaled to studs) and focus: an object, a Rig, a point or a distance.
        fstop=None: no depth of field. focus=None: focus on the look point."""
        if self.hand:  # the user's camera keeps its focus; its focus empty is still built so its
            if fstop is not None and focus is not None and not isinstance(focus, (int, float))                     and _is_point(focus):  # Lens Optics focus driver finds a fresh one to aim at
                self.s.empty(f"{self.s.name}_focus", tuple(focus))
            return self
        d = self.cam.data.dof
        d.use_dof = fstop is not None
        if fstop is None:
            return self
        d.aperture_fstop = fstop * STUD
        sc = bpy.context.scene
        sc.eevee.bokeh_max_size = max(sc.eevee.bokeh_max_size, 200)
        if focus is None:
            d.focus_object = self.aim
        elif isinstance(focus, (int, float)):
            d.focus_object, d.focus_distance = None, float(focus)
        elif _is_point(focus):
            d.focus_object = self.s.empty(f"{self.s.name}_focus", tuple(focus))
        else:
            d.focus_object = focus if isinstance(focus, bpy.types.Object) else (
                getattr(focus, "head_centre", None) or getattr(focus, "head", focus))
        return self

    def zoom(self, t0, t1, to_mm, ease="inout"):
        if self.hand:
            return self
        s, cd = self.s, self.cam.data
        core.key(cd, "lens", cd.lens, s.f(t0))
        _ease(cd, "lens", s.f(t0), ease)
        core.key(cd, "lens", to_mm, s.f(t1))
        return self

    def snap_zoom(self, t, to_mm, dur=0.12):
        """Crash zoom: punch the lens to to_mm over a few frames (quad out)."""
        return self.zoom(t, t + dur, to_mm, "out")

    # --- moves ----------------------------------------------------------------------

    def move(self, t0, t1, pos=None, look=None, ease="inout"):
        s = self.s
        if pos is not None:
            self.pos.move(s.f(t0), s.f(t1), pos, ease)
        if look is not None:
            self.look.move(s.f(t0), s.f(t1), look, ease)
        return self

    def cut(self, t, pos=None, look=None, mm=None):
        """Jump to a new framing at t, inside one shot."""
        s = self.s
        if pos is not None:
            self.pos.move(s.f(t), s.f(t), pos)
        if look is not None:
            self.look.move(s.f(t), s.f(t), look)
        if mm is not None and not self.hand:
            cd = self.cam.data
            core.key(cd, "lens", cd.lens, s.f(t) - 1, "CONSTANT")
            core.key(cd, "lens", mm, s.f(t), "CONSTANT")
        return self

    def roll(self, deg, to_deg=None, t0=0.0, t1=None, ease="inout"):
        """Dutch angle in degrees; with to_deg, roll from deg to to_deg between t0 and t1."""
        s = self.s
        core.key(self.cam, "rotation_euler", (0, 0, math.radians(deg)), s.f(t0))
        _ease(self.cam, "rotation_euler", s.f(t0), ease)
        if to_deg is not None:
            core.key(self.cam, "rotation_euler", (0, 0, math.radians(to_deg)), s.f(s.dur if t1 is None else t1))
        return self

    def declip(self, step=2, margin=1.5, reach=30.0):
        """Keep the camera from showing the inside of a building it passes through or skims:
        after the episode is built, every `step` frames it looks along its line of sight and,
        while a town surface sits within `reach` studs of the lens, keys the near clip
        (clip_start) just past it; it drops back to 0.1 once the camera is clear. Buildings
        further off are left alone, so the frame never opens onto an empty void."""
        self.s.after.append(lambda: _declip(self, step, margin, reach))
        return self

    def shake(self, amount, t0=0.0, t1=None):
        """Handheld wobble in studs (0.1-0.3 reads as handheld): noise on the camera's
        position and, at half strength, on where it looks."""
        s = self.s
        t1 = s.dur if t1 is None else t1
        for ob, amp, seed in ((self.cam, amount, 0.0), (self.aim, amount * 0.5, 37.0)):
            for i in range(3):
                ob.keyframe_insert("location", index=i, frame=s.f0)
            for fc in core.fcurves(ob):
                if fc.data_path != "location":
                    continue
                m = fc.modifiers.new("NOISE")
                m.scale = s.fps / 1.7
                m.strength = amp * 2
                m.phase = seed + fc.array_index * 11.3 + zlib.crc32(s.name.encode()) % 97
                m.use_restricted_range = True
                m.frame_start, m.frame_end = s.f(t0), s.f(t1)
                m.blend_in = m.blend_out = 3
        return self


GROUNDS = ("Ground.", "Backdrop.")  # never clipped: cutting the ground would open a void under the frame


def _declip(c, step, margin, reach):
    """See Cam.declip. Runs once the whole episode exists (build.py calls the shot's `after`)."""
    s, sc, cd = c.s, bpy.context.scene, c.cam.data
    own = {o.name for o in s.coll.all_objects}  # the cast, tags and props never count
    near = 0.1
    frames = list(range(s.f0, s.f1 + 1, step))
    if frames[-1] != s.f1:
        frames.append(s.f1)
    needed = []
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cam = c.cam.matrix_world.translation.copy()
        aim = c.aim.matrix_world.translation.copy()
        clip = near
        span = (cam - aim).length
        rot = c.cam.matrix_world.to_3x3()
        corners = cd.view_frame(scene=sc)  # camera-space frame corners: tr, br, bl, tl
        tr, bl = corners[0], corners[2]
        for fx in (0.1, 0.5, 0.9):  # a grid of rays through the frame, not just its centre
            for fy in (0.05, 0.25, 0.5, 0.75, 0.95):
                p = Vector((bl.x + (tr.x - bl.x) * fx, bl.y + (tr.y - bl.y) * fy, bl.z))
                d = (rot @ p).normalized()
                o, travelled = cam.copy(), 0.0
                while travelled < min(reach, span - 3.0):  # out from the lens: every surface within reach
                    hit, loc, _n, _i, ob, _m = sc.ray_cast(dg, o, d, distance=min(reach, span - 3.0) - travelled)
                    if not hit:
                        break
                    dc = (loc - cam).length
                    if ob is not None and ob.name not in own and not ob.name.startswith(GROUNDS):
                        clip = max(clip, dc + margin)  # past this wall (the next loop finds its far side)
                    o, travelled = loc + d * 0.05, dc + 0.05
        needed.append((f, min(clip, (cam - aim).length - 2.0)))
    for f, v in needed:
        core.key(cd, "clip_start", max(near, v), f, "LINEAR")
    cleared = sum(1 for _, v in needed if v > near)
    print(f"  {s.name}: declip keyed {len(needed)} frames, {cleared} clipped past a building")


def static(s, pos, look, mm=50, fstop=None, focus=None):
    return Cam(s, pos, look, mm, fstop, focus)


def push(s, pos, to_pos, look, mm=50, t0=0.0, t1=None, ease="inout", fstop=None, focus=None):
    """Dolly from pos to to_pos (push in, or pull out) while looking at look."""
    return Cam(s, pos, look, mm, fstop, focus).move(t0, s.dur if t1 is None else t1, pos=to_pos, ease=ease)


def pan(s, pos, look, to_look, mm=50, t0=0.0, t1=None, ease="inout", fstop=None, focus=None):
    """Turn from look to to_look on a fixed tripod (to_look may be a walker)."""
    return Cam(s, pos, look, mm, fstop, focus).move(t0, s.dur if t1 is None else t1, look=to_look, ease=ease)


def crane(s, pos, to_pos, look, to_look=None, mm=50, t0=0.0, t1=None, ease="inout", fstop=None, focus=None):
    """Move position and look together (crane up/down, tracking)."""
    return Cam(s, pos, look, mm, fstop, focus).move(t0, s.dur if t1 is None else t1, to_pos, to_look, ease)


def orbit(s, center, r, h, a0, a1, mm=50, t0=0.0, t1=None, ease="inout", look=None, fstop=None, focus=None):
    """Circle around center at radius r and height h (negative = low angle), from angle a0 to
    a1 degrees: 0 = +X, counter-clockwise seen from above. A Roblox orbit angle a is -a here.
    center may be a moving object."""
    t1 = s.dur if t1 is None else t1
    c = Cam(s, (r, 0, h), look if look is not None else center, mm, fstop, focus)
    pivot = Track(s, f"{s.name}_orbit", center)
    arm = s.empty(f"{s.name}_arm", parent=pivot.ob)
    core.key(arm, "rotation_euler", (0, 0, math.radians(a0)), s.f(t0))
    _ease(arm, "rotation_euler", s.f(t0), ease)
    core.key(arm, "rotation_euler", (0, 0, math.radians(a1)), s.f(t1))
    c.pos.ob.parent = arm   # its (r, 0, h) key is now relative to the turning arm
    return c
