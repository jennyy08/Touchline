from pathlib import Path
import hashlib
import json
import time
from collections import Counter
from .config import Config
from .video import decode, metadata, PlaybackWriter
from .detection import BallDetector
from .pose import PoseDetector
from .tracking import BallTracker
from .appearance import AppearanceBridge
from .counting import count_touches, add_audio_evidence
from .audio import onsets


def analyze(source: Path, output: Path, models: Path, config=None, progress=lambda **kw: None):
    config = config or Config()
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    info = metadata(source)
    progress(stage="loading_models", frames=0, total=info["expected_frames"])
    ball, pose = BallDetector(models, config), PoseDetector(models, config)
    tracker = BallTracker(config)
    appearance = AppearanceBridge(config) if config.appearance_enabled else None
    samples = []
    writer = None
    try:
        for frame in decode(source):
            if writer is None:
                height, width = frame.image.shape[:2]
                writer = PlaybackWriter(output / "playback.mp4", width, height)
            if frame.time > 180:
                raise ValueError("This prototype supports clips up to 3 minutes. Trim the video and retry.")
            detections = tracker.filter_detections(frame.time, ball.detect(frame.image))
            proposals = appearance.propose(frame.time, frame.image, detections) if appearance else detections
            tracked = tracker.update(frame.time, proposals)
            if appearance:
                appearance.accept(frame.time, tracked)
            sample = {"frame": frame.index, "time": frame.time,
                      **tracked, "pose": pose.detect(frame.image)}
            samples.append(sample)
            writer.write(frame)
            progress(stage="analyzing", frames=frame.index + 1, total=info["expected_frames"])
    finally:
        if writer:
            writer.close()
    if len(samples) < 5:
        raise ValueError("The clip contains fewer than 5 readable frames. Try a longer video.")
    progress(stage="counting", frames=len(samples), total=len(samples))
    heard, audio_warning = [], None
    if config.audio_enabled:
        try:
            heard = onsets(source)
            if not heard:
                audio_warning = "No audio track found; touches are counted from video only."
        except Exception as error:  # Audio is supplementary; never fail the video analysis.
            audio_warning = f"Audio could not be read ({error}); touches are counted from video only."
    result = add_audio_evidence(count_touches(samples, config), samples, heard, config)
    gaps = []
    for sample in samples:
        if sample["status"] != "observed":
            if not gaps or gaps[-1]["end_frame"] != sample["frame"] - 1:
                gaps.append({"start": sample["time"], "end": sample["time"],
                             "start_frame": sample["frame"], "end_frame": sample["frame"]})
            else:
                gaps[-1].update(end=sample["time"], end_frame=sample["frame"])
    digest = hashlib.sha256()
    with source.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    result.update(schema_version=1, video={"sha256": digest.hexdigest(), "width": width,
                  "height": height, "frames": len(samples), "duration": samples[-1]["time"],
                  "nominal_fps": info["nominal_fps"], "container_expected_frames": info["expected_frames"]}, config=config.to_dict(), samples=samples,
                  tracking_gaps=gaps, tracking_summary=dict(Counter(s["status"] for s in samples)),
                  observation_sources=dict(Counter(s["source"] for s in samples if s["status"] == "observed")),
                  runtime_seconds=time.perf_counter() - started,
                  warnings=["Estimates require review. No accuracy confidence score is assigned.",
                            "Hidden contacts and contacts without a visible downward/upward reversal may be missed."])
    if info["expected_frames"] and len(samples) != info["expected_frames"]:
        result["warnings"].append(f"Container reports {info['expected_frames']} frames; {len(samples)} frames decoded. Results cover decoded footage only.")
    if gaps:
        result["warnings"].append("Ball observations are missing in some intervals; inspect the tracking gaps.")
    if audio_warning:
        result["warnings"].append(audio_warning)
    if result["heard_count"]:
        result["warnings"].append(f"{result['heard_count']} touch(es) were heard but not seen: the ball was out of view. "
                                  "A thump in rhythm is weaker evidence than a visible contact.")
    if not result["estimated_count"]:
        result["warnings"].append("No supported touches found. This does not mean no touches occurred.")
    (output / "result.json").write_text(json.dumps(result, indent=2))
    return result
