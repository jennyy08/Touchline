"""Toe-tap entry/release cycles. No ball bounce or cadence-only counting.

Distances use the observed ball diameter. Missing evidence resets a cycle;
we never manufacture alternating feet or count a foot resting on the ball.
"""
from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class ToeTapConfig:
    horizontal_radius: float = .65
    top_min: float = -.95
    top_max: float = -.25
    release_margin: float = .08
    max_gap_seconds: float = .12
    min_contact_seconds: float = .05
    max_contact_seconds: float = 1.0
    debounce_seconds: float = .22


def count_toe_taps(samples, config=None):
    c = config or ToeTapConfig()
    events = []
    states = {s: dict(armed=False, entry=None, last=None, last_event=-math.inf, inside_frames=0) for s in ('left','right')}
    usable = 0
    for sample in samples:
        t = sample['time']
        for side, state in states.items():
            pose = sample.get('pose', {})
            points = [pose[k] for k in (side+'_big_toe', side+'_small_toe') if k in pose]
            valid = sample['status'] == 'observed' and sample.get('center') and sample.get('diameter') and points
            if not valid or (state['last'] is not None and t-state['last'] > c.max_gap_seconds):
                state.update(armed=False, entry=None, last=None, inside_frames=0)
                if not valid:
                    continue
            state['last'] = t
            usable += 1
            x,y = sample['center']; diameter = sample['diameter']
            # Pick the toe closest to the top-center of the ball.
            px,py = min(points, key=lambda p: (p[0]-x)**2+(p[1]-(y-diameter*.5))**2)
            dx,dy = (px-x)/diameter, (py-y)/diameter
            inside = abs(dx)<=c.horizontal_radius and c.top_min<=dy<=c.top_max
            outside = abs(dx)>c.horizontal_radius+c.release_margin or dy<c.top_min-c.release_margin or dy>c.top_max+c.release_margin
            if inside and state['armed'] and state['entry'] is None:
                state['entry'] = sample
                state['inside_frames'] = 0
            if inside and state['entry'] is not None:
                state['inside_frames'] += 1
            if outside:
                entry = state['entry']
                if entry is not None:
                    duration = t-entry['time']
                    if state['inside_frames']>=2 and c.min_contact_seconds<=duration<=c.max_contact_seconds and entry['time']-state['last_event']>=c.debounce_seconds:
                        events.append(dict(id=f"tap-{len(events)+1}",time=entry['time'],frame=entry['frame'],status='counted',reason='toe_entered_ball_top_then_released',body_part=side+'_foot',evidence_sources=['ball_detection','toe_landmarks'],end_time=t))
                        state['last_event']=entry['time']
                state.update(armed=True,entry=None)
            elif state['entry'] is not None and t-state['entry']['time']>c.max_contact_seconds:
                state.update(armed=False,entry=None)
    events.sort(key=lambda e:e['time'])
    # Simultaneous feet often indicate confused landmarks: expose, do not count.
    for a,b in zip(events,events[1:]):
        if b['time']-a['time']<c.debounce_seconds:
            for event in (a,b):
                event.update(status='review',reason='overlapping_foot_cycles')
    return dict(drill='toe_taps',estimated_count=sum(e['status']=='counted' for e in events),events=events,floor_y=None,heard_count=0,
                toe_taps=dict(config=asdict(c),usable_foot_samples=usable,possible_foot_samples=2*len(samples)))
