# Side-to-side prototype validation — 2026-10-17

The edge-return revision below supersedes the initial turn totals and UI behavior.
These are development observations, **not measured accuracy**. There is no
independent full-clip reference for turns or marker crossings. The three provided
side-to-side videos were processed; close-control and toe-tap clips were not.

## Initial configuration and outputs (before edge-return revision)

YOLO11s, CPU, 640 inference; default Kalman association and 0.15 s prediction
horizon. No appearance bridge, pose, feet, or audio. Fixed-camera temporal median
background at 480×320 from samples at roughly 1 Hz; reject detections with less
than 20% changed central pixels at a max-channel difference of 35. This removes
many stationary paddle false positives; it does not guarantee ball identity.

Upright-video ROI `[0, .42, 1, 1]`, approximate marker x coordinates `[.19, .835]`,
reach goal enabled. These are reviewable setup choices, not universal defaults.
Full horizontal width preserves the actual left-side ball path. Pace is timed
between the inner 15% and 85% of marker spacing, a consistent central section;
not time for the entire repetition. Comparisons require 3 sections per direction.

| Clip | Decoded frames | Observed / predicted / lost | Estimated turns | Timed sections | Possible hidden-turn windows | Runtime |
|---|---:|---|---:|---:|---:|---:|
| side2side1 | 920 | 766 / 77 / 77 | 2 | 5 | 1 | 51.6 s |
| side2side2 | 1002 | 618 / 123 / 261 | 1 | 3 | 0 | 54.3 s |
| side2side3 | 1342 | 1006 / 99 / 237 | 7 | 9 | 4 | 76.6 s |

Runtime includes scene reading, model loading, decoding, tracking, and H.264
playback encoding on this Mac. Full-width final runs were sequential. Container
frame totals differ from decoded counts and are disclosed in each result.
`clip-*-result.json` preserves timestamps, boxes, gaps, events, setup and parameters.
`comparison.json` preserves the earlier cropped-run summary.

## What testing changed

1. Raw sports-ball detections repeatedly selected the stationary right paddle.
   For example, an initial clip-1 track remained around x=1348 from about 3–6 s.
   Background filtering rejects static room objects rather than relying on colour.
2. An initial ROI starting at x=.24, then .15, clipped actual left-side ball
   movement. It was too aggressive: the earlier suggestion to exclude that entire
   area as a mirror was not justified. Full-width input recovered ball observations
   and left turns. The UI leaves full width selected by default; crop only genuine
   irrelevant regions. Cropping also changes detector scale, so higher coverage
   alone does not prove better event accuracy.
3. With cropped input, clip 2 flagged 10.42–11.49 s at about 74% of its leftward
   median speed. Sampled frame review at 1.13–1.90 and 10.44–11.50 showed boxes on
   the actual ball. The full-width run lost enough observations that it could no
   longer make that comparison. **The final output does not retain that flag.**
4. The final clip-3 output flags 21.68–23.37 s at about 70% of the rightward median.
   This is a measurement from its accepted track, not independently verified
   coaching feedback. No fatigue, control-loss, or technique diagnosis follows.

## Visual review and limits

Sampled frames across all three clips and closer sequences were inspected.
For clip 1, sequences around 3–4.3 s and 9.8–11.6 s reveal actual ball movement
outside the earlier crop; those gaps were not proof of losing control.
For clip 3, three-frame sequences around all seven initial candidate times
(23.67, 25.67, 27.60, 29.47, 31.24, 34.94, 40.01 s) showed geometric turn/reversal
contexts. This is a spot check, not an independent frame-by-frame reference or
an event-level precision/recall evaluation. The final wider-ROI left turn at
25.60 s shifts slightly from the cropped result. The 40.01 s event is near the
end of practice and may be a finishing ball adjustment rather than a full drill
turn. The app cannot determine intent.

Marker reach uses the observed ball edge, with a one-ball-diameter “near” band.
Boundary-obscured turns are unassessed. Full-width clip 3 produces three reached,
four near, zero clearly-short estimates. **Short-of-marker feedback is covered by
synthetic tests, not established by an independently labelled real shortfall.**
The marker coordinates themselves were placed approximately from imagery.

Main failures remain occlusion, camera-edge exits, cropped boxes, occasional
paddle/shoe false detections and missed turns. Long gaps split all evidence; no
speed is computed across them. Some possible hidden turns are linked for review,
but that heuristic is incomplete. The absence of a flag means insufficient or
non-triggering evidence, not that the attempt was perfect. Changed lighting,
moving cameras, reflections, other rooms, multiple players, depth motion and
mostly stationary balls are unverified. No automated coaching recommendation is
implemented. There is no accuracy percentage.

## Checks and reproduction

101 Python tests pass, including reversals versus small touches, irregular
timestamps, gap handling, reacquisition, marker reach/near/short/disabled states,
slow same-direction sections, equal-distance timing, hidden-turn review windows,
static-object rejection, and invalid setup without claiming the shared worker.
Nine existing frontend tests and TypeScript/Vite production build pass.
The HTTP upload/progress/result/playback path was exercised on all three clips;
final analysis was rerun directly through the same pipeline after widening the ROI.
Browser checks covered loading a MOV preview, rendering completed results,
selecting the slower section (seeks with lead-in and switches to 0.5×), and frame
stepping with a synchronized ball overlay and marker/pace guides. Automated
pointer tests for setup-canvas placement and browser download completion were
not performed; geometry validation is covered in Python.

To reproduce, with the existing dependencies and models installed:

```sh
.venv/bin/python scripts/validate_dribbling.py \
  ~/Downloads/side2side1.mov ~/Downloads/side2side2.mov ~/Downloads/side2side3.mov \
  --roi 0 .42 1 1 --markers .19 .835 --reach
```

Results and playback go to `.runtime/dribbling-validation/` by default.
The regular app remains `uvicorn juggling.api:app` with the existing setup in
README. Choose the new side-to-side page and review the area/markers per clip.


## Edge-return revision after player review

The player asked to count off-camera side reversals, identifying approximate
misses at 2.7, 7.5, 10, 14.5 and 19 seconds in clip 3. The counter now infers a
single turn when observed outward motion approaches an actual image edge and
observed inward motion returns from that same edge. It requires observed ball
boundary proximity and size continuity; disappearance in the middle alone is
not sufficient. Maximum observation absence is 6 seconds, maximum edge visit
10 seconds. Thresholds live in `DribbleConfig`; no clip event times are encoded.

The inferred event's `time` is the start of a replay window, not an estimated
contact instant. `time_interval` gives the full approach/return window. Its marker
reach is unassessed and its unseen path contributes no pace measurements.
Visible reversals suppress duplicates. Small paddle reacquisitions initially
produced extra edge returns on clips 1 and 2; requiring a plausible returning
ball diameter eliminated those specific duplicates. This is not a general proof
against detector errors or a claim that an inferred reversal was controlled.

| Clip | Previous visible turns | Added inferred turns | New estimated total | Timed sections (unchanged) |
|---|---:|---:|---:|---:|
| 1 | 2 | 4 | 6 | 5 |
| 2 | 1 | 6 | 7 | 3 |
| 3 | 7 | 8 | 15 | 9 |

Clip 3's added replay windows are 2.60–4.43, 6.30–8.60, 10.10–11.67,
13.63–17.37, 19.07–20.47, 32.57–33.70, 36.70–37.70 and 41.04–43.07 seconds.
The first five correspond to the player's approximate early reports (allowing
0.3 s around the reported timestamps). This is partial player validation, not
an independently verified full-clip total or exact event-time accuracy.
No fresh model inference was needed: all three saved timestamped tracks were
reanalysed using the revised rules. Original detector/pipeline runtimes remain
unchanged; `event_reanalysis_seconds` records the inexpensive new pass.
`edge-return-comparison.json` records the before/after totals and inferred windows.

The main UI now shows total turns and the visible/inferred split, merges inferred
returns into the ordinary turn list, and removes the unverified-window list.
Raw gaps and technical notes remain in a collapsed optional disclosure and JSON.
The broader UI redesign is deferred. 110 Python tests pass, including same-side
returns, no-return exits, opposite-edge reappearance, long absences, size-collapse
false returns, prediction-only returns, crop boundaries, visible/inferred
deduplication, and a regression for the player's five reported early intervals.
