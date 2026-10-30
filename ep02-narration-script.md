# EP02: The Sneakers (narration script)

Voice: the same narrator as EP01, first person, calm, a little wry. Don't perform it.
Pace: about 150 words a minute, with real pauses where the script has "/". About 140 words, so about 56 s of voice plus about 12 s of held silence: roughly 68 s in all.

The shoes never get a voice. They "talk" in speech bubbles that pop up at ankle height with a tiny squeak (an SFX). When the narrator reads a price, the bubble shows it at the same moment. Bubbles marked *(picture only)* are the punchline: let the picture say it, with no voice.

Read prices as words: "twelve", "three hundred", "four hundred". Always say them the same way, so they become catchphrases.

| Shot | Line | Approx. spoken | Bubble on screen | Note |
|---|---|---|---|---|
| 01 | At my school, / sneakers talk. | 2.2 s | **$240** | Hook: say it plainly |
| 02 | But all they ever say / is their price. | 3.0 s | $90 · $120 · $90 · $175 | The hallway chatters |
| 03 | Mine said twelve. / Quietly. | 2.4 s | a tiny **$12** | Small beat before "Quietly" |
| 04 | Max's said three hundred. / Every single step. | 3.2 s | **$300** on every footfall | Dry, not mean |
| 05 | And Pia's said nothing at all. | 2.4 s | none | |
| 06 | Everyone figured they were too old to talk. | 3.0 s | none | Pia is carrying someone else's books |
| 07 | So I gave mine a logo. | 2.0 s | *(picture only)* **$12. PLUS MARKER.** | Hold 1.2 s for the bubble |
| 08 | I wore them in the box, / so they'd look brand-new. | 3.2 s | *(picture only)* **BOX SOLD SEPARATELY** | Hold 1.0 s |
| 09 | Then I borrowed my cousin's. | 1.8 s | none (the giant shoes are the joke) | |
| 10 | Four hundred. / Four hundred. / Four hundred. | 3.0 s | **$400** on each clomp | Hit each one on the step |
| 11 | They were so loud, / I couldn't hear anything else. | 3.2 s | $400 stacked into noise | The tone turns; slow down |
| 12 | Not even Theo. | 1.6 s | prices chirp past him | **Music drops.** 1.5 s silence after |
| 13 | Then Pia's sneakers / walked straight into the puddle. | 3.0 s | none | Quiet |
| 14 | And for the first time, / I heard them talk. | 2.8 s | *(picture only)* warm bubbles: "Bus stop mud." "Mrs. Lee's stairs." "Theo's puddle." | 3 s of silence while they appear |
| 15 | I stepped out of the four hundred. | 2.2 s | the empty giant shoes keep shouting **$400** at nobody | The one laugh inside the turn |
| 16 | And got my socks wet. | 1.6 s | none | Let the picture carry it |
| 17 | Next day, / my twelve-dollar shoes said something new. | 3.2 s | *(picture only)* warm: "Theo's puddle." | Echo of 02 |
| 18 | Turns out a price only tells you where a shoe came from. / The scuffs tell you where it's been. | 6.5 s | a hallway of mixed bubbles: prices and places | Slowest line of all |
| End card | *(no voice. Text: "Where did your feet take you this week, just to help someone?")* | | | 3 s |

## Recording or generating the voice
- Kokoro TTS: the lines go into `episodes/ep02_sneakers/script.yaml` with `shot:` names, one per "/" segment with a short `pause`, as in EP01. Then `pipeline/tts.py` makes `voice.wav`, `timing.json` and `captions.ass`.
- Your own voice: the EP01 steps (quiet room, one file, 2 s between lines, 2–3 takes), saved as `voice.wav`; the timing is remeasured from it.
- Highlight words in the captions (mint, the price colour): twelve, three, four, hundred.
