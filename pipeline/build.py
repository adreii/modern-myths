"""Build an episode's Blender scene from timing.json + shots.py, then optionally render.

Usage (run with the Python that has `bpy`, or `blender -b -P pipeline/build.py -- ...`):
  python pipeline/build.py episodes/ep01_toys              # build + save .blend
  python pipeline/build.py episodes/ep01_toys --stills     # + one preview PNG per shot
  python pipeline/build.py episodes/ep01_toys --render     # + every frame (for assemble.py)
Options: --scale 50 (resolution %), --samples 24, --fps 12, --engine CYCLES|BLENDER_EEVEE_NEXT, --style brick, --gpu,
         --only build,creator (stills for some shots), --frames 100-200
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bpy  # noqa: E402
import yaml  # noqa: E402

from lib.core import Shot, new_scene  # noqa: E402
from lib.imported import load_cast  # noqa: E402


def group_shots(timing):
    """Consecutive lines with the same shot name become one shot spanning to the next shot."""
    groups = []
    for ln in timing["lines"]:
        if groups and groups[-1]["name"] == ln["shot"]:
            groups[-1]["lines"].append(ln)
        else:
            groups.append({"name": ln["shot"], "lines": [ln]})
    for i, g in enumerate(groups):
        g["start"] = 0.0 if i == 0 else groups[i - 1]["end"]
        g["end"] = timing["total"] if i == len(groups) - 1 else g["lines"][-1]["next"]
    return groups


def load_shots(ep):
    spec = importlib.util.spec_from_file_location(f"{ep.name}_shots", ep / "shots.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SHOTS


def build(ep, a):
    timing = json.loads((ep / "timing.json").read_text())
    load_cast(ep / "cast.yaml")  # optional Roblox Studio exports
    shots = load_shots(ep)
    style = a.style or yaml.safe_load((ep / "script.yaml").read_text()).get("style", "toy")
    sc = new_scene(fps=a.fps, scale=a.scale, engine=a.engine, samples=a.samples, style=style)
    built = []
    for i, g in enumerate(group_shots(timing)):
        s = Shot(g["name"], i, g["start"], g["end"], a.fps, g["lines"])
        shots[g["name"]](s)
        s.finish()
        built.append(s)
        print(f"  {i:02d} {g['name']:<10} {g['start']:6.2f}-{g['end']:6.2f}s  frames {s.f0}-{s.f1}")
    sc.frame_start, sc.frame_end = 1, round(timing["total"] * a.fps)
    out = ep / "build"
    out.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "episode.blend"))
    return sc, built, out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--stills", action="store_true")
    p.add_argument("--render", action="store_true")
    p.add_argument("--only", default="")
    p.add_argument("--frames", default="")
    p.add_argument("--at", type=float, default=0.6, help="where in each shot to grab the still (0-1)")
    p.add_argument("--scale", type=int, default=100)
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--engine", default="CYCLES")
    p.add_argument("--gpu", action="store_true", help="render Cycles on the GPU (OptiX/CUDA/HIP/Metal)")
    p.add_argument("--style", default="", help="toy | brick (default: script.yaml `style:`)")
    a = p.parse_args(argv)
    ep = (ROOT / a.episode) if not Path(a.episode).is_absolute() else Path(a.episode)

    sc, built, out = build(ep, a)
    if a.gpu:
        use_gpu(sc)
    only = set(filter(None, a.only.split(",")))
    if a.stills:
        (out / "stills").mkdir(exist_ok=True)
        for i, s in enumerate(built):
            if only and s.name not in only:
                continue
            solo(built, s)
            sc.frame_set(round(s.f0 + (s.f1 - s.f0) * a.at))
            sc.render.filepath = str(out / "stills" / f"{i:02d}_{s.name}.png")
            bpy.ops.render.render(write_still=True)
            print("still", sc.render.filepath, flush=True)
    if a.render:
        lo, hi = map(int, a.frames.split("-")) if a.frames else (sc.frame_start, sc.frame_end)
        sc.render.filepath = str(out / "frames") + "/"
        sc.render.image_settings.file_format = "PNG"
        sc.render.use_overwrite = False  # resume-friendly: skips frames already on disk
        sc.render.use_placeholder = True
        for s in built:  # one shot at a time, with only that shot's set loaded
            if (only and s.name not in only) or s.f1 < lo or s.f0 > hi:
                continue
            solo(built, s)
            sc.frame_start, sc.frame_end = max(s.f0, lo), min(s.f1, hi)
            print(f"render {s.name} {sc.frame_start}-{sc.frame_end}", flush=True)
            bpy.ops.render.render(animation=True)


def use_gpu(sc):
    """Switch Cycles to the best available GPU backend (OptiX first for RTX cards)."""
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            sc.cycles.device = "GPU"
            print(f"GPU render: {backend} on {', '.join(d.name for d in gpus)}", flush=True)
            return
    print("No GPU found; rendering on CPU", flush=True)


def solo(built, shot):
    """Exclude every other shot's collection so Cycles only syncs this set."""
    layer = bpy.context.view_layer.layer_collection
    for s in built:
        layer.children[s.coll.name].exclude = s is not shot
    # Blender builds the render scene from the *current* frame, and each shot's objects are
    # hidden outside its range, so jump to the shot first or it renders empty.
    bpy.context.scene.frame_set(shot.f0)
    bpy.context.scene.camera = shot.cam


if __name__ == "__main__":
    main()
