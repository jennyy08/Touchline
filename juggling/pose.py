"""Optional contact evidence. Low-quality/missing keypoints are not filled in."""
from pathlib import Path
from .detection import load_model
from .feet import FootDetector


class PoseDetector:
    def __init__(self, directory: Path, config):
        self.config = config
        self.model = load_model(directory / config.pose_model)
        self.feet = FootDetector(directory / config.foot_model) if config.foot_model else None

    def detect(self, image):
        result = self.model.predict(image, imgsz=self.config.pose_size,
                                    conf=0.25, device=self.config.device, verbose=False)[0]
        if result.keypoints is None or not len(result.boxes):
            return {}
        # Single-player baseline: largest person, not arbitrary detection order.
        boxes = result.boxes.xyxy.cpu().numpy()
        person = ((boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])).argmax()
        points = result.keypoints.data[person].cpu().tolist()
        names = {9: "left_wrist", 10: "right_wrist", 11: "left_hip", 12: "right_hip",
                 13: "left_knee", 14: "right_knee", 15: "left_ankle", 16: "right_ankle"}
        landmarks = {name: [float(points[i][0]), float(points[i][1])]
                     for i, name in names.items() if points[i][2] >= self.config.landmark_threshold}
        if self.feet:
            # Heel/toe points from a second model, run on the same person box.
            landmarks.update(self.feet.detect(image, boxes[person].tolist(), self.config.landmark_threshold))
        return landmarks
