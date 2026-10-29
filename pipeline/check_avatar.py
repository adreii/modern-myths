"""Check Roblox Studio avatars in Blender before using them in an episode.

One exported avatar (.obj): imports it as a posable R6/R15 rig (lib/imported.py), raises its
right arm and renders a still from the front, so you can see whether `turn` and `stud` in
cast.yaml are right.

    blender -b --python pipeline/check_avatar.py -- assets/roblox/hero.obj [--turn 180]

Avatars from avatars.json painted on one shared body (see roblox/Tools/DumpAvatars.luau):

    blender -b --python pipeline/check_avatar.py -- Hero --body assets/roblox/body_r15.obj --face smile_adult
    blender -b --python pipeline/check_avatar.py -- --all --body assets/roblox/body_r15.obj   # line-up

Runs in Blender's own Python too (no yaml or venv needed).
"""
import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bpy  # noqa: E402

from lib import core, imported  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("who", nargs="?", help="an .obj file, or an avatar name from avatars.json")
ap.add_argument("--all", action="store_true", help="every avatar in avatars.json, side by side")
ap.add_argument("--body", help="the shared exported body (.obj) avatars are painted on")
ap.add_argument("--avatars", help="avatars.json (default assets/roblox/avatars.json)")
ap.add_argument("--face", help="face from assets/faces/, e.g. smile or worried_old")
ap.add_argument("--turn", type=float, default=0)
ap.add_argument("--out", default=None)
ap.add_argument("--engine", default="BLENDER_EEVEE")
a = ap.parse_args(argv)

core.new_scene(fps=12, res=(1080, 1920), scale=40, engine=a.engine, samples=16, style="brick")
imported.CAST.update(turn=a.turn, body=a.body)
if a.avatars:
    imported.CAST["avatars"] = a.avatars
if a.all:
    import json
    names = list(json.loads((ROOT / imported.CAST["avatars"]).read_text(encoding="utf-8")))
else:
    names = [a.who]
imported.CAST["characters"] = {f"c{i}": n for i, n in enumerate(names)}
if a.face:
    imported.CAST["faces"] = {f"c{i}": a.face for i in range(len(names))}

s = core.Shot("check", 0, 0.0, 1.0, 12, [])
gap = 1.0
for i in range(len(names)):
    x = (i - (len(names) - 1) / 2) * gap
    rig = imported.roblox_avatar(s, f"c{i}", (x, 0, 0), h=1.0)
    if len(names) == 1:
        rig.arm_r.rotation_euler.x = math.radians(-150)  # wave: the raised arm shows screen-right
        print("CHECK parts:", {k: getattr(rig, k).name for k in ("head", "body", "arm_l", "arm_r")})

wide = len(names) > 1
if wide:
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1920 * 2, 1080
    bpy.context.scene.render.resolution_percentage = 50
dist = max(3.2, (len(names) * gap + 0.6) / 2 / 0.36) if wide else 3.2  # 50 mm: half-width ~0.36 x distance
k = dist / 3.2  # keep the light the same strength at any distance
core.camera(s, (0, -dist, 0.6), (0, 0, 0.5), lens=50)
core.light(s, "AREA", (1.5 * k, -2.5 * k, 2.5 * k), 300 * k * k, size=3.0 * k, look=(0, 0, 0.5))

stem = "lineup" if a.all else Path(a.who).stem.lower()
out = Path(a.out or ROOT / "assets" / "roblox" / f"{stem}_check.png").resolve()
bpy.context.scene.camera = bpy.context.scene.timeline_markers["check"].camera
bpy.context.scene.frame_set(s.f0)
bpy.context.scene.render.filepath = str(out)
bpy.ops.render.render(write_still=True)
print("CHECK still:", out)
