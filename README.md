# Touchline — local juggling lab

A small, study-friendly soccer juggling prototype with uploaded clips and experimental live webcam counting. Upload a clip, watch the tracked ball, inspect estimated contact timestamps, and make a separate manual review. All video analysis runs on your computer. No accounts, paid APIs, database, or language-model video service.

**This is an inspection tool, not a validated coaching product.** See [the validation report](validation/RESULTS.md) for measured results and failures on the supplied clip.

## Run it

Tested on Apple Silicon / macOS 15.7.4, Python 3.11, Node 24. Python 3.11 and Node 22.12+ are recommended. CPU inference is the default; no GPU required. Keep a few GB free for the environment and video outputs.

From this directory:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/download_models.py --include-small
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m uvicorn juggling.api:app --host 127.0.0.1 --port 8000 --ws-max-size 1048576 --ws-max-queue 1
```

Open **http://127.0.0.1:8000**. Stop with Ctrl-C. If `python3.11` is not available but `python3 --version` says 3.11, use `python3` for the first command.

The improved tracker uses the existing OpenCV dependency; no additional model downloads are needed.

`requirements.txt` lists direct dependencies; `requirements-lock.txt` freezes the tested environment. PyAV 16.1 includes FFmpeg libraries and the H.264 encoder in its macOS wheel: no Homebrew FFmpeg installation is needed. If pip tries to compile PyAV, check that your OS/Python combination has a compatible wheel; use Python 3.11 on macOS 14+ for the tested setup. Other operating systems have not been verified.

Setup downloads packages and model weights. Afterwards, the UI uses only local assets and analysis uses local weights; missing models produce an error rather than a silent download. Ultralytics sync is disabled. Do not expose this prototype server to the internet.

### Models and licenses

The explicit download script fetches official Ultralytics assets from its GitHub v8.3.0 release, plus the MMPose RTMPose foot model (zip SHA-256 checked before extraction). Sources and downloaded SHA-256 hashes are recorded in `models/manifest.json`. Weights are not committed.

- `yolo11n.pt`: initial ball-detector baseline.
- `yolo11s.pt`: larger ball detector used in the final comparison/configuration.
- `yolo11n-pose.pt`: person box plus hip/knee/ankle landmarks.
- `rtmpose-x-halpe26.onnx` (~200 MB): heel, big-toe and small-toe landmarks, from the official [MMPose RTMPose](https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose) ONNX release (Apache-2.0; trained on public pose datasets with their own terms). It runs locally via `onnxruntime` and adds roughly 50–85 ms per frame on CPU. Disable it with `Config(foot_model="")`.

Ultralytics code and these weights use AGPL-3.0; see [official model documentation](https://docs.ultralytics.com/models/yolo11/) and [license information](https://www.ultralytics.com/license). Keep the license implications in mind if you later distribute or commercialize a derivative app. No commercial license or API is needed for this local experiment. This repository's original source is provided under AGPL-3.0 as described in `LICENSE`.

## Live webcam (experimental)

Open **http://127.0.0.1:8000/live.html**, or choose **Live practice** from the
upload page. For the currently running development server, use
**http://127.0.0.1:8001/live.html** (port 8000 was already in use).

1. Click **Start camera** and allow camera access for this localhost page.
2. Keep the ball and both feet in view. The counter needs observed motion and a
   floor estimate; hidden contacts may be missed.
3. Toggle **Show tracking** to switch between the exact last analyzed frame and
   the direct camera preview. This preference is remembered in your browser.
4. **Stop session** releases the camera and closes the last contact window. A
   last supported touch may appear when stopping.

No microphone or session recording is used yet. Frames stay in memory on this
computer and are not saved by the live endpoint. Use a current Chrome or Safari
on localhost if your embedded browser does not support camera access. The
physical-camera permission flow has not been exercised in this development run.

The server is **localhost-only, with no authentication**. It accepts one live
session or upload job at a time. Live uses CPU, 320 ball/body inputs and no
detailed foot model; uploads retain 640 inputs and detailed feet. Both use the
same causal visual counter. The offline audio pass remains separate.

Read [live validation and limitations](validation/live-revision/LIVE.md),
[streaming-counter regression](validation/live-revision/STREAMING.md), and the
[earlier speed benchmark](validation/live-revision/README.md). Live replay counts
are lower than the offline audio-assisted counts; do not treat them as equivalent.

## Using the upload app

1. Choose one MOV/MP4 video with one player and one ball. Limit: 250 MB and 3 minutes. A stationary camera with the ball and feet visible works best.
2. Wait for local model loading, frame processing, and contact analysis. One job runs at a time.
3. Inspect green detector boxes, teal appearance matches, amber dashed predictions, and blue leg landmarks. “Tracking lost” means no trustworthy current ball observation. Prediction is not contact evidence.
4. Blue outlined timeline spans and “STOPPED” rows mark where the ball was held still for a second or more (e.g. a catch). They never change the count. Click a contact or timeline marker for a short lead-in. Use playback speed and frame buttons to inspect it. Shaded timeline spans show missing observations.
5. In **Your call**, correct times, select touch/floor/pickup/hand/uncertain, delete events, or add one at the playhead. Only `touch` contributes to this separate count. An initial copy of automatic events is **not** a completed human review.
6. Export your review JSON to keep it. The export dialog offers a download and copyable JSON text (useful in embedded browsers that block file downloads). Reviews also save in localStorage, keyed by the original video hash. Import rejects another video's annotations or invalid timestamps. Automatic results never change when you edit a review.

For the supplied clip, import `validation/manual-review.json` to inspect the independent visual reference. It is approximate, agent-authored, and not yet certified by the player. You can correct it in the same UI.

Playback is a silent H.264 copy; original audio is not retained. Original uploads and playback files live under a new OS temporary directory (`juggle-lab-*`) per server process. Jobs are unavailable after restarting the server. Browser review exports remain usable after re-uploading the identical original file. Temporary files are removed at normal server exit; a crash may leave a directory for OS cleanup. CLI output stays in the directory you specify.

## Development and tests

Backend in one terminal:

```sh
.venv/bin/python -m uvicorn juggling.api:app --host 127.0.0.1 --port 8000 --reload
```

UI in another:

```sh
npm run dev --prefix frontend
```

Open the Vite address printed in the terminal. It proxies `/api` to port 8000. Layout and styles live in `frontend/src`; changes there do not affect detection or counting. Rebuild the frontend for the single-server production-style command above.

```sh
.venv/bin/python -m pytest -q
npm test --prefix frontend
npm run build --prefix frontend
```

Analyze without a browser:

```sh
.venv/bin/python -m juggling.cli '/absolute/path/to/video.mov' --output .runtime/my-clip
.venv/bin/python scripts/evaluate.py .runtime/my-clip/result.json --reference validation/manual-review.json
```

To reproduce the detector-only baseline, add `--no-appearance` to the CLI command. The contact-counting rules stay the same.

Only evaluate against a reference for the **same video**. The evaluator checks the hash. Its matching tolerance is ±0.10 seconds, with one-to-one matching. Full automatic JSON includes frame timestamps, tracking states, landmarks, configuration, gaps, candidates/reasons, and runtime.

## Troubleshooting

- **Missing model:** run the model-download command above from the project root.
- **Certificate error during download:** the script uses certifi's trusted CA bundle; don't disable TLS verification. Check your network certificate configuration if it still fails.
- **Invalid video / no frames:** re-export to H.264 MP4. The original MOV's nominal frame count may differ from its decoded frame count; the app uses actual decoded timestamps.
- **Slow processing:** CPU inference is not real time. Trim the clip. See the report for this machine's measured runtime.
- **Zero/low count:** inspect gaps and candidate reasons. A low estimate does not establish that you made few touches.
- **Job not found after restart:** upload the original clip again, then import your saved review.

[Architecture and learning guide](ARCHITECTURE.md) · [Validation results](validation/RESULTS.md)

Additional footage: [three player-counted clips and tracking-loss findings](validation/additional-clips/README.md). These use supplied totals, not event-level reference labels.

Tracking revision: [direction-aware edge handling and shoe rejection](validation/tracking-revision/README.md).

Contact revision: [foot reach, no wrist veto, top exits, stop markers](validation/contact-revision/README.md).

Foot revision: [detected heel/toe landmarks](validation/foot-revision/README.md).

Floor revision: [floor line from planted soles, three new clips](validation/floor-revision/README.md).

Latest audio revision: [impact sounds as separate "heard, not seen" evidence](validation/audio-revision/README.md). Add `--no-audio` to the CLI for video-only analysis.

Live implementation: [webcam setup and measured replay results](validation/live-revision/LIVE.md). The earlier [CPU/MPS benchmark](validation/live-revision/README.md) remains a historical comparison.

## Side-to-side dribbling (uploaded clips)

Open `/dribbling.html` on the same local server, or choose **Side to side** on
the upload page. Existing juggling upload and live modes are separate.

1. Choose a stationary-camera clip. Pause the preview and click **Practice area**,
   then two opposite corners. Include the entire actual ball route, including
   beyond the paddles, but exclude mirrors. Cropping too tightly hides turns.
2. Click **Markers** and select the two paddle/cone positions. These create
   vertical image guides. Enable **My goal is to reach both markers** only when
   that was your intention. Going past a marker is allowed.
3. Analyze. Select a turn, trip, or tracking gap to replay it at half speed;
   use the frame buttons for closer inspection. Export JSON to retain evidence.

Pace is horizontal ball displacement in **practice-area widths per second**,
not running speed or km/h. With markers, timed sections measure the middle 70% of the marker spacing
(blue lines), excluding the turns; otherwise they run between visible turns. The app flags a
trip over 25% slower than the median of at least three sections in the same direction.
This is a within-clip observation, not a technique grade or fatigue diagnosis.
Pauses may be intentional. Marker feedback refers to the ball, not the feet.

A ball approaching an image edge and returning inward from that same edge now
counts as an **inferred turn**. Its replay window is shown instead of an exact
turn timestamp. Visible and inferred turns both contribute to the turn total.
Predicted positions alone never support events, and pace never crosses gaps.
Returns after more than six seconds without observations are not joined.
Raw tracking gaps are hidden under **Tracking details (optional)**.
Visible turns near the crop boundary have unassessed marker reach. This first
version has no live dribbling, depth measurement, or automatic drill prescription.
Use a fixed camera: temporal background filtering can reject a ball that stays
still for most of the clip, and moving cameras/lighting changes are unverified.

No additional dependencies or models are required. This mode uses the installed
YOLO11s sports-ball detector at 640, the existing Kalman tracker, and a temporal
median background filter; it does not load pose, foot, or audio models. Setup
coordinates are normalized in the upright video. A second decode pass builds the
background before tracking, so processing takes longer than a single detector pass.
See `validation/dribbling-revision/README.md` for actual results and limitations.

### Practice interface

The side-to-side page opens with a short app introduction and upload. The animated
path is a decorative drill illustration, not analysis of an uploaded clip. Its
caption sits outside the SVG. Scroll motion eases toward its target and stops
rendering when settled or off screen; reduced-motion users see a static path.

After selecting a clip, the page goes directly to setup, then video results.
Turn counts, pace feedback, and event lists stay beside the replay. Playback has
frame stepping, speed controls, tracking, and focus mode (Escape to close).
Setup also accepts keyboard-accessible numeric coordinates.

Edit `frontend/src/session-story.html` and `session-story.css` for the introduction
and visual theme; `session-story.ts` connects motion and playback. Analysis stays
separate. The earlier narrative chapters and browser-history comparison are no
longer shown or written; any previously saved browser summaries remain untouched.

The locally bundled Space Grotesk font comes from Google Fonts' official
`google/fonts` repository (`ofl/spacegrotesk/SpaceGrotesk[wght].ttf`). Its SIL Open
Font License is included at `frontend/public/fonts/OFL.txt`. No remote font request
is needed during use.

## Toe taps (experimental)

Open `/toe-taps.html` after starting the server. Upload a clip with the ball and
both feet visible. Review the estimated taps with native video controls, slow
motion, frame stepping, and ball/foot overlays. The correction list starts as an
**unverified copy** of the automatic events; add or remove taps and export JSON to
save it. To retime an event, remove it and add it at the correct frame. Imports
are validated against the exact video hash. Corrections do not alter automatic
results and are not persisted unless exported.

This uses the existing YOLO11s ball detector, YOLO11n pose and RTMPose Halpe-26
foot landmarks, with the existing dependencies and model downloads. No new
models, APIs, accounts, or training. The counting module is
`juggling/toe_taps.py`: a foot must enter the observed ball-top zone and then
leave it, with at least two in-zone frames. Missing evidence resets the cycle;
predicted ball positions never support a tap. Closely overlapping foot cycles
are review candidates. The thresholds are ball-relative and time-based.
A shoe passing in front of the ball can still look like a contact in 2D.

Offline command-line processing:

```sh
PYTHONPATH=. .venv/bin/python scripts/analyze_toe_taps.py /path/to/taps.mov .runtime/my-taps
```

`drill=toe_taps` on the existing upload endpoint selects this counter; juggling
and side-to-side retain their own counters. `frontend/src/toe-taps.ts` is the
upload/review controller, `toe-taps.css` contains page-specific styles, and the
existing player handles timestamp-aligned overlays. See
`validation/toe-taps/README.md` for results and limits. Live toe taps are not implemented.

Toe-tap revision 2 confirms observed approaches either from sustained in-zone
observations or a quick observed entry/release. A final confirmed hold counts
once; an initial on-ball pose does not. Short toe-only gaps retain state without
adding evidence. Nearby duplicate foot IDs merge into one event; unclear foot
identity is labeled explicitly. See `validation/toe-taps/revision-2/README.md`
for the event-level comparison and remaining misses. The earlier baseline report
and results are retained for comparison.

Toe-tap revision 3 addresses the reported misses near 1.2, 4.75 and 11 seconds:
33 estimated events match the 33 approximate development-reference events at
±0.15s. This is not held-out accuracy. See
[the event-level report](validation/toe-taps/revision-3/README.md), including
unverified changes on the other clips. Video playback now reloads after a
background/foreground transition, and toe-tap replay includes **Refresh video**
to recover a black picture without losing the selected timestamp.

Toe-tap revision 4 adds short, checked image-motion observations and a second
lower-body pose crop. Raw pose observations remain available; supplemental
contacts show dashed teal (motion) or amber (crop) shoe outlines near their
timestamp. This runs the existing local models—no new weights or dependencies.
It is slower because it runs the foot model twice per frame. See
[revision 4 validation](validation/toe-taps/revision-4/README.md) for before/after
comparisons and remaining misses. Older saved jobs keep their original results;
re-upload to analyze with the new implementation.
