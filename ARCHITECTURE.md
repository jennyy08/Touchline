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

- **`juggling/video.py`** owns decoding, orientation, presentation timestamps, and playback encoding. A `Frame` has an index, time in seconds, and BGR image. The webcam adapter supplies the same timestamp/image concept, and both counting paths need subsequent observations to confirm a reversal.
- **`detection.py` and `pose.py`** wrap pretrained models. Both return coordinates in the original upright image; Ultralytics handles resizing/letterboxing internally. `pose.py` takes the largest YOLO person box and, if `foot_model` is set, adds heel/big-toe/small-toe points from **`feet.py`** (RTMPose-x Halpe-26 via onnxruntime: affine person crop → network → SimCC argmax, written out explicitly so it can be read and modified). Ball scores only filter proposals and are not estimates of touch accuracy.
- **`appearance.py`** compares a grayscale ball template against a bounded local search at three scales. It supplies image-backed observations when detection drops out, and can repair an oversized detector box when the appearance match agrees spatially. Templates expire without a detector anchor after 0.25 seconds; a long frame gap or weak correlation prevents a match. At an edge, outward motion clears the template; mainly parallel motion can retain it. This uses timestamp-based velocity normal to each nearby boundary, so an edge touch is not automatically discarded. Missing motion history or a low-texture patch cannot establish a template. This is image evidence, not interpolation.
- **`tracking.py`** chooses a consistent ball across detections. Its constant-velocity Kalman state is `[x, y, vx, vy]`. Center distance and box-size continuity reject implausible associations. Before appearance matching, a detector box whose mean size abruptly drops below 75% of the previous observation is removed; this lets the matcher or another ball detection compete instead of immediately switching to a shoe. Size history expires after the prediction horizon. Observed samples keep raw detector centers to avoid smoothing away sharp contacts; the Kalman estimate supports association and brief dashed predictions only.
- **`counting.py`** is pure numerical logic over samples. It uses the causal counter in `streaming.py`, which estimates a rolling floor line from still (planted) heels and toes already received, falling back to still ankles plus an ankle-height offset, examines observed vertical velocity before/after a local bottom of the ball's flight, checks proximity to leg landmarks, and debounces candidates. A flight apex reverses in the opposite direction and is not a touch. Missing contact/floor evidence produces a review candidate rather than an invented probability.
  - *Leg support* is the nearest of detected foot outline (heel–toe segments), ankle, knee, and knee–hip (thigh) segment, taken over the contact frame and neighboring observed frames within 0.075 seconds (each compared with its own ball position), because landmarks jitter or vanish on a fast kicking leg. If a foot supports the contact it wins the label, since a ball on a raised foot also overlaps the knee in a 2D front view.
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

No live microphone analysis, session recording, custom training pipeline, multi-player identity logic, or biomechanical coaching is implemented. Head/torso touches and contacts that do not form a clear observed vertical reversal remain outside this baseline's reliable behavior.

Tracking experiment: `scripts/inspect_frames.py` creates timestamp-checked evidence sheets from a video and result JSON. Current before/after results are in `validation/tracking-revision/README.md`. The three new clips have user-supplied totals, not complete reference timestamps.

## Live preparation benchmarks

`juggling/live_settings.py` contains two small experimental components: `FrameGate`
selects frames using presentation time, and `FootSchedule` decides whether to run
the detailed heel/toe model using current/past observed descent near the legs plus
periodic floor samples. Neither reads touch labels or future frames. Missing foot
landmarks stay missing rather than being copied from an older frame.

`PoseDetector.detect_body()` returns body landmarks and the chosen person box
without running RTMPose. Existing upload callers still use `detect()`, which
combines both models as before. This boundary lets a later live adapter schedule
feet independently without changing detector coordinates or counting rules.

`scripts/benchmark_live.py` caches measured inference outputs, then replays the
same tracking/counting logic for each sampling and foot schedule. Its service-time
estimates are followed by `scripts/validate_live_profile.py`, which runs one
selected profile directly in a fresh process. The [benchmark report](validation/live-revision/README.md)
keeps video-only counts separate from offline audio-assisted results. These
scripts recorded the pre-streaming benchmark. The visual counter is now causal;
offline audio still uses future information. Browser camera latency remains unmeasured.

## Live data flow

`frontend/src/live.ts` requests camera video only after Start. It downsizes each
frame to at most 640 pixels on its longest edge, encodes JPEG at quality 0.85, and
sends an eight-byte little-endian timestamp (seconds) followed by the JPEG. Only
one frame is in flight: the next capture follows the previous reply. Slow
inference drops old camera frames rather than building a stale queue.

`live_api.py` owns the `/api/live` WebSocket and shares the upload worker lock.
It checks localhost Host/same browser Origin, message limits, dimensions and
increasing timestamps. This is localhost-only without authentication. Disconnect
or failure releases the session. `live.py` owns per-session models, tracker,
appearance bridge, optional foot schedule and `StreamingCounter`; none of these
are shared between players/sessions. The default foot schedule is off. `near`
and `all` remain explicit protocol/benchmark options; the measured near-foot
live experiment performed poorly, so it is not exposed as a recommended UI mode.

`streaming.py` waits the outgoing velocity window, uses five seconds of past
floor observations, and emits immutable contact events. `count_touches()` feeds
this same implementation, then adds informational stop intervals for uploads.
EOF/Stop closes the final window using actual remaining observations, not
predicted positions. `confirmed_at` is distinct from the estimated contact time.
Live sound-assisted counting is not implemented; offline audio rules still need
future information and must not be presented as live evidence.

The live UI has its own HTML, CSS, protocol helper and entry point. Its overlay
uses the captured frame associated with each reply, avoiding misleading boxes
on a newer preview frame. Turning the overlay off shows the direct preview.
`scripts/replay_live.py` sends recorded clips through the actual WebSocket with
one frame in flight and measures frame drops and response/confirmation timing.
JPEGs are prepared beforehand, so it does not measure browser camera/encoding
cost. See the [live report](validation/live-revision/LIVE.md).

## Side-to-side extension

`juggling/dribbling.py` is a pure timestamped-sample analyzer plus validated
`DrillSetup`. It separates median-smoothed reversal confirmation from the raw
observed extreme used for event time and marker reach. Distance hysteresis ignores
small within-trip touches. Long gaps and tracker segment changes split evidence.
Inner marker gates time equal distances (middle 70% of marker spacing); without markers, consecutive turns define
trips. Same-direction medians provide relative pace only when at least three
complete trips exist. The edge-return pass in `juggling/edge_turns.py` counts observed outward
approaches followed by inward returns at the same actual image edge, including
fragmented tracks. It requires boundary evidence, motion in both directions and
plausible ball size; it rejects crop-only boundaries, opposite-edge jumps and
long absences. Visible reversals suppress duplicate edge events. Inferred events
use `evidence: "inferred_edge_return"`, `time_kind: "interval"`, and a
`time_interval` replay window; `time` is the window start, not an exact turn time.
This pass runs after pace analysis, so it cannot create speed measurements
across missing observations.

`juggling/dribble_scene.py` builds a 1 Hz temporal median background and rejects
static detector boxes using their central pixels. This is needed because paddles
can be sports-ball false positives. The fixed-camera assumption is explicit.
`pipeline.analyze(..., drill_setup=DrillSetup(...))` crops only inference input,
translates detections back to playback coordinates, skips pose/audio/appearance,
and returns the common replay envelope with `drill: "side_to_side"` and a
`dribbling` section. `estimated_count: 0` is an unused juggling compatibility
field, not a dribbling score. The dedicated UI uses `dribbling.turns` and `trips`.

`POST /api/jobs` retains its default juggling behavior; optional multipart fields
`drill=side_to_side` and `setup` (JSON: `roi`, `markers`, `require_markers`) select
the new path. All geometry is validated before claiming the shared worker.
Existing status/result/video routes, upload limits, and offline model loading apply.
The new TypeScript page uses the existing timestamp-aligned player. Its HTML/CSS
are separate from analysis. No database or external service was introduced.

### Toe taps

The shared `pipeline.analyze(..., drill="toe_taps")` decodes frames, observes the
ball and estimates foot landmarks using the existing models. Appearance bridging
and audio inference are disabled for this drill. `toe_taps.count_toe_taps` is a
pure per-foot entry/release state machine, independent of FastAPI and the UI.
Its configurable top-of-ball zone uses ball-relative coordinates, hysteresis,
minimum observed duration and multiple in-zone frames. A gap resets the state.
Near-simultaneous candidates are exposed for review, not counted twice.
This measures 2D proximity cycles, not proven sole/ball contact or foot skill.
The UI reuses `AnnotatedPlayer`, `seedReview`, and hash-validated `parseReview`.

Revision 2 adds sustained-entry confirmation alongside the quick departure path,
retains state across short toe-only dropouts, and merges nearby candidates while
preserving contributing timestamps. It does not fill events using cadence or an
expected count. `algorithm_version=2` distinguishes new toe-tap results.

### Toe-tap supplementary observations

`shoe_motion.py` maintains two short shoe tracks using OpenCV Lucas–Kanade
image motion. Forward/backward checks and feature-translation agreement reject
weak tracks. It can reassign switched toe groups and bridge a detector mismatch
for at most 0.15 seconds after a detector anchor. No feature evidence means no
bridge. The ball texture is excluded from feature seeding. This is still a 2D
heuristic: nearby leg/background texture may contaminate a shoe track.

`PoseDetector.detect_toe_taps` also runs the existing foot model on the lower
60% of the person box (with the model's usual padding). Its ankles and toes
come from the same model. This separate crop is an alternate observation, not
an overwrite of the original pose or an independent accuracy vote.

The pure `count_toe_taps` function remains the single-view state machine.
`analyze_toe_taps` applies it to raw, motion-associated, and detail-crop poses,
keeps primary events, and adds only separated alternate candidates. A close
candidate after ball loss stays review-only; no predicted ball counts as
contact evidence. Event `observation_view` identifies its supporting overlay.
The supplemental views are correlated and may introduce false positives on
new clips. The user count is never an input to the algorithm.

Inspect `ShoeMotionConfig` for motion gates, `ToeTapConfig` for contact gates,
and the revision-4 report for rejected alternatives and development-set limits.
Juggling, live juggling, and side-to-side do not use this additional pipeline.

Revision 5 adds `toe_observations.py`, a pure one-frame lookahead filter that
removes isolated toe jumps without mutating or interpolating raw observations.
`count_toe_taps` applies it independently to each observation view. Ball loss
clears partial contacts but can retain a previously observed off-ball state
for up to 0.20s, subject to local position/size checks on reacquisition. All
contact confirmation after that gap comes from fresh observed frames.
`contact_end` and `departure_time` expose evidence duration; null departure
means no departure was observed. Reverse optical-flow experiments were rejected
and do not add a second decoding pass or latency to the production pipeline.

Revision 6 merges same-foot candidate intervals separated by at most 0.08s,
with consecutive entry times below the existing debounce and observed ball
samples throughout the interruption. It retains interrupted entry timestamps
and prevents alternate views from re-adding events inside that merged interval.
This can merge genuinely rapid repeated contacts; see the revision-6 report.
