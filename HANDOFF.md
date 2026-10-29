# Handoff: Modern Myths (Everyday Myths)

Paste this into a new Claude Code session opened in a clone of this repo on the 4090 PC.
Repo: https://github.com/adreii/modern-myths (branch `main`)

## Project
A short-video channel (YouTube Shorts, Instagram Reels) for kids 8-13. Each episode follows
Roland Barthes' *Mythologies*: an absurd "in my town…" rule told with a straight face decodes the
hidden myth in an everyday thing, then ends on an ethical question. The episodes form a corpus to
derive ethics from. Vertical 1080×1920, 60-90 s, Roblox-style visuals.

The repo holds **two production tracks**:

| Track | Where | Status |
|---|---|---|
| **Roblox Studio** (current) | `roblox/`, `ep01-*.md`, `town-plan.md`, `locations.md` | EP01 shot and staged in Studio; voice and picture not recorded |
| Blender pipeline (earlier) | `pipeline/`, `lib/`, `episodes/ep01_toys/`, `make.sh` | ep01 "Toys" built and narrated; never rendered |

New work goes into the Roblox Studio track. Keep the Blender pipeline as a fallback renderer and for
its TTS, caption and ffmpeg steps.

## State: Roblox Studio track
- **EP01 "Everyone Has a Number 🔢"**: everyone's number floats over their head; the baker with
  "9" quietly feeds the street. 18 shots, about 62 s of picture, plus a 2 s end card.
  - `ep01-shot-list.md` has the visual plan (contrast and affinity, power flip, echo 06/13, lens key)
    and a "why" for every shot. `ep01-narration-script.md` has the voice script (about 70 s).
  - `roblox/EP01_Shots.client.luau` plays the shots in Studio. Controls in Play: **P** plays all 18,
    **N/B** next/previous, **R** replays, **F** returns to free mode.
- **The town** (`town-plan.md`): one connected town for every episode, with cutaway walls for
  interiors. Phase 1 and phase 2a/2b interiors (the Hero's house, garage, school) are built by
  `roblox/Build/*.luau`.
- **StoryKit** (`roblox/StoryKit/`): `CameraRig`, `LightingPresets`, `NumberBillboard`, `Puppet`
  (placeholder acting) and `Sets` (`Sets.cutaway`, `Sets.reset`).
- **The Studio place is "Episode1"**, saved locally in Roblox Studio, not in this repo. The local
  `.luau` files are the source of truth; copy changes both ways.
- **EP02-08** premises and the sets they need are in `locations.md`. They're proposals, not approved.
- **Corpus tracker:** https://claude.ai/artifact/N1RKyp9u41NHKVKsi7GF19 (db collection `episodes`).
  `everyday-myths-corpus.html` is a local copy of the page.
- **Episode skill:** `.claude/skills/everyday-myths-episode/` writes ideas, scripts and shot lists
  with real cinematography. It hasn't been tested on a real prompt yet.

## Setup on the PC
1. Install **Roblox Studio** and open the "Episode1" place (or a new Baseplate; see `roblox/SETUP.md`
   to install StoryKit and run the `roblox/Build/` scripts).
2. In Studio: **Assistant → … → Manage MCP Servers → Enable Studio as MCP server**. `.mcp.json` in
   this repo connects Claude Code. Start the Claude session *after* Studio is open.
3. For capture: OBS at 1080×1920, 60 fps, NVENC, Window Capture of Studio cropped to the game view.
   In Studio, Test tab → Device → a portrait phone.
4. Optional, for the Blender track: Python **3.11**, ffmpeg with libass, `pip install -r
   requirements.txt` and the Kokoro models (commands in `README.md`).

## Next steps
1. **Save the place** in Studio (Ctrl+S) if the last session's work is still unsaved.
2. **Check 9:16 framing**: capture all 18 shots in a portrait viewport. Every check so far was
   landscape. Numbers ("212", "10,000") and the billboards must stay in frame. Re-check shots 01,
   03-06, 08, 09, 11, 13, 14 and 16, which weren't looked at after the camera revamp.
3. **Record the voice** (`ep01-voice.wav`: whole script, 2 s gaps, 2-3 takes).
4. **Retime the shots** to the voice: measure each line with ffmpeg, set each shot to "line + a
   breath" in `EP01_Shots` (Studio and the local copy).
5. **Record the picture** in one take with **P**, then assemble in CapCut (captions, music, sound
   effects, end card). `pipeline/assemble.py` could replace CapCut later.
6. Then: phase 2c shop interiors, the phone/screen overlay, phase 3 dressing with CC0 props, and
   writing EP02 with the episode skill.

`TODO.md` has the full, ordered list with who does what, plus what's blocked and unverified.

## Decisions still open
- Roblox Terms of Use for monetized off-platform videos: not yet read at the source.
- YouTube "made for kids" (COPPA) setting, channel name and handle, posting cadence.
- Narrator (own voice vs TTS) and a licensed music source.

## Notes
- Barthes is still under copyright: paraphrase, credit him on the end card, and keep quotes short.
- Use only your own Roblox avatar and builds, or CC0 assets (Kenney, Quaternius, ambientCG, Poly
  Haven). Toolbox models are licensed for use on Roblox only and can hide scripts. Keep a licence log.
- Keep Roblox names and logos out of titles and thumbnails.
- `bible/format.md` has the original story formula; `bible/episode-ideas.md` has 9 more ideas from
  the Blender track.
