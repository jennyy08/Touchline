"""A tiny constant-velocity Kalman tracker. Predictions are never observations."""
import numpy as np


class BallTracker:
    def __init__(self, config):
        self.config = config
        self.x = None
        self.p = None
        self.size = None
        self.time = None
        self.last_observed = None
        self.segment = -1

    def filter_detections(self, time, detections):
        """Reject abrupt size collapse before appearance fallback is attempted."""
        if self.size is None or self.last_observed is None or time - self.last_observed > self.config.prediction_seconds:
            return detections
        diameter = max(float(np.mean(self.size)), 1)
        return [d for d in detections if
                np.mean(np.asarray(d["box"][2:]) - d["box"][:2]) / diameter >= self.config.minimum_size_ratio]

    def update(self, time, detections):
        if self.last_observed is not None and time - self.last_observed > self.config.prediction_seconds:
            self.x = None
        dt = max(0.001, time - self.time) if self.time is not None else 1 / 30
        self.time = time
        if self.x is not None:
            f = np.eye(4); f[0, 2] = dt; f[1, 3] = dt
            self.x = f @ self.x
            self.p = f @ self.p @ f.T + np.diag([4, 4, 1600 * dt, 1600 * dt])
        eligible = []
        for detection in detections:
            box = np.array(detection["box"], dtype=float)
            size = box[2:] - box[:2]
            center = (box[:2] + box[2:]) / 2
            if min(size) <= 0:
                continue
            if self.x is None:
                cost = -detection["score"]
            else:
                diameter = max(float(np.mean(self.size)), 1)
                distance = float(np.linalg.norm(center - self.x[:2])) / diameter
                ratio = float(np.mean(size)) / diameter
                if distance > self.config.association_diameters or not self.config.minimum_size_ratio <= ratio < 2.2:
                    continue
                cost = distance + abs(np.log(ratio)) - 0.2 * detection["score"]
            eligible.append((cost, center, size, box, detection.get("source", "detector")))
        if eligible:
            _, center, size, box, source = min(eligible, key=lambda item: item[0])
            if self.x is None:
                self.segment += 1
                self.x = np.array([*center, 0., 0.])
                self.p = np.diag([25., 25., 10000., 10000.])
            else:
                h = np.eye(2, 4)
                r = np.eye(2) * max(4, float(np.mean(size)) * 0.05) ** 2
                k = self.p @ h.T @ np.linalg.inv(h @ self.p @ h.T + r)
                self.x += k @ (center - h @ self.x)
                self.p = (np.eye(4) - k @ h) @ self.p
            self.size = size
            self.last_observed = time
            # Raw observed centers preserve sharp contact reversals; the filter is for association.
            return {"status": "observed", "source": source, "box": box.tolist(), "center": center.tolist(),
                    "diameter": float(np.mean(size)), "segment": self.segment}
        if self.x is not None:
            half = self.size / 2
            return {"status": "predicted", "source": None, "box": [*(self.x[:2] - half), *(self.x[:2] + half)],
                    "center": self.x[:2].tolist(), "diameter": float(np.mean(self.size)),
                    "segment": self.segment}
        return {"status": "lost", "source": None, "box": None, "center": None, "diameter": None,
                "segment": self.segment}
