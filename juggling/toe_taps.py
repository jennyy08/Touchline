"""Observed foot approaches to the ball top, with independent per-foot state.

A contact is an estimate from 2D landmarks, not proof of physical contact.
Confirm an entry from multiple observed frames; a later departure rearms the
foot. Brief missing toe landmarks preserve state but contribute no evidence.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ToeTapConfig:
    horizontal_radius: float = .65
    top_min: float = -.95
    top_max: float = -.25
    release_margin: float = .08
    max_gap_seconds: float = .12
    min_contact_seconds: float = .05
    debounce_seconds: float = .22


def _state():
    return dict(last=None, armed=False, entry=None, inside=0,
                last_inside=None, observed_seconds=0.0)


def count_toe_taps(samples, config=None):
    c = config or ToeTapConfig()
    states = {side: _state() for side in ('left', 'right')}
    candidates = []
    usable = 0
    for sample in samples:
        t = sample['time']
        for side in states:
            state = states[side]
            points = [sample.get('pose', {}).get(side + '_' + name)
                      for name in ('big_toe', 'small_toe')]
            points = [point for point in points if point is not None]
            ball_valid = (sample['status'] == 'observed' and sample.get('center')
                          and sample.get('diameter', 0) and sample['diameter'] > 0)
            if not ball_valid:
                states[side] = _state()
                continue
            if state['last'] is not None and t - state['last'] > c.max_gap_seconds:
                state = states[side] = _state()
            if not points:
                # Keep an approach across a short toe-only dropout. Never accrue
                # confirmation time across that dropout or infer an unseen entry.
                state['last_inside'] = None
                continue
            usable += 1
            state['last'] = t
            x, y = sample['center']
            diameter = sample['diameter']
            px, py = min(points, key=lambda p: (p[0]-x)**2 + (p[1]-y+.5*diameter)**2)
            dx, dy = (px-x)/diameter, (py-y)/diameter
            inside = abs(dx) <= c.horizontal_radius and c.top_min <= dy <= c.top_max
            outside = (abs(dx) > c.horizontal_radius + c.release_margin
                       or dy < c.top_min - c.release_margin
                       or dy > c.top_max + c.release_margin)
            if outside:
                entry = state['entry']
                # A quick tap may leave before the sustained-contact timer fires.
                # Two observed in-zone frames plus a visible departure still
                # support the original entry/release evidence path.
                if entry is not None and state['inside'] >= 2 and t-entry['time'] >= c.min_contact_seconds:
                    candidates.append(dict(time=entry['time'], frame=entry['frame'],
                                           confirmed_time=t, body_part=side+'_foot',
                                           confirmation='departure'))
                state.update(armed=True, entry=None, inside=0,
                             last_inside=None, observed_seconds=0.)
            elif inside and state['armed']:
                if state['entry'] is None:
                    state['entry'] = sample
                if state['last_inside'] is not None:
                    state['observed_seconds'] += t - state['last_inside']
                state['last_inside'] = t
                state['inside'] += 1
                if state['inside'] >= 2 and state['observed_seconds'] + 1e-9 >= c.min_contact_seconds:
                    entry = state['entry']
                    candidates.append(dict(time=entry['time'], frame=entry['frame'],
                                           confirmed_time=t, body_part=side+'_foot',
                                           confirmation='sustained'))
                    # Holding the foot there is one event, including at clip end.
                    state.update(armed=False, entry=None, inside=0,
                                 last_inside=None, observed_seconds=0.)
            else:
                state['last_inside'] = None

    # Anatomical IDs can flip on overlap. Nearby supported approaches represent
    # one candidate, not two discarded contacts. Preserve every contributing time.
    groups = []
    for event in sorted(candidates, key=lambda e: e['time']):
        if groups and event['time'] - groups[-1][0]['time'] < c.debounce_seconds:
            groups[-1].append(event)
        else:
            groups.append([event])
    events = []
    for index, group in enumerate(groups):
        first = min(group, key=lambda e: (e["confirmation"] != "sustained", e["time"]))
        ambiguous = len({e['body_part'] for e in group}) > 1
        events.append(dict(id=f'tap-{index+1}', **first, status='counted',
                           reason='observed_ball_top_approach',
                           evidence_sources=['ball_detection', 'toe_landmarks'],
                           foot_identity_ambiguous=ambiguous,
                           merged_candidate_times=[e['time'] for e in group]))
        if ambiguous:
            events[-1]['body_part'] = None
    return dict(drill='toe_taps', estimated_count=len(events), events=events,
                floor_y=None, heard_count=0,
                toe_taps=dict(algorithm_version=2, config=asdict(c),
                              usable_foot_samples=usable,
                              possible_foot_samples=2*len(samples)))
