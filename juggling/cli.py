import argparse
from pathlib import Path
from .config import Config
from .pipeline import analyze


def main():
    p = argparse.ArgumentParser(description="Analyze an uploaded juggling clip locally")
    p.add_argument("video", type=Path)
    p.add_argument("--output", type=Path, default=Path(".runtime/cli"))
    p.add_argument("--models", type=Path, default=Path("models"))
    p.add_argument("--detector", default=Config().detector)
    p.add_argument("--image-size", type=int, default=Config().image_size)
    p.add_argument("--device", default="cpu")
    p.add_argument("--detection-threshold", type=float, default=Config().detection_threshold)
    p.add_argument("--no-appearance", action="store_true", help="Run the detector-only baseline")
    a = p.parse_args()
    def progress(**state):
        if state["frames"] % 30 == 0:
            print(state, flush=True)
    result = analyze(a.video, a.output, a.models,
                     Config(detector=a.detector, image_size=a.image_size, device=a.device, detection_threshold=a.detection_threshold, appearance_enabled=not a.no_appearance), progress)
    print({k: result[k] for k in ("estimated_count", "tracking_summary", "runtime_seconds")})


if __name__ == "__main__":
    main()
