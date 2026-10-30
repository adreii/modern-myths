# Per-episode production checklist

Tick these for every video. It puts together the rules that were spread out before: the formula and writing rules in `bible/format.md`, the story checklist in the `everyday-myths-episode` skill, the pipeline in `HANDOFF.md`, and the channel rules in `TODO.md`.

Note: `format.md` describes a 7-beat formula (Rule, Escalation, Stake, Resistance, Turn, Reveal, Card). The skill's 5 beats (Hook, Myth, Escalation, Turn, Landing) are newer, and EP01 follows them. Use the 5 beats; the 7 fit inside them.

## 1. Story (before any build)
- [ ] Premise approved by you (one line, in `locations.md` / the tracker)
- [ ] Pitch: title with one emoji, everyday thing, myth, sideways lesson, end-card question
- [ ] Myth decode (3–5 sentences, Barthes-style) for the corpus
- [ ] Three candidate morals written (obvious / opposite / sideways); the sideways one chosen
- [ ] First frame + first sentence stops a scroll; no logo, no "hey guys"
- [ ] The absurd rule is stated with a straight face; the narrator never winks
- [ ] Each escalation step is bigger; at least one real laugh every 10–15 s
- [ ] The good action is **shown on screen** by a likeable character
- [ ] A quiet turn: music drops, the picture speaks, the voice says less
- [ ] The landing line reverses or reframes the hook, and it's the slowest line
- [ ] The end card is a question about the viewer's own life, not a summary
- [ ] Narration is about 130–230 words, short sentences, `/` pauses marked
- [ ] Barthes is paraphrased, never quoted at length; credited where needed
- [ ] Ethics: no shame (the watching kid may be the "low" one), dignity for the "villain", no copyable stunts, no jokes about bodies, families, money at home or any group
- [ ] Would a parent be glad, and would the kid still want to watch?

## 2. Shot list
- [ ] Visual plan written above the table: contrast/affinity map, power flip, one echo, one motif
- [ ] Every shot's size, angle, lens (mm), movement and light chosen for a reason ("Why" column)
- [ ] 180° line, screen direction, eyeline and the 30° rule checked
- [ ] Faces and key props kept out of the lower third (captions) and the right edge (app buttons)
- [ ] "Build this before recording" list: reuse sets, presets, acting moves first; new builds named

## 3. Episode files (`episodes/epNN_<name>/`)
- [ ] `script.yaml` (title, essay credit, voice, speed, `style: brick`, `engine: CYCLES`, highlight words, lines with `shot:`)
- [ ] `cast.yaml` (characters, default faces), new avatars added to `assets/roblox/avatars.json`
- [ ] `shots.py` (one function per shot)
- [ ] Empty `looks.yaml` and `camera_moves.yaml` ready for hand edits
- [ ] Corpus tracker entry updated (status Idea → Scripted → Animated → Posted)

## 4. Voice and timing
- [ ] Narrator decided (Kokoro voice or your recording)
- [ ] `pipeline/tts.py` run → `voice.wav`, `timing.json`, `captions.ass`
- [ ] Captions checked: key words highlighted in the myth colour

## 5. Build and look
- [ ] New sets, props and acting moves built and checked on a still
- [ ] `build.py --stills --scale 40` → review sheet; you approve or give per-shot notes
- [ ] Your hand edits (lights, Lens Optics cameras, camera moves) done in `episode.blend`
- [ ] **`grab_looks.py` run before every rebuild**, so your edits survive
- [ ] Known dark or clipped shots fixed; the echo shots keep the same framing

## 6. Render and assemble
- [ ] `build.py --render --final` (Cycles, OptiX, 1080×1920); 0-byte PNGs deleted before resuming
- [ ] Music: a licensed track (licence saved), drops at the turn, back for the landing
- [ ] SFX placed (the whoosh, the quiet beat, the landing chime or equivalent)
- [ ] `assemble.py` → `build/<episode>.mp4`; watched end to end on a phone

## 7. Publish
- [ ] Title with one emoji; no Roblox names or logos in the title or thumbnail
- [ ] Description credits CC0 / CC-BY assets (`assets/ext/LICENSES.md`)
- [ ] YouTube "made for kids" setting chosen (decision still open in `TODO.md`)
- [ ] Posted to Reels and Shorts; first-day numbers noted in the tracker
- [ ] Episode files and code committed
