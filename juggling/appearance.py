"""Short-lived image evidence between detector hits, not motion interpolation.

Normalized grayscale template matching uses the ball's texture, rather than a
blue/white color mask. A detector must periodically re-anchor the template.
"""
import cv2
import numpy as np


class AppearanceBridge:
    def __init__(self, config):
        self.config = config
        self.template = None
        self.box = None
        self.anchor_time = None
        self.last_time = None
        self.gray = None
        self.scale = 1.0

    def propose(self, time, image, detections):
        self.scale = min(1.0, 810 / image.shape[1])
        self.gray = cv2.cvtColor(cv2.resize(image, None, fx=self.scale, fy=self.scale), cv2.COLOR_BGR2GRAY)
        if (self.template is None or self.anchor_time is None
                or time - self.anchor_time > self.config.appearance_horizon_seconds
                or time - self.last_time > self.config.prediction_seconds):
            return detections
        box = self.box * self.scale
        size = box[2:] - box[:2]
        center = (box[:2] + box[2:]) / 2
        radius = float(np.mean(size)) * 1.8
        height, width = self.gray.shape
        x1, y1 = np.maximum(0, np.floor(center - radius)).astype(int)
        x2, y2 = np.minimum([width, height], np.ceil(center + radius)).astype(int)
        search = self.gray[y1:y2, x1:x2]
        best = None
        for factor in (0.9, 1.0, 1.1):
            template = cv2.resize(self.template, None, fx=factor, fy=factor)
            h, w = template.shape
            if min(h, w) < 8 or search.shape[0] < h or search.shape[1] < w:
                continue
            scores = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(scores)
            if best is None or score > best[0]:
                x, y = location
                best = (score, np.array([x1+x, y1+y, x1+x+w, y1+y+h]) / self.scale)
        if best is None or best[0] < self.config.appearance_similarity:
            return detections
        score, matched_box = best
        match_center = (matched_box[:2] + matched_box[2:]) / 2
        match_size = float(np.mean(matched_box[2:] - matched_box[:2]))
        if detections:
            # Only repair an inflated box when image evidence agrees on location.
            nearest = min(detections, key=lambda d: np.linalg.norm(
                (np.array(d['box'][:2])+d['box'][2:])/2-match_center))
            detected = np.asarray(nearest['box'])
            detected_size = detected[2:] - detected[:2]
            displacement = np.linalg.norm((detected[:2]+detected[2:])/2-match_center)
            if not (displacement < match_size * .65
                    and max(detected_size) > match_size * 1.3
                    and score >= self.config.appearance_similarity + .08):
                return detections
        return [{'box': matched_box.tolist(), 'score': score, 'source': 'appearance'}]

    def accept(self, time, sample):
        if sample['status'] != 'observed':
            return
        box = np.asarray(sample['box'])
        height, width = self.gray.shape
        x1, y1, x2, y2 = np.rint(box * self.scale).astype(int)
        # A clipped ball patch contains mostly background/body as it exits.
        # Clear the old template too: retaining it would allow fallback drift
        # after the next detector miss. A new interior detector hit re-anchors.
        margin = max(2, float(np.mean(box[2:] - box[:2])) * self.scale * 0.05)
        if min(x1, y1, width - x2, height - y2) <= margin:
            self.template = None
            self.anchor_time = None
            self.last_time = None
            return
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height or min(x2-x1, y2-y1) < 8:
            return
        patch = self.gray[y1:y2, x1:x2]
        if patch.std() < 10:
            return
        self.template = patch.copy()
        self.box = box
        self.last_time = time
        if sample.get('source') == 'detector':
            self.anchor_time = time
