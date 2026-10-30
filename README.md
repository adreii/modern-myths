# Modern Myths

> **Current episodes are made in Blender 5.2** (see `HANDOFF.md` for commands and setup). EP01 lives in `episodes/ep01_number/`; `episodes/ep01_toys/` is the older pipeline test.

Absurdist animated Shorts built on Roland Barthes' *Mythologies*: one impossible
rule, one small story, one lesson. Everything is generated from text: a script
becomes narration, the narration timing drives a Blender scene built in Python,
and the frames are assembled into a captioned vertical video.

```
script.yaml ──tts.py──▶ voice.wav + timing.json + captions.ass
                           │
shots.py + lib/ ──build.py─▶ episode.blend ──render──▶ frames/*.png
                                                         │
music.py ──▶ music.wav ──────────────assemble.py────────▶ build/<episode>.mp4
```

## Layout

| Path | What it is |
|---|---|
| `bible/format.md` | The story formula, writing rules and visual style |
| `bible/episode-ideas.md` | Barthes essay → absurd-rule slate |
| `episodes/<ep>/script.yaml` | Narration lines, each tagged with a shot name |
| `episodes/<ep>/shots.py` | One Python function per shot: set, camera, animation |
| `episodes/<ep>/publish.md` | Title, description, hashtags, pinned comment |
| `lib/core.py` | Scene, materials, primitives, keyframe helpers, `Shot` context |
| `lib/toys.py` | Peg-doll characters, rooms and props (the toy-world kit) |
| `pipeline/` | `tts.py`, `music.py`, `build.py`, `assemble.py` |

## Setup (once)

You need Python **3.11** (the `bpy` wheel is built for 3.11) and ffmpeg built with libass.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd assets/voices
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Captions use the **Arial Black** and **Georgia** fonts (both ship with Windows). To use others, change the
font names in `ASS_HEADER` in `pipeline/tts.py`.

## Make an episode

```bash
./make.sh episodes/ep01_toys            # preview: 540x960, 8 samples (fast)
./make.sh episodes/ep01_toys final      # final: 1080x1920, 32 samples
```

Useful while iterating:

```bash
python pipeline/build.py episodes/ep01_toys --stills --scale 40 --samples 16      # one PNG per shot
python pipeline/build.py episodes/ep01_toys --stills --only build,creator         # just some shots
python pipeline/build.py episodes/ep01_toys --render --frames 650-769             # re-render a range
```

Frames that already exist are skipped. To re-render a shot, delete its frames first.
To tweak things by hand, open `episodes/<ep>/build/episode.blend` in Blender.
Each shot is a collection with its own camera, and the timeline markers switch cameras.
On a machine with a GPU, `--engine BLENDER_EEVEE_NEXT` is much faster than Cycles.

## Using Roblox Studio models

1. In Roblox Studio, load your avatar as an **R6** rig (Avatar tab → Rig Builder, or insert your character) and dress it.
2. Right-click the model in Explorer → **Export Selection** → save as `assets/roblox/<name>.obj`. Keep the `.mtl` and textures next to it.
3. List it in `episodes/<ep>/cast.yaml` under `characters:` (`kid`, `grandpa`, `soldier`, `baby`).
4. Build rooms or maps in Studio the same way and list them under `sets:` (`room` replaces every procedural room).
5. Render stills. If characters face away from the camera, set `turn: 180`. If sets come out the wrong size, adjust `stud:`.

Anything not listed falls back to the built-in procedural blocky avatars and rooms.

## New episode

1. Copy `episodes/ep01_toys` and rewrite `script.yaml` (see `bible/format.md`).
2. Run `pipeline/tts.py` and check the timing. Change the voice, speed or pauses until it sounds right.
3. Write a function in `shots.py` for each shot name. Use `s.cue(line, "word")` to land actions on words.
4. Render stills, fix the framing, then render the whole episode.
