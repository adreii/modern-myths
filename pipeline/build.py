"""Build an episode's Blender scene from timing.json + shots.py, then optionally render.

Usage (Blender 5.2; pyyaml goes in .deps/blender, see README):
  blender -b --factory-startup -P pipeline/build.py -- episodes/ep01_number              # build + save .blend
  blender -b --factory-startup -P pipeline/build.py -- episodes/ep01_number --stills     # + one preview PNG per shot
  blender -b --factory-startup -P pipeline/build.py -- episodes/ep01_number --render     # + every frame (for assemble.py)
Options: --scale 50 (resolution %), --samples 24, --fps 24, --engine BLENDER_EEVEE|CYCLES, --style brick, --gpu,
         --only s01,s05 (stills for some shots), --frames 100-200

A shots.py may define build_town(): it runs once before the shots, into collections every
shot shares (never excluded or hidden), and its result is set as the module's TOWN.
With STAGE_AT_ORIGIN = True every shot is staged at the origin, in the town's coordinates.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / ".deps" / "blender"))  # pyyaml for Blender's own Python

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
    return mod


def build(ep, a):
    timing = json.loads((ep / "timing.json").read_text(encoding="utf-8"))
    load_cast(ep / "cast.yaml")  # optional Roblox Studio exports
    mod = load_shots(ep)
    shots = mod.SHOTS
    style = a.style or yaml.safe_load((ep / "script.yaml").read_text(encoding="utf-8")).get("style", "toy")
    sc = new_scene(fps=a.fps, scale=a.scale, engine=a.engine, samples=a.samples, style=style)
    if hasattr(mod, "build_town"):
        mod.TOWN = mod.build_town()
    at_origin = getattr(mod, "STAGE_AT_ORIGIN", False)
    hand_lights = load_lights(ep)
    load_cameras(ep)
    built = []
    for i, g in enumerate(group_shots(timing)):
        s = Shot(g["name"], i, g["start"], g["end"], a.fps, g["lines"], at_origin=at_origin)
        shots[g["name"]](s)
        for ob in hand_lights.get(g["name"], []):
            s.lights.objects.link(ob)
        s.finish()
        built.append(s)
        print(f"  {i:02d} {g['name']:<10} {g['start']:6.2f}-{g['end']:6.2f}s  frames {s.f0}-{s.f1}")
    sc.frame_start, sc.frame_end = 1, round(timing["total"] * a.fps)
    for s in built:  # work that needs the finished episode (e.g. camera declip ray casts)
        if s.after:
            solo(built, s)
            for fn in s.after:
                fn()
    remap_hand_cameras()
    camera_moves(built, ep)
    add_key_lights_text()
    add_sound(sc, ep)
    layer = bpy.context.view_layer.layer_collection
    for s in built:  # save with every shot switched on (rendering solos them again itself)
        layer.children[s.coll.name].exclude = False
    out = ep / "build"
    out.mkdir(exist_ok=True)
    if a.gpu:
        use_gpu(sc)  # saved with the GPU on, for rendering from the file by hand
    # saved ready to render by hand (Render > Render Animation): full 1080x1920, PNG frames
    # into build/frames/0001.png..., which pipeline/assemble.py turns into the mp4
    r = sc.render
    r.resolution_percentage = 100
    r.filepath = "//frames/"
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_overwrite, r.use_placeholder = True, False
    r.use_lock_interface = True  # the viewport stays still while rendering (avoids a known crash)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "episode.blend"))
    r.resolution_percentage = a.scale  # this run's stills / test renders use the requested size
    return sc, built, out


def load_lights(ep):
    """Lights added by hand (saved by grab_looks.py into the episode's lights.blend), by shot."""
    path = ep / "lights.blend"
    if not path.exists():
        return {}
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = list(src.objects)
    out = {}
    for ob in dst.objects:
        if ob is None:
            continue
        ob.animation_data_clear()  # old visibility keys; finish() keys the shot's current frames
        out.setdefault(ob.get("shot", ""), []).append(ob)
    print(f"  hand-made lights: {sum(len(v) for v in out.values())} from {path.name}")
    return out


def load_cameras(ep):
    """Cameras set up by hand (saved by grab_looks.py into the episode's cameras.blend): their
    camera data replaces the built one for that shot, untouched (see lib/cam.py HAND)."""
    from lib import cam
    cam.HAND.clear()
    path = ep / "cameras.blend"
    if not path.exists():
        return
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.cameras = list(src.cameras)
    # objects that came along as references (Lens Optics' focus driver reads the camera and its
    # focus target): rename them out of the way so the fresh build keeps the real names, and
    # point the references at the fresh objects once every shot exists (remap_hand_cameras)
    for ob in set(bpy.data.objects) - before:
        ob["stale_of"] = ob.name
        ob.name = ob.name + "__stale"
    for cd in dst.cameras:
        if cd is None or not cd.get("shot"):
            continue
        ad = cd.animation_data
        if ad and ad.action:  # old hide/lens keys; the shot keys visibility itself (drivers stay)
            ad.action = None
        cd.name = f"{cd['shot']}_cam_hand"  # keeps the shot's camera object named <shot>_cam
        cam.HAND[cd["shot"]] = cd
    print(f"  hand-made cameras: {', '.join(sorted(cam.HAND))} from {path.name}")


def remap_hand_cameras():
    """Point the hand cameras' drivers, focus objects and Lens Optics focus target at the freshly
    built objects of the same names, then drop the stale copies."""
    from lib import cam

    keep = set()

    def fresh(idb, shot):
        """The rebuilt object of the same name; if the build has none (a focus empty only the
        user's camera used), the user's own object is kept and put back in its shot."""
        if not (isinstance(idb, bpy.types.Object) and "stale_of" in idb):
            return idb
        new = bpy.data.objects.get(idb["stale_of"])
        if new is not None:
            return new
        if idb not in keep:
            keep.add(idb)
            idb.name = idb["stale_of"]
            coll = next((c for c in bpy.data.collections if c.name.endswith(f"_{shot}") and c.name[:2].isdigit()), None)
            if coll is not None and idb.name not in coll.objects:
                coll.objects.link(idb)
            idb.parent = None  # its saved world position stands
        return idb
    for cd in cam.HAND.values():
        shot = cd["shot"]
        ad = cd.animation_data
        for fc in (ad.drivers if ad else []):
            for var in fc.driver.variables:
                for t in var.targets:
                    if t.id is not None:
                        t.id = fresh(t.id, shot)
        if cd.dof.focus_object is not None:
            cd.dof.focus_object = fresh(cd.dof.focus_object, shot)
        at = cd.get("atelier")
        if at is not None and at.get("focus_target") is not None:
            at["focus_target"] = fresh(at["focus_target"], shot)
    for o in keep:
        del o["stale_of"]
    stale = [o for o in bpy.data.objects if "stale_of" in o]
    for o in stale:
        bpy.data.objects.remove(o)
    if stale:
        print(f"  hand cameras re-pointed; kept {sorted(o.name for o in keep)}; {len(stale)} stale copies removed")


MOVERS = ("_rig", "_lookat")  # the camera spheres


def location_keys(ob, f0):
    """An object's location keys as [frame - f0, x, y, z, interpolation, easing]."""
    from lib.core import fcurves
    fcs = {fc.array_index: fc for fc in fcurves(ob) if fc.data_path == "location"}
    if len(fcs) < 3:
        return []
    out = []
    for i, kp in enumerate(fcs[0].keyframe_points):
        f = kp.co.x
        vals = [fcs[a].evaluate(f) for a in range(3)]
        out.append([round(f - f0, 3), *[round(v, 4) for v in vals], kp.interpolation, kp.easing])
    return out


def camera_moves(built, ep):
    """Record each camera sphere's built keys (so grab_looks.py can tell what you changed by
    hand), then put back the moves you made, saved in the episode's camera_moves.yaml."""
    import json
    path = ep / "camera_moves.yaml"
    moves = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    used = []
    for s in built:
        for suffix in MOVERS:
            ob = bpy.data.objects.get(f"{s.name}{suffix}")
            if ob is None:
                continue
            ob["shot_f0"], ob["shot_f1"] = s.f0, s.f1
            ob["built_keys"] = json.dumps(location_keys(ob, s.f0))
            keys = moves.get(ob.name)
            if not keys:
                continue
            from lib.core import fcurves
            for fc in fcurves(ob):
                if fc.data_path == "location":
                    fc.keyframe_points.clear()
            for rel, x, y, z, interp, easing in keys:
                f = min(s.f0 + rel, s.f1)
                ob.location = (x, y, z)
                ob.keyframe_insert("location", frame=f)
                for fc in fcurves(ob):
                    if fc.data_path == "location":
                        for kp in fc.keyframe_points:
                            if abs(kp.co.x - f) < 0.5:
                                kp.interpolation, kp.easing = interp, easing
            used.append(ob.name)
    if used:
        print(f"  hand-made camera moves: {', '.join(sorted(used))}")


KEY_LIGHTS = """# Run this (Text Editor > Run Script) after adding lights to a shot's <shot>_Lights collection:
# each one is keyed to show only during its shot. Then save, and run pipeline/grab_looks.py so a
# rebuild keeps them.
import bpy
for coll in bpy.data.collections:
    if "f0" not in coll or not coll.name.endswith("_Lights"):
        continue
    f0, f1 = coll["f0"], coll["f1"]
    for ob in coll.objects:
        ob["shot"] = coll["shot"]
        for prop in ("hide_render", "hide_viewport"):
            for frame, val in ((f0 - 1, True), (f0, False), (f1 + 1, True)):
                setattr(ob, prop, val)
                ob.keyframe_insert(prop, frame=frame)
    print(coll.name, len(coll.objects), "lights keyed to frames", f0, "-", f1)
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
"""


def add_sound(sc, ep):
    """The narration (and music, if made) as sound strips in the Video Sequencer, so the
    timeline plays with the voice in Blender. Renders still come from the 3D scene."""
    se = sc.sequence_editor or sc.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences  # (an empty collection is falsy)
    for name, ch, vol in (("voice.wav", 1, 1.0), ("music.wav", 2, 0.35)):
        f = ep / name
        if f.exists():
            st = strips.new_sound(name[:-4].title(), str(f), channel=ch, frame_start=1)
            st.volume = vol
    sc.render.use_sequencer = False  # (sound only: frames render from the 3D scene)
    sc.sync_mode = "AUDIO_SYNC"  # play in step with the voice, dropping frames if needed


def add_key_lights_text():
    t = bpy.data.texts.get("key_shot_lights.py") or bpy.data.texts.new("key_shot_lights.py")
    t.from_string(KEY_LIGHTS)
    # the in-Blender render: one shot at a time, resumable, then the mp4
    r = bpy.data.texts.get("render_episode.py") or bpy.data.texts.new("render_episode.py")
    r.from_string((ROOT / "pipeline" / "blender_tools" / "render_episode.py").read_text(encoding="utf-8"))


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
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--engine", default="", help="BLENDER_EEVEE | CYCLES (default: script.yaml `engine:`, else EEVEE)")
    p.add_argument("--gpu", action="store_true", help="render Cycles on the GPU (OptiX/CUDA/HIP/Metal)")
    p.add_argument("--final", action="store_true",
                   help="release quality: full 1080x1920, 64 samples, EEVEE ray tracing (not 4K)")
    p.add_argument("--style", default="", help="toy | brick (default: script.yaml `style:`)")
    a = p.parse_args(argv)
    ep = (ROOT / a.episode) if not Path(a.episode).is_absolute() else Path(a.episode)
    if not a.engine:
        a.engine = yaml.safe_load((ep / "script.yaml").read_text(encoding="utf-8")).get("engine", "BLENDER_EEVEE")
    if a.engine == "CYCLES":
        a.gpu = True  # OptiX on the 4090 (Lens Optics cameras need CPU or OptiX)

    if a.final:
        a.scale, a.samples = 100, max(a.samples, 64)
    sc, built, out = build(ep, a)
    if a.final and a.engine.startswith("BLENDER_EEVEE"):
        ee = sc.eevee
        for prop, val in (("use_raytracing", True), ("use_shadows", True), ("use_gtao", True)):
            if hasattr(ee, prop):
                setattr(ee, prop, val)
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
        if hasattr(sc.render.image_settings, "media_type"):  # Blender 5: pick image before format
            sc.render.image_settings.media_type = "IMAGE"
        sc.render.image_settings.file_format = "PNG"
        sc.render.use_overwrite = False  # resume-friendly: skips frames already on disk
        sc.render.use_placeholder = True
        sc.render.use_persistent_data = False  # it keeps the first shot's set and ignores solo()
        for s in built:  # one shot at a time, with only that shot's set loaded
            if (only and s.name not in only) or s.f1 < lo or s.f0 > hi:
                continue
            solo(built, s)
            sc.frame_start, sc.frame_end = max(s.f0, lo), min(s.f1, hi)
            # evaluate the shot's first frame: sets its camera from the marker and replaces the
            # hide values left over from building (the last one written is "hidden")
            sc.frame_set(sc.frame_start)
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
    if shot.cam:
        bpy.context.scene.camera = shot.cam


if __name__ == "__main__":
    main()
