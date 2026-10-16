# Touchline — local juggling lab

A small, study-friendly soccer juggling prototype: upload a clip, watch the tracked ball, inspect estimated contact timestamps, and make a separate manual review. All video analysis runs on your computer. No accounts, paid APIs, database, or language-model video service.

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
.venv/bin/python -m uvicorn juggling.api:app --host 127.0.0.1 --port 8000
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

## Using the app

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

Latest floor revision: [floor line from planted soles, three new clips](validation/floor-revision/README.md).
