# Live-readiness benchmark

Historical benchmark milestone. The live page and streaming counter are now
implemented; see [current live results and setup](LIVE.md). Numbers below retain
the original benchmark method for comparison.

This milestone measures candidate settings before implementing the streaming counter or webcam endpoints. The upload app's defaults remain unchanged. No new endpoint, camera/microphone capture, or recording is introduced here.

## Decision: provisional speed-first settings

Start the streaming implementation with **CPU, ball input 320, body pose 320,
detailed feet off, default eight PyTorch threads**, and a **30 fps capture ceiling**.
The [saved profile](recommended-profile.json) documents this choice; it does not
change upload defaults. This follows the user's preference for quick feedback
while catching most touches. It is a starting point, not an accepted live
performance target: the measured service capacity is only **22.4 fps** and the
actual one-frame-in-flight loop will drop frames. Its resulting count must be
measured before calling the live milestone complete.

A separate direct run processed all seven recordings (2,693 selected frames):
**44.6 ms mean**, **60.7 ms worst per-clip p95**, 120.2 seconds total frame
processing. Weighted stage means were decode 6.7 ms, ball 18.9 ms, body pose
11.4 ms, tracking/scheduling 7.7 ms, feet 0 ms. Counter/audio processing is
excluded. There is no measured sub-0.5-second event-delay claim.

| Check | Clips | Mean ms/frame | Worst clip p95 ms/frame |
|---|---|---:|---:|
| CPU, ball/body 640, feet off, 8 threads | Original only | 96.7 | 107.7 |
| MPS, ball/body 640, feet off | Original only | 88.3 | 108.3 |
| CPU, ball/body 640, feet off, 4 threads | Original only | 99.3 | 113.6 |
| **CPU, ball/body 320, feet off, 8 threads** | **All seven** | **44.6** | **60.7** |

The first three rows are single-clip follow-up checks, not seven-clip averages.
The last row changes body-pose resolution too, unlike the main matrix. A smaller
pose model input on MPS was not directly tested; no global optimum is claimed.

| Clip | User total | Video only | With offline audio |
|---|---:|---:|---:|
| Original, 2.02 AM | 26 | 24 | 26 |
| 1, 12.26 PM | 16 | 16 | 16 |
| 2, 12.28 PM | 29 | 28 | 28 |
| 3, 12.29 PM | 21 | 21 | 21 |
| 4, 2.59 PM | 13 | 11 | 11 |
| 5, 3.01 PM | 25 | 22 | 25 |
| 6, 2.59 PM #2 | 23 | 21 | 23 |

On the original timestamp reference (±0.10 seconds), the selected profile has
**24 visual matches, zero extra events and two misses**, at reference times
6.60 and 10.50 seconds. With offline audio it has **26 matches, zero extras and
zero misses**. Mean absolute timing error among matches is 5.6 ms in both cases;
the reference timestamps are approximate, so this is not a claim of millisecond
physical contact accuracy. Full matches/misses and predicted events are retained
in `benchmark/direct-cpu-320-pose320-off.json`. Other clips have totals only.

At 640/30, keeping near-contact feet is the quality comparison: its totals match
all seven references with offline audio, but the measured service costs are too
high for the requested cadence. The smaller speed-first profile sacrifices
spatial/contact evidence. Missing foot landmarks also weaken floor and contact
classification. Keep those candidates inspectable and uncertain; do not present
this tradeoff as a validated solution for floor bounces.

## Verification

- 70 Python tests pass, including six new timestamp-gate/scheduler tests for
  jitter, capture gaps, descent, periodic refresh, lost/reacquired tracks and
  disabled/no-person behavior.
- Six frontend tests pass; production build passes. No UI code changed.
- The existing upload path still calls combined body/foot inference. No defaults,
  model weights or dependencies changed, and no camera or endpoint was added.

## Machine and scope

Measured on 2026-10-17: MacBook Air, Apple M4 (4 performance + 6 efficiency CPU cores), 16 GB RAM, macOS 15.7.4, PyTorch 2.7.1 and Ultralytics 8.3.162. Detailed environment/startup timings are in `benchmark/*-environment.json`. No dependency or model was changed.

## Method

`python scripts/benchmark_live.py` measures the seven existing development clips on CPU and Metal/MPS, synchronizing GPU work for timing. Metal must be available to the process; on this Mac it is hidden in the restricted sandbox but available to a normally launched terminal process. An unavailable device is reported, not silently substituted.

The 36 profiles are the Cartesian product of CPU/MPS, ball input sizes 640/480/320, timestamp-selected 30/15 fps, and feet off/every selected frame/near descending ball plus periodic floor samples. Body pose remains YOLO11n-pose at 640; foot inference remains RTMPose-x ONNX on CPU, even in MPS profiles. This is not a comparison of every possible body-pose resolution or foot runtime provider.

Models are loaded and warmed separately. Every source frame is decoded at original resolution and used to measure body pose, foot inference, and ball detection at each size. Detector/pose outputs and per-frame costs are cached under `.runtime/live-benchmark/`, keyed by source hash, model hashes, model-wrapper source, configuration and environment. Original pixels are decoded again for tracking replays; compressed playback is not used as inference input. One tracking replay per device/size/FPS is shared by the three foot schedules because foot landmarks do not influence ball association.

The scheduler uses current/past observed motion and available leg points, plus a periodic sample for floor evidence. It never reads reference times or the expected count, and does not carry foot landmarks across skipped frames. Production upload behavior still runs the foot model on every eligible frame. The candidate scheduler is experimental; integrating it in the production live pipeline is a later task.

### Timing interpretation

- Decode, ball detection, body pose, feet and tracking service costs are measured separately in milliseconds.
- Foot costs are charged only on scheduled frames. Tracking costs are replay measurements. Their sum is an **estimated service time**, not a directly measured browser round trip or complete live pipeline time.
- Table p95 is the **largest per-clip p95**, not a pooled p95. Mean costs are weighted by processed frame counts.
- Service-capacity FPS is the reciprocal of mean service time. A requested sampling rate above that capacity cannot be sustained by one sequential worker. Even a good mean does not remove slow-frame spikes.
- Excluded from service timing: browser capture/JPEG conversion, network, queueing, streaming counter updates, audio processing/confirmation, and recording. Offline counter/audio-merge time is reported separately; audio decoding/onset extraction is not included in service estimates.
- Decode is measured for the recorded source and charged to selected frames only. It is not an estimate of the browser's capture cost. The tool itself still decodes all source frames.
- Single passes with warm models are observational measurements; thermal load and background work can affect them. There is no live latency claim yet.

### Count interpretation

Reference totals are 26/16/29/21/13/25/23, excluding pickup and floor bounces. These are the user's totals, not new recounts. Only the original clip has a full approximate timestamp reference; its one-to-one results are included in each profile.

`video_only_count` reports the current visual counter. `estimated_count` includes **offline** audio confirmation/heard events. The current floor estimate, audio normalisation, rhythm and return checks use future clip information. Neither count represents the planned streaming implementation. Sum absolute total difference is not an event-error count: extra and missed events can cancel. Changing sampling can change both visual evidence and the audio rules' rhythm estimate. The current counter also checks neighboring source-frame IDs for leg support; at 15 fps, skipped source frames can remove that support. These results intentionally benchmark the unchanged counter, not a proposed streaming refactor with different adjacency rules.

The seven clips were already used for development. Results on them cannot establish new-footage accuracy. In particular, the audio strength threshold has a thin development-set margin documented in `validation/audio-revision/README.md`.

## Reproduce

From the repository root, after normal setup:

```sh
.venv/bin/python scripts/benchmark_live.py
.venv/bin/python scripts/summarize_live_benchmark.py validation/live-revision/benchmark
```

Use `--devices cpu` or `--devices mps` to run one device, and `--clips 0 1` for a subset. Completed inference caches are reused after interruptions. Only complete seven-clip groups appear in the summary. Raw videos/models/caches remain local and ignored by Git. Per-profile counts, stage statistics and the summary table are saved in `benchmark/`.

Current code: `juggling/live_settings.py` (timestamp gate and experimental foot scheduler), `scripts/benchmark_live.py` (measure/replay), and `scripts/summarize_live_benchmark.py` (report). `PoseDetector.detect_body()` exposes body inference separately; existing `detect()` still combines body and feet for uploads.

## Matrix results

All 36 seven-clip profiles completed. CPU/MPS counts agree for every profile.
Body landmark presence also agrees on every frame; the largest coordinate
separation is 0.014 pixels (rounded up) across seven clips. That supports using
MPS on this stack for this footage, despite the installed warning.

The [full matrix](benchmark/MATRIX.md) includes every setting. Selected 30 fps
rows below use body input 640; costs are cached-stage estimates, not direct
live timings. Video order is original, then clips 1–6.

| Device / ball / feet | Video counts | With offline audio | Mean service ms | Worst clip p95 ms |
|---|---|---|---:|---:|
| cpu / 320 / off | 24 / 16 / 29 / 21 / 11 / 22 / 20 | 26 / 16 / 29 / 21 / 11 / 25 / 22 | 66.7 | 95.1 |
| cpu / 480 / off | 25 / 16 / 29 / 21 / 12 / 22 / 20 | 26 / 16 / 29 / 21 / 13 / 22 / 22 | 82.4 | 125.3 |
| cpu / 640 / all | 26 / 16 / 29 / 21 / 12 / 21 / 20 | 26 / 16 / 29 / 21 / 13 / 25 / 23 | 176.2 | 271.9 |
| cpu / 640 / near | 26 / 16 / 29 / 21 / 12 / 21 / 20 | 26 / 16 / 29 / 21 / 13 / 25 / 23 | 137.9 | 222.7 |
| cpu / 640 / off | 26 / 16 / 29 / 20 / 12 / 21 / 19 | 26 / 16 / 29 / 20 / 13 / 25 / 22 | 108.6 | 153.5 |
| mps / 640 / all | 26 / 16 / 29 / 21 / 12 / 21 / 20 | 26 / 16 / 29 / 21 / 13 / 25 / 23 | 170.0 | 220.9 |
| mps / 640 / near | 26 / 16 / 29 / 21 / 12 / 21 / 20 | 26 / 16 / 29 / 21 / 13 / 25 / 23 | 132.5 | 200.3 |
| mps / 640 / off | 26 / 16 / 29 / 20 / 12 / 21 / 19 | 26 / 16 / 29 / 20 / 13 / 25 / 22 | 103.6 | 131.5 |

- **Near-contact feet:** at 640/30, RTMPose ran on 43% of selected frames
  instead of 98% (frames without a person box cannot run it). Both schedules
  retain the same visual and audio-assisted totals on these clips. This supports
  the scheduling experiment, not a claim that skipped foot evidence is harmless
  on arbitrary footage.
- **15 fps:** the original clip drops from 26 to 23 at 640, for all foot schedules;
  other clips also regress. Retaining temporal evidence matters.
- **Smaller ball inputs:** 320/30 loses two counts on clip 4, and 480/30 loses
  three on clip 5 even with feet/audio. They are not a free speed improvement.
- **No feet:** 640/30 loses one count on clip 3 and one on clip 6. This is a
  plausible speed-first tradeoff to investigate, but it weakens floor/contact
  evidence and must be exposed honestly in the live implementation.

No cached profile meets its target period at the worst clip's p95. The foot
runtime is loaded and active during collection even for timings later charged
to the no-foot schedule. Therefore a fresh-process direct validation is needed
before selecting a live starting point; the table alone is insufficient.

## Backend warning check

The pinned Ultralytics release prints an MPS pose warning. The upstream
[issue #4031](https://github.com/ultralytics/ultralytics/issues/4031) records the
historical problem and later removal of the warning; that history alone does not
establish whether this pinned stack is affected. We compare CPU/MPS body landmark
presence and coordinates on identical source frames, saving
`benchmark/pose-parity.json`. This is backend agreement, not a labeled pose
accuracy test. A warm-up also emitted an NMS time-limit warning; cold start is
excluded from the measured frame costs.

## Reproduce the direct checks

Run each command separately, with no competing inference process. These checks
process recordings as fast as possible; they do **not** replay browser
backpressure or drop additional frames when service time exceeds the target.

```sh
.venv/bin/python scripts/validate_live_profile.py --device cpu --size 640 --fps 30 --feet off --clips 0 --output validation/live-revision/benchmark/direct-cpu-640-off.json
.venv/bin/python scripts/validate_live_profile.py --device mps --size 640 --fps 30 --feet off --clips 0 --output validation/live-revision/benchmark/direct-mps-640-off.json
.venv/bin/python scripts/validate_live_profile.py --device cpu --size 640 --fps 30 --feet off --threads 4 --clips 0 --output validation/live-revision/benchmark/direct-cpu-640-off-t4.json
.venv/bin/python scripts/validate_live_profile.py --device cpu --size 320 --pose-size 320 --fps 30 --feet off --output validation/live-revision/benchmark/direct-cpu-320-pose320-off.json
.venv/bin/python scripts/compare_backend_pose.py
```

The four-thread check is separate from the original matrix's default eight
PyTorch threads. It did not improve speed on the original clip, so it is not
recommended. All direct runs retain full-resolution source images for tracking;
only neural-network inputs are resized. Frame service costs still exclude the
offline counter/audio, network, camera capture and encoding.

## What is still unverified

- Sustained live sampling, browser round-trip delay and event-confirmation delay.
- Streaming floor estimation and counting equivalence; the current counter uses
  whole-clip information and source-frame adjacency.
- Live audio: whole-clip normalization cannot be reused as-is. Heard-only events
  currently wait for a ball return and may arrive later than the desired 0.5 s.
- Event-level accuracy on clips 1–6; only user-provided totals are available.
- New-footage performance, reliable hand/floor discrimination and different
  cameras/lighting. These development clips are not a held-out test set.

The next milestone is a streaming counter with timestamp-based evidence windows,
a rolling floor estimate, and regression comparisons on saved samples. The
benchmark's scheduler can then be integrated separately. No live endpoint was
added in this milestone.
