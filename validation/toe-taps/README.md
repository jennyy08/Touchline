# Toe-tap baseline — 2026-10-23

## Method and actual checks

Three supplied files `~/Downloads/taps1.mov`, `taps2.mov`, `taps3.mov` were decoded
and processed locally with YOLO11s (640 CPU), YOLO11n-pose and RTMPose Halpe-26.
Existing model files and pinned dependencies are sufficient. Raw observations and
browser MP4s are in ignored `.runtime/toe-taps/taps{1,2,3}`. The initial extraction
used the shared pipeline with audio and appearance disabled; cached samples were
then passed through the new pure toe-tap counter, avoiding repeated inference.
The upload API calls the same counter through `drill=toe_taps`.

Sampled all three clips at 1, 3, 5, 7 seconds. These show low-camera views,
partly cropped legs, a moving ball and shoe overlap. Inspected 0.4–5.1 seconds of
taps1 in sequences spaced 0.1 seconds apart. The partial reference records 13
approximate contacts in 0.8–5.2 seconds; everything outside this interval is
explicitly unlabeled. Contact timing is coarse and sometimes occluded. This is
not an independently verified full-clip reference and is not an accuracy claim.

At a **±0.15 s exploratory matching tolerance** (not the earlier juggling
protocol's ±0.10 s), the broad-zone comparison matches 3/13, misses 10, with 0
unmatched counted events in the reviewed interval. The revised zone matches
10/13, misses 3, with 1 unmatched counted event. See the JSON comparisons for
individual times. Both use the final multi-frame requirement; the broad-zone
ablation uses the earlier zone/debounce thresholds. These comparisons use the
same development interval that informed the change, not held-out evaluation.

## What changed, and what remains wrong

A broad top zone extended down near the ball center and its release hysteresis
included the resting foot beside the ball. That prevented rearming, especially
for the far foot. The revised lower limit is -0.25 ball diameters relative to the
ball center, with a 0.08-diameter release margin. This recovers more cycles.
Two in-zone frames reject isolated landmark glitches; candidates less than 0.22s
apart are review-only rather than claiming two taps. No alternating pattern or
expected total is used to fill missing events.

Foot landmarks sometimes swap sides or follow the other shoe when the shoes
overlap. Anatomical left/right labels are model estimates. The counter still
misses contacts and can mistake a shoe passing in front of the ball for a tap.
Its event time is entry into the proximity zone, not a measured impact instant.
Initial on-ball poses, incomplete final cycles, long holds, and cycles interrupted
by missing ball/toe evidence are deliberately uncounted. No foot/balance rating,
fatigue diagnosis or confidence percentage is shown.

## Tests and unverified cases

119 backend tests and 14 frontend tests pass, including toe-tap cycle counting,
held/initial feet, predicted ball exclusion, missing landmarks, long gaps,
uncompleted cycles, floor/side positions, isolated glitches, repeated same-foot
cycles, irregular timestamps, simultaneous-foot ambiguity, and upload dispatch.
These synthetic tests do not establish real-footage accuracy. No live toe taps,
new camera angles, children, varied footwear, or full-clip event-level accuracy
have been verified. Use the correction editor to add/remove events and export an
annotation JSON; automatic and manually edited results remain separate.

## Saved clip results

| Clip | Estimated taps | Review candidates | Decoded / container frames | Inference + playback runtime |
| --- | ---: | ---: | ---: | ---: |
| taps1 | 23 | 4 | 423 / 423 | 72.0 s |
| taps2 | 13 | 6 | 414 / 425 | 71.2 s |
| taps3 | 16 | 0 | 399 / 407 | 74.1 s |

These are estimates, not supplied ground truth. Clip 3 contains 39 lost and 16
predicted ball samples. Clip 2 has six predicted samples. The decoder/container
frame-count discrepancies are reported in the result warnings; no missing
frames are invented. Saved sample replay and correction add/remove were checked
in the local browser. `results.json` preserves configuration and coverage.

A fresh taps1 upload through the browser completed through the new API path and
returned the same 23 estimated taps / 4 review candidates. Seeking and frame
alignment were checked on that result. Correction export JSON was round-tripped
through the import UI on taps2 (13 editable taps retained). The embedded browser
did not emit a download confirmation, so export also provides copyable JSON;
file-save behavior in other browsers is unverified.
