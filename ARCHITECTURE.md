# How the prototype works

```text
MOV/MP4 → timestamped upright frames → ball detector + appearance → Kalman association
                         │                                  │
                         └→ pose landmarks ────────────────┤
                                                          ↓
                                  observed trajectory + contact rules
                                                          ↓
                          result.json + browser-safe playback.mp4
                                                          ↓
                          video/canvas UI + independent review JSON
```

## Boundaries worth keeping

- **`juggling/video.py`** owns decoding, orientation, presentation timestamps, and playback encoding. A `Frame` has an index, time in seconds, and BGR image. This is the future webcam boundary, although the current offline counter also needs subsequent frames to confirm a reversal.
- **`detection.py` and `pose.py`** wrap pretrained models. Both return coordinates in the original upright image; Ultralytics handles resizing/letterboxing internally. `pose.py` takes the largest YOLO person box and, if `foot_model` is set, adds heel/big-toe/small-toe points from **`feet.py`** (RTMPose-x Halpe-26 via onnxruntime: affine person crop → network → SimCC argmax, written out explicitly so it can be read and modified). Ball scores only filter proposals and are not estimates of touch accuracy.
- **`appearance.py`** compares a grayscale ball template against a bounded local search at three scales. It supplies image-backed observations when detection drops out, and can repair an oversized detector box when the appearance match agrees spatially. Templates expire without a detector anchor after 0.25 seconds; a long frame gap or weak correlation prevents a match. At an edge, outward motion clears the template; mainly parallel motion can retain it. This uses timestamp-based velocity normal to each nearby boundary, so an edge touch is not automatically discarded. Missing motion history or a low-texture patch cannot establish a template. This is image evidence, not interpolation.
- **`tracking.py`** chooses a consistent ball across detections. Its constant-velocity Kalman state is `[x, y, vx, vy]`. Center distance and box-size continuity reject implausible associations. Before appearance matching, a detector box whose mean size abruptly drops below 75% of the previous observation is removed; this lets the matcher or another ball detection compete instead of immediately switching to a shoe. Size history expires after the prediction horizon. Observed samples keep raw detector centers to avoid smoothing away sharp contacts; the Kalman estimate supports association and brief dashed predictions only.
- **`counting.py`** is pure numerical logic over samples. It estimates the floor line from still (planted) heels and toes, falling back to still ankles plus an ankle-height offset, examines observed vertical velocity before/after a local bottom of the ball's flight, checks proximity to leg landmarks, and debounces candidates. A flight apex reverses in the opposite direction and is not a touch. Missing contact/floor evidence produces a review candidate rather than an invented probability.
  - *Leg support* is the nearest of detected foot outline (heel–toe segments), ankle, knee, and knee–hip (thigh) segment, taken over the contact frame and its adjacent observed frames (each compared with its own ball position), because landmarks jitter or vanish on a fast kicking leg. If a foot supports the contact it wins the label, since a ball on a raised foot also overlaps the knee in a 2D front view.
  - *Fallback estimated foot*, used only for a side without heel/toe points: a horizontal segment either side of the ankle, half-length `foot_length_shin_ratio` × knee–ankle length. It only applies between knee height and just below the ankle.
  - *Wrists are ignored.* A projected arm near the ball neither creates nor blocks a touch.
  - *Top exits:* if the only outgoing observation is a box cut off by the top image edge and the ball then leaves view, outgoing motion is measured from the box's bottom edge (a clipped box's center is biased downward). The event is tagged `evidence: ["top_exit"]`. Predictions are still never evidence.
  - *Stops:* `find_stops` reports intervals where the observed ball stays within `stop_radius_diameters` for at least `stop_seconds` (e.g. a catch). Stops are informational and never change the count.
  - *Audio:* **`audio.py`** only reports impact onsets (spectral flux). `add_audio_evidence` decides what they mean: sound may confirm a leg-supported gap flag (never a floor flag) or add a `heard_ball_out_of_view` touch when a strong thump fits the clip's rhythm, the ball is not visibly on the floor, and it comes back into view. Results report `seen_count` and `heard_count` separately; the strength gate was chosen on the development clips.
  - Knee/thigh touches still count, but no real knee/thigh, catch, or hand-contact clip has been tested; the knee/thigh labels are only synthetic-tested, and left/right foot labels were not individually verified.
- **`pipeline.py`** coordinates these modules and writes JSON/MP4. **`api.py`** adapts it to a single-worker local HTTP job with progress. **`cli.py`** runs the same pipeline without HTTP.
- **`frontend/src/player.ts`** handles timestamp lookup and overlays. **`review.ts`** validates independent annotations. **`layout.html`** owns the provisional page structure; **`main.ts`** wires interactions; **`style.css`** owns the theme. No analysis rules live in the frontend.

## Time matters more than frame rate

The MOV reports an average rate near 29.79 fps, but nominal random-seek frame indexes drift from decoded frames. Derivatives use presentation timestamps. Browser stepping seeks to the next saved timestamp, and overlays select the latest presented frame at or before the playhead. The transcoded MP4 retains relative presentation timestamps with a 1/90,000-second time base.

Coordinates use an origin at the top-left: increasing `y` is downward. A foot touch often has positive incoming vertical velocity and negative outgoing velocity. Thresholds are expressed in seconds and ball diameters instead of fixed pixels. A short sampling window balances jitter suppression against separating nearby touches.

## What the interfaces mean

`POST /api/jobs` accepts multipart `file`, returns `{id}` with HTTP 202, and rejects concurrent jobs with 409. `GET /api/jobs/{id}` returns stage (`queued`, `loading_models`, `analyzing`, `counting`, `complete`, or `error`), processed frames, expected total, and useful error text. `GET /api/jobs/{id}/result` returns the result after completion; `/video` serves MP4 with byte-range support for seeking. `/api/health` reports basic availability and whether default weights are present.

Results use `schema_version: 1`. Samples contain frame/time, status (`observed`, `predicted`, `lost`), ball box/center/diameter, segment ID, and available named landmarks. Observed samples carry `source: detector | appearance`; events record their `evidence_sources`. Correlation scores are internal similarity gates, not touch-confidence percentages. A new segment starts after the prediction horizon expires; the counter cannot bridge segments. Events contain time/frame, `counted` or `review`, a reason, approximate body part, and incoming/outgoing velocity evidence. `estimated_count` counts only `counted` events.

Reviews use `schema_version: 1`, `video_sha256`, and events with unique `id`, seconds `time`, `label`, and `note`. Optional `uncertain_intervals` preserve gaps in reference knowledge. The UI supports labels `touch`, `floor`, `pickup`, `hand`, and `uncertain`. LocalStorage stores review edits, while JSON export makes them portable. Never replace automatic events with manual labels when reporting algorithm performance.

## Useful learning exercises

1. **Read `config.py`, then plot a contact.** Inspect the JSON's observed `center[1]` versus time around a touch. Compare it with an apex and with an occlusion.
2. **Understand a tracker failure.** The constant-velocity model lags during fast acceleration. Tight gates drop real detections; loose gates can switch to a shoe. Compare observed boxes, predictions, and segment IDs. Teal boxes show appearance matches, green boxes show detector hits, and dashed amber boxes are motion-only predictions.
3. **Improve contact evidence.** Compare a contact with `foot_model=""` (ankle-only COCO landmarks) and with heel/toe points; `validation/foot-revision/` shows where they differ. The floor estimate is approximate and perspective-dependent. Test improved foot geometry against explicit floor-bounce clips before claiming it solves bounces.
4. **Evaluate on new footage.** Label it before tuning, compare timestamps, and hold out clips. The supplied clip is a development example, not a benchmark proving general accuracy.
5. **Change the design independently.** Adjust CSS variables, section layout in `main.ts`, or review interactions without changing any Python code.

No live camera adapter, custom training pipeline, multi-player identity logic, or biomechanical coaching is implemented. Head/torso touches and contacts that do not form a clear observed vertical reversal remain outside this baseline's reliable behavior.

Tracking experiment: `scripts/inspect_frames.py` creates timestamp-checked evidence sheets from a video and result JSON. Current before/after results are in `validation/tracking-revision/README.md`. The three new clips have user-supplied totals, not complete reference timestamps.
