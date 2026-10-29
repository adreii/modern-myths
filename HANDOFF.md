# Handoff: Modern Myths

Paste this into a new Claude Code session opened in a clone of this repo on the 4090 PC.

## Project
A YouTube Shorts channel: absurdist "In this world…" stories, each built on one essay from
Roland Barthes' *Mythologies*, ending with a one-line ethical lesson. Vertical 1080×1920,
60–90s, text-to-speech narration, Roblox-like blocky visuals rendered in Blender.
Repo: https://github.com/adreii/modern-myths (branch `main`)

## State
- **ep01 "The Toys That Play Themselves"** (essay "Toys") is written, narrated and built.
  - `voice.wav` is 85.5s, with captions, music and timing generated.
  - There are 21 shots, about 1,026 frames at 12 fps.
- **Style:** `brick` (Roblox-like R6 avatars, saturated plastic). It's set in `script.yaml`; `style: toy` gives the older wooden peg dolls.
- **Roblox Studio importer** (`lib/imported.py` + `episodes/ep01_toys/cast.yaml`): R6 avatar or set `.obj` exports replace the procedural ones.
  - It was tested only with a stand-in file (`assets/roblox/test_r6.obj`), not a real Studio export yet.
  - If a real export faces the wrong way, set `turn: 180`. If the scale is off, adjust `stud:`.
- **Not rendered yet:** no frames in this repo (`build/` is gitignored). A CPU preview was started in a cloud session but doesn't carry over.

## How it works
`script.yaml` → `pipeline/tts.py` (Kokoro TTS: voice.wav, timing.json, captions.ass)
→ `pipeline/music.py` → `pipeline/build.py` (bpy builds one set per shot from `shots.py`
and `lib/`, renders frames) → `pipeline/assemble.py` (ffmpeg: MP4 with ducked music and burned-in captions).
In shots, `s.cue(line, "word")` times actions to spoken words.

## Setup on the PC
1. Install Python **3.11** (the `bpy==4.2.0` wheel is cp311), Git, and ffmpeg with libass.
2. Install the fonts Inter Black and DejaVu Serif, or edit `ASS_HEADER` in `pipeline/tts.py`.
3. Run:
   ```bash
   python -m venv .venv
   ```
   then activate it, then:
   ```bash
   pip install -r requirements.txt
   ```
4. Download the Kokoro models into `assets/voices/`. The commands are in the README.

## Next steps
1. **Render on the 4090:**
   ```bash
   python pipeline/build.py episodes/ep01_toys --render --scale 100 --samples 64 --gpu
   ```
   `--gpu` picks OptiX and has never been run on a real GPU. Try `--engine BLENDER_EEVEE_NEXT` for speed.
2. **Make the video:**
   ```bash
   python pipeline/assemble.py episodes/ep01_toys
   ```
   The output is `episodes/ep01_toys/build/ep01_toys.mp4`.
3. Review the story and timing, then swap in real Roblox Studio exports via `cast.yaml`.
4. **Then: a video organizer project.** Track titles, descriptions, thumbnails and per-platform upload checklists (YouTube, TikTok, Instagram and others). Extras agreed: a pipeline board, platform rule checks, a calendar, A/B title logs, analytics notes, an essay tracker, a rights and credits log, a repurposing checklist, and an idea inbox.

## Notes
- Barthes is still under copyright: paraphrase, credit him on the end card, and keep quotes short.
- Use only your own Roblox avatar and builds, or licensed assets. Keep Roblox names and logos out of titles and thumbnails.
- `bible/format.md` has the story formula, and `bible/episode-ideas.md` has 9 more episode ideas.
