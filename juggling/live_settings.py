"""Causal sampling/scheduling candidates for benchmarks; upload defaults are unchanged."""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class LiveSettings:
    device: str = 'cpu'
    image_size: int = 640
    fps: int = 30
    feet: str = 'all'  # off, all, near; never reuse stale heel/toe points
    floor_refresh_seconds: float = .5
    near_leg_diameters: float = 3.0


class FrameGate:
    """First frame in each timestamp bin; tolerate 10% capture timestamp jitter.

    Does not select by frame number or look ahead to a later frame. Times must
    increase. This limits inference cadence, not video decoding/capture cost.
    """
    def __init__(self, fps):
        if fps <= 0:
            raise ValueError('FPS must be positive')
        self.fps, self.origin, self.bin = fps, None, -1
        self.last_time = None

    def accept(self, time):
        if self.last_time is not None and time <= self.last_time:
            raise ValueError('Frame timestamps must increase')
        self.last_time = time
        if self.origin is None:
            self.origin = time
        index = math.floor((time - self.origin) * self.fps + .1)
        if index <= self.bin:
            return False
        self.bin = index
        return True


class FootSchedule:
    """Use only current/past observed ball and body points; no event labels."""
    def __init__(self, settings):
        if settings.feet not in ('off', 'all', 'near'):
            raise ValueError('Foot mode must be off, all or near')
        self.settings = settings
        self.previous = None
        self.last_run = None

    def decide(self, time, track, pose, person_box):
        previous = self.previous
        # Do not carry a velocity estimate through a tracking gap.
        self.previous = (time, track) if track['status'] == 'observed' else None
        if self.settings.feet == 'off' or person_box is None:
            return False
        periodic = self.last_run is None or time-self.last_run >= self.settings.floor_refresh_seconds
        near = False
        if (previous and track['status'] == 'observed'
                and previous[1]['segment'] == track['segment'] and time-previous[0] <= .15):
            descending = track['center'][1] > previous[1]['center'][1]
            legs = [point for name, point in pose.items() if name.endswith(('_ankle', '_knee'))]
            near = descending and any(np.linalg.norm(np.subtract(track['center'], p))
                                      <= self.settings.near_leg_diameters * track['diameter'] for p in legs)
        run = self.settings.feet == 'all' or periodic or near
        if run:
            self.last_run = time
        return run
