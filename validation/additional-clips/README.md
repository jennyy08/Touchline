# Three additional clips — user totals and targeted diagnostics

The player supplied totals of **16, 29, and 21**, in filename order 12.26 PM, 12.28 PM, 12.29 PM, excluding the opening lift/pickup. These totals are accepted as the reference. No full manual recount was performed and no reference event times were invented. SHA-256 hashes bind each total to its file in `clip-N-reference.json`.

## Unchanged baseline

| Clip | User total | Automatic | Review candidates | Signed difference |
|---|---:|---:|---:|---:|
| 1 / 12.26 PM | 16 | 14 | 1 | −2 |
| 2 / 12.28 PM | 29 | 22 | 6 | −7 |
| 3 / 12.29 PM | 21 | 19 | 3 | −2 |

These are count differences, **not numbers of missed events**. In particular, clip 3 contains a verified extra automatic event at 11.068 seconds after the ball exits. A smaller difference can hide a worse event result. Precision/recall and matched-event counts are unavailable without timestamp labels.

All three ran with the same previously selected YOLO11s/640, 0.05 detector threshold, appearance matcher, pose model, and contact rules. Baseline files are retained as `clip-N-result.json`. Decoded frame counts are 329, 474, 350; last timestamps are 10.935, 15.768, 11.635 seconds. Container nominal counts (330, 485, 380) differ; processing uses decoded timestamps. Runtime was approximately 34.4, 53.1, and 34.2 seconds, including playback encoding. These are not controlled benchmarks.

## What targeted inspection revealed

Only openings, endings, flagged contacts, and selected tracking problems were inspected—not each touch in each clip.

- **Clip 1, about 3.50 s:** the detector selects the raised shoe while the ball is visibly higher. There is an observation gap immediately afterward. This is an identity-switch failure, not proof that juggling stopped.
- **Clip 1, 7.935 s:** the ball is visible by the extended foot, but pose landmarks are displaced and the candidate is flagged `contact_not_supported`. Increasing the proximity threshold blindly could count unrelated ball motion.
- **Clip 1, ending:** the ball exits left. Border-clipped detections seed a bad appearance template, which then follows clothing around 8.90–9.10 s. The baseline eventually marks loss; it does not count a later contact in this interval.
- **Clip 2, 2.568 s:** the `possible_floor_contact` candidate actually tracks a shoe while the ball is above it. It is not evidence of a real floor bounce.
- **Clip 2, 8.968, 9.602, 10.168, 14.135 s:** `possible_hand_contact` flags occur with raised feet/ball and nearby projected wrist landmarks. These frames expose the limitations of 2D wrist proximity; they are not certified hand contacts. The 15.602 s `contact_not_supported` candidate has a visibly extended foot and displaced ankle landmarks.
- **Clip 2, ending:** the ball is still visible near the right edge in the final decoded frame. There is no observed sustained exit to label as tracking loss before the video ends.
- **Clip 3:** more of both shoes and the floor are visible. Nonetheless, candidates at 3.368 and 3.835 s have poor ankle support and 10.202 s triggers the wrist-proximity rule. Clearer framing alone does not fix landmark or classification errors.
- **Clip 3, ending:** after the final visible kick, top-clipped detections seed a template of clothing/background. An appearance-derived reversal at **11.068 s** is counted even though the ball has left the frame. This extra count is directly verified from nearby frames.

`clip-N-ending.jpg` shows sampled opening/ending context. `clip-N-diagnostics.jpg` shows the targeted baseline errors, with yellow tracking boxes and blue pose points. A displayed box is algorithm output, not a correct annotation. The red horizontal line in clip 2 is the approximate floor estimate.

## Narrow correction

The appearance matcher now clears its template when an accepted box is within 5% of its mean diameter (minimum two working-resolution pixels) of an image edge. It requires a new interior detector observation before appearance matching resumes. It still displays detector observations at the edge; it does not invent an “out of frame” certainty or infer a touch through missing evidence. This prevents a truncated ball/background patch from becoming the next matching template.

This is an evidence-based correction for the inspected identity drift, not a threshold adjustment to reach the supplied totals. Results are saved separately in `clip-N-edge-guard-result.json`; `clip-0-edge-guard-result.json` is the original clip regression run. The current matcher retains other risks: detector shoe false positives, interior template drift, and pose ambiguity. Genuine low foot contacts versus floor bounces still need further validation.

Run `python scripts/compare_clip_totals.py validation/additional-clips` to rebuild `total-comparison.json`. It deliberately leaves event precision/recall null. Raw videos remain outside version control; generated silent playbacks are in `.runtime/additional-N/` and `.runtime/edge-guard-N/`.

## Rerun outcome and tradeoff

| Clip | User total | Before safeguard | Current automatic | Current review candidates |
|---|---:|---:|---:|---:|
| 1 | 16 | 14 | 14 | 1 |
| 2 | 29 | 22 | 22 | 6 |
| 3 | 21 | 19 | 18 | 3 |
| Original clip | 26 | 24 | 23 | 1 |

For the new clips, the counted event timestamps are unchanged except removal of clip 3's false event at frame 332 / 11.068 s. Clip 1 begins missing-observation status at 8.902 s instead of 9.135 s; clip 3 at 11.002 s instead of 11.235 s. Motion predictions last at most 0.15 seconds before loss. The safeguard also causes some extra gaps near boundaries; observed frames fall from 267/467/336 to 259/454/323. Fewer observed frames are not automatically worse when earlier observations were wrong, but the original clip demonstrates a real cost.

**Regression:** the original clip loses its real contact at 10.50 s along the right image boundary. The ball remains partly visible, but the guard disables appearance support and the contact has no candidate. Against the existing timestamp reference, the current original-clip result has 23 matched counted events, zero unmatched counted events, and three misses. See `original-edge-guard-evaluation.json`. The conservative default is retained because it prevents the verified clothing-derived count, with this limitation explicitly recorded. Distinguishing a ball moving along an edge from one exiting across it is a useful next improvement; simply extending tracking duration would reintroduce the failure.

The new clips were unseen baseline tests before this safeguard; once used to design it, they became development/regression examples, not an independent final accuracy test. User totals remain untouched. Counts alone do not support event-accuracy claims.

**Verification:** 30 Python tests pass, including two new tests for clearing edge templates and reacquisition. All four videos were reprocessed through the full pipeline after the change. No frontend code changed in this iteration. Current local review jobs are `additional-1`, `additional-2`, and `additional-3`; the standard app can also process fresh uploads with the new safeguard. As before, server jobs are temporary. The local session helper `.runtime/serve_clip_review.py` restores these three generated runs while their `.runtime/edge-guard-N/` directories remain available.
