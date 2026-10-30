# Render the whole episode from inside Blender, one shot at a time (Text Editor > Run Script).
#
# Why one shot at a time: every shot's cast, camera, sun and lights switch on and off with
# keyframes, and Blender can crash when that happens in the middle of one long Render Animation.
# Here only the current shot's collection is switched on while it renders, so nothing changes
# visibility mid-render. The same way the pipeline renders in the background.
#
# - Uses the file's own output settings (Output Properties: path, format, resolution, samples).
# - Skips frames already on disk, so after a crash or a stop just run it again to continue.
# - Blender is busy until it finishes; watch progress in Window > Toggle System Console.
# - At the end it makes the mp4 (voice, music, captions) with pipeline/assemble.py.
#
# Settings: render only some shots, e.g. ONLY = ["s16", "s17"]; ASSEMBLE = False to skip the mp4.
ONLY = []
ASSEMBLE = True

import subprocess
from pathlib import Path

import bpy

sc = bpy.context.scene
layer = bpy.context.view_layer.layer_collection
shots = sorted(((c["f0"], c["f1"], c["shot"]) for c in bpy.data.collections
                if c.name.endswith("_Lights") and "f0" in c), key=lambda x: x[0])
shot_colls = {lc.name: lc for lc in layer.children if lc.name[:2].isdigit()}
was = {n: lc.exclude for n, lc in shot_colls.items()}
r = sc.render
keep = (sc.frame_start, sc.frame_end, r.use_overwrite, r.use_placeholder, r.use_lock_interface)
r.use_overwrite, r.use_placeholder, r.use_lock_interface = False, True, True
out_dir = Path(bpy.path.abspath(r.filepath)).parent
if out_dir.is_dir():  # a crash leaves its frame as an empty placeholder: render it again
    for f in out_dir.iterdir():
        if f.is_file() and f.stat().st_size == 0:
            f.unlink()
try:
    for f0, f1, shot in shots:
        if ONLY and shot not in ONLY:
            continue
        for name, lc in shot_colls.items():
            lc.exclude = not name.endswith(f"_{shot}")
        sc.frame_start, sc.frame_end = f0, f1
        sc.frame_set(f0)
        print(f"render {shot}: frames {f0}-{f1}", flush=True)
        bpy.ops.render.render(animation=True)
finally:
    for name, lc in shot_colls.items():
        lc.exclude = was[name]
    sc.frame_start, sc.frame_end, r.use_overwrite, r.use_placeholder, r.use_lock_interface = keep
    sc.frame_set(sc.frame_start)
print("all shots rendered", flush=True)

if ASSEMBLE and not ONLY:
    blend = Path(bpy.data.filepath)  # <repo>/episodes/<ep>/build/episode.blend
    ep, repo = blend.parents[1], blend.parents[3]
    py = repo / ".venv" / "Scripts" / "python.exe"
    if py.exists():
        print("assembling the mp4 ...", flush=True)
        subprocess.run([str(py), str(repo / "pipeline" / "assemble.py"), str(ep)], check=False)
    else:
        print(f"no {py}: run pipeline/assemble.py yourself", flush=True)
