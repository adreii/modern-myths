---
name: everyday-myths-episode
description: Writes Everyday Myths episodes, the Roblox-style Shorts/Reels channel that teaches kids how to be a good person through absurd, funny stories with twist lessons. Covers the idea, the decoded myth, the script, and a shot list built on real cinematography (shot sizes, lens, angle, movement, light, composition, contrast and affinity). Use it whenever the user wants a new episode, an episode idea, a pitch, a script or narration, a shot list, a storyboard, a rewrite of a scene or shot, or asks to make an episode funnier, weirder, shorter or clearer for kids. Use it even when they only say "EP02", "next episode", "make this land better" or "how should I shoot this".
---

# Everyday Myths: making an episode

The channel takes one everyday thing (likes, grades, "being cool", saying sorry, winning), shows the hidden belief inside it, the way Barthes's *Mythologies* does, and lets a kid walk away a little kinder. The audience is kids, roughly 8 to 13. The vehicle is an absurd, funny, slightly-off story told in Roblox, ending on a lesson nobody saw coming.

The goal is **influence through delight, not instruction**. A kid should rewatch it because it's weird and funny, and send it to a friend, and only later notice it changed how they think. If it feels like a school assembly, it has failed, however good the lesson.

## Read these when you need them
- `references/story-craft.md`: the absurdist toolbox, twist patterns, comic timing, how kids actually take in morals, and the ethics checklist. Read it before writing any idea or script.
- `references/cinematography.md`: shot grammar, lens and FOV table for Roblox, composition, light, colour, movement, editing rhythm, and the principles of art turned into camera choices. Read it before writing any shot list.
- Project files: `ep01-shot-list.md` and `ep01-narration-script.md` are the house format and tone reference; `roblox/StoryKit/CameraRig.luau` (shot kinds), `LightingPresets.luau`, `Puppet.luau` (available acting) and `NumberBillboard.luau` say what can be filmed today.

## The episode in five beats
Every episode is 60 to 90 seconds, 9:16, and moves through these beats. The timings are a guide.

1. **Hook (0 to 3 s).** An absurd image plus a plain sentence that states the strange rule of the world. No logo, no "hey guys". "In my town, everyone has a number floating over their head."
2. **The myth, played straight (to about 30%).** Show the everyday belief as the world's normal law. The narrator half-believes it too. Ground it in one or two specific, visual examples.
3. **Escalation (to about 70%).** The hero buys into the myth and pushes it too far. Each step is bigger and sillier than the last (rule of three, then break it). This is where most jokes live.
4. **The turn (one quiet beat).** Something small and concrete exposes what the myth was hiding. Music drops out. The picture does the work and the voice says less.
5. **The landing.** One last line that reframes everything, ideally reversing the hook's own words. Then a 2-second end card with a question the kid answers about their own life, never a summary of the moral.

## The unexpected lesson
The lesson has to be one a kid would not guess from the first five seconds. The obvious moral ("don't care about likes") is the myth's surface; the episode's lesson is underneath it ("likes only measure who was watching, so the best things you do will never show up").

To find it, write three candidate morals for the idea:
- the **obvious** one the kid already expects,
- the **opposite** one (what if the myth is partly right?),
- the **sideways** one: a different value altogether shows up and quietly wins.

Choose the sideways one most of the time. It is the twist, and it is what makes the ending feel earned rather than preached.

Then check the lesson is about **being** good, something a kid can do tomorrow (notice someone, share, own a mistake, tell the truth when it costs, be kind when no one sees), not an abstract slogan. The end-card question should point at that action.

## Humour and absurdity
Aim for the deadpan end of absurd: an impossible rule (numbers over heads, a town where apologies cost money, a kid whose shadow quits) treated with total seriousness. The narrator never winks; the world is strange and everyone acts as if it's normal. That gap is the joke, and it is also what makes the myth visible.

Kids laugh hardest at: literalised metaphors, escalation that goes one step too far, adults or "cool" characters being humbled gently, a sudden cut to a silly image after a serious line, and repetition with a twist. Keep the cruelty out: laugh at ideas and situations, never at a body, a disability, a family or a group. Details and patterns are in `references/story-craft.md`.

## Ethics and safety for a kids' channel
These episodes are made to shape children's values, so hold them to a higher standard than ordinary content:
- **Show, don't sermonise.** Research on moral comprehension (Narvaez and colleagues) found younger children often miss the moral a writer intended. So make the good action visible on screen, done by a character the kid likes, and state the landing line plainly. Don't rely on symbolism alone.
- **Model the behaviour, not the bad one.** The hero can be wrong for most of the episode, but the wrong behaviour should look silly or empty, never cool or rewarded. Never show copyable dangerous stunts.
- **No shame.** The kid watching may be the one with the low number. End with dignity for everyone, including the "villain".
- **Questions over answers.** The end card asks, it doesn't tell. The corpus exists to derive ethics, so leave the room open.
- **Platform rules.** Content made for kids triggers COPPA rules on YouTube ("made for kids" designation: no comments, no personalised ads). Flag this to the user when an episode clearly targets young children; the decision about the channel setting is theirs, and it's still open in `TODO.md`.

## Writing the shot list
Use the EP01 format (table: #, Sec, Set / light, Picture, Camera, Voiceover), plus a "Why" note for any shot where the camera choice carries meaning. Before writing shots, decide the episode's **visual plan** (see `references/cinematography.md`):

1. **Contrast and affinity map.** Pick two or three visual components (space, tone, colour, movement, rhythm) and plan how they shift across the five beats. Usually: affinity (calm, similar) in the myth, rising contrast through the escalation, the strongest contrast or a sudden stillness at the turn, a resolved affinity at the landing.
2. **Power through angle and size.** Who is big, who is small, and when that flips. The flip should land on the turn.
3. **One visual echo.** Repeat one exact framing early and late so the change in what's inside it tells the story (EP01: full doorsteps, then bare ones, same camera).
4. **One motif.** A single visual symbol of the myth (the floating number) that stays on screen and changes meaning by the end.

Then, for each shot, choose size, angle, lens (FOV), movement and light on purpose, and keep the rules of continuity (180-degree line, screen direction, eyeline). Roblox specifics, FOV numbers and CameraRig kinds are in `references/cinematography.md`.

Shots are 2 to 4 seconds; vary their length in rhythm with the voice. The voice is recorded first and the picture is retimed to it, so write the narration with natural pauses (`/`) the way `ep01-narration-script.md` does.

## What to hand back
For a new episode, produce, in this order:
1. **Pitch** (5 lines): title with one emoji, the everyday thing, the myth it hides, the sideways lesson, the end-card question.
2. **Myth decode** (3 to 5 sentences, Barthes-style): what the thing appears to mean, what it quietly teaches, who it serves. This is for the corpus, not the video.
3. **Narration script** in the `ep01-narration-script.md` format, with spoken-length estimates at about 150 words a minute.
4. **Shot list** in the `ep01-shot-list.md` format, with the visual plan (contrast/affinity map, power flip, echo, motif) written above the table and a "Build this before recording" section that reuses existing sets, presets and Puppet moves where possible.
5. **Self-check** against the checklist below, with any weak spots named honestly.

Save files as `epNN-shot-list.md` and `epNN-narration-script.md` in the project root. If the corpus tracker (https://claude.ai/artifact/N1RKyp9u41NHKVKsi7GF19, collection `episodes`) holds the idea, update that episode's status there.

For a smaller request (just ideas, one scene, one shot) do only that part, but still apply the same principles.

## Checklist before handing back
- Does the first frame plus first sentence make a kid stop scrolling?
- Is the world's rule absurd but stated with a straight face?
- Does each escalation step get bigger, and is there at least one real laugh per 15 seconds?
- Is the lesson the sideways one, and is the good action shown on screen?
- Is there a quiet turn where the music drops and the picture speaks?
- Does the landing line reverse or reframe the hook?
- Is the end card a question about the viewer's own life?
- Is every shot's size, angle, lens and movement chosen for a reason, and do the reasons follow the contrast/affinity map?
- Can it be filmed with today's StoryKit, or are new builds listed?
- Would a parent be glad their kid watched it, and would the kid still want to?
