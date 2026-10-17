"""Causal visual counting. No audio, model inference, wall clock or network here."""
from collections import deque
import math
from .counting import contact_candidates, estimate_floor


class StreamingCounter:
    def __init__(self, config):
        self.config = config
        self.samples = deque()
        self.pending = deque()
        self.events = []
        self.last_time = None
        self.floor = None
        self.floor_history_seconds = 5.0
        self.finished = False

    def update(self, sample):
        """Confirm each contact after its outgoing-motion window has elapsed.

        Confirmed events never change afterwards. The first supported candidate
        wins within the debounce interval, rather than revising a visible count.
        Floor evidence is restricted to the last five seconds already received.
        """
        if self.finished:
            raise ValueError('This counter has finished. Start a new session.')
        now = sample['time']
        if not math.isfinite(now) or (self.last_time is not None and now <= self.last_time):
            raise ValueError('Frame timestamps must be finite and strictly increasing.')
        self.last_time = now
        self.samples.append(sample)
        if sample['status'] == 'observed':
            self.pending.append(sample)
        while self.samples and now - self.samples[0]['time'] > self.floor_history_seconds:
            self.samples.popleft()
        self.floor = estimate_floor(list(self.samples))
        return self._confirm(now)

    def _confirm(self, now, ending=False):
        new = []
        window = self.config.velocity_window_seconds
        while self.pending and now - self.pending[0]['time'] >= window - 1e-6:
            target = self.pending.popleft()
            # Include a following lost frame for the special top-exit rule, but
            # never observed velocity evidence beyond the outgoing window.
            nearby = [s for s in self.samples if target['time'] - window - 1e-6 <= s['time']]
            candidates = contact_candidates(nearby, self.config, self.floor)
            event = next((e for e in candidates if e['frame'] == target['frame']), None)
            if event is None:
                continue
            if self.events and event['time'] - self.events[-1]['time'] < self.config.debounce_seconds:
                continue
            event['confirmed_at'] = now
            if ending:
                event['confirmation_context'] = 'end_of_stream'
            event['floor_y_at_confirmation'] = self.floor
            self.events.append(event)
            new.append(event)
        return new

    def finish(self):
        """Close the outgoing window with existing evidence only.

        A live caller waits one window after capture stops before calling this.
        Offline EOF establishes that no further evidence will arrive. Two actual
        outgoing observations (or the explicit top-exit rule) are still required.
        """
        if self.finished or self.last_time is None:
            return []
        self.finished = True
        return self._confirm(self.last_time + self.config.velocity_window_seconds, ending=True)

    def result(self):
        return {'events': list(self.events),
                'estimated_count': sum(e['status'] == 'counted' for e in self.events),
                'floor_y': self.floor, 'stops': [],
                'pending_tail_samples': len(self.pending)}
