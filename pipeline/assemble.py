"""Frames + voice + music + captions -> final vertical MP4 (1080x1920, 24 or 30 fps).

Usage: python pipeline/assemble.py episodes/ep01_number [--fps 24] [--music 0.22]
"""
import argparse
import re
import subprocess
from pathlib import Path

IMAGES = (".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff")


def frame_pattern(folder):
    """The rendered sequence in build/frames, whatever its name: Blender's `0001.png`, or a
    prefix like `Ep_01_0001.jpg`. Returns (ffmpeg pattern, first frame number)."""
    seqs = {}
    for f in sorted(folder.iterdir()):
        m = re.fullmatch(r"(.*?)(\d+)(\.\w+)", f.name)
        if m and f.suffix.lower() in IMAGES:
            seqs.setdefault((m[1], len(m[2]), m[3]), []).append(int(m[2]))
    if not seqs:
        raise SystemExit(f"no rendered frames in {folder}")
    (prefix, digits, ext), nums = max(seqs.items(), key=lambda kv: len(kv[1]))
    print(f"frames: {prefix}{'#' * digits}{ext}, {len(nums)} images, {min(nums)}-{max(nums)}")
    return str(folder / f"{prefix}%0{digits}d{ext}"), min(nums)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--fps", type=int, default=24, help="fps the frames were rendered at")
    p.add_argument("--music", type=float, default=0.22, help="music volume under the voice")
    a = p.parse_args()
    ep = Path(a.episode).resolve()
    out = ep / "build" / f"{ep.name}.mp4"
    music = ep / "music.wav"
    pattern, first = frame_pattern(ep / "build" / "frames")
    inputs = ["-framerate", str(a.fps), "-start_number", str(first), "-i", pattern, "-i", str(ep / "voice.wav")]
    if music.exists():
        inputs += ["-i", str(music)]
        # duck the music whenever the narrator speaks
        audio = (f"[1:a]asplit=2[v1][v2];[2:a]volume={a.music}[m];"
                 "[m][v1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
                 "[v2][md]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    else:
        audio = "[1:a]anull[a]"
    out_fps = a.fps if a.fps >= 24 else 30  # 24 fps stays 24 (no judder); 12 fps doubles up
    video = (f"[0:v]scale=1080:1920:flags=lanczos,fps={out_fps},"
             "ass=captions.ass[v]")  # run from the episode folder: no Windows path escaping
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", f"{video};{audio}",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, cwd=ep)
    print(out)


if __name__ == "__main__":
    main()
