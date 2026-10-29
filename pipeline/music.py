"""A gentle procedural music-box loop, so episodes have royalty-free music out of the box.

Usage: python pipeline/music.py episodes/ep01_toys   -> music.wav (length of voice.wav)
Swap in your own track by dropping a music.wav in the episode folder instead.
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
BPM = 96
# C major pentatonic, MIDI note numbers; None = rest
MELODY = [72, 76, 79, 76, 81, 79, 76, None, 74, 76, 72, 74, 67, None, 72, None,
          72, 76, 79, 84, 81, 79, 76, None, 74, 72, 74, 76, 72, None, None, None]
BASS = [48, 45, 41, 43]  # C  Am  F  G, one per 8 steps


def note(midi, dur, amp=0.25, decay=3.5):
    f = 440 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-decay * t) * np.minimum(t / 0.004, 1)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-6 * t) \
        + 0.15 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-12 * t)  # bell-ish partial
    return amp * env * tone


def main(ep):
    ep = Path(ep)
    total = json.loads((ep / "timing.json").read_text())["total"]
    step = 60 / BPM / 2  # eighth notes
    out = np.zeros(int((total + 3) * SR))
    i = 0
    while i * step < total:
        pos = int(i * step * SR)
        m = MELODY[i % len(MELODY)]
        if m is not None:
            n = note(m, 2.0)
            out[pos:pos + len(n)] += n[: len(out) - pos]
        if i % 8 == 0:
            b = note(BASS[(i // 8) % len(BASS)], 3.0, 0.18, 1.5)
            out[pos:pos + len(b)] += b[: len(out) - pos]
        i += 1
    out = out[: int(total * SR)]
    fade = int(2.0 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out /= np.abs(out).max() + 1e-9
    sf.write(ep / "music.wav", (out * 0.8).astype(np.float32), SR)
    print(f"music.wav {total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
