"""Per-session live analysis; model wrappers and the counter remain independent."""
from dataclasses import replace
import time
import cv2
import numpy as np
from .config import Config
from .detection import BallDetector
from .pose import PoseDetector
from .tracking import BallTracker
from .appearance import AppearanceBridge
from .streaming import StreamingCounter
from .live_settings import FootSchedule, LiveSettings


class LiveAnalyzer:
    def __init__(self, models, feet='off'):
        self.config = replace(Config(), image_size=320, pose_size=320, audio_enabled=False,
                              foot_model='' if feet == 'off' else Config().foot_model)
        self.ball = BallDetector(models, self.config)
        self.pose = PoseDetector(models, self.config)
        self.tracker = BallTracker(self.config)
        self.appearance = AppearanceBridge(self.config)
        self.counter = StreamingCounter(self.config)
        self.schedule = FootSchedule(LiveSettings(image_size=320, feet=feet))
        self.index = 0
        self.shape = None
        self.feet_runs = 0
        # Initialize inference before telling the client it can start capture.
        blank = np.zeros((360, 640, 3), dtype=np.uint8)
        self.ball.detect(blank)
        self.pose.detect_body(blank)

    def process(self, image, timestamp):
        started = time.perf_counter()
        if self.shape is not None and image.shape != self.shape:
            raise ValueError('Camera dimensions changed. Stop and start a new session.')
        self.shape = image.shape
        proposals = self.tracker.filter_detections(timestamp, self.ball.detect(image))
        proposals = self.appearance.propose(timestamp, image, proposals)
        track = self.tracker.update(timestamp, proposals)
        self.appearance.accept(timestamp, track)
        pose, box = self.pose.detect_body(image)
        if self.schedule.decide(timestamp, track, pose, box):
            pose.update(self.pose.feet.detect(image, box, self.config.landmark_threshold))
            self.feet_runs += 1
        sample = {'frame':self.index, 'time':timestamp, **track, 'pose':pose}
        self.index += 1
        events = self.counter.update(sample)
        return {'type':'frame', 'sample':sample, 'new_events':events,
                'count':self.counter.result()['estimated_count'], 'floor_y':self.counter.floor,
                'feet_runs':self.feet_runs, 'processing_ms':(time.perf_counter()-started)*1000}

    def finish(self):
        events = self.counter.finish()
        return {'type':'stopped', 'count':self.counter.result()['estimated_count'],
                'new_events':events, 'events':self.counter.events}
