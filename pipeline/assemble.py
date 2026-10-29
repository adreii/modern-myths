"""Frames + voice + music + captions -> final vertical MP4 (1080x1920, 30 fps).

Usage: python pipeline/assemble.py episodes/ep01_toys [--fps 12] [--music 0.22]
"""
import argparse
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--fps", type=int, default=12, help="fps the frames were rendered at")
    p.add_argument("--music", type=float, default=0.22, help="music volume under the voice")
    a = p.parse_args()
    ep = Path(a.episode)
    out = ep / "build" / f"{ep.name}.mp4"
    music = ep / "music.wav"
    inputs = ["-framerate", str(a.fps), "-i", str(ep / "build" / "frames" / "%04d.png"), "-i", str(ep / "voice.wav")]
    if music.exists():
        inputs += ["-i", str(music)]
        # duck the music whenever the narrator speaks
        audio = (f"[1:a]asplit=2[v1][v2];[2:a]volume={a.music}[m];"
                 "[m][v1]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
                 "[v2][md]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    else:
        audio = "[1:a]anull[a]"
    video = (f"[0:v]scale=1080:1920:flags=lanczos,fps=30,"
             f"ass={ep / 'captions.ass'}[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", f"{video};{audio}",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
