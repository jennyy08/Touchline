"""Side-to-side observations, independent of HTTP, models, and presentation.

Coordinates are upright video pixels. Speed is horizontal image displacement per
second divided by practice-area width, NOT metres/second. Predictions never
support a turn. Pace never crosses gaps. Edge-return turns use observed approach
and return evidence, with a time interval instead of an invented exact instant.
"""
from dataclasses import dataclass, asdict
from statistics import median
import math
from pydantic import BaseModel, model_validator
from .edge_turns import infer_edge_returns


class DrillSetup(BaseModel):
    # Normalized x/y coordinates keep setup independent of inference resolution.
    roi: tuple[float, float, float, float] = (0, 0, 1, 1)
    markers: tuple[float, float] | None = None
    require_markers: bool = False

    @model_validator(mode='after')
    def valid_geometry(self):
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in self.roi):
            raise ValueError('Practice area coordinates must be between 0 and 1.')
        x1,y1,x2,y2 = self.roi
        if x2-x1 < .1 or y2-y1 < .1:
            raise ValueError('Practice area must cover at least 10% of the video in each direction.')
        if self.markers is not None:
            left,right = self.markers
            if not all(math.isfinite(v) for v in self.markers) or not x1 <= left < right <= x2 or right-left < .1:
                raise ValueError('Place two separated markers inside the practice area.')
        if self.require_markers and self.markers is None:
            raise ValueError('Set both markers before enabling marker feedback.')
        return self


@dataclass(frozen=True)
class DribbleConfig:
    gap_seconds: float = .15
    smoothing_seconds: float = .10
    # Hysteresis suppresses small foot-to-foot oscillations within a trip.
    reversal_width_fraction: float = .08
    reversal_diameters: float = 2.5
    minimum_trip_width_fraction: float = .18
    minimum_trip_seconds: float = .4
    pace_inset_fraction: float = .15  # Time the middle 70% of marker spacing.
    slow_ratio: float = .75
    minimum_comparison_trips: int = 3
    edge_return_max_gap_seconds: float = 6.0
    edge_visit_max_seconds: float = 10.0
    edge_direction_seconds: float = .8
    edge_zone_width_fraction: float = .12
    edge_boundary_margin_fraction: float = .025
    edge_approach_width_fraction: float = .06
    edge_return_width_fraction: float = .08
    edge_minimum_size_ratio: float = .7


def analyze_dribbling(samples, width, setup: DrillSetup, config=None):
    c = config or DribbleConfig()
    area_width = width * (setup.roi[2]-setup.roi[0])
    runs, run = [], []
    for s in samples:
        if s['status'] != 'observed' or not s['center']:
            continue
        if run and (s['segment'] != run[-1]['segment'] or s['time']-run[-1]['time'] > c.gap_seconds):
            runs.append(run); run=[]
        run.append(s)
    if run: runs.append(run)
    turns, trips = [], []
    for run_id, run in enumerate(runs):
        # Local median removes box jitter without connecting separate observations.
        points=[]
        lo=hi=0
        for s in run:
            while run[lo]['time'] < s['time']-c.smoothing_seconds: lo+=1
            while hi < len(run) and run[hi]['time'] <= s['time']+c.smoothing_seconds: hi+=1
            points.append({**s, 'x':median(p['center'][0] for p in run[lo:hi])})
        if not points: continue
        threshold=max(area_width*c.reversal_width_fraction, median(p['diameter'] for p in points)*c.reversal_diameters)
        low=high=extreme=points[0]; direction=0; run_turns=[]
        for p in points[1:]:
            if not direction:
                if p['x'] < low['x']: low=p
                if p['x'] > high['x']: high=p
                if p['x']-low['x'] >= threshold: direction=1; extreme=p
                elif high['x']-p['x'] >= threshold: direction=-1; extreme=p
                continue
            if direction*(p['x']-extreme['x']) >= 0:
                extreme=p
            elif direction*(extreme['x']-p['x']) >= threshold:
                # Median confirms direction; use an actual nearby observation for
                # marker reach and event timing so smoothing cannot shorten a trip.
                nearby=[q for q in points if abs(q['time']-extreme['time']) <= c.smoothing_seconds]
                observed=max(nearby,key=lambda q:direction*q['center'][0])
                contact={**observed, 'x':observed['center'][0]}
                side='right' if direction==1 else 'left'
                reach='not_assessed'; shortfall=None
                # Boundary exits cannot establish the location of the true turn.
                edge=min(contact['x']-width*setup.roi[0], width*setup.roi[2]-contact['x'])
                if setup.require_markers and edge > contact['diameter']:
                    marker=width*setup.markers[1 if direction==1 else 0]
                    shortfall=direction*(marker-contact['x'])-contact['diameter']/2
                    reach='reached' if shortfall<=0 else 'near' if shortfall<=contact['diameter'] else 'short'
                event={'id':f'turn-{len(turns)+len(run_turns)+1}', 'time':contact['time'],
                       'frame':contact['frame'], 'x':contact['x'], 'side':side,
                       'run':run_id, 'marker_status':reach, 'shortfall_pixels':shortfall,
                       'confirmed_at':p['time'], 'evidence':'visible_reversal', 'time_kind':'observed'}
                run_turns.append(event)
                direction=-direction; extreme=p
        for a,b in zip(run_turns,run_turns[1:]):
            distance=abs(b['x']-a['x']); duration=b['time']-a['time']
            if distance < c.minimum_trip_width_fraction*area_width or duration < c.minimum_trip_seconds: continue
            trips.append({'id':f'trip-{len(trips)+1}', 'start':a['time'], 'end':b['time'],
                          'direction':b['side'], 'duration':duration,
                          'speed':distance/area_width/duration, 'end_turn_id':b['id'],
                          'relative_speed':None, 'slower':False})
        turns.extend(run_turns)
    if setup.markers is not None:
        # Compare equal distances when markers exist. This still measures useful
        # trips when the player turns beyond the camera edge. Never span a gap.
        trips=[]
        left,right=[m*width for m in setup.markers]
        inset=(right-left)*c.pace_inset_fraction
        left+=inset; right-=inset
        for run in runs:
            pending=None
            for a,b in zip(run,run[1:]):
                ax,bx=a['center'][0],b['center'][0]
                if ax==bx: continue
                direction='right' if bx>ax else 'left'
                boundaries=(left,right) if bx>ax else (right,left)
                for boundary in boundaries:
                    crossed=(ax < boundary <= bx) if bx>ax else (bx <= boundary < ax)
                    if not crossed:continue
                    t=a['time']+(b['time']-a['time'])*(boundary-ax)/(bx-ax)
                    departure=boundary==boundaries[0]
                    if departure:
                        pending=(direction,t)
                    elif pending and pending[0]==direction:
                        duration=t-pending[1]
                        if duration>=c.minimum_trip_seconds:
                            trips.append({'id':f'trip-{len(trips)+1}', 'start':pending[1], 'end':t,
                                          'direction':direction, 'duration':duration,
                                          'speed':(right-left)/area_width/duration,
                                          'relative_speed':None,'slower':False, 'basis':'inner_marker_section'})
                        pending=None
    review_windows=[]
    for before,after in zip(runs,runs[1:]):
        gap=after[0]['time']-before[-1]['time']
        if not .15 < gap <= 2.5: continue
        incoming=[s for s in before if s['time'] >= before[-1]['time']-.6]
        outgoing=[s for s in after if s['time'] <= after[0]['time']+.6]
        dx_in=incoming[-1]['center'][0]-incoming[0]['center'][0]
        dx_out=outgoing[-1]['center'][0]-outgoing[0]['center'][0]
        if dx_in*dx_out<0 and min(abs(dx_in),abs(dx_out)) >= area_width*.06:
            review_windows.append({'start':before[-1]['time'], 'end':after[0]['time'],
                                   'side':'right' if dx_in>0 else 'left',
                                   'reason':'Opposite travel directions around a tracking gap. A turn may be hidden; its time and marker reach are unverified.'})
    turns.extend(infer_edge_returns(samples, width, setup, c, turns))
    turns.sort(key=lambda t: t['time'])
    for direction in ('left','right'):
        group=[t for t in trips if t['direction']==direction]
        if len(group) >= c.minimum_comparison_trips:
            typical=median(t['speed'] for t in group)
            for t in group:
                t['relative_speed']=t['speed']/typical
                t['slower']=t['relative_speed'] < c.slow_ratio
    return {'analysis_revision':'edge-return-v1', 'setup':setup.model_dump(), 'config':asdict(c), 'turns':turns, 'trips':trips,
            'speed_unit':'practice-area widths / second',
            'review_windows':review_windows,
            'trip_basis':'inner_marker_section' if setup.markers is not None else 'turn_to_turn',
            'pace_gates': [left/width,right/width] if setup.markers is not None else None,
            'notes':['Speed measures sideways ball movement in this camera view, not running speed or metres per second.',
                     'Slower means over 25% below the median of at least 3 trips in the same direction. Pauses and shorter trips can affect it.',
                     'Turns include visible reversals and inferred same-edge returns. Inferred turns show a time interval; their exact moment and hidden marker reach are not measured.',
                     'With markers, pace measures the middle 70% of their spacing, not a whole repetition. Otherwise trips run between visible turns. Incomplete sections and sections spanning tracking gaps are omitted.',
                     'Marker reach uses the ball edge, not your feet. Near-marker and boundary-obscured turns need your review.']}
