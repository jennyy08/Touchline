"""Pretrained object detection, independent of tracking and event rules."""
from pathlib import Path


def load_model(path: Path):
    if not path.is_file():
        raise ValueError(f"Missing model {path.name}. Run .venv/bin/python scripts/download_models.py first.")
    import os
    runtime = Path(__file__).resolve().parents[1] / ".runtime"
    runtime.mkdir(exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(runtime))
    os.environ.setdefault("MPLCONFIGDIR", str(runtime / "matplotlib"))
    from ultralytics import YOLO, settings
    settings.update({"sync": False})
    return YOLO(str(path))


class BallDetector:
    def __init__(self, directory: Path, config):
        self.config = config
        self.model = load_model(directory / config.detector)

    def detect(self, image):
        result = self.model.predict(image, classes=[32], imgsz=self.config.image_size,
                                    conf=self.config.detection_threshold,
                                    device=self.config.device, verbose=False)[0]
        return [{"box": b, "score": float(s)} for b, s in
                zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist())]
