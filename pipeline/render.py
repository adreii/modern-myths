"""Render an episode's .blend to frames, surviving Blender crashes, then make the mp4.

  .venv/Scripts/python pipeline/render.py episodes/ep01_number            # every shot, then the mp4
  .venv/Scripts/python pipeline/render.py episodes/ep01_number --only s16 # just these shots

It runs Blender in the background on build/episode.blend with render_episode.py (one shot at a
time, the file's own Output settings, frames already on disk skipped). If Blender crashes (the
Lens Optics OSL camera and keyed visibility both can), it clears the half-written frame and starts
Blender again, until every shot reports done. Then pipeline/assemble.py makes build/<ep>.mp4.
Save and close the .blend in Blender first, or it renders the last saved state.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
SCRIPT = ROOT / "pipeline" / "blender_tools" / "render_episode.py"


def clear_partial(frames):
    """A crash leaves the frame it was on as an empty placeholder: remove it so it renders again."""
    gone = [f for f in frames.glob("*") if f.is_file() and f.stat().st_size == 0]
    for f in gone:
        f.unlink()
    return len(gone)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--only", default="", help="comma-separated shots, e.g. s16,s17")
    p.add_argument("--tries", type=int, default=50)
    p.add_argument("--blender", default=BLENDER)
    a = p.parse_args()
    ep = (ROOT / a.episode).resolve()
    blend = ep / "build" / "episode.blend"
    frames = ep / "build" / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    only = [s for s in a.only.split(",") if s]
    # the in-Blender script, told which shots and not to assemble (done here, once)
    expr = f"ONLY = {only!r}; ASSEMBLE = False"
    code = SCRIPT.read_text(encoding="utf-8").replace("ONLY = []\nASSEMBLE = True", expr)
    tmp = ep / "build" / "_render_run.py"
    tmp.write_text(code, encoding="utf-8")
    for attempt in range(1, a.tries + 1):
        n = clear_partial(frames)
        if n:
            print(f"(cleared {n} half-written frame{'s' if n > 1 else ''})", flush=True)
        print(f"--- Blender run {attempt} ---", flush=True)
        t0 = time.time()
        proc = subprocess.Popen([a.blender, "-b", str(blend), "--python", str(tmp)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        done = False
        for line in proc.stdout:
            if line.startswith(("render ", "Fra:", "all shots rendered")) or "Saved:" in line:
                if "Saved:" in line or line.startswith(("render ", "all shots")):
                    print(line.rstrip(), flush=True)
            if line.startswith("all shots rendered"):
                done = True
        proc.wait()
        if done:
            break
        print(f"Blender stopped (exit {proc.returncode}) after {time.time() - t0:.0f}s; starting it again", flush=True)
    else:
        sys.exit(f"gave up after {a.tries} runs")
    tmp.unlink(missing_ok=True)
    clear_partial(frames)
    if not only:
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "assemble.py"), str(ep)], check=True)


if __name__ == "__main__":
    main()
