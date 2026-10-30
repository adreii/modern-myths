# EP02: The Sneakers 👟 (full plan)

Draft for your approval, 2026-10-30. Based on the `locations.md` premise ("At my school, sneakers talk, but all they ever say is their price. The quietest pair belongs to the kid who actually helps people"), written with the `everyday-myths-episode` skill.

Files:
- `ep02-narration-script.md`: the voice, line by line
- `ep02-shot-list.md`: 18 shots, the visual plan, the build list, sound
- `bible/production-checklist.md`: the checklist to tick for this and every episode

## 1. Pitch
- **Title:** The Sneakers 👟
- **Everyday thing:** brand-new, expensive sneakers
- **Myth:** what you own is who you are (a price is a personality)
- **Sideways lesson:** a price only says where a shoe came from; what it's done (the scuffs) says where it's been, and that's the part that's yours
- **End-card question:** "Where did your feet take you this week, just to help someone?"

## 2. Myth decode (for the corpus)
A sneaker looks like a choice of style, a small piece of self-expression. What it quietly teaches is that a person can be read from what they paid: the price speaks for you, louder than anything you do, and it's settled at the till before you've done anything at all. That serves whoever sells the next pair, because a voice you buy has to be bought again once it goes quiet. The myth hides the other record every shoe carries, the mud and scuffs of where it has actually been, which no shop can sell and no price can fake.

## 3. Choosing the lesson
| Kind | Moral | Verdict |
|---|---|---|
| Obvious | "Don't care about brands." | Expected after 5 seconds; preachy |
| Opposite | "Shoes do say something about you." | Partly true, and kept: they do talk, just not about price |
| **Sideways** | "A price says where a shoe came from; the scuffs say where it's been." | **Chosen.** Helping shows up as a new kind of "voice"; the good act is concrete (stepping into the puddle for Theo) |

## 4. The story in five beats
1. **Hook (0–3 s).** A sneaker squeaks "$240" on a shiny school floor. "At my school, sneakers talk."
2. **Myth played straight (to ~20 s).** The hallway chatters prices. The Hero's shoes say a tiny "$12". Max's say "$300" on every step. Pia's taped old pair says nothing, and everyone figures they're too old to talk.
3. **Escalation (to ~42 s).** The Hero gives his a marker logo ("$12. PLUS MARKER."), wears them in the box ("BOX SOLD SEPARATELY"), then borrows his cousin's giant gold pair: "Four hundred. Four hundred. Four hundred." So loud he can't hear anything else. Through the window, Theo drops his homework into a puddle.
4. **The turn (quiet).** In the grey schoolyard, everyone walks round Theo. Pia's sneakers walk straight into the puddle, and for the first time the Hero hears them talk: "Bus stop mud." "Mrs. Lee's stairs." "Theo's puddle." He steps out of the four hundred (which keep shouting at nobody) and gets his socks wet helping.
5. **Landing.** Next day his muddy $12 shoes say "Theo's puddle." Crane up the yard; Max steps into a puddle to help too. "Turns out a price only tells you where a shoe came from. / The scuffs tell you where it's been."

## 5. Production plan (in order)

**Before EP02 (from `TODO.md`):** EP01 isn't rendered or posted yet, and the to-do list says to post EP01 and note its first-day numbers before planning EP02. Writing and building EP02 can start now; the posting order is your call.

| Phase | Who | What | Done when |
|---|---|---|---|
| 0. Approve | You | Read this plan, the script and the shot list; give notes on the story, the tone, the names (Max, Pia, Theo) | Script approved |
| 1. Episode folder | Claude | `episodes/ep02_sneakers/`: `script.yaml` (lines from the narration script, mint highlight words), `cast.yaml`, empty `looks.yaml` and `camera_moves.yaml`, stub `shots.py` | Folder builds an empty scene |
| 2. Voice | Claude (or you) | `tts.py` → `voice.wav`, `timing.json`, `captions.ass`; same voice as EP01 unless you pick another | Timing measured; ~68 s |
| 3. Pipeline check | Claude | Remove EP01-only assumptions (`EP01_World`, the EP01 look table) so a second episode builds | EP01 still builds the same; EP02 builds |
| 4. Builds | Claude | The 8 new builds in the shot list: sneakers on feet, speech bubbles, schoolyard + puddles, school interior inside the Old Town shell, two looks, Max and Pia, new acting moves, props | Each checked on a test still |
| 5. Shots | Claude | `shots.py` s01–s18 + the card; `build.py --stills --scale 40`; review sheet | Sheet sent to you |
| 6. Your pass | You | Notes per shot; hand-edit lights, Lens Optics cameras and camera moves in `episode.blend` | You say "done" |
| 7. Capture + rebuild | Claude | `grab_looks.py` first, then rebuild with your edits | Your edits survive |
| 8. Final render | Claude | `--render --final` (Cycles, OptiX, 1080×1920), music, SFX, `assemble.py` | `build/ep02_sneakers.mp4` |
| 9. Publish | You | Title with 👟, credits, made-for-kids setting, post; tracker → Posted | Posted |

## 6. Self-check (skill checklist)
- **Scroll-stopper?** Yes: a sneaker that squeaks its own price.
- **Absurd rule, straight face?** Yes. Nobody in the world finds talking shoes odd.
- **Escalation and laughs?** Marker logo → shoebox → giant shoes (rule of three), then the empty shoes still shouting (the break). Roughly one laugh every 8–12 s until the turn.
- **Sideways lesson, good act on screen?** Yes: Pia steps into the puddle; the Hero kneels in his socks to help Theo.
- **Quiet turn?** Shots 12–14: music out, static camera, 3 s of silence for the warm bubbles.
- **Landing reframes the hook?** "Sneakers talk / only their price" becomes "a price says where it came from; the scuffs say where it's been."
- **End card about the viewer's life?** Yes.
- **Every shot reasoned?** Yes; "Why" column, tied to the contrast/affinity map.
- **Filmable today?** Partly. The town, School shell, Hero's house, avatars, acting basics, number tags and cameras exist. Eight builds are new (above); sneakers on feet and the speech bubble are the biggest.
- **Parent glad, kid still watching?** I think so.

**Weak spots, honestly:**
- **Money.** Prices are close to "money at home", which the skill keeps out of jokes. Mitigation in the script: nobody mocks anyone's cheap shoes; the Hero only feels it himself; the cheap, old pair is the hero of the story; Max is never punished. Still worth your read: a kid with $12 shoes should feel proud, not seen.
- **"Too old to talk"** is the only line said about Pia's shoes by others. It's mild, but you could swap it for "Everyone figured they were broken."
- **Close to EP01's shape** (a quiet helper, a hero who performs, a "didn't change / said something new" ending). That's a corpus pattern, but EP03 should break it.
- **The warm bubbles in 14** carry the turn. If the text is too small on a phone, the episode loses its point; test it on a phone early.
- **Socks in a puddle** is safe and not a stunt, but keep the puddle obviously shallow.
- **COPPA:** this one clearly targets kids; the made-for-kids decision is still open in `TODO.md`.
