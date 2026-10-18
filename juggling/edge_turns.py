"""Infer one turn from an observed approach to an image edge and return.

We do not reconstruct the hidden path or assign an exact contact time. The
interval begins on approach and ends when inward movement confirms the return.
Short fragmented tracks are allowed here; pace calculations still split at gaps.
"""
from statistics import median


def infer_edge_returns(samples, width, setup, config, visible_turns):
    observed = [s for s in samples if s['status'] == 'observed' and s['center']]
    area_width = width * (setup.roi[2] - setup.roi[0])
    history = []
    active = None
    inferred = []

    for sample in observed:
        time = sample['time']
        x = sample['center'][0]
        diameter = sample['diameter']
        if history and time - history[-1]['time'] > config.edge_return_max_gap_seconds:
            active = None
            history = []
        history.append(sample)
        recent = [s for s in history if time - s['time'] <= config.edge_direction_seconds]
        history = recent

        if active is None:
            if len(recent) < 3:
                continue
            dx = x - recent[0]['center'][0]
            if abs(dx) < config.edge_approach_width_fraction * area_width:
                continue
            side = 'left' if dx < 0 else 'right'
            # Only actual image edges, not an arbitrary user crop boundary.
            boundary_distance = x if side == 'left' else width - x
            zone = max(width * config.edge_zone_width_fraction, diameter * 1.5)
            if boundary_distance > zone:
                continue
            active = {'side': side, 'start': time, 'first': sample,
                      'extreme': sample, 'touches_edge': False, 'recent': [],
                      'approach_diameter': median(s['diameter'] for s in recent)}

        side = active['side']
        sign = -1 if side == 'left' else 1
        # A jump to the opposite edge is not a return from the same edge.
        if (side == 'left' and x > width * .75) or (side == 'right' and x < width * .25):
            active = None
            continue
        if time - active['start'] > config.edge_visit_max_seconds:
            active = None
            continue
        if sign * (x - active['extreme']['center'][0]) >= 0:
            active['extreme'] = sample
        box = sample.get('box')
        ball_edge = (box[0] if side == 'left' else width - box[2]) if box else (
            (x if side == 'left' else width - x) - diameter / 2)
        if ball_edge <= width * config.edge_boundary_margin_fraction:
            active['touches_edge'] = True

        active['recent'].append(sample)
        returning = [s for s in active['recent'] if time - s['time'] <= config.edge_direction_seconds]
        active['recent'] = returning
        retreat = -sign * (x - active['extreme']['center'][0])
        needed = max(area_width * config.edge_return_width_fraction,
                     median(s['diameter'] for s in returning) * .75)
        inward_trend = -sign * (x - returning[0]['center'][0])
        plausible_size = diameter >= active['approach_diameter'] * config.edge_minimum_size_ratio
        if (not active['touches_edge'] or not plausible_size or retreat < needed or len(returning) < 3
                or inward_trend < area_width * config.edge_approach_width_fraction):
            continue

        start, end = active['start'], time
        # A visible reversal and its edge return describe the same turn.
        duplicate = any(t['side'] == side and start - .2 <= t['time'] <= end
                        for t in visible_turns)
        if not duplicate:
            inferred.append({
                'id': f'edge-turn-{len(inferred) + 1}',
                'time': start, 'time_interval': {'start': start, 'end': end},
                'time_kind': 'interval', 'evidence': 'inferred_edge_return',
                'frame': active['first']['frame'], 'x': None, 'side': side,
                'marker_status': 'not_assessed', 'shortfall_pixels': None,
                'confirmed_at': end,
                'reason': 'Observed outward approach at this image edge, then inward return from the same side. Exact turn time and hidden marker reach were not observed.',
            })
        active = None
        # Require a fresh outward approach before another turn on this side.
        history = [sample]
    return inferred
