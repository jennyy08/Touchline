# Revision 5: resolve the two remaining taps2 contacts

User rule: taps2 has 31 taps, excluding the opening held pose and including
the final control touch. No count or clip-specific timestamp enters the code.

## Retained changes

1. **Short occlusion retains only off-ball context.** A previously observed
   outside state can survive at most 0.20s without a ball observation. On
   return, the ball must be within one previous diameter and its diameter
   within a 0.75–1/0.75 ratio. Partial/active contacts, confirmation duration,
   and geometry history are discarded. Predicted frames never provide contact
   evidence. Two fresh toe/ball observations after return are still required.
   This yields an event at 1.800s, observed through 1.900s, with departure at
   1.933s—separate from the next event at 2.067s.
2. **Reject isolated toe jumps with one-frame lookahead.** Both neighbouring
   frames must be observed, in the same ball segment, and within 0.08s. Their
   normalized toe positions must agree within 0.35 ball diameters, while the
   middle position differs from both by more than one diameter. Only the
   middle toe observations are removed. No points are interpolated or invented.
   At 3.000s this removes a floor/other-shoe jump, preserving actual in-zone
   observations at 2.967s and 3.033s plus departure at 3.133s.
3. Contact records now retain the final observed in-zone timestamp and an
   observed departure timestamp, when available. The event-button tooltip
   exposes this evidence interval. These are zone observations, not exact
   physical-impact bounds. Missing departure stays null.

Raw samples remain unchanged for inspection. `rejected_by_view` records every
removed observation. Thresholds live in `ToeTapConfig`; preprocessing is the
small pure function in `juggling/toe_observations.py`.

## What did not work

The old early motion candidate extends continuously from 1.867s through 2.300s.
Its interval overlaps the next tap, so relaxing debounce alone was rejected.
The retained approach recovers an independent raw-pose contact after the gap.

Reverse-time optical-flow trials used bounded 30-frame blocks with six-frame
lookahead overlap. Raw-pose backward tracking returned 24 events on taps2,
with 22 matches and two extras at ±0.15s. Backward tracking from detail-crop
poses returned 21 events, with 19 matches and two extras. Neither recovered
both missing contacts. They are not in the production pipeline. The retained
one-frame lookahead is simpler and adds negligible counter cost.

## Event-level comparison

References are the same approximate, non-blind development annotations in
revision 2 (taps1) and revision 4 (taps2). They are not independent accuracy
measurements. Samples are unchanged, allowing direct before/after comparison.

| Clip | Previous | Revised | Matches at ±0.15s | Misses / extras |
|---|---:|---:|---:|---:|
| taps1 | 33 | 33 | 33 / 33 | 0 / 0 |
| taps2 | 29 | 31 | 31 / 31 | 0 / 0 |
| taps3 | 21 | 22 | Not labeled | Unverified |

At ±0.10s, taps1 has 31 matches and taps2 has 29; each has two existing timing
mismatches. These did not improve, and the wider tolerance must not be hidden.
The corrected taps2 events match even at the narrower tolerance. taps3's added
contact has not been manually verified; its count is not an accuracy result.

Possible failures: a real very fast toe excursion may look like an isolated
jump; a short occlusion may conceal additional activity; similarly positioned
objects may pass the ball-reacquisition gate. Both clips were used to develop
these rules. Testing new videos remains necessary.

## Validation and replay

143 Python tests and 17 frontend tests pass, and the frontend builds. New tests
cover short/long ball gaps, distant and resized reacquisition, held-pose
non-duplication, discarding partial evidence, isolated jumps, consistent motion,
missing neighbours, segment changes, and preservation of raw samples.

Cached observation reruns are in `.runtime/toe-taps/revision-5/taps-v5-*`.
Their runtime field retains the original inference runtime; separate
`counter_runtime_seconds` values measure only recounting (about 0.01s).
A fresh full-pipeline run of taps2 is also used to verify the production path.
Old jobs stay available separately; new uploads use revision 5 after restart.

Fresh full-pipeline verification: taps2 returned 31 with exactly the same event
records as the cached-observation recount. Runtime: 107.8s.
The fresh result is served as `taps-v5-2`; its inference runtime is measured.

Browser check: the revised replay shows 31 estimated taps and no review
candidates. The 2.97s event seeks correctly and its tooltip reports observed
evidence through 3.03s and departure at 3.13s. Video reaches readyState 4.
