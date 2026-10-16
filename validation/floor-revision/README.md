# Floor revision: floor line from planted heels and toes

The floor check flags a reversal when the ball's bottom edge reaches the estimated floor line. The line was estimated from still ankles plus a guessed ankle height. With heel/toe landmarks now available, it comes from the planted soles directly. The ankle method is kept as a fallback. Counting rules and thresholds are otherwise unchanged.

## New clips (user totals, not recounted)

| ID | File | User total | Notes from the player |
|---|---|---:|---|
| 4 | `2.59 PM.mov` | 13 | 8th touch (~4.5 s) sends the ball above the frame; the bounce after the 13th touch is a floor bounce, not a touch |
| 5 | `3.01 PM.mov` | 25 | 4 touches near the end while the ball is mostly out of frame |
| 6 | `2.59 PM #2.mov` | 23 | 2 touches near the end while the ball is mostly out of frame |

References are in `clip-N-reference.json`. They hold totals only, with no event timestamps. Results are counting re-runs on the saved samples from your app uploads, so tracking is the same pipeline output.

## What changed

| Clip | Before | After | Change |
|---|---:|---:|---|
| 4 (13) | 12 + 1 floor flag | 12 + 1 floor flag | none |
| 5 (25) | 21 | 21 | none |
| 6 (23) | 19 + floor flag + gap flag | 20 + gap flag | 6.868 s now counted |
| Original + clips 1–3 | 26/16/29/21 | 26/16/29/21 | none; original still 26/26 matched, 0 extra, 0 missed |

**Clip 6 at 6.868 s / frame 206** (`clip-6-low-touch-6868.jpg`): a low touch. The ball comes down between the feet, and the right foot lifts with it in the next frames. The old floor line (915 px) sat about 50 px above the planted toes. The new line is 971 px, and the ball bottom at 900 px is clearly above it.

**Clip 4 at 7.367 s stays flagged, correctly** (`clip-4-floor-bounce-7367.jpg`). The ball falls past the foot, reaches the floor at the bottom of the frame, and bounces up below the raised foot. The player confirmed the final bounce is not a touch. An earlier suggestion in this session to treat it as a touch, based on "ball moving toward the camera", was wrong and was not implemented.

**Stops before the first touch are hidden.** In clip 6 the ball rests on the floor before the pickup, and that was shown as "juggling stopped" for 0–1.0 s.

## Still missed (needs other evidence)

- **Clip 4:** the 8th touch at about 4.5 s, where the ball is above or at the top of the frame and the tracker loses it for about 1.2 s.
- **Clip 5:** 4 touches at the end, out of frame.
- **Clip 6:** 2 touches at the end, out of frame. There's also a `gap_near_contact` flag at 9.40 s, not inspected here.

Each of these lines up with a strong audio onset, which is what the next revision addresses.

## Verification

55 Python tests pass. New ones cover the floor line coming from planted soles, a low touch above the soles counting, a ball reaching sole level still being flagged, and a stop before the first touch being hidden. No real floor-bounce footage existed before clip 4, and clip 4's bounce is the only real one tested.
