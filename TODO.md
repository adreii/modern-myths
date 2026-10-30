# Everyday Myths: to-do list
2026-10-30 (updated, after the EP02 plan chat)

Order matters: each item unblocks the ones after it. Roblox Studio is dropped. Videos are now made in Blender 5.2 with the repo's Python pipeline (see `HANDOFF.md`). EP01 "Everyone Has a Number" is rebuilt: `lib/town.py` (interiors), `lib/oldtown.py` + `lib/town_layout.yaml` (the Old Town), `lib/backdrop.py` (terrain, forest, mountains), `lib/acting.py`, `lib/numbers.py`, `lib/lighting.py`, `lib/cam.py`, and `episodes/ep01_number/` (script with Kokoro TTS voice am_michael, now 64.4 s, cast with 11 avatars and faces, 18 shots plus the end card). Nothing from the Blender work is committed yet.

Built this chat (the approved Old Town plan, https://claude.ai/artifact/L3XrvNSMcmrkXModPAUmXs):
- End-card text removed (the card line in `script.yaml` has no text; `tts.py` skips silent holds); voice and timing regenerated.
- Poly Haven CC0 assets in `assets/ext/` (3 HDRIs, 4 textures, shrub_03, painted_wooden_bench); `assets/ext/LICENSES.md` lists them and the Sketchfab CC-BY picks still to download.
- `lib/town_layout.yaml` and `lib/oldtown.py`: procedural plaster houses, bakery, church with spire, keep/belfry, town hall, log houses, bandstand, fountain, stalls, lanterns, lamps, trees and a stand-in loaf. A `.glb` in `assets/ext/<folder>/` replaces a stand-in (loaf, linden, oak, cypress, fountain, gazebo). `shots.py` builds the Old Town.
- `lib/backdrop.py`: terrain (Church Hill, Castle Ridge, river), bridge, Geometry Nodes forest (about 2,300 trees), two mountain ranges.
- `lib/lighting.py`: `EP01_World` has one node group per shot (WG_S01..WG_CARD) in labelled frames, selected by `scene["ep_shot"]` through a driver; HDRI per look; fog retuned.
- `pipeline/lookdev.py`: `lookdev/ep01_number_lookdev.blend` with 8 LD_* scenes (plus `_Painterly` copies with Kuwahara), stills in `lookdev/stills`, review sheets `lookdev/shots_sheet.png` and `lookdev/lookdev_sheet.png`.
- Shots reworked: s04 85 mm close-up of the Baker, s05 26 mm wide of the empty lane, s06 push-in to a loaf, s10 park bandstand, s13 empty step, s16 insert at 65 mm. Stills rendered at 40%.
- `HANDOFF.md` and `CLAUDE.md` updated; `.gitignore` ignores `assets/ext/*/` and `lookdev/*.blend`.

Built in the lighting/camera chat:
- Camera rigs: `<shot>_rig` and `<shot>_lookat` empties display as spheres, always in front, for directing cameras in the viewport (`lib/cam.py`).
- Per-shot suns: each shot has an unkeyed `<shot>_Sun` in its collection (s11's day-to-dusk blend still keys its sun); world group inputs are no longer keyed for still shots. Compositor grade and exposure stay shared/keyed.
- Hand-made light persistence: `pipeline/grab_looks.py` reads an edited .blend and writes differences from the preset into `episodes/ep01_number/looks.yaml` (currently empty); `shots.py` applies it on every build; `--reset s01` drops a shot's changes. Tested with a simulated edit, then reset. `HANDOFF.md` has a "Lighting a shot by hand" section.
- s18: `Cam.declip()` keys camera clip_start past buildings within 30 studs of the lens (ground/terrain never clipped), back to 0.1 when clear; 22 of 79 sampled frames were clipped. Clip_end unchanged (9000). Verified on test frames; houses the crane passes through show cut cross-sections while clipped.

Built in the hand-edit chat (shot 01 lights and cameras):
- You hand-edited shot 01: sun (kept in `looks.yaml`), 5 area lights in `s01_Lights` (saved to `episodes/ep01_number/lights.blend`), and Lens Optics Lite (anamorphic) on the s01 and s18 cameras (saved to `episodes/ep01_number/cameras.blend`).
- `grab_looks.py` now saves lights and hand cameras; `build.py` loads them; hand cameras get no lens/zoom/DOF keys (`lib/cam.py` HAND). Verified on a scratch rebuild.
- The episode builds with Cycles + OptiX GPU (`engine: CYCLES` in `script.yaml`); Lens Optics needs Cycles CPU/OptiX. s18 `declip` clip_start still works through the Lens Optics camera in Cycles.
- Builds save with all shot collections on; camera spheres are violet (rig) / green (lookat) via the Empty Color add-on; camera passepartout is 1.0.
- Backups of your edited files: `episodes/ep01_number/build/episode_handedit_0938.blend` and `_0956.blend`.
- Rule: always run `grab_looks` before rebuilding; never overwrite your hand camera.

Built in the windows/terrain chat (code only; your open `episode.blend` was NOT rebuilt; checked on a scratch rebuild with Cycles stills):
- Window lights by time of day: `WindowGlass` material with per-window random `win_rand` and keyed `LitFraction` (pre-dawn/dawn/day 0, dusk 0.4, night 0.65); `windows_warm` removed from s18 and the card.
- Game-style card trees (alpha leaf cards) from `pipeline/make_leaf_cards.py` sprites (Poly Haven shrub_03 leaves) in `assets/ext/generated/`.
- Town details (layout `details:`): round two-bowl fountain with water, 30 flower pots, 6 bikes, 8 hanging signs (CAFÉ, BOOKS, TAILOR, FLOWERS, CHEESE, INN, SHOES, CLOCKS), 3 wall signs (TOWN HALL, POST, PHARMACY), 8 extra lamps.
- Terrain runs to the horizon (variable grid to ±7000): farmland hills south/east/west, southern woods (about 3,300 trees total), SouthHills + SouthRange mountains, 9 camera-only fog planes.
- Narration: the build adds `voice.wav` + `music.wav` as Video Sequencer sound strips (AUDIO_SYNC); you were given a snippet to add them to the open file now.
- Colour default is AgX with no look (your choice).
- Your 11:02 save (art direction to keep; capture with `grab_looks` when done): brighter suns s01-s03, s07, s08; s06 sun turned; skies s01, s05, s06, s07 changed; AgX; new lights (Area.005 in s01, Spot in s06); Lens Optics on s01-s08 and s18.

Built in the rebuild chat (your art direction is done; the real `episode.blend` is rebuilt):
- Backed up your file as `episodes/ep01_number/build/episode_handedit_1128.blend`. `grab_looks` captured suns/skies (s01, s02, s03, s05, s06, s07, s08), 7 lights (6 in s01, a spot in s06) and Lens Optics cameras s01-s08 and s18.
- Rebuilt `episode.blend` (Cycles, OptiX, AgX, all collections on, voice + music sound strips) with the window lights, card trees, details, fountain, terrain to the horizon, south ranges and fog planes. 19 Cycles stills at 30% in `build/stills`; sheet at `lookdev/shots_sheet_cycles.png`.
- Fixed: the hand cameras' Lens Optics focus drivers pointed at stale object copies loaded with `cameras.blend`. `build.py` now renames those copies and re-points drivers/focus to the fresh objects (`remap_hand_cameras`); `cam.dof` still builds the focus empty for hand cameras. Verified: s06 focus 4.87 (matches yours), camera names kept.

Built in the camera end-key chat (code only; your open `episode.blend` was NOT rebuilt):
- Fixed: camera end keys (the B point) landed one frame after a shot's last visible frame, i.e. on the next shot. `lib/core.py` `Shot.f()` now clamps to the shot's last frame, so every move ends on a visible frame. Verified on a scratch build (s06_rig keys 388 and 484 = f0 and f1).
- Hand camera moves persist: builds stamp each camera sphere (`<shot>_rig`, `<shot>_lookat`) with its built keys; `pipeline/grab_looks.py` saves changed keys to `episodes/ep01_number/camera_moves.yaml` (frames counted from shot start); `build.py` replays them. Round trip verified on a scratch copy (a lifted s06 B point survived grab + rebuild).
- `pipeline/blender_tools/fix_camera_end_keys.py`: run in Blender's Text Editor on your current `episode.blend` (built before the fix). It moves end keys onto each shot's last frame and stamps built keys so later moves are captured. Tested on a copy (27 keys moved, 19 shots).

Built in the camera-moves / doors chat (your camera moves are done; the real `episode.blend` is rebuilt):
- Backed up your file as `episodes/ep01_number/build/episode_handedit_1158.blend`. `grab_looks` captured camera moves (s05, s06, s14, s15), looks (adds s10, s12, s14), 9 lights (adds s10, s13) and 15 Lens Optics cameras (s01-s13, s15, s18; not s14).
- Rebuilt `episode.blend`; 19 Cycles stills, sheet `lookdev/shots_sheet_cycles.png`.
- s03 line is now "Mine was two hundred and twelve." (`script.yaml`; TTS regenerated, 64.4 s; captions highlight TWO/HUNDRED/TWELVE).
- s16: the hero hands the real loaf (Bread_1 model) to the Baker: closer staging, he holds it out, she takes it with her left hand (hold transfer), insert camera moved side-on over the pots. Frames confirm the loaf ends in her hand.
- Doors: plank-wood material (per-plank shade, gaps, grain, bump; 6 paint colours), cross rails, iron hinge straps, brass knob with rose, keyhole plate; church double door with rails and straps.
- End lights: `lighting.windows()` override; s18 windows come on one by one as the crane rises (0 to 0.3), the card holds 0.3. Verified.

Built in the EP02 plan chat (docs only; no code or Blender files changed, nothing committed):
- Wrote the EP02 "The Sneakers 👟" plan with the `everyday-myths-episode` skill: `ep02-plan.md` (pitch, myth decode, lesson choice, five beats, production phases 0-9, self-check with weak spots), `ep02-narration-script.md` (about 140 words, about 68 s; the shoes talk in speech bubbles, no shoe voices), `ep02-shot-list.md` (18 shots plus a 3 s end card, visual plan, 8 new builds, sound).
- Added `bible/production-checklist.md`: one checklist per episode (story, shot list, episode files, voice, build/look, render, publish), gathered from `bible/format.md`, the skill checklist, `HANDOFF.md` and this file. It notes that the 7 beats in `format.md` are superseded by the skill's 5.
- Corpus tracker: ep02 set to Scripted, with myth, surface, question and values.

Built in the render chat (full EP01 render done):
- Eye ovals removed from avatar heads in builds (`lib/imported.py` `_drop_eyes`); `pipeline/blender_tools/remove_eye_ovals.py` fixes old files. Face cards cast no shadow (`lib/imported.py`; `pipeline/blender_tools/face_cards_no_shadow.py` for old files). Your file was fixed and saved.
- Builds save render-ready (100%, `//frames/`, PNG, Lock Interface on) and include `render_episode.py` text (shot-by-shot, resumable, then assemble). `assemble.py` finds any frame naming in `build/frames` (e.g. `Ep_01_####.jpg`).
- Rendering in the Blender UI crashed twice (depsgraph visibility crash, then an OSL crash in the Lens Optics camera shader). New `pipeline/render.py` renders in the background shot by shot and restarts Blender from the stopped frame after a crash.
- Full EP01 render completed with it (1 crash at frame 835 in s11, recovered): `episodes/ep01_number/build/ep01_number.mp4`, 1080x1920, 24 fps, 64.4 s, Cycles at your 32 samples, JPEG frames.
- You handled the sky (pylon in the HDRI) yourself.

Render tip: rendering skips frames already on disk, so a crashed render resumes. To redo a shot, delete its frames, then run `--render --final --only s05,s16` (shot ids, comma-separated). Delete any 0-byte PNG first.

## Waiting on you (Old Town)

- [x] **You** Camera moves finished and captured (`camera_moves.yaml`); `episode.blend` rebuilt. **Claude** still runs `grab_looks.py` before any further rebuild.
- [x] **You** Sky: you fixed the HDRI pylon yourself.

- [ ] **You** Review the new Cycles stills (`build/stills`, `lookdev/shots_sheet_cycles.png`) and the look-dev sheets (`lookdev/shots_sheet.png`, `lookdev/lookdev_sheet.png`); approve or give per-shot notes before the 1080x1920 render.
- [ ] **You** Shot 01 lights and cameras are done. Decide whether to hand-edit other shots the same way (open `episode.blend`, edit, save; **Claude** runs `pipeline/grab_looks.py` first, then rebuilds).
- [x] **You** s01 and s18 zooms: decided no zoom. Your Lens Optics focal length stays fixed on both shots.
- [ ] **You** Pick painterly (Kuwahara) on or off.
- [ ] **You** Decide shot 11: move it to the park bandstand with shot 10, or keep it in the square.
- [ ] **You** Sign in to Sketchfab and download the CC-BY picks (Claude can't sign in): meerschaumdigital Loaf Of Bread + Bakery Pack, animau3d Medieval Houses 1-4, alexferrart3D Gothic Church, AspectStudio Market Stall, Sereib 4 Linden Trees, greg-l Oak, ElectroNick Cypress, ahmagh2e distant mountains, wolfgar74 fountain, Alexey.inc street lantern, smolaaa gazebo, donnichols log cabin. Save as `.glb` in `assets/ext/<folder>/` and check each page's licence.
- [ ] **You** Approve committing all of the Blender work (`lib/`, `episodes/ep01_number/`, `pipeline/`, docs, `assets/ext/LICENSES.md`). Rendered frames, `.venv`, `.deps`, `assets/ext/*/` and `lookdev/*.blend` are git-ignored.

## EP02 (The Sneakers)

- [ ] **You** Read `ep02-plan.md`, `ep02-narration-script.md` and `ep02-shot-list.md`; approve or give notes (story, tone, names Max/Pia/Theo; the money/price weak spot; optional line swap "too old to talk" -> "broken").
- [ ] **You** Decide the order: finish and post EP01 first (the list says to note EP01's first-day numbers before planning EP02), or build EP02 in parallel.
- [ ] **Claude** After approval: create `episodes/ep02_sneakers/` (`script.yaml`, `cast.yaml`, empty `looks.yaml` and `camera_moves.yaml`, `shots.py`) and run `tts.py`.
- [ ] **Claude** Generalise the EP01-only pipeline parts (`EP01_World` in `lib/lighting.py`, the EP01 look table in `shots.py`) so a second episode builds; check EP01 still builds the same.
- [ ] **Claude** EP02 builds: sneakers on avatar feet (extend the `lib/imported.py` accessories to feet; Hero blue, Max white-gold, Pia taped grey, giant gold 1.6x, shoebox variant; no real brands); speech bubble (extend the `lib/numbers.py` tag: text, tail, pop, stacking, mint price and warm handwritten styles); schoolyard with puddles next to the Old Town School; port the `lib/town.py` school hallway interior into the Old Town School shell; looks `indoor_fluorescent` and `overcast_wet`; Max and Pia avatars in `avatars.json` and `cast.yaml`; acting moves kneel, pick up, step out of shoes, clomp walk, slow-mo strut, carry books; props (books, wet sheets, marker, shoeboxes).
- [ ] **Claude** Shots s01-s18 plus the card, a stills review sheet, then your hand-edit pass (`grab_looks` before any rebuild), final render, assemble.

## Next (Claude, after your review)

- [ ] **Claude** Fix the known look issues: s11 crowd blocks the camera in the orbit; s13 and s16 read very dark; s16's loaf hand-off reads small and dark (brighten the light, enlarge or reframe the loaf); the HDRI pylon/lines in the sky (see Waiting on you); s18/card dawn haze is heavy and brown; BreadBag reads as a box.
- [ ] **Claude** Check mountain visibility (they sit behind roofs in many shots; far peaks were raised once).
- [ ] **Claude** Test the Sketchfab `.glb` import path (`ext_model`) once files exist; it is untested.
- [x] **Claude** Full 1080x1920 render with the Old Town done (`pipeline/render.py`, see the render chat above).
- [ ] **Claude** Apply your per-shot notes from the mp4 review, then re-render only the changed shots (`render.py`).
- [ ] **Claude** Check noise: the render used 32 samples and noise was not inspected; raise samples if grainy.

## Next session (do first)

- [ ] **You** Watch `episodes/ep01_number/build/ep01_number.mp4` (rendered, 64.4 s) and note what to change per shot: framing, timing, faces, voice choice.
- [ ] **You** Decide the narrator: keep Kokoro TTS (try other voices: am_puck, am_fenrir, af_heart) or record your own and replace `voice.wav`. Then **Claude** reruns timing and re-renders.

## This week

- [ ] **You** Look at the starter faces (`assets/faces/`) and say which to redraw, or draw your own; decide each character's default face and age (e.g. Baker _old?).
- [ ] **Claude** Replace the placeholder `music.py` music box with a licensed track once you pick one.
- [ ] **Claude** Accessory pieces (hair, apron, glasses, shades) for the Baker, Influencer and crowd, to show age and look (the importer already hangs accessories on the head or body).
- [x] **Claude** Write EP02 with the episode skill once the premise is approved. Draft is in `ep02-plan.md` (not yet approved, see EP02 below).
- [ ] **You** Approve or change the EP02-08 premises in `locations.md` (EP02 is now drafted; EP03-08 are still proposals), then Claude writes each episode with the `everyday-myths-episode` skill (EP02 is the skill's first real test; update its status in the corpus tracker). Also read the skill and say what to change in tone, humour level, target age (it says kids 8-13) or structure.
- [ ] **You** Download the chosen Kenney and Quaternius packs (CC0) if you want them as props, and keep the licence log (source URL, pack name and version, licence screenshot, author, date). `assets/ext/LICENSES.md` is the start; Sketchfab CC-BY credits go in the video description.

## Later

- [ ] **Claude** More town interiors and dressing, added to `lib/town.py` (or `lib/oldtown.py`) as episodes need them: shops (sneakers, café, corner shop, pizza, laundry), the Baker's bedroom inside her house (shot 14 still uses a separate bedroom set), apartment block "Maple Court", library, Town Hall main room, arena "Friday Night Rumble", park with playground and pond. Dressing: signs, parked cars, bins, fences, crowd spots, CC0 props.
- [ ] **Claude** Build the phone/screen overlay for the episodes that need it (not built).
- [ ] **Claude** Check the `day`, `dusk` and `night` lighting presets in `lib/lighting.py` and the lens key in `lib/cam.py` against the FOV table in `references/cinematography.md` in the `everyday-myths-episode` skill.
- [ ] **Claude** Better acting: elbow/knee joints for R15 if the acting needs them, and more reusable moves in `lib/acting.py`.
- [ ] **You** Post EP01 as a test (Reels and Shorts, emoji in the title), credit any CC0 and CC-BY assets in the description, keep Roblox names and logos out of the title and thumbnail, and note the first-day numbers before planning EP02.
- [ ] **Claude** Optional: verify the Narvaez figures (8-year-olds about 10%, 10-year-olds about 50% theme comprehension) against the original paper; they came from a secondary Notre Dame guide and the skill avoids quoting them.
- [ ] **Claude** Optional: a script chain for the whole episode (TTS, timing, build, render, captions, assemble) in one command once the steps are stable.

Obsolete since the move to Blender (not to be done): saving the Studio place, Studio 9:16 framing, OBS capture, recording with P, CapCut assembly, the BlenderNav plugin, the Studio MCP and `.mcp.json`, Town phase 2c-3 in Studio, Moon Animator, and the Stages 2/3 ShotRunner. The Luau in `roblox/` stays only as the reference the Blender version was ported from.

## Decisions to make

- [ ] **You** Read Roblox's Terms of Use and brand guidelines for monetized off-platform videos at the source (create.roblox.com / roblox.com/info/terms) and decide whether the plan is safe, since the look is Roblox-style. Do this before posting for money. The research subagent could not read the ToU page (access was blocked), so nothing is confirmed.
- [ ] **You** Decide the YouTube "made for kids" (COPPA) setting. The skill says the audience is kids 8-13. Made-for-kids disables comments, notifications and personalised ads; the FTC's amended COPPA Rule had an April 2026 compliance date. Check YouTube Help and the FTC COPPA page at the source.
- [ ] **You** Pick the channel name and handle (check Instagram and YouTube by hand; no accounts created yet), and decide the posting cadence and episode length (reference channel posts often with 2-3 min reels; EP01 is about 64 s).
- [ ] **You** Pick the audio: narrator for later episodes (your own voice vs Kokoro TTS) and a royalty-free music source for the lo-fi piano/music-box loop (about 85 BPM). Keep the licence for every track.
- [ ] **You** Identify the audio of the reference reel (craftee_films, "The Older You Get, The Faster You Move", https://www.instagram.com/p/De034jVg1-S/), which Instagram lists only as "Original audio" (the comments don't name the voice or music; two web searches found nothing). Music: play it and run Shazam or Google "Search a song", or tap "Original audio" while logged in. Voice: compare by ear against the ElevenLabs voice library (an unconfirmed guess), check their YouTube descriptions, or ask in the comments or Discord. Then decide whether to use a similar narrator and music style, tied to "Pick the audio" above.

## Blocked / unverified

- EP02 is a draft only, not approved. The school interior in `lib/town.py` is a Studio port and hasn't been checked in Blender inside the Old Town shell. Whether `build.py` and the lighting can build a second episode without EP01-specific names is unchecked. The warm bubble text size on a phone (shot 14) is untested.
- Camera end-key fix and `camera_moves.yaml` persistence are now in the real rebuilt `episode.blend` (moves for s05, s06, s14, s15 captured and replayed); only checked on stills, not in a video render.
- Nothing from this chat is committed (many untracked files); the dark shots and the s16 loaf are unresolved (the sky pylon is fixed).
- The full EP01 video is rendered (`ep01_number.mp4`) but you have not reviewed it; the render used 32 samples and noise was not checked. Exposure and grade are shared per shot and not hand-editable yet.
- The Sketchfab CC-BY picks need your sign-in, and each page's licence must be checked. The `.glb` import path (`ext_model`) is untested because no files exist yet.
- Known look issues: s11 crowd members block the camera during the orbit; s10, s11, s13, s16, s18 and the card still read dark in Cycles; s18/card dawn haze is heavy and brown; BreadBag reads as a box; the south slopes are bare (no trees); the large leaf cards look big up close.
- Mountains show only in some shots (they sit behind roofs in many); far peaks were raised once.
- Face decals from side angles may float in front of the head (flat planes on a rounded head).
- Blender 5.2 crashes now and then (EXCEPTION_ACCESS_VIOLATION, depsgraph, OSL in the Lens Optics shader); render in the background with `pipeline/render.py`, which restarts after a crash.
- Nothing from the Blender work is committed. The earlier commits 49e8a94 and 4f8002f are pushed to github.com/adreii/modern-myths `main`.
- `HANDOFF.md` and `CLAUDE.md` were updated this chat and haven't been reviewed by you.
- The `day`, `dusk` and `night` lighting presets and the lens key are unchecked on screen. The `everyday-myths-episode` skill has not been tested on a real prompt, and the EP02-08 premises in `locations.md` are proposals only.
- Legal and channel: Roblox's Terms of Use have not been read at the source (the automated read failed). Use only your own builds or CC0 sources (Kenney, Quaternius, ambientCG, Poly Haven) for monetized videos; CC-BY Sketchfab assets are allowed only with credit in the description. The YouTube made-for-kids (COPPA) status, channel name and handle, music source and posting cadence are undecided; no accounts created.
- The craftee_films reel's voice and music are unidentified: nothing was verified, and the audio itself was not listened to. The ElevenLabs idea is a guess.
- Avatars have no clothing or accessories yet.
