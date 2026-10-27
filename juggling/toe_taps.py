"""Observed foot approaches to the ball top, with independent per-foot state.

A contact is an estimate from 2D landmarks, not proof of physical contact.
Confirm an entry from multiple observed frames; a later departure rearms the
foot. Brief missing toe landmarks preserve state but contribute no evidence.
"""
from dataclasses import asdict, dataclass
from .toe_observations import reject_toe_spikes


@dataclass(frozen=True)
class ToeTapConfig:
    horizontal_radius: float = .65
    top_min: float = -.95
    top_max: float = -.25
    release_margin: float = .08
    max_gap_seconds: float = .12
    ball_context_seconds: float = .2
    ball_reacquisition_radius: float = 1.0
    ball_reacquisition_size_ratio: float = .75
    spike_neighbor_seconds: float = .08
    spike_return_radius: float = .35
    spike_min_jump: float = 1.0
    min_contact_seconds: float = .05
    debounce_seconds: float = .22
    contact_interruption_seconds: float = .08
    toe_offset_jump: float = .5
    stable_ankle_motion: float = .25


def _state():
    return dict(last=None, armed=False, entry=None, inside=0,
                last_inside=None, observed_seconds=0.0, active=None, geometry=None, last_contact=None)


def count_toe_taps(samples, config=None):
    c = config or ToeTapConfig()
    samples, rejected = reject_toe_spikes(samples, c.spike_neighbor_seconds,
                                        c.spike_return_radius, c.spike_min_jump)
    states = {side: _state() for side in ('left', 'right')}
    candidates = []
    usable = 0
    last_ball = None
    ball_gap = False
    for sample in samples:
        t = sample['time']
        ball_valid = (sample['status'] == 'observed' and sample.get('center')
                      and sample.get('diameter', 0) and sample['diameter'] > 0)
        if ball_valid:
            if ball_gap:
                continuous = (last_ball is not None and t-last_ball['time'] <= c.ball_context_seconds and
                              sum((a-b)**2 for a,b in zip(sample['center'],last_ball['center']))**.5 <=
                              c.ball_reacquisition_radius*last_ball['diameter'] and
                              c.ball_reacquisition_size_ratio <= sample['diameter']/last_ball['diameter'] <= 1/c.ball_reacquisition_size_ratio)
                if not continuous:
                    states = {side: _state() for side in states}
            last_ball, ball_gap = sample, False
        else:
            ball_gap = True
        for side in states:
            state = states[side]
            points = [sample.get('pose', {}).get(side + '_' + name)
                      for name in ('big_toe', 'small_toe')]
            points = [point for point in points if point is not None]
            if not ball_valid:
                # Retain only a previously observed off-ball state across a short
                # local occlusion. Discard every partial/active contact: predicted
                # ball frames never contribute contact observations or duration.
                armed = state['armed'] and last_ball is not None and t-last_ball['time'] <= c.ball_context_seconds
                states[side] = _state()
                states[side]['armed'] = armed
                continue
            if state['last'] is not None and t - state['last'] > c.max_gap_seconds:
                state = states[side] = _state()
            # A toe can jump to the floor while its ankle barely moves. Treat
            # that inconsistent frame as missing, never as an observed release.
            ankle = sample.get('pose', {}).get(side + '_ankle')
            geometry = state['geometry']
            if points and ankle is not None:
                d = sample['diameter']
                toe = min(points, key=lambda p: (p[0]-sample['center'][0])**2 +
                          (p[1]-sample['center'][1]+.5*d)**2)
                offset = ((toe[0]-ankle[0])/d, (toe[1]-ankle[1])/d)
                if geometry is not None and t-geometry[0] <= c.max_gap_seconds:
                    _, old_ankle, old_offset = geometry
                    ankle_motion = sum(((ankle[i]-old_ankle[i])/d)**2 for i in (0,1))**.5
                    offset_jump = offset[1] - old_offset[1]
                    if ankle_motion < c.stable_ankle_motion and offset_jump > c.toe_offset_jump:
                        points = []
                if points:
                    state['geometry'] = (t, ankle, offset)
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
            outside = (all(abs((point[0]-x)/diameter) > c.horizontal_radius for point in points)
                       or dy < c.top_min - c.release_margin
                       or dy > c.top_max + c.release_margin)
            # Retain actual observed support after confirmation so an overlapping
            # short landmark glitch cannot outrank a longer supported approach.
            if inside:
                state['last_contact'] = t
            if inside and state['active'] is not None:
                state['active']['support_frames'] += 1
                state['active']['contact_end'] = t
            if outside:
                if state['active'] is not None:
                    state['active']['departure_time'] = t
                state['active'] = None
                entry = state['entry']
                # A quick tap may leave before the sustained-contact timer fires.
                # Two observed in-zone frames plus a visible departure still
                # support the original entry/release evidence path.
                if entry is not None and state['inside'] >= 2 and t-entry['time'] >= c.min_contact_seconds:
                    candidates.append(dict(time=entry['time'], frame=entry['frame'],
                                           confirmed_time=t, body_part=side+'_foot',
                                           confirmation='departure', support_frames=state['inside'],
                                           contact_end=state['last_contact'], departure_time=t))
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
                                           confirmation='sustained', support_frames=state['inside'],
                                           contact_end=t, departure_time=None))
                    state['active'] = candidates[-1]
                    # Holding the foot there is one event, including at clip end.
                    state.update(armed=False, entry=None, inside=0,
                                 last_inside=None, observed_seconds=0.)
            else:
                state['last_inside'] = None

    # A brief release/re-entry of the same landmark during a confirmed
    # contact is commonly a pose excursion. Merge its evidence interval rather
    # than allowing candidate grouping to split a sustained hold into two taps.
    continuous = []
    for event in sorted(candidates, key=lambda e: e['time']):
        previous = next((e for e in reversed(continuous)
                         if e['body_part'] == event['body_part']), None)
        if (previous is not None and previous['contact_end'] is not None and
                event['time'] - previous.get('interrupted_entry_times', [previous['time']])[-1] < c.debounce_seconds and
                0 <= event['time'] - previous['contact_end'] <= c.contact_interruption_seconds and
                all(s['status'] == 'observed' for s in samples
                    if previous['contact_end'] <= s['time'] <= event['time'])):
            previous['contact_end'] = event['contact_end']
            previous['departure_time'] = event['departure_time']
            previous['support_frames'] += event['support_frames']
            previous.setdefault('interrupted_entry_times', []).append(event['time'])
        else:
            continuous.append(event)
    candidates = continuous

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
        first = min(group, key=lambda e: (e["confirmation"] != "sustained", -e["support_frames"], e["time"]))
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
                toe_taps=dict(algorithm_version=6, config=asdict(c),
                              rejected_toe_observations=rejected,
                              usable_foot_samples=usable,
                              possible_foot_samples=2*len(samples)))


def analyze_toe_taps(samples, config=None):
    """Keep primary evidence and add only separated, supported alternate events.

    Multiple views are not independent votes or confidence scores. They can
    share errors. Events near an existing contact are not counted twice.
    """
    c = config or ToeTapConfig()
    result = count_toe_taps(samples, c)
    for event in result['events']:
        event['observation_view'] = 'pose'
    result['toe_taps']['rejected_by_view'] = {'pose': result['toe_taps']['rejected_toe_observations']}
    for view in ('motion_pose', 'detail_pose'):
        alternate = [dict(s, pose=s.get(view, {})) for s in samples]
        counted = count_toe_taps(alternate, c)
        result['toe_taps']['rejected_by_view'][view] = counted['toe_taps']['rejected_toe_observations']
        for event in counted['events']:
            if any(e.get('interrupted_entry_times') and
                   e['time'] <= event['time'] <= (e.get('contact_end') or e['time'])
                   for e in result['events']):
                continue
            distance = min((abs(event['time']-e['time']) for e in result['events']), default=float('inf'))
            if distance < c.debounce_seconds:
                # A delayed reacquisition can sit close to the following tap.
                # Preserve it for inspection, not as an extra automatic count.
                recent_gap = any(event['time']-.25 <= s['time'] < event['time'] and
                                 s['status'] != 'observed' for s in samples)
                if distance <= .12 or not recent_gap:
                    continue
                event = dict(event, status='review', reason='reacquired_contact_timing_ambiguous')
            event['observation_view'] = view
            event['evidence_sources'] = ['ball_detection', 'toe_landmarks',
                                         'measured_image_motion' if view == 'motion_pose' else 'lower_body_crop']
            # Stable image tracks are not verified anatomical identities.
            if view == 'motion_pose':
                event['body_part'] = None
                event['foot_identity_ambiguous'] = True
            result['events'].append(event)
    result['events'].sort(key=lambda e:e['time'])
    for i,event in enumerate(result['events']):
        event['id'] = f'tap-{i+1}'
    result['estimated_count'] = sum(e['status'] == 'counted' for e in result['events'])
    result['toe_taps'].update(algorithm_version=6,
                             observation_views=['pose', 'motion_pose', 'detail_pose'])
    return result
