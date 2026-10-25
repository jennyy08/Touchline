"""Heel and toe landmarks from a pretrained RTMPose Halpe-26 model (ONNX, local CPU).

COCO pose (YOLO) has ankles but no toes, so an extended foot looks far from the ball.
RTMPose's Halpe-26 output adds big toe, small toe and heel per foot. This is a small,
readable re-implementation of the standard RTMPose top-down inference (as in MMPose /
rtmlib, Apache-2.0): crop the person box with an affine warp, normalise, run the network,
and decode the SimCC x/y distributions with an argmax. Nothing is downloaded here.
"""
from pathlib import Path
import cv2
import numpy as np

# Halpe-26 keypoint indices used here (the first 17 are COCO).
FOOT_POINTS = {20: "left_big_toe", 21: "right_big_toe", 22: "left_small_toe",
               23: "right_small_toe", 24: "left_heel", 25: "right_heel"}
MEAN = np.array([123.675, 116.28, 103.53], dtype=np.float32)
STD = np.array([58.395, 57.12, 57.375], dtype=np.float32)


def crop_transform(box, input_size, padding=1.25):
    """Affine matrix mapping a padded person box (fixed aspect ratio) to the model input."""
    w, h = input_size
    x1, y1, x2, y2 = box
    center = np.array([(x1 + x2) / 2, (y1 + y2) / 2], dtype=np.float32)
    bw, bh = (x2 - x1) * padding, (y2 - y1) * padding
    # Grow the shorter side so the crop matches the network's aspect ratio (no distortion).
    if bw > bh * w / h:
        bh = bw * h / w
    else:
        bw = bh * w / h
    scale = np.array([bw, bh], dtype=np.float32)
    src = np.float32([center, center + [0, -bw / 2], center + [-bw / 2, -bw / 2]])
    dst = np.float32([[w / 2, h / 2], [w / 2, h / 2 - w / 2], [0, h / 2 - w / 2]])
    return cv2.getAffineTransform(src, dst), center, scale


class FootDetector:
    def __init__(self, path: Path, input_size=(288, 384)):
        if not path.is_file():
            raise ValueError(f"Missing model {path.name}. Run .venv/bin/python scripts/download_models.py first.")
        import onnxruntime as ort
        self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        self.input_size = input_size  # (width, height) for the RTMPose-x 384x288 model

    def detect(self, image, box, threshold, include_ankles=False):
        """Foot points in original image coordinates; low-scoring points are omitted."""
        w, h = self.input_size
        matrix, center, scale = crop_transform(box, self.input_size)
        crop = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR)
        tensor = ((crop.astype(np.float32) - MEAN) / STD).transpose(2, 0, 1)[None]
        simcc_x, simcc_y = self.session.run(None, {self.session.get_inputs()[0].name: tensor})
        # SimCC: one 1-D distribution per axis at 2x input resolution.
        xs, ys = simcc_x[0].argmax(1) / 2.0, simcc_y[0].argmax(1) / 2.0
        scores = (simcc_x[0].max(1) + simcc_y[0].max(1)) / 2
        points = np.stack([xs, ys], 1) / [w, h] * scale + center - scale / 2
        names = {**FOOT_POINTS, **({15: "left_ankle", 16: "right_ankle"} if include_ankles else {})}
        return {name: [float(points[i][0]), float(points[i][1])]
                for i, name in names.items() if scores[i] >= threshold}
