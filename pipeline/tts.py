"""Narration: script.yaml -> voice.wav + timing.json (+ captions.ass).

Usage: python pipeline/tts.py episodes/ep01_toys
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

ROOT = Path(__file__).resolve().parent.parent
VOICES = ROOT / "assets" / "voices"
LEAD_IN = 0.25  # silence before the first line


def load_script(ep):
    return yaml.safe_load((ep / "script.yaml").read_text(encoding="utf-8"))


def synth(lines, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(str(VOICES / "kokoro-v1.0.onnx"), str(VOICES / "voices-v1.0.bin"))
    for line in lines:
        if line.get("say"):
            audio, sr = k.create(line["say"], voice=line.get("voice", voice), speed=speed, lang="en-us")
            yield trim(audio, sr), sr
        else:
            yield None, None


def trim(a, sr, thresh=0.01, keep=0.04):
    """Cut leading/trailing silence so our own pauses control the rhythm."""
    idx = np.where(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    pad = int(keep * sr)
    return a[max(idx[0] - pad, 0): idx[-1] + pad]


def main(ep):
    ep = Path(ep)
    s = load_script(ep)
    sr = 24000
    chunks = [np.zeros(int(LEAD_IN * sr), np.float32)]
    t = LEAD_IN
    timing = []
    for line, (audio, asr) in zip(s["lines"], synth(s["lines"], s["voice"], s.get("speed", 1.0))):
        if audio is not None:
            sr = asr
            dur = len(audio) / sr
            chunks.append(audio.astype(np.float32))
        else:
            dur = float(line.get("hold", 3.0))
            chunks.append(np.zeros(int(dur * sr), np.float32))
        pause = float(line.get("pause", s.get("pause", 0.3))) if audio is not None else 0.0
        chunks.append(np.zeros(int(pause * sr), np.float32))
        timing.append({"shot": line["shot"], "text": line.get("say", ""), "card": line.get("card"),
                       "start": round(t, 3), "end": round(t + dur, 3), "next": round(t + dur + pause, 3)})
        t += dur + pause
    voice = np.concatenate(chunks)
    sf.write(ep / "voice.wav", voice, sr)
    out = {"title": s["title"], "essay": s["essay"], "total": round(len(voice) / sr, 3), "lines": timing,
           "highlight": s.get("highlight", [])}
    (ep / "timing.json").write_text(json.dumps(out, indent=2))
    write_ass(ep / "captions.ass", out)
    print(f"voice.wav {out['total']:.1f}s, {len(timing)} lines")


# --- captions ---------------------------------------------------------------

def chunk_words(text, max_words=4):
    """Split into short caption chunks, breaking at punctuation when possible."""
    words, out, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,!?;:]\"?$", w):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [" ".join(c) for c in out]


def ts(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,88,&H00FFFFFF,&H000000FF,&H00201810,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,560,1
Style: Card,Georgia,74,&H00E8F4FA,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,0,1
Style: Credit,Georgia,40,&H0090A8B8,&H000000FF,&H00000000,&H00000000,0,1,0,0,100,100,0,0,1,0,0,2,90,90,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


YELLOW = r"{\c&H4AD2FF&}"  # #FFD24A, the number-tag yellow (ASS colours are BGR)


def highlight(text, phrases):
    """Colour every listed phrase (e.g. the numbers) yellow, whole words only."""
    if not phrases:
        return text
    alts = "|".join(re.escape(p.upper()) for p in sorted(phrases, key=len, reverse=True))  # longest wins
    return re.sub(rf"(?<![\w-])(?:{alts})(?![\w-])", lambda m: YELLOW + m.group(0) + r"{\c}", text)


def write_ass(path, timing):
    ev = []
    for ln in timing["lines"]:
        if ln["card"]:
            body = ln["card"].strip().replace("\n", "\\N")
            end = timing["total"]
            ev.append(f"Dialogue: 0,{ts(ln['start'])},{ts(end)},Card,,0,0,0,,{{\\fad(600,0)}}{body}")
            ev.append(f"Dialogue: 0,{ts(ln['start'] + 1.0)},{ts(end)},Credit,,0,0,0,,{{\\fad(600,0)}}{timing['essay']}")
            continue
        if not ln["text"].strip():  # a silent hold (e.g. a card with no text): picture only
            continue
        chunks = chunk_words(ln["text"])
        weights = [len(c) + 3 for c in chunks]
        t, span = ln["start"], ln["end"] - ln["start"]
        for c, w in zip(chunks, weights):
            d = span * w / sum(weights)
            # small pop-in on each chunk
            ev.append(f"Dialogue: 0,{ts(t)},{ts(t + d)},Cap,,0,0,0,,{{\\fscx92\\fscy92\\t(0,80,\\fscx100\\fscy100)}}{highlight(c.upper(), timing.get('highlight', []))}")
            t += d
    Path(path).write_text(ASS_HEADER + "\n".join(ev) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
