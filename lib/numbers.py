"""The floating number tag (port of roblox/StoryKit/NumberBillboard.luau).

    tag = numbers.tag(s, hero, 212)          # hero: a Rig (rides its head) or any object
    tag.count_to(1.0, 10000, dur=1.5)        # ticks up, quad-out
    tag.pulse(2.5)
    tag.dim(3.0, 0.6)                        # 0 = full glow, 1 = gone

Yellow bold text with a dark outline and a soft glow layer behind it, emission only so it
ignores scene light. It rides 3.2 studs above the head, bobs ±0.15 at 1.6 rad/s and always
lies in the camera's view plane, like a BillboardGui.

Every displayed value is its own pre-built group of text objects, switched on and off with
constant scale keys: no frame handlers, so background renders match the viewport.
"""
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

from . import core

COLOR = (1.0, 210 / 255, 74 / 255)          # #FFD24A
OUTLINE = (20 / 255, 20 / 255, 28 / 255)
FONT_PATH = r"C:\Windows\Fonts\ariblk.ttf"
HEIGHT = 3.2                                # studs above the head centre
BOB, BOB_SPEED = 0.15, 1.6                  # studs, rad/s
EMIT = 1.6                                  # emission strength: offsets the brick look's -0.9 exposure
LINE_W, GLOW_W = 0.02, 0.04              # outline and glow widths, as a fraction of the tag width
GLOW_ALPHA = 0.3                            # glow layer opacity

_PENDING = {}                               # shot name -> tags waiting for a camera
_COUNT = {}


def fmt(n):
    """10000 -> "10,000"."""
    return f"{int(math.floor(n + 0.5)):,}"


def _font():
    f = bpy.data.fonts.get("StoryKit_Number")
    if f is None:
        f = bpy.data.fonts.load(FONT_PATH if os.path.exists(FONT_PATH) else "<builtin>", check_existing=True)
        f.name = "StoryKit_Number"
    return f


def _emit_mat(name, color, strength):
    """Emission mixed with transparent; the mix factor ("alpha") is what dim/fade key."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.name = "alpha"
    mix.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*color, 1)
    return m


def _shot_camera(s):
    for m in bpy.context.scene.timeline_markers:
        if m.name == s.name and m.camera:
            return m.camera
    return None


def bind(s, cam=None):
    """Point every tag of shot s that is still waiting at its camera (cam.py calls this)."""
    cam = cam or _shot_camera(s)
    if cam:
        for t in _PENDING.pop(s.name, []):
            t.face(cam)


def tag(s, target, value, size=6, cam=None, height=HEIGHT, color=COLOR, bob=True):
    return Tag(s, target, value, size, cam, height, color, bob)


class Tag:
    def __init__(self, s, target, value, size=6, cam=None, height=HEIGHT, color=COLOR, bob=True):
        self.s, self.size, self.value = s, size, value
        self.groups = {}       # displayed value -> group empty
        self.shown = None      # value currently shown at the latest keyed time
        self.level = 1.0       # current opacity (1 - dim)
        _COUNT[s.name] = _COUNT.get(s.name, 0) + 1
        self.name = n = f"{s.name}_num{_COUNT[s.name]}"

        # root: follows the anchor in world space, faces the camera; its scale is show/hide
        self.root = s.empty(n)
        self.root.parent = None
        anchor = self._anchor(target)
        c = self.root.constraints.new("COPY_LOCATION")
        c.target, c.use_offset = anchor, True
        self.root.location = (0, 0, height)
        if bob:
            self.root.keyframe_insert("location", index=2, frame=s.f0)
            fc = next(f for f in core.fcurves(self.root) if f.data_path == "location" and f.array_index == 2)
            g = fc.modifiers.new("FNGENERATOR")
            g.function_type, g.use_additive = "SIN", True
            g.amplitude = BOB
            g.phase_multiplier = BOB_SPEED / s.fps
            g.phase_offset = random.Random(n).uniform(0, 2 * math.pi)
        self.rot = self.root.constraints.new("COPY_ROTATION")
        # pop: pulse scale lives here, below the show/hide scale on root
        self.pop = s.empty(n + "_pop", parent=self.root)

        self.mats = {
            "front": _emit_mat(n + "_front", color, EMIT),
            "outline": _emit_mat(n + "_outline", OUTLINE, 1.0),
            "glow": _emit_mat(n + "_glow", color, EMIT),
        }
        self.mats["glow"].node_tree.nodes["alpha"].inputs[0].default_value = GLOW_ALPHA
        # the soft glow is blended (no dither grain); number and outline stay dithered so
        # they write depth and depth of field treats them right
        self.mats["glow"].surface_render_method = "BLENDED"

        self.face(cam or _shot_camera(s))
        self._switch(s.f0, value)

    # --- setup ---------------------------------------------------------------------

    def _anchor(self, target):
        """An empty at the head centre (Rig) or the object's origin, following it."""
        s = self.s
        head = getattr(target, "head", None)
        if head is None:
            return target
        bpy.context.view_layer.update()
        corners = [head.matrix_world @ Vector(c) for c in head.bound_box]
        centre = sum(corners, Vector()) / 8
        a = s.empty(self.name + "_anchor", parent=getattr(target, "neck", head))
        a.matrix_world = Matrix.Translation(centre)
        return a

    def face(self, cam):
        """Lie in this camera's view plane (copy its world rotation)."""
        if cam is None:
            _PENDING.setdefault(self.s.name, []).append(self)
        else:
            self.rot.target = cam

    def _text(self, body, mat, offset, z, parent):
        cu = bpy.data.curves.new(self.name + "_txt", "FONT")
        cu.body = body
        cu.font = _font()
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.offset = offset
        cu.materials.append(mat)
        ob = self.s.adopt(bpy.data.objects.new(cu.name, cu), parent, (0, 0, z))
        return ob

    def _group(self, value):
        """Build (once) the outline + glow + front texts for one displayed value."""
        if value in self.groups:
            return self.groups[value]
        body = fmt(value)
        g = self.s.empty(f"{self.name}_{body}", parent=self.pop)
        front = self._text(body, self.mats["front"], 0.0, 0.0, g)
        bpy.context.view_layer.update()
        w, h = front.dimensions.x, front.dimensions.y
        # TextScaled: fit inside a size x size/3 box
        k = min(self.size * 0.95 / max(w, 1e-4), self.size / 3 * 0.8 / max(h, 1e-4))
        g.scale = (k, k, k)
        self._text(body, self.mats["outline"], LINE_W * self.size / k, -0.01, g)
        self._text(body, self.mats["glow"], GLOW_W * self.size / k, -0.02, g)
        g.scale = (0, 0, 0)
        g.keyframe_insert("scale", frame=self.s.f0 - 1)
        g["k"] = k
        self.groups[value] = g
        return g

    def _key_scale(self, g, k, frame):
        g.scale = (k, k, k)
        g.keyframe_insert("scale", frame=frame)
        core.set_interp(g, "scale", "CONSTANT")

    def _switch(self, frame, value):
        if value == self.shown:
            return
        g = self._group(value)
        if self.shown is not None:
            self._key_scale(self.groups[self.shown], 0, frame)
        self._key_scale(g, g["k"], frame)
        self.shown = self.value = value

    # --- beats -----------------------------------------------------------------------

    def set(self, t, value):
        """Instant change of the number at time t."""
        self._switch(self.s.f(t), value)

    def count_to(self, t0, values_or_target, dur=1.5):
        """A number: tick from the current value to it, quad-out, one step per frame (12+).
        A list: show those values one after another, evenly spread over dur."""
        s = self.s
        if isinstance(values_or_target, (list, tuple)):
            vals = list(values_or_target)
            for i, v in enumerate(vals):
                self._switch(s.f(t0 + dur * i / max(len(vals) - 1, 1)), v)
            return
        a, b = self.value, values_or_target
        steps = max(12, round(dur * s.fps))
        for i in range(1, steps + 1):
            x = i / steps
            e = 1 - (1 - x) ** 2
            self._switch(s.f(t0 + dur * x), round(a + (b - a) * e))
        self._switch(s.f(t0 + dur), b)

    def pulse(self, t, scale=1.25):
        """Quick pop: up in 0.08 s, settle back with a small overshoot."""
        s = self.s
        for dt, k in ((0, 1.0), (0.08, scale), (0.22, 0.96), (0.33, 1.0)):
            core.key(self.pop, "scale", (k, k, k), s.f(t + dt))

    def _key_alpha(self, frame, level):
        for name, m in self.mats.items():
            a = m.node_tree.nodes["alpha"].inputs[0]
            a.default_value = level * (GLOW_ALPHA if name == "glow" else 1.0)
            a.keyframe_insert("default_value", frame=frame)
            for fc in core.fcurves(m.node_tree):
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - frame) < 0.5:
                        kp.interpolation, kp.easing = "SINE", "EASE_IN_OUT"

    def dim(self, t, amount, dur=0.6):
        """0 = full glow, 1 = invisible (the baker is sick)."""
        s = self.s
        self._key_alpha(s.f(t), self.level)
        self.level = 1 - max(0.0, min(1.0, amount))
        self._key_alpha(s.f(t + dur), self.level)

    def fade_in(self, t, dur=1.0):
        s = self.s
        self._key_alpha(s.f(t), 0.0)
        self._key_alpha(s.f(t + dur), self.level)

    def _vis(self, t, on):
        frame = self.s.f(t)
        if not any(f.data_path == "scale" for f in core.fcurves(self.root)):
            self._vis_key(frame - 1, not on)  # the opposite state until t
        self._vis_key(frame, on)

    def _vis_key(self, frame, on):
        self.root.scale = (1, 1, 1) if on else (0, 0, 0)
        self.root.keyframe_insert("scale", frame=frame)
        core.set_interp(self.root, "scale", "CONSTANT")

    def show(self, t):
        """Appear at t (hidden before, if nothing else was keyed)."""
        self._vis(t, True)

    def hide(self, t):
        self._vis(t, False)
