# Cinematography for Everyday Myths

A practical guide drawn from the standard texts (Joseph Mascelli's *The Five C's of Cinematography*, Bruce Block's *The Visual Story*, Blain Brown's *Cinematography: Theory and Practice*) and the classical principles of art, translated into Roblox Studio and the StoryKit camera.

## Contents
1. The Five C's
2. Shot sizes and what they do
3. Angles and power
4. Lenses: FOV table for Roblox
5. Camera movement and CameraRig kinds
6. Composition in 9:16
7. Contrast and affinity (the visual plan)
8. Principles and elements of art as camera choices
9. Light and colour
10. Continuity rules
11. Editing rhythm for Shorts
12. Shot list "Why" notes

## 1. The Five C's (Mascelli)
Run every shot through these:
- **Camera angle**: what the viewer sees and from whose point of view (objective, subjective, POV), and from what height.
- **Continuity**: time, space and screen direction read clearly across cuts.
- **Cutting**: why we cut here (on action, on a look, for contrast, for a reveal).
- **Close-ups**: saved for what matters; cut-ins and cutaways show the detail that carries the story.
- **Composition**: where the eye goes first, balance, and the centre of interest.

## 2. Shot sizes and what they do
| Size | Frame | Use it for |
|---|---|---|
| Extreme wide (EWS) | whole town, figures tiny | the world's rule, scale, endings that pull away |
| Wide (WS) | full set, full bodies | geography, crowds, loneliness in space |
| Full (FS) | head to toe | physical comedy, poses, walking |
| Medium (MS) | waist up | dialogue, reactions, the default storytelling size |
| Medium close (MCU) | chest up | the narrator's feelings starting to show |
| Close-up (CU) | face, or the number | emotion, decisions, the motif |
| Extreme close-up (ECU) | eyes, a hand, a loaf | the turn, the key detail, comic emphasis |
| Insert | an object | information the kid must not miss |

Rule of thumb: go wide to explain, tight to make it felt. Change size meaningfully between consecutive shots of the same subject (at least one step), or the cut jumps.

On a phone screen, faces and objects read small. Lean one size tighter than you would for a TV, and keep the important thing big.

## 3. Angles and power
- **Low angle** (camera below eyes, looking up): the subject feels big, powerful, heroic, or full of themselves. Use for the myth's "winner".
- **High angle** (looking down): small, vulnerable, overlooked. Use for the "loser" and for the hero when the myth crushes them.
- **Eye level**: equal, honest, calm. Use at the landing, when the hero sees clearly.
- **Overhead / top-down**: pattern, fate, a god's-eye view of the rule. Great for echoes (EP01 doorsteps).
- **Dutch tilt** (`roll`): unease, the world going wrong. Use sparingly, one escalation beat at most.
- **POV / over-the-shoulder**: put the kid in someone's place, usually the person being ignored.

Plan the **power flip**: whoever is shot from below early is shot from eye level or above after the turn, and the reverse for the overlooked character.

## 4. Lenses: FOV table for Roblox
Roblox `Camera.FieldOfView` is the **vertical** angle. In 9:16 portrait the vertical side is the long side, so this table maps full-frame lens lengths using the 36 mm side: FOV = 2·atan(18 / focal length).

| Lens (full-frame equivalent) | Roblox FOV | Feel | Use it for |
|---|---|---|---|
| 16 mm | 97 | warped, comic, huge space | absurd reveals, cartoon close-ups for laughs |
| 24 mm | 74 (Roblox default 70) | wide, deep, energetic | establishing, crowds, action |
| 35 mm | 54 | natural, slightly wide | walk-and-talk, the everyday default |
| 50 mm | 40 | like the eye, honest | medium shots, calm moments, the landing |
| 85 mm | 24 | flattering, background soft and close | emotional close-ups, the turn |
| 135 mm | 15 | compressed, isolating, voyeuristic | watching from far away, crowds stacked flat |

Notes:
- Wide lens close to a face exaggerates features. Good for comedy, bad for sincere moments.
- Long lens far away flattens space and isolates a character from a crowd: perfect for "alone in the square".
- Keep lens choices consistent within a beat; change lens family when the beat changes (wide in escalation, long at the turn).
- Roblox has no real depth of field on the camera; fake focus with `DepthOfFieldEffect` in Lighting (FocusDistance, InFocusRadius, FarIntensity) for long-lens shots, and set it per shot.
- `fovTo` on a shot gives a zoom; a fast `snapZoom` is a comic beat, a slow creep-in zoom is tension.

## 5. Camera movement and CameraRig kinds
Movement should have a motive: follow action, reveal information, or change the emotional distance.
| CameraRig `kind` | Real-world move | Meaning |
|---|---|---|
| `static` | locked-off | observation, deadpan comedy (let the absurd thing happen in a still frame), the turn |
| `push_in` | dolly in | growing realisation, importance, pressure |
| `pull_out` | dolly out | isolation, reveal of context, endings |
| `pan` | pan / tracking | follow movement, reveal across space |
| `crane` | crane up/down | enter or leave the world, scale, fate |
| `orbit` | arc | showing off, vanity, a character at the centre of the world |
| `shake` 0.1 to 0.3 | handheld | chaos, montage, energy |
| `roll` / `rollTo` | dutch / roll | disorientation |
| `snapZoom` | crash zoom | comic emphasis, sudden decision |

Ease: `Sine` InOut for most moves (weight and calm); `Linear` for mechanical or deadpan moves; `Back` or `Elastic` only for cartoon gags.

Deadpan comedy usually plays best **still**: a static wide where the impossible thing just happens. Save moving cameras for energy and meaning.

## 6. Composition in 9:16
- **Thirds on a tall frame.** Eyes on the upper third line. The motif (the number) in the top third, the action in the middle, captions live in the lower third, so keep faces and key props out of it.
- **Safe zones.** Reels and Shorts overlay buttons on the right edge and text along the bottom. Keep important things in the centre and upper-middle.
- **Headroom and lead room.** A little space above heads; leave space in the direction a character looks or moves.
- **Centre framing** is strong in portrait and suits deadpan symmetry (Wes Anderson style). Use symmetry for the "rule" of the world and break it when the rule breaks.
- **Depth.** Foreground, midground, background layers make Roblox sets look less flat: a lamp post or doorway in the foreground, the hero in the middle, the town behind.
- **Frames within frames.** Windows and doorways frame isolation or watching (EP01 shot 14).
- **Leading lines.** Streets, fences and rows of houses pull the eye to the subject. Vertical lines suit the tall frame.
- **Negative space.** A small figure in a large empty area reads as lonely; use it at the turn.

## 7. Contrast and affinity (the visual plan)
Bruce Block's core principle: the more contrast in a visual component, the more intensity; the more affinity (similarity), the less. His basic visual components are **space, line, shape, tone, colour, movement and rhythm**. Structure an episode by planning how two or three of them change across the five beats.

Example map for an episode:
| Component | Hook / myth | Escalation | Turn | Landing |
|---|---|---|---|---|
| Space | deep, open | flatter, crowded | huge empty space around the hero | deep and open again |
| Tone | even daylight | brighter, harsher | dim, low contrast, still | soft dawn |
| Colour | myth colour (yellow numbers) everywhere | myth colour louder, more saturated | myth colour drained | warm natural colour wins |
| Movement | gentle moves | fast, shaking, whip cuts | static | one slow big move |
| Rhythm | 3 s shots | 1.5 to 2 s shots | one 4 s held shot | long final shot |

The turn should be the point of greatest contrast with what came just before it. Usually that means stillness after motion and quiet after noise.

## 8. Principles and elements of art as camera choices
Elements: line, shape, form, space, value (light and dark), colour, texture. Principles, and how they become shot decisions:
- **Balance**: symmetrical framing for order and the world's rule; asymmetrical for tension and imbalance of power.
- **Contrast**: the brightest, sharpest or most saturated thing is where the eye goes; make it the story point.
- **Emphasis**: one centre of interest per shot. Use light, size, colour or isolation to point at it.
- **Movement**: how the eye travels; lines and character motion should lead to the subject.
- **Pattern and repetition**: rows of numbers, houses, doorsteps; then break the pattern to show the story (one dark window).
- **Rhythm**: the timing of cuts and repeated visual beats, like music.
- **Proportion and scale**: big and small sells power and absurdity (a gigantic number over a tiny kid).
- **Unity and variety**: a consistent palette and look across the channel, with enough variety in size and angle to keep each shot fresh.

Shape language for character and set design: circles read friendly and safe (the baker), squares read stable and stubborn, triangles read sharp, dynamic or threatening (the influencer's pointed sunglasses).

## 9. Light and colour
- **Three-point thinking** even in Roblox: a key light (the sun or a `SpotLight`), fill (Ambient / OutdoorAmbient), and a back or rim light (`PointLight` behind a character) to separate them from the background.
- **Time of day as emotion.** `dawn`: hope and new start; `day`: the ordinary world, the myth in full swing; `dusk`: things ending, doubt; `night` / `pre_dawn_dark`: hidden goodness, secrets. Use `LightingPresets` and transition between presets on the beat change, not mid-beat.
- **Motivated light.** Every light should have a source the kid can believe (a bakery window, a lamp, the glowing number). Warm practical lights read as kindness and home.
- **Colour scripting.** Give the myth a colour (EP01: yellow numbers) and the real value another (warm bread and dawn orange). Let the balance shift across the episode. Keep the palette to two or three dominant hues per episode.
- **Value.** Silhouettes read instantly on a phone; place characters against a lighter or darker background so they pop.

## 10. Continuity rules
- **180-degree rule.** In a scene between two characters, keep the camera on one side of the line joining them, so left stays left. Cross it only on purpose (a neutral shot along the line, or a visible camera move across).
- **Screen direction.** If the hero walks left to right toward the bakery, keep it that way every time they head there. Reverse it when they turn back from the myth.
- **Eyeline match.** A character looking off-screen right should cut to what they see from roughly their position.
- **30-degree rule.** When cutting to the same subject, change the angle at least 30 degrees or change size, or it jump-cuts.
- **Match on action.** Cut in the middle of a movement (a knock, a turn) to hide the cut.
- **Lighting continuity.** The same scene keeps the same preset unless time passing is the point.

## 11. Editing rhythm for Shorts
- First frame is the hook; no fade-in, no title.
- 2 to 4 s shots on average, shorter in escalation, one long held shot at the turn.
- Cut on the word or on the beat: the picture changes as the narration changes idea.
- Picture follows voice: record voice first, retime shots to it (see `ep01-narration-script.md`).
- Sound does half the work: whoosh on fast moves, a silence before the turn, music back on the landing.
- Captions word by word, white with black stroke, lower third; the myth's key word highlighted in the myth colour.

## 12. Shot list "Why" notes
For any shot where the camera carries meaning, add a one-line "Why" naming the principle, so later episodes can learn from the corpus. Examples:
- "Low angle + orbit, 24 mm: the influencer at the centre of his own world (power, vanity)."
- "Same top-down as 06: visual echo; only what's in frame changes."
- "85 mm from far away, hero small in empty square: isolation through compression and negative space."
- "Static, framed by the window: we are outsiders looking in; the turn is quiet."
