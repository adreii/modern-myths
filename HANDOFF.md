# Handoff: Modern Myths (Everyday Myths)

Paste this into a new Claude Code session opened in a clone of this repo on the 4090 PC.
Repo: https://github.com/adreii/modern-myths (branch `main`)

## Project
A short-video channel (YouTube Shorts, Instagram Reels) for kids 8-13. Each episode follows
Roland Barthes' *Mythologies*: an absurd "in my town…" rule told with a straight face decodes the
hidden myth in an everyday thing, then ends on an ethical question. The episodes form a corpus to
derive ethics from. Vertical 1080×1920, 60-90 s, Roblox-style blocky look.

**Everything is made in Blender** (5.2, Python, headless). Roblox Studio is no longer used; the
Luau in `roblox/` stays only as the reference the Blender version was ported from.

## How an episode is made
```
script.yaml ──tts.py──▶ voice.wav + timing.json + captions.ass (numbers in yellow)
shots.py + lib/ ──build.py (Blender)──▶ build/episode.blend ──render──▶ build/frames/*.png
music.py ──▶ music.wav ───────────────assemble.py──────────▶ build/<episode>.mp4
```
- `episodes/ep01_number/`: EP01 "Everyone Has a Number" (script, cast, 18 shots + end card).
- `lib/oldtown.py` + `lib/town_layout.yaml`: the Old Town (plaster houses with clay-tile roofs,
  the bakery, Church Hill with its spire, the keep on Castle Ridge, Linden Park and its bandstand,
  the Wooden Quarter by the river, ~100 placed trees). The layout is data: move a house or a tree
  in the YAML. Built once per episode; every shot films in it. 1 unit = 1 stud; `rbx(x, y, z)` maps
  the plan coordinates. Models dropped into `assets/ext/<folder>/` as .glb replace their stand-ins
  (loaf, linden, oak, cypress, fountain, gazebo; see `assets/ext/LICENSES.md`).
- `lib/backdrop.py`: terrain out to the horizon on every side (fine near town, coarser further
  out), the river, a Geometry Nodes forest (~3,300 trees), mountain ranges north (2) and south (2),
  and fog planes: see-through haze sheets across the valleys, seen only by the camera.
- Trees are game-style card trees: bark trunk and branches with alpha leaf cards. The leaf
  sprites come from `pipeline/make_leaf_cards.py` (Poly Haven shrub_03 leaves, CC0) in
  `assets/ext/generated/`; rerun it if that folder is missing.
- Windows: one `WindowGlass` material; each window has a random number and lights when it is
  below `LitFraction`, which the lighting keys per shot (dawn/day 0, dusk 0.4, night 0.65).
- Details (layout `details:`): flower pots, bicycles, hanging and wall signs, extra lamps; the
  fountain is a round two-bowl fountain with water.
- The build puts `voice.wav` and `music.wav` in the Video Sequencer, so the timeline plays with
  the narration (renders still come from the 3D scene). AgX, no look, is the colour default.
- `lib/town.py`: the old Studio-port town. Its helpers (`Town`, `rbx`, markers) are still used;
  the Hero's house and school interiors there are for later episodes.
- `lib/imported.py`: avatars. One exported R15 body (`assets/roblox/body_r15.obj`) painted per
  character from `assets/roblox/avatars.json`, with faces from `assets/faces/` (30 starter faces:
  10 expressions × kid / `_adult` / `_old`; `pipeline/make_faces.py` draws them).
- `lib/acting.py`: poses, walk, turn, knock, backflip, lie, hold/release props, expressions.
- `lib/numbers.py`: the floating number tags (count-up, pulse, dim, fade).
- `lib/lighting.py`: pre_dawn_dark, dawn, day, dusk, night (sun, sky, fog, grade, bloom). The world
  is `EP01_World`: one node group per shot (`WG_S04` …) in a labelled frame, left to right in shot
  order, picked by the scene's `ep_shot`. Tune one shot's sky in its own group.
- `lib/cam.py`: real lenses in mm, DOF, push/pan/crane/orbit/cut/snap zoom/shake/roll. Each camera
  has two sphere empties to grab in the viewport: `<shot>_rig` (big, the camera) and
  `<shot>_lookat` (small, where it looks). `.declip()` keys the near clip past buildings the
  camera skims (used on s18's crane).

## Your defaults (every build does these)
Features you asked for, now built into every `episode.blend`:
- **Camera spheres:** each shot camera has a violet sphere `<shot>_rig` (the camera, 1.5) and a
  green sphere `<shot>_lookat` (where it looks, 0.7), drawn through walls, coloured through the
  Empty Color add-on.
- **Passepartout 1.0** on every camera: camera view shows only the frame.
- **Camera moves end on the shot's last visible frame**, so the B point can be set there.
- **Shot 18's crane clips** buildings it passes through (near clip keyed), ground never clipped.
- **Your own work survives rebuilds** (via `grab_looks.py`, run before every rebuild): suns and
  skies (`looks.yaml`), extra lights in `<shot>_Lights` (`lights.blend`), Lens Optics / `keep_camera`
  cameras untouched (`cameras.blend`), camera sphere moves (`camera_moves.yaml`).
- **Each shot has its own sun** (`<shot>_Sun`) and its own sky group in `EP01_World`, laid out left
  to right and labelled by shot.
- **`<shot>_Lights` collections** with the `key_shot_lights.py` text to key new lights to their shot.
- **All shot collections switched on** when the file opens.
- **Colour:** AgX, no look, exposure -0.9. **Engine:** Cycles on OptiX (Lens Optics needs it).
- **Narration and music** in the Video Sequencer, synced to the timeline.
- **Render-ready:** 1080x1920 at 100%, PNG frames to `//frames/` (= `build/frames/0001.png` ...).
- **Face cards cast no shadow** (`pipeline/blender_tools/face_cards_no_shadow.py` for an older file).
- **No eye-oval geometry in the avatar heads**: the face plane draws the eyes (`_drop_eyes` in
  `lib/imported.py`; `pipeline/blender_tools/remove_eye_ovals.py` cleans an older file).
- **Window lights by time of day** (none at dawn/day, some at dusk); shot 18 turns lights on as it
  rises and the end card keeps them on.

## Rendering (crash-proof, recommended)
Save and close the .blend, then:
```bash
.venv/Scripts/python pipeline/render.py episodes/ep01_number
```
Blender renders in the background, one shot at a time with the file's Output settings; if it
crashes (the Lens Optics OSL camera and keyed visibility both can), it is started again and
continues from the last finished frame. Then the mp4 is made. `--only s16,s17` re-renders shots.

## Rendering by hand (in Blender)
Open `episodes/<ep>/build/episode.blend`, Text Editor > `render_episode.py` > Run Script. It renders
one shot at a time with only that shot's collection on (one long Render Animation can crash on the
keyed visibility), skips frames already on disk (rerun to continue), uses the file's Output
settings, then runs `pipeline/assemble.py` to make `build/<ep>.mp4` (voice, music, captions).
Progress: Window > Toggle System Console. `ONLY = ["s16"]` at the top re-renders single shots.
For a file without the text, open `pipeline/blender_tools/render_episode.py` in the Text Editor.

## Lighting a shot by hand
Each shot has its own sun, `<shot>_Sun`, in its collection in the Outliner (e.g. `00_s01` >
`s01_Sun`): rotate it to move the sun, and set strength and colour in its Object Data (light)
properties. The sky is that shot's group in the World node tree (Shader Editor > World >
`WG_S01` frame): ambient, horizon, zenith, HDRI strength, mix and rotation. Save the .blend, then
keep the changes with:
```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b episodes/ep01_number/build/episode.blend --factory-startup -P pipeline/grab_looks.py -- episodes/ep01_number
```
That writes what differs from the preset into `episodes/ep01_number/looks.yaml`, which every build
applies (`--reset s01` drops a shot's changes). Exposure and the colour grade are still shared.

Hand-made cameras: a shot camera you set up yourself (anything with the Lens Optics add-on, or any
camera data you give a custom property `keep_camera`) is saved by `grab_looks.py` into
`episodes/ep01_number/cameras.blend`, and builds use it as is: no lens, zoom or focus keys are
written on it (Lens Optics drives `lens` from its own `focal_mm`). The rig spheres still move it.
Currently: s01 and s18 (Lens Optics, anamorphic). Lens Optics needs Cycles on CPU or OptiX; the
episode builds with `engine: CYCLES` (script.yaml) and the GPU on.

Camera moves: every move ends on its shot's last visible frame, so the B point can be set there.
Moves you key on the camera spheres (`<shot>_rig`, `<shot>_lookat`) are saved by `grab_looks.py`
into `episodes/ep01_number/camera_moves.yaml` (frames from the shot's start) and put back on every
build. For a file built before 2026-10-30 afternoon, run `pipeline/blender_tools/fix_camera_end_keys.py`
in Blender's Text Editor once first.

Extra lights: each shot collection has a `<shot>_Lights` collection (e.g. `00_s01` > `s01_Lights`).
Put lights there, run the `key_shot_lights.py` text (Text Editor > Run Script) so each shows only
during its shot, save, then run `grab_looks.py`: it saves them to `episodes/ep01_number/lights.blend`,
and every build puts them back in their shot.
- `episodes/ep01_toys/`: the older "Toys" story, kept only as a pipeline test.

## Commands (from the repo root)
```bash
.venv/Scripts/python pipeline/tts.py episodes/ep01_number
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P pipeline/build.py -- episodes/ep01_number --stills --scale 40
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P pipeline/build.py -- episodes/ep01_number --render --final
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P pipeline/lookdev.py -- episodes/ep01_number --painterly
.venv/Scripts/python pipeline/music.py episodes/ep01_number
.venv/Scripts/python pipeline/assemble.py episodes/ep01_number
```
`lookdev.py` writes `lookdev/ep01_number_lookdev.blend` (one scene per look: `LD_PreDawn_Lane`,
`LD_Dawn_Doorstep`, `LD_Dawn_Square`, `LD_Day_Square`, `LD_Day_Park`, `LD_Dusk_Square`,
`LD_Dawn_BakerRoom`, `LD_Dawn_BakerDoor`) and a still of each in `lookdev/stills/`, with grey and
chrome balls in the corner; `--painterly` adds Kuwahara brush-stroke versions.
`--final` = 1080×1920, 64 samples, EEVEE ray tracing (not 4K). Rendering skips frames already on
disk, so a crashed render resumes; delete any 0-byte PNG first. Blender 5.2 has crashed now and
then (`EXCEPTION_ACCESS_VIOLATION`); rerunning continues.

## Setup on a new PC
1. Blender 5.2, Python 3.11, ffmpeg with libass, Git.
2. `py -3.11 -m venv .venv` then `.venv/Scripts/python -m pip install kokoro-onnx soundfile numpy pyyaml pillow`.
3. Kokoro models into `assets/voices/` (commands in `README.md`).
4. pyyaml for Blender's own Python:
   `"<Blender>/5.2/python/bin/python.exe" -m pip install --target .deps/blender pyyaml`.
5. Fonts: Arial Black and Georgia (Windows has both).

## State
- EP01 was rendered once at 1080×1920 in the old blocky town. The town is now the Old Town (plan:
  https://claude.ai/artifact/L3XrvNSMcmrkXModPAUmXs); shots 04, 05, 06, 10, 13, 16 are reworked and
  the end card has no text. Stills and look dev are rendered; the full video is not re-rendered yet.
- Sketchfab models (CC-BY) are not downloaded yet; stand-ins are used (`assets/ext/LICENSES.md`).
- Voice is Kokoro TTS (`am_michael`, 63.9 s). The user's own recording can replace `voice.wav`;
  then rerun the timing (shots follow `timing.json`).
- Avatars are plain body colours with faces; no clothes or accessories yet.

`TODO.md` has the ordered list with who does what, and what's blocked or unverified.

## Decisions still open
- Roblox Terms of Use for videos posted outside Roblox (the look is Roblox-style), not read at the source.
- YouTube "made for kids" (COPPA) setting, channel name and handle, posting cadence.
- Narrator (own voice vs TTS) and a licensed music source (`music.py` makes a placeholder).

## Notes
- The stories are the Everyday Myths ones (EP01 and the EP02-08 premises in `locations.md`), written
  with the `everyday-myths-episode` skill; the Blender handoff's "Toys" story is parked.
- Barthes is still under copyright: paraphrase, credit him on the end card, keep quotes short.
- Use only your own avatar and builds, or CC0 assets (Kenney, Quaternius, ambientCG, Poly Haven).
  Keep Roblox names and logos out of titles and thumbnails.
