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
from .dribbling import analyze_dribbling
from .toe_taps import analyze_toe_taps
from .shoe_motion import ShoeMotion
from .dribble_scene import background, moving_detections


def analyze(source: Path, output: Path, models: Path, config=None, progress=lambda **kw: None, drill_setup=None, drill="juggling"):
    config = config or Config()
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    info = metadata(source)
    progress(stage="loading_models", frames=0, total=info["expected_frames"])
    ball = BallDetector(models, config)
    pose = PoseDetector(models, config) if drill_setup is None else None
    tracker = BallTracker(config)
    appearance = AppearanceBridge(config) if config.appearance_enabled and drill_setup is None and drill != "toe_taps" else None
    reference = background(source, progress) if drill_setup is not None else None
    shoe_motion = ShoeMotion() if drill == "toe_taps" else None
    samples = []
    writer = None
    try:
        for frame in decode(source):
            if writer is None:
                height, width = frame.image.shape[:2]
                writer = PlaybackWriter(output / "playback.mp4", width, height)
            if frame.time > 180:
                raise ValueError("This prototype supports clips up to 3 minutes. Trim the video and retry.")
            if drill_setup is None:
                detections = ball.detect(frame.image)
            else:
                h, w = frame.image.shape[:2]
                x1,y1,x2,y2 = [int(v*d) for v,d in zip(drill_setup.roi, (w,h,w,h))]
                detections = ball.detect(frame.image[y1:y2, x1:x2])
                for d in detections:
                    b = d['box']
                    d['box'] = [b[0]+x1,b[1]+y1,b[2]+x1,b[3]+y1]
            if reference is not None:
                detections = moving_detections(frame.image, detections, reference)
            detections = tracker.filter_detections(frame.time, detections)
            proposals = appearance.propose(frame.time, frame.image, detections) if appearance else detections
            tracked = tracker.update(frame.time, proposals)
            if appearance:
                appearance.accept(frame.time, tracked)
            if shoe_motion:
                landmarks, detail = pose.detect_toe_taps(frame.image)
            else:
                landmarks, detail = pose.detect(frame.image) if pose else {}, {}
            sample = {"frame": frame.index, "time": frame.time,
                      **tracked, "pose": landmarks}
            if shoe_motion:
                sample['detail_pose'] = detail
                sample['motion_pose'], sample['shoe_motion'] = shoe_motion.observe(frame.image, sample)
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
    if config.audio_enabled and drill_setup is None and drill != "toe_taps":
        try:
            heard = onsets(source)
            if not heard:
                audio_warning = "No audio track found; touches are counted from video only."
        except Exception as error:  # Audio is supplementary; never fail the video analysis.
            audio_warning = f"Audio could not be read ({error}); touches are counted from video only."
    if drill == "toe_taps":
        result = analyze_toe_taps(samples)
    elif drill_setup is None:
        result = add_audio_evidence(count_touches(samples, config), samples, heard, config)
    else:
        result = {"drill": "side_to_side", "dribbling": analyze_dribbling(samples, width, drill_setup),
                  "estimated_count": 0, "events": [], "floor_y": None, "heard_count": 0}
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
    if drill_setup is None and not result["estimated_count"]:
        result["warnings"].append("No supported touches found. This does not mean no touches occurred.")
    if drill_setup is not None:
        result['warnings'] = [w for w in result['warnings'] if not w.startswith('Hidden contacts')]
        result['warnings'].append('Experimental side-to-side analysis. Detection errors may create or hide turns; inspect the overlay.')
    if drill == "toe_taps":
        result['warnings'] = ["Experimental toe-tap estimates, not verified physical contacts.",
            "Counts require an observed ball and an approach confirmed by multiple toe observations. Occlusion, cropped feet and depth can cause misses or extra events.",
            "Colored alternate shoe outlines appear near events supported by image motion or a lower-body crop. These are additional observations, not confidence scores.",
            "Initial on-ball poses and unconfirmed approaches are excluded. A confirmed final contact counts even if the foot stays on the ball. Brief toe-only gaps preserve state. Short, spatially consistent ball gaps preserve only an earlier off-ball state; contact confirmation requires fresh observed frames after return. Review the footage and correct events separately."]
    (output / "result.json").write_text(json.dumps(result, indent=2))
    return result
