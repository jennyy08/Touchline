"""Short image-motion observations for shoe identity, never cadence predictions.

Lucas–Kanade features are checked forwards and backwards and must agree on
translation. Detector disagreement may be bridged for at most 0.15 seconds.
The ball area is excluded from feature seeding to avoid tracking its texture.
"""
from dataclasses import dataclass
import cv2
import numpy as np

SIDES = ('left', 'right')
PARTS = ('big_toe', 'small_toe', 'heel')


@dataclass(frozen=True)
class ShoeMotionConfig:
    max_frame_gap: float = .12
    max_bridge: float = .15
    forward_backward_pixels: float = 1.5
    minimum_features: int = 4
    translation_spread: float = .15  # ball diameters
    assignment_margin: float = .2
    detector_disagreement: float = .6


def toe_center(points):
    toes = [v for k, v in points.items() if 'toe' in k]
    return np.mean(toes, axis=0) if toes else None


class ShoeMotion:
    def __init__(self, config=None):
        self.config = config or ShoeMotionConfig()
        self.previous = None
        self.tracks = {}

    def _flow(self, gray, track, time, diameter):
        c = self.config
        if self.previous is None or time-track['time'] > c.max_frame_gap or track['features'] is None:
            return None
        before = track['features']
        after, status, _ = cv2.calcOpticalFlowPyrLK(
            self.previous, gray, before, None, winSize=(31,31), maxLevel=3)
        if after is None:
            return None
        back, back_status, _ = cv2.calcOpticalFlowPyrLK(
            gray, self.previous, after, None, winSize=(31,31), maxLevel=3)
        if back is None:
            return None
        valid = ((status.ravel() > 0) & (back_status.ravel() > 0) &
                 (np.linalg.norm(before-back, axis=2).ravel() < c.forward_backward_pixels))
        if valid.sum() < c.minimum_features:
            return None
        shifts = (after-before)[valid, 0]
        move = np.median(shifts, axis=0)
        if (np.linalg.norm(shifts-move, axis=1) < c.translation_spread*diameter).sum() < c.minimum_features:
            return None
        return {name: (np.asarray(point)+move).tolist() for name, point in track['points'].items()}

    def observe(self, image, sample):
        """Return an alternate pose plus provenance; don't mutate raw observations."""
        c = self.config
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        time, diameter = sample['time'], sample.get('diameter')
        if not diameter or self.previous is not None and gray.shape != self.previous.shape:
            self.tracks = {}
            self.previous = gray
            return {}, {'bridged': [], 'reassigned': False}
        pose = dict(sample['pose'])
        observations = {side: {n: pose[side+'_'+n] for n in PARTS if side+'_'+n in pose} for side in SIDES}
        flows = {side: points for side, track in self.tracks.items()
                 if (points := self._flow(gray, track, time, diameter)) is not None}
        swapped = False
        if len(flows) == 2 and all(toe_center(o) is not None for o in observations.values()):
            def cost(swap):
                return sum(np.linalg.norm(toe_center(flows[a])-toe_center(observations[b]))
                           for a,b in zip(SIDES, reversed(SIDES) if swap else SIDES)
                           if toe_center(flows[a]) is not None)
            if cost(True)+c.assignment_margin*diameter < cost(False):
                observations = dict(zip(SIDES, reversed(list(observations.values()))))
                swapped = True
        bridged = []
        next_tracks = {}
        for side in SIDES:
            points, predicted, track = observations[side], flows.get(side), self.tracks.get(side)
            use_flow = (predicted is not None and toe_center(predicted) is not None and
                        (toe_center(points) is None or np.linalg.norm(toe_center(points)-toe_center(predicted)) > c.detector_disagreement*diameter) and
                        time-track['anchor'] < c.max_bridge)
            if use_flow:
                points = predicted
                bridged.append(side)
            for name in PARTS:
                pose.pop(side+'_'+name, None)
            pose.update({side+'_'+name: point for name,point in points.items()})
            if not points:
                continue
            pts = np.array(list(points.values()))
            mask = np.zeros(gray.shape, np.uint8)
            x1,y1 = np.maximum(0,np.min(pts,axis=0)-.35*diameter).astype(int)
            x2,y2 = np.minimum([gray.shape[1],gray.shape[0]],np.max(pts,axis=0)+.25*diameter).astype(int)
            mask[y1:y2,x1:x2] = 255
            if sample.get('center'):
                x,y = sample['center']
                cv2.circle(mask,(round(x),round(y)),round(diameter*.48),0,-1)
            features = cv2.goodFeaturesToTrack(gray,maxCorners=30,qualityLevel=.01,minDistance=5,mask=mask)
            next_tracks[side] = dict(points=points,features=features,time=time,
                                     anchor=track['anchor'] if use_flow else time)
        self.tracks, self.previous = next_tracks, gray
        return pose, {'bridged': bridged, 'reassigned': swapped}
