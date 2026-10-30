"""Keep the light you set by hand: read each shot's sun and world group from an edited .blend and
write what differs from its preset into the episode's looks.yaml (shots.py applies it on every
build, so a rebuild no longer throws your changes away). Extra lights in each shot's
<shot>_Lights collection are saved to the episode's lights.blend, which build.py loads back.

Usage (Blender 5.2), after saving your edits in Blender:
  blender -b episodes/ep01_number/build/episode.blend --factory-startup -P pipeline/grab_looks.py -- episodes/ep01_number
Options: --only s01,s04 (just those shots), --reset s01 (drop a shot's hand-made look)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / ".deps" / "blender"))

import bpy  # noqa: E402
import yaml  # noqa: E402

from lib.core import fcurves  # noqa: E402
from lib.lighting import read_look  # noqa: E402

HEADER = """# Hand-made light per shot, on top of the lighting presets. Written by pipeline/grab_looks.py from
# the .blend you edited (only values that differ from the preset); read by shots.py on every build.
# Per shot: sun (rotation in degrees, strength, color, angle) and world (the shot's WG_ group inputs).
"""


def differs(a, b):
    if isinstance(a, list):
        return any(abs(x - y) > 1e-3 for x, y in zip(a, b))
    return abs(a - b) > 1e-3


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--only", default="")
    p.add_argument("--reset", default="")
    a = p.parse_args(argv)
    ep = (ROOT / a.episode) if not Path(a.episode).is_absolute() else Path(a.episode)
    path = ep / "looks.yaml"
    looks = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    only = set(filter(None, a.only.split(",")))
    for name in filter(None, a.reset.split(",")):
        looks.pop(name, None)
        print(f"{name}: reset to its preset")
    nodes = bpy.data.worlds["EP01_World"].node_tree.nodes if "EP01_World" in bpy.data.worlds else []
    for sun in sorted((o for o in bpy.data.objects if o.name.endswith("_Sun") and "preset_look" in o),
                      key=lambda o: o.name):
        shot = sun.name[:-4]
        if only and shot not in only:
            continue
        wg = nodes.get(f"WG_{shot.upper()}") if nodes else None
        if wg is None:
            continue
        if any(fc.data_path == "rotation_euler" for fc in fcurves(sun)):  # a keyed blend (s11): edit it in shots.py
            print(f"{shot}: skipped, its light is animated")
            continue
        now = read_look(sun, wg)
        base = {"sun": json.loads(sun["preset_look"]), "world": json.loads(wg["preset_look"])}
        entry = {}
        for part in ("sun", "world"):
            changed = {k: v for k, v in now[part].items() if differs(v, base[part][k])}
            if changed:
                entry[part] = changed
        if entry:
            looks[shot] = entry
            print(f"{shot}: kept {', '.join(f'{p}.{k}' for p in entry for k in entry[p])}")
        elif shot in looks:
            looks.pop(shot)
            print(f"{shot}: back to its preset")
    path.write_text(HEADER + (yaml.safe_dump(looks, sort_keys=True) if looks else "{}\n"), encoding="utf-8")
    print("wrote", path)
    save_lights(ep)
    save_cameras(ep)
    save_moves(ep)


def save_moves(ep):
    """Camera sphere keys you changed by hand (position or timing) go to the episode's
    camera_moves.yaml, frames counted from the shot's start; builds put them back."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    from build import location_keys
    path = ep / "camera_moves.yaml"
    moves = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    for ob in bpy.data.objects:
        if "built_keys" not in ob:
            continue
        now = location_keys(ob, ob["shot_f0"])
        built = json.loads(ob["built_keys"])
        same = len(now) == len(built) and all(
            abs(a[0] - b[0]) < 0.5 and all(abs(x - y) < 1e-3 for x, y in zip(a[1:4], b[1:4])) for a, b in zip(now, built))
        if same:
            if moves.pop(ob.name, None) is not None:
                print(f"{ob.name}: back to the built move")
        else:
            moves[ob.name] = now
            print(f"{ob.name}: kept your move ({len(now)} keys)")
    path.write_text("# Camera sphere moves you made by hand (pipeline/grab_looks.py); frames from the shot's start.\n"
                    + (yaml.safe_dump(moves, sort_keys=True) if moves else "{}\n"), encoding="utf-8")


def save_cameras(ep):
    """Camera data the user set up by hand (anything Lens Optics owns, or marked keep_camera) goes
    to the episode's cameras.blend; build.py uses it for that shot instead of building one."""
    keep = []
    for cd in bpy.data.cameras:
        shot = cd.get("shot") or (cd.name.split("_cam")[0] if "_cam" in cd.name else None)
        if shot and (cd.get("_atelier_owned_v1") or cd.get("keep_camera")):
            cd["shot"] = shot
            keep.append(cd)
    path = ep / "cameras.blend"
    if not keep:
        print("no hand-made cameras")
        return
    bpy.data.libraries.write(str(path), set(keep), fake_user=True)
    print(f"saved {len(keep)} hand-made cameras to {path}:", ", ".join(sorted(c["shot"] for c in keep)))


def save_lights(ep):
    """Every object in a <shot>_Lights collection goes to the episode's lights.blend, tagged with
    its shot; build.py puts them back in the same shot's collection on every build."""
    obs = set()
    for coll in bpy.data.collections:
        if coll.name.endswith("_Lights") and "shot" in coll:
            for ob in coll.objects:
                ob["shot"] = coll["shot"]
                obs.add(ob)
    path = ep / "lights.blend"
    if not obs:
        if path.exists():
            path.unlink()
        print("no hand-made lights")
        return
    bpy.data.libraries.write(str(path), obs, fake_user=True)
    print(f"saved {len(obs)} hand-made lights to {path}:", ", ".join(sorted(f"{o['shot']}/{o.name}" for o in obs)))


if __name__ == "__main__":
    main()
