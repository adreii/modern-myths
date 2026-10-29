# EP01: Everyone Has a Number (narration script)

Voice: first person, calm, a little wry, like telling a friend something you only just understood. Don't perform it.
Pace: about 150 words a minute, with real pauses where the script has "/". Total spoken length is about 70 seconds.

Read numbers as words: "two-twelve", "nine", "fifty thousand", "nine hundred, three thousand, ten thousand".

| Shot | Shot length now | Line | Approx. spoken | Note |
|---|---|---|---|---|
| 01 | 3.0 s | In my town, everyone has a number floating over their head. | 4.0 s | **Longer than shot.** Hook: say it plainly, no build-up |
| 02 | 3.0 s | Nobody remembers who put it there. | 2.3 s | |
| 03 | 2.5 s | Mine was two-twelve. / Low. / Embarrassing. | 3.2 s | **Longer.** Small beat before each of the last two words |
| 04 | 3.0 s | The baker had nine. / Just nine. | 2.6 s | |
| 05 | 3.5 s | But every morning, before anyone woke up… | 2.8 s | Trail off, it continues into 06 |
| 06 | 3.0 s | …she left bread on the doorsteps of houses with no lights on. | 4.3 s | **Longer** |
| 07 | 3.0 s | The guy with fifty thousand never said hi to anyone. | 3.6 s | **Longer** |
| 08 | 2.5 s | He was busy making his number go up. | 2.8 s | **Slightly longer**. Dry, not mean |
| 09 | 3.0 s | So I did what everyone does. | 2.2 s | |
| 10 | 2.0 s | I started performing. | 1.4 s | |
| 11 | 4.5 s | Nine hundred. / Three thousand. / Ten thousand. | 3.6 s | Hit each number as the counter pops |
| 12 | 4.0 s | And the bigger it got, the fewer people actually knew my name. | 4.4 s | **Slightly longer**. Slow down here, the tone turns |
| 13 | 3.5 s | One morning, / there was no bread. | 2.5 s | Quiet |
| 14 | 2.5 s | The baker was sick. | 1.6 s | |
| 15 | 3.5 s | And I realized no number in town could have told me that. | 4.2 s | **Longer** |
| 16 | 4.0 s | So I brought her bread. | 1.8 s | Let the picture carry the rest |
| 17 | 3.5 s | My number didn't move. / Not even by one. | 3.0 s | Leave a full second of silence after |
| 18 | 6.0 s | Turns out the number never measured what we thought. / It only measured who was watching. | 5.8 s | Last line slowest of all |
| End card | 2.0 s | *(no voice. Text: "What's something good you did that nobody saw?")* | | |

The shots add up to about 62 s, the voice to about 70 s. Seven lines run longer than their shot.
So the picture follows the voice, not the other way round: record the voice first, then the shots get retimed to fit it.

## Recording the voice
1. Quiet room, phone or mic 15–20 cm from your mouth, slightly off to the side.
2. Record the whole script in one file. Leave **2 seconds of silence between lines**. If you fluff a line, pause and say it again; keep the best take.
3. Do 2–3 full takes and pick the most natural one.
4. Save it as `ep01-voice.wav` (or .m4a/.mp3) in this folder.

## Timing it to the picture
1. Give Claude the voice file. Claude measures each line (ffmpeg is installed) and updates every shot's length in `EP01_Shots` to "line + a short breath", so camera moves stretch to match.
2. Record the picture in one take with **P** (see the OBS steps in `roblox/SETUP.md` or ask Claude).
3. In your editor (CapCut is easiest): put the video on one track, the voice on another, line up the first word with the start of shot 01. Each line should land on its shot.
4. Add word-by-word captions (CapCut: Text > Auto captions), music, sound effects and the end card.
