# Everyday Myths channel

A Roblox-style short-video channel (Instagram Reels / YouTube Shorts). Each episode follows Barthes's *Mythologies*: it decodes the hidden "myth" in an everyday thing, then asks an ethical question. The episodes form a corpus to derive ethics from.

Videos are made in **Blender 5.2** with the Python pipeline in this repo (github.com/adreii/modern-myths). Roblox Studio is no longer used; `roblox/` is reference only.

- Start here: `HANDOFF.md` (pipeline, commands, setup, state)
- Corpus tracker: https://claude.ai/artifact/N1RKyp9u41NHKVKsi7GF19 (db collection `episodes`)
- Episodes: `episodes/ep01_number/` (script.yaml, cast.yaml, shots.py); shot list `ep01-shot-list.md`
- Libraries: `lib/oldtown.py` + `lib/town_layout.yaml` (town), `lib/backdrop.py` (terrain, forest, mountains), `pipeline/lookdev.py` (look dev), `lib/imported.py` (avatars, faces), `lib/acting.py`, `lib/numbers.py`, `lib/lighting.py`, `lib/cam.py`
- Episode skill (ideas, scripts, shot lists, cinematography): `.claude/skills/everyday-myths-episode/SKILL.md`
- Run Blender headless: `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P pipeline/build.py -- episodes/<ep> …`; voice/assembly use `.venv/Scripts/python`

## Working rules
- **Easy questions (how-to, "how do I…", quick facts) go to a subagent.** Brief it with the facts it needs, then relay its answer.
- **At the end of every chat, have a Sonnet subagent build a to-do list.** It writes or updates `TODO.md` here from what the chat did, what's blocked and what's unverified. Then relay it to the user.
