# Tracking revision: edges and shoe identity switches

This revision changes ball tracking only. Detection weights, pose inference, touch classification, floor rules, and debounce thresholds stay unchanged. User totals remain 26 for the original clip and 16/29/21 for the three additional clips. The additional videos were not manually recounted.

## Changes

- **Direction-aware edges:** compute timestamp-based velocity from consecutive observed box centers, expressed in ball diameters per second. Within a 5%-diameter edge margin, clear the appearance template when outward velocity exceeds both 0.5 diameters/s and 20% of total velocity. Mostly parallel movement can retain image evidence. Edge observations without recent motion history cannot seed a template. Weak/invalid patches clear stale templates.
- **Size continuity before appearance matching:** reject detector proposals smaller than 75% of the previous observed mean box dimension while that track is recent. Another detector proposal or an image match can then recover the ball. The same size gate applies in Kalman association; after more than 0.15 s without observations, reacquisition is free to establish a new size.
- **Unchanged evidence standard:** predicted points remain display/association aids, never standalone touch evidence. These gates do not assign touch-confidence percentages or certify an exit direction.

No new models or dependencies. Tunable values are in `juggling/config.py`; the algorithms remain in `appearance.py` and `tracking.py`, with one filtering call in `pipeline.py`.

## Before and after

“Before” is the previous conservative edge safeguard. Earlier pre-safeguard results remain in `validation/additional-clips/`.

| Clip | Reference total | Before | Revised automatic | Review candidates |
|---|---:|---:|---:|---:|
| Original | 26 | 23 | 24 | 1 |
| 1 / 12.26 PM | 16 | 14 | 15 | 1 |
| 2 / 12.28 PM | 29 | 22 | 24 | 5 |
| 3 / 12.29 PM | 21 | 18 | 18 | 3 |

Only the original has a complete approximate timestamp reference: 24 one-to-one matches within ±0.10 s, zero unmatched counted events, two misses. This does not establish zero false counts on the other three clips. Their totals alone cannot establish event precision/recall or exact misses.

## Changes inspected in footage

- **Original, 10.50 s / frame 315:** recovered the real right-edge touch that the blanket safeguard removed. Consecutive images in `original-edge.jpg` show the box following the ball while it moves along the boundary.
- **Clip 1, 3.40 s / frame 102:** recovered a contact by keeping the detector on the ball instead of switching to the shoe around frame 105. `clip-1-repaired.jpg` also shows predicted/lost status after the left exit, rather than clothing marked as observed. The remaining 7.935 s candidate is still flagged for poor leg proximity.
- **Clip 2, 2.068 and 2.602 s / frames 62 and 78:** two additional counted contacts, inspected in `clip-2-recovered.jpg`. The former shoe-based floor warning at frame 77 is replaced by ball evidence near frame 78. Four wrist-proximity flags and one leg-support flag remain uncounted.
- **Clip 3:** the total stays 18, but events move from frames 221/266/279/296 to 220/263/278/292. Some shifts are one-frame timing changes. The former shoe trajectory at frame 296 is replaced by the ball trajectory around frame 292; selected evidence is in `clip-3-repaired.jpg` and `clip-3-events.jpg` (the latter shows the rejected intermediate version). The clothing-derived event at 11.068 s remains absent. Three classification flags remain.

These are targeted checks, not full new reference annotations. A more accurate total was not the sole selection criterion.

## Experiments and limits

An initial direction threshold of 40% retained diagonal-exit clothing drift in clip 1; 20% rejected that observed failure while retaining the original edge touch. A 65% size threshold still accepted the shoe around clip 3 frame 294 and returned 17 counted events. The 75% gate recovered ball evidence there. Intermediate `clip-N-size065.json` files preserve replay outputs. Their `runtime_seconds` belongs to the initial full inference run; `replay_seconds` is separately measured and excludes inference/encoding.

Detector/pose outputs were cached locally for controlled tracking experiments, replaying **original decoded pixels**, not compressed playback. The selected version is then run through the complete pipeline for all four clips; final `clip-N-result.json` contains the actual configuration, observations, candidates, gaps and runtime. Original event comparison is `original-evaluation.json`.

The gates are heuristics. A ball rapidly moving away from the camera can shrink legitimately; a similar-sized shoe can still pass; cropped box centers can misrepresent direction. Motion predictions can visibly lag or point at clothing after an exit, but remain explicitly predicted and cannot create a count by themselves. These four videos are now development/regression examples, not an independent final accuracy test. Better pose/contact classification is still needed for the remaining flagged touches.

35 Python tests pass, including direction along an edge versus outward/diagonal exit, low-texture invalidation, abrupt size collapse, moderate size changes, and reacquisition after loss. Existing counting/API/video tests also pass. No frontend changes in this revision.

Final full-run times on this Mac were 48.3 / 31.1 / 49.6 / 40.3 seconds (original / clips 1–3), including inference and playback encoding. These are single-run observations, not speed benchmarks. `comparison.json` summarizes the final outputs. Local app result and HTTP byte-range playback endpoints were verified for all four saved jobs (`tracking-0` through `tracking-3`). The app was restarted with the revised backend. These temporary jobs can be restored locally with `.venv/bin/python .runtime/serve_tracking_review.py` while the generated runtime directories exist; ordinary setup/upload commands are unchanged.
