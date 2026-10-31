# Revision 7: separate supported alternating contacts

## Finding and change

The 6.967-second contact in taps3 was detected, but the 0.22-second grouping
window merged it with the next contact at 7.167 seconds. The earlier contact
has observed support through 7.033 and departure at 7.133. Frame inspection
around 6.8–7.3 confirms two alternating contacts, although automatic entry
labels are approximate rather than exact physical contact times.

The counter now keeps nearby opposite-foot contacts separate only when both
are sustained confirmations, the first has an observed departure before the
second entry, and intervening ball samples remain observed. Overlapping IDs
still merge. Same-foot interruption handling from revision 6 remains intact.
No hard-coded timestamps or target counts are used.

An initial departure-only version introduced an extra event on taps2 around
0.8 seconds. Requiring sustained evidence for both contacts removed that
regression. This remains development-set tuning, not a general accuracy claim.

## Saved-observation regression checks

| Clip | Revision 6 | Revision 7 | Matches at ±0.15 seconds |
| --- | ---: | ---: | --- |
| taps1 | 33 | 33 | 33 before and after |
| taps2 | 31 | 31 | 31 before and after |
| taps3 | 21 + 1 review | 22 | No complete reference |

At ±0.10 seconds, taps1 stays at 32 matches and taps2 at 29. References have
approximate visual times. The recovered taps3 event is 6.967 seconds; there
remain poorly observed contacts near the left boundary. No full actual total
is claimed. JSON comparisons retain before/after events and errors.

## Detection reproducibility and rejected experiment

The earlier differing runs share exact source checksum, timestamps and raw
foot landmarks, but 367 ball boxes differ. Current repeated first-frame model
loads return identical detections. A complete repeat also reproduced all
399 frames of the last fresh run exactly, including ball, pose, alternate
views and events. Thus an ongoing random fluctuation is not established.
The old runs lack model/runtime fingerprints, so their historical discrepancy
cannot be attributed confidently to one cause.

New pipeline results record model file SHA-256, package versions and selected
Torch runtime settings under `inference_provenance`. No machine paths or
arbitrary environment variables are recorded. `scripts/compare_inference.py`
compares frame observations separately from counter outputs and rejects
mismatched videos/timestamps. Agreement is not an accuracy measure.

A mirrored-image pose experiment on 5.8–8.0 seconds did not recover earlier
contact evidence; it still proposed the delayed 6.967-second contact. It was
not added to production, avoiding another model pass per frame.

153 Python tests pass, including separate opposite-foot contacts, overlapping
ID flicker, differing ball observations, input mismatch and unknown provenance.
Model inference and thresholds are unchanged. The recovered event comes from
correctly grouping existing evidence, not retraining the model.

Fresh revision-7 pipeline: 22 taps, 125.8s. Observations identical across the two fingerprinted runs: True; fingerprints identical: True. The event difference is the intended counter change.
