# First live webcam milestone

The app now has a separate **Live practice** page (`/live.html`) with camera
start/stop, an estimated visual count, observed/predicted/lost status, recent
contact/review events, a remembered overlay toggle and processed-FPS/round-trip
readouts. Tracking view uses the exact analyzed frame; plain preview uses the
camera directly. No microphone, recording or dribble mode is implemented here.

## Start and try it

After installing `requirements-lock.txt` and building the frontend:

```sh
.venv/bin/python -m uvicorn juggling.api:app --host 127.0.0.1 --port 8001 --ws-max-size 1048576 --ws-max-queue 1
```

Open http://127.0.0.1:8001/live.html. Allow camera access after pressing Start.
Stop releases camera tracks and closes the final confirmation window. Use a
current Chrome/Safari browser if an embedded browser cannot access the camera.
The server is **localhost-only, without authentication**; keep the loopback bind.
One live session or uploaded analysis can own the analysis worker at a time.

The new direct dependency is `websockets==15.0.1`; Pillow, already in the lockfile,
is now also listed explicitly because JPEG header dimensions are validated
before decoding. All model inference stays local; no extra model downloads.
Transport follows the documented [FastAPI WebSocket API](https://fastapi.tiangolo.com/advanced/websockets/)
and [websockets 15.0.1 client](https://websockets.readthedocs.io/en/15.0.1/).

## Protocol and boundaries

- Connect `/api/live`; server sends `loading`. Send `{"type":"start","feet":"off"}`;
  server loads/warms models and sends `ready`. Optional `near`/`all` feet are
  benchmark choices, not recommended UI settings.
- Send binary `float64 little-endian timestamp in seconds + JPEG bytes`.
  Timestamp is relative to capture start, strictly increasing, at most one hour.
  JPEG is under 1 MB, at most 1280 pixels per side and 921,600 total pixels.
  UI uses longest edge 640 and quality 0.85. Dimensions cannot change mid-session.
- Wait for each `frame` reply before sending another. It includes the sample,
  new candidate events, estimated count, floor estimate and processing time.
  Predictions remain separate and never supply touch evidence.
- Send `{"type":"stop"}`; the server waits 0.14 seconds, closes remaining windows
  using existing observations, sends `stopped` and closes the socket. Abrupt
  disconnection releases resources but does not produce a final report.
- Local Host and matching browser Origin are checked; CLI clients can omit Origin.
  Bad frames/timestamps, missing models, busy sessions and timeouts have explicit
  errors. Inference runs in the shared single-worker executor, not the async loop.

The live endpoint keeps frame evidence in memory only and does not save video.
The regression script deliberately stores diagnostic samples locally under
ignored `.runtime/live-replay/`. Committed reports contain metrics and events.

## Actual WebSocket replay on this Mac

Apple M4 MacBook Air, 16 GB, macOS 15.7.4, pinned environment. CPU, ball/body input
320, detailed feet off. Camera-like frames were downsized to longest edge 640
and JPEG encoded. Each source was then paced at its timestamps through the
actual localhost WebSocket with one frame in flight; stale source frames were
skipped. This is a **recorded-input live-path test**, not a physical-camera test.
JPEG preparation happened before timing. Browser capture/encoding, rendering,
permission flow and real-world webcam juggling remain unverified.

| Clip | User total | Live visual | Processed / source frames | Processed fps | Mean / p95 round trip ms | Mean / p95 candidate delay ms |
|---|---:|---:|---:|---:|---:|---:|
| Original | 26 | 23 | 381 / 427 | 26.5 | 37 / 45 | 226 / 244 |
| 1 | 16 | 16 | 320 / 329 | 28.8 | 34 / 37 | 221 / 230 |
| 2 | 29 | 26 | 440 / 474 | 27.6 | 36 / 40 | 224 / 260 |
| 3 | 21 | 20 | 340 / 350 | 28.8 | 34 / 37 | 214 / 233 |
| 4 | 13 | 10 | 240 / 252 | 28.1 | 35 / 40 | 219 / 237 |
| 5 | 25 | 21 | 419 / 443 | 28.2 | 34 / 39 | 220 / 241 |
| 6 | 23 | 21 | 386 / 418 | 27.5 | 35 / 42 | 223 / 241 |

Delay means reply arrival minus the candidate's estimated source contact time,
for emitted counted **and review** candidates, including Stop-confirmed tails.
Missed touches have no delay measurement. These single-pass numbers do not prove
sub-0.5-second feedback in a real browser, nor long-session thermal performance.
The current speed result is better than the earlier full-resolution benchmark
partly because tracking/decoding now operate on smaller camera-like JPEG frames.

On the original approximate timestamp reference (±0.10 s), real-time replay has
**23 matches, zero extras, three misses** at 3.00, 10.50 and 14.102 seconds. Mean
absolute matching error is 0.013 seconds. Other clips have user totals only, so
matching/mismatching totals cannot establish their event-level accuracy.

Sending **all 427 frames** of the original through the same JPEG/320 pipeline,
without real-time dropping, gives **24**. Thus both reduced spatial evidence and
frame dropping matter. It is not just a different total-count threshold.
Raw results: `websocket-replay.json`, `websocket-all-frames-original.json`.
On every tested frame sequence, WebSocket events equal the offline wrapper's
outputs on those **same received samples**, including the final Stop events.

## Optional feet: measured failure, left off

The on-demand scheduler is integrated in `LiveAnalyzer` for explicit experiments.
On the original real-time replay, `near` ran RTMPose on **83 / 253 processed
frames (33%)**, but throughput fell to **17.5 fps**, 174 source frames were
skipped, and **zero touches** were counted (one gap candidate required review).
Mean / p95 round trip was 56 / 109 ms. Long processing bursts near contacts
remove outgoing observations and trigger conservative gap rules; the expensive
model can therefore hurt this sequential live loop despite helping offline.
See `websocket-near-original.json`. Do not enable it as a quality upgrade until
its runtime/scheduling and resulting contact evidence improve. No thresholds
were relaxed merely to recover the supplied totals.

## Reproduce and checks

With the server running:

```sh
.venv/bin/python scripts/validate_streaming.py
.venv/bin/python scripts/replay_live.py
.venv/bin/python scripts/replay_live.py --clips 0 --all-frames --output validation/live-revision/websocket-all-frames-original.json
.venv/bin/python scripts/replay_live.py --clips 0 --feet near --output validation/live-revision/websocket-near-original.json
.venv/bin/python -m pytest -q
npm test --prefix frontend
npm run build --prefix frontend
```

87 Python tests, nine frontend tests and production build pass. Transport tests
use deterministic observations to isolate protocol/counting behavior; the replay
above exercises real models. Tests cover counter timing/causality/tails, worker
exclusion, disconnect cleanup, invalid JPEG/size/timestamps, missing weights,
Origin/Host restrictions, binary framing and frontend backpressure. The live
page was visually inspected in the in-app browser. Physical camera capture and
browser permission prompts were not exercised; the user must try that flow.

Remaining work: real webcam validation, stream-friendly audio (offline sound
rules still need future information), optional recording, and the later dribble
mode. The upload model settings remain unchanged; the shared causal counter
preserves the prior seven saved-sample totals ([regression](STREAMING.md)).
