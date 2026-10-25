# Revision 4: shoe-motion and detail-crop evidence

The user reports **31 taps in taps2**, excluding the opening held pose and
including the final control touch. `taps2-reference.json` is an importable,
approximate visual event reference from 0.1s frame sequences, informed by that
total. It is not blind or frame-accurate annotation. taps1 retains its previous
33-event reference from revision 2. Compare events, not just totals.

## Retained approach

- Preserve the previous counter as primary evidence.
- Track local shoe image features forwards/backwards, requiring at least four
  consistent feature displacements. Use their motion for association and a
  maximum 0.15s bridge from a detector anchor. Do not extrapolate indefinitely.
- Run the existing RTMPose foot model on a lower-body crop as a second view.
- Count alternate candidates only when separated from existing events by
  0.22s. A nearby candidate after a ball gap is review-only rather than counted.
- Preserve raw and alternate observations and label each event's source.
  Dashed teal outlines show motion evidence; amber shows the detail crop.
- Missing/predicted ball positions remain ineligible in every view. No forced
  alternation, cadence filling, clip times, or target counts enter the code.

## Rejected alternatives

- Nearest-position temporal reassignment alone: taps1 31 (30 matches + 1 extra),
  taps2 26. Position alone cannot disambiguate overlap.
- Replacing all primary observations with image-motion output: loses real
  contacts the primary method retains. Use only supplementary candidates.
- Same-model ankles with original full-body crop: taps1 31, taps2 27.
- Tighter full-person padding: taps1 26, taps2 25.
- Lower-body crop alone: taps1 19, taps2 23 (including an extra at 2.733s).
- Ball-only detector crops around recent tracks recovered no accepted missing
  detections in taps1 or taps2. At 2.9s the crop detects a much narrower partial
  ball; it fails size continuity. Do not relax this gate just to reach 31.

## Remaining limits

Development results do not establish accuracy on new recordings. Two views
can share errors, and adding alternate candidates can introduce false counts.
Very fast separate contacts can be merged. Optical flow can follow background
or ball edges; the gates reduce rather than eliminate that risk.

The early taps2 candidate around 1.87s is delayed after a ball gap and close to
the next contact. It needs manual review. The approximately 2.95s contact stays
unresolved with fragmented foot observations and ball occlusion. Neither is
silently added to reach the user total. The correct final control is included.

Full pipeline runtimes and event comparisons are in `summary.json` and the
per-clip comparison files. ±0.15s is the exploratory tolerance for these coarse
labels; ±0.10s results are also saved to expose timing sensitivity. taps3 has
no user-verified event reference and cannot be treated as an accuracy test.

Reproduce the pipeline with:

```sh
PYTHONPATH=. .venv/bin/python scripts/analyze_toe_taps.py /path/to/taps2.mov /tmp/taps2-result
```

No new dependencies or model downloads. The extra foot-model pass and image
motion increase runtime. Results from earlier jobs are preserved, not rewritten.

## Full pipeline results

| Clip | Previous count | Revised count | Review candidates | Matches at ±0.15s | Runtime |
|---|---:|---:|---:|---:|---:|
| taps1 | 33 | 33 | 0 | 33 / 33 | 116.5s |
| taps2 | 27 | 29 | 1 | 29 / 31 | 121.6s |
| taps3 | 19 | 21 | 1 | Unverified | 115.9s |

No extras are found for taps1/taps2 at ±0.15s. At ±0.10s, taps1 has 31 matches
and two timing mismatches; taps2 has 27 matches and two timing mismatches in
addition to the two remaining missing contacts. This sensitivity matters:
the labels are coarse and the automatic event is zone entry, not exact impact.

135 Python tests and 17 frontend tests pass; the production frontend build
passes. Focused new tests cover measured translation, textureless-image
failure, track expiry, resolution changes, independent crop observations,
multiview deduplication, predicted-ball exclusion, and review-only reacquisition.

Browser verification: taps-v4-2 displays 29 counted events and one review
candidate. Event seeking and stepping reached frame 183 at 6.100s with visible
video and the teal supporting shoe outline aligned to that frame.
