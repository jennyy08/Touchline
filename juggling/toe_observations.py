"""Reject isolated toe-ID jumps using adjacent observed video frames.

This is an offline one-frame lookahead, not trajectory interpolation. Removed
points become missing evidence; their neighbours keep their original positions.
"""
from math import dist


def reject_toe_spikes(samples, max_neighbor_gap=.08, return_radius=.35, min_jump=1.):
    def point(sample, side):
        if sample['status'] != 'observed' or not sample.get('diameter') or not sample.get('center'):
            return None
        points = [sample.get('pose', {}).get(side+'_'+name) for name in ('big_toe', 'small_toe')]
        points = [p for p in points if p is not None]
        if not points:
            return None
        x,y = sample['center']
        diameter = sample['diameter']
        px,py = min(points, key=lambda p:(p[0]-x)**2+(p[1]-y+.5*diameter)**2)
        return ((px-x)/diameter, (py-y)/diameter)

    output, rejected = list(samples), []
    for i in range(1, len(samples)-1):
        before,current,after = samples[i-1:i+2]
        if not (0 < current['time']-before['time'] <= max_neighbor_gap and
                0 < after['time']-current['time'] <= max_neighbor_gap):
            continue
        if not before.get('segment') == current.get('segment') == after.get('segment'):
            continue
        for side in ('left', 'right'):
            a,b,c = [point(sample,side) for sample in (before,current,after)]
            if any(p is None for p in (a,b,c)):
                continue
            if dist(a,c) < return_radius and min(dist(a,b),dist(b,c)) > min_jump:
                # Clone only the modified dictionaries. The UI/export retains raw data.
                output[i] = dict(output[i], pose=dict(output[i].get('pose', {})))
                for name in ('big_toe', 'small_toe'):
                    output[i]['pose'].pop(side+'_'+name, None)
                rejected.append(dict(frame=current['frame'], time=current['time'], side=side,
                                     reason='isolated_toe_jump'))
    return output, rejected
