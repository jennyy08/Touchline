# Foot revision: detected heel and toe landmarks

The YOLO11n-pose (COCO) landmarks have ankles but no toes. On these clips that caused two visible problems: an extended foot looked far from the ball, and in clip 3 at 3.835 s both ankle points landed on the standing foot. This revision adds a second pretrained pose model that outputs heel, big toe and small toe per foot. Tracking is unchanged: the full reruns produced samples identical to `validation/contact-revision/`. User totals stay 26/16/29/21. Every touch was a foot touch (confirmed by the player). The clips were not recounted.

## What was added

- **Model:** RTMPose-x, Halpe-26 keypoints, 384×288 input, the official MMPose ONNX export (`models/rtmpose-x-halpe26.onnx`, ~200 MB). `scripts/download_models.py` fetches it, checks the zip SHA-256 before extracting, and records the source and hash in `models/manifest.json`. It runs locally on CPU through `onnxruntime==1.31.0`, the only new Python dependency.
- **`juggling/feet.py`:** a short, readable version of RTMPose top-down inference. It crops the YOLO person box with an affine warp, normalises it, runs the network, and takes the argmax of the SimCC x/y outputs. On real frames it matches the reference `rtmlib` implementation to within 0.0001 px, so `rtmlib` is not a dependency. Points below `landmark_threshold` (0.35) are omitted.
- **Counting:** if a side has heel/toe points, foot support is the distance from the ball center to the foot outline (heel–big toe, heel–small toe, big–small toe). The ankle-based foot estimate from the previous revision is now only a fallback when those points are missing. The 1.15-diameter contact threshold is unchanged.
- **Labels:** in this front view, a ball on a raised foot also overlaps the knee in 2D. So if a foot supports the contact, the label is foot. A genuine knee/thigh touch leaves the foot hanging well below the ball, so it still gets the knee/thigh label (synthetic test only).
- **UI:** the replay overlay draws each detected foot outline in the leg-landmark blue.

## Selection evidence

Measured before wiring anything in: at each of the 92 candidate events (contact frame ±1), the distance from the ball center to the nearest detected foot outline, in ball diameters. A ball resting on a foot gives about 0.5.

| Model | Events with foot > 0.9 diameters |
|---|---|
| MediaPipe Pose Landmarker heavy (heel + foot index) | 43 of 92 tested; the toe/heel often stayed on the standing foot or near the hips, and some frames had no person |
| RTMPose-m Halpe-26 (clip 2 only) | 6 / 29 |
| **RTMPose-x Halpe-26** | **0 / 92** |

MediaPipe was installed for this test and then fully removed. The venv now differs from the previous lock only by `onnxruntime`, `flatbuffers` and `protobuf`.

## Results

| Clip | User total | Contact revision | Foot revision | Labelled foot | Review |
|---|---:|---:|---:|---:|---|
| Original | 26 | 26 | 26 | 26 / 26 | none |
| 1 / 12.26 PM | 16 | 16 | 16 | 16 / 16 | none |
| 2 / 12.28 PM | 29 | 29 | 29 | 29 / 29 | none |
| 3 / 12.29 PM | 21 | 20 | 21 | 21 / 21 | none |

Before this revision, many touches were labelled knee or thigh. Now every event is labelled foot.

**Original (timestamp reference):** 26/26 matched within ±0.10 s, 0 unmatched counted events, 0 misses (`original-evaluation.json`).

**Only count change:** clip 3 at 3.835 s / frame 115 (`clip-3-recovered-3835.jpg`). The toe points sit on the kicking shoe at the ball, and the ball rises immediately afterwards.

**Label checks:** `clip-2-former-knee-labels.jpg` and `clip-1-feet.jpg` show former knee/thigh-labelled touches. In each, the toe points are on the kicking shoe beneath the ball.

Clips 1–3 have totals only, so matching them does not prove each event is right (a miss and an extra could cancel). These four clips have now guided three revisions. They are regression examples, not an independent accuracy test.

## Cost and limits

- **Runtime:** full runs took 69.9 / 53.0 / 80.6 / 60.8 s, up from 43.1 / 31.7 / 45.1 / 34.9 s. RTMPose-x adds roughly 50–85 ms per frame on this Mac's CPU (single runs, not benchmarks). Set `foot_model=""` in `Config` to disable it.
- Left/right foot labels were not individually verified.
- Heel/toe points were missing (below threshold) in 28 of 329 frames in clip 1 and 31 of 474 in clip 2. The ankle-based estimate covers those frames.
- Still untested on real footage: knee/thigh touches, catches, hand contacts, floor bounces, other cameras and other players.
- Model license: the MMPose code and release are Apache-2.0. The weights were trained on public pose datasets, which have their own terms. That's fine for this personal, local prototype; check those terms before any wider distribution.

## Verification

51 Python tests pass. New ones cover a missing foot model raising an actionable error with no download, crop geometry, a detected foot under the ball counting as foot, a far foot not counting, foot-over-knee labelling, a genuine knee touch with the foot hanging below, and detected toes overriding the ankle estimate. Frontend: 5 tests, the TypeScript check and the production build pass.
