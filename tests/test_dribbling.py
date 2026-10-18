import numpy as np
import pytest
from juggling.dribbling import DrillSetup, analyze_dribbling
from juggling.dribble_scene import moving_detections


def trajectory(xs, times=None, segment=0):
    return [dict(frame=i,time=times[i] if times is not None else i*.05,status='observed',
                 center=[x,300],diameter=20,segment=segment,pose={}) for i,x in enumerate(xs)]


def trips_path(durations):
    samples=[];t=0
    for i,duration in enumerate(durations):
        a,b=(100,900) if i%2==0 else (900,100)
        for j in range(40):
            samples.append(dict(frame=len(samples),time=t+j*duration/40,status='observed',center=[a+(b-a)*j/40,300],diameter=20,segment=0,pose={}))
        t+=duration
    return samples


def test_turns_not_small_touches_or_incomplete_ends():
    result=analyze_dribbling(trips_path([2]*8),1000,DrillSetup())
    assert len(result['turns'])==7
    assert len(result['trips'])==6
    assert [t['side'] for t in result['turns']]==['right','left','right','left','right','left','right']
    assert not analyze_dribbling(trajectory([500,510,490,520,500]*10),1000,DrillSetup())['turns']


def test_marker_goal_reached_short_near_and_optional():
    samples=trips_path([2]*4)
    for markers,expected in [((.1,.9),'reached'),((0,1),'short'),((.08,.92),'near')]:
        r=analyze_dribbling(samples,1000,DrillSetup(markers=markers,require_markers=True))
        assert all(t['marker_status']==expected for t in r['turns'])
    assert all(t['marker_status']=='not_assessed' for t in analyze_dribbling(samples,1000,DrillSetup())['turns'])


def test_slow_same_direction_and_timestamp_based():
    r=analyze_dribbling(trips_path([2,2,2,2,2,4,2,2,2]),1000,DrillSetup())
    slow=[t for t in r['trips'] if t['slower']]
    assert len(slow)==1
    assert slow[0]['direction']=='left'
    assert slow[0]['relative_speed']==pytest.approx(.5,abs=.05)


def test_long_gaps_reacquisition_predictions_do_not_make_turn():
    samples=trips_path([2,2])
    for s in samples[35:45]: s['status']='predicted'
    assert analyze_dribbling(samples,1000,DrillSetup())['turns']==[]
    samples=trips_path([2,2])
    for s in samples[40:]:s['segment']=1
    assert analyze_dribbling(samples,1000,DrillSetup())['turns']==[]


def test_short_gap_and_irregular_timestamps():
    samples=trips_path([2,2,2,2])
    samples.pop(20)
    samples[50]['status']='predicted'
    r=analyze_dribbling(samples,1000,DrillSetup())
    assert len(r['turns'])==3
    assert len(r['trips'])==2
    assert all(t['relative_speed'] is None for t in r['trips'])


@pytest.mark.parametrize('kwargs',[{'roi':(0,0,.01,1)},{'roi':(0,0,float('nan'),1)}, {'markers':(.8,.2)}, {'require_markers':True}, {'roi':(.3,0,1,1),'markers':(.1,.8)}])
def test_invalid_setup(kwargs):
    with pytest.raises(ValueError):DrillSetup(**kwargs)


def test_static_background_rejects_fixed_objects():
    ref=np.zeros((320,480,3),dtype=np.uint8); image=ref.copy();image[100:140,200:240]=150
    fixed={'box':[20,100,60,140],'score':.9}; ball={'box':[200,100,240,140],'score':.4}
    assert moving_detections(image,[fixed,ball],ref)==[ball]


def test_marker_crossings_measure_equal_distance_without_visible_turns():
    samples=trajectory(np.linspace(0,1000,51))
    r=analyze_dribbling(samples,1000,DrillSetup(markers=(.2,.8)))
    assert not r['turns']
    assert len(r['trips'])==1
    assert r['trips'][0]['duration']==pytest.approx(1.05)
    assert r['trips'][0]['speed']==pytest.approx(.4)
    samples[25]['status']='lost';samples[26]['status']='lost';samples[27]['status']='lost'
    assert not analyze_dribbling(samples,1000,DrillSetup(markers=(.2,.8)))['trips']


def test_hidden_reversal_is_review_interval_not_turn_or_speed():
    samples=trips_path([2,2])
    for s in samples[35:45]:s['status']='lost'
    r=analyze_dribbling(samples,1000,DrillSetup())
    assert not r['turns'] and not r['trips']
    assert len(r['review_windows'])==1
    assert r['review_windows'][0]['start'] < 2 < r['review_windows'][0]['end']


def edge_excursion(side='left', gap=2):
    """Approach and re-enter the same image edge, with a real observation gap."""
    xs=list(np.linspace(600,10,21))+list(np.linspace(10,600,21))
    times=list(np.linspace(0,1,21))+list(np.linspace(1+gap,2+gap,21))
    if side=='right': xs=[1000-x for x in xs]
    samples=trajectory(xs,times)
    for s in samples[21:]:s['segment']=1
    return samples


@pytest.mark.parametrize('side',['left','right'])
def test_edge_exit_and_return_counts_one_inferred_turn(side):
    r=analyze_dribbling(edge_excursion(side),1000,DrillSetup())
    assert len(r['turns'])==1 and not r['trips']
    t=r['turns'][0]
    assert t['side']==side and t['evidence']=='inferred_edge_return'
    assert t['time_kind']=='interval' and t['marker_status']=='not_assessed'
    assert t['time_interval']['start'] < 1 < 3 < t['time_interval']['end']


def test_edge_exit_without_return_or_with_long_absence_is_not_turn():
    assert not analyze_dribbling(edge_excursion()[:21],1000,DrillSetup())['turns']
    assert not analyze_dribbling(edge_excursion(gap=7),1000,DrillSetup())['turns']


def test_opposite_edge_reappearance_is_not_same_side_return():
    samples=edge_excursion()
    for s in samples[21:]:s['center'][0]=1000-s['center'][0]
    assert not analyze_dribbling(samples,1000,DrillSetup())['turns']


def test_visible_edge_turn_not_counted_again_as_inferred():
    samples=edge_excursion(gap=.05)
    for s in samples:s['segment']=0
    r=analyze_dribbling(samples,1000,DrillSetup())
    assert len(r['turns'])==1
    assert r['turns'][0]['evidence']=='visible_reversal'


def test_small_stationary_object_reacquisition_cannot_confirm_return():
    samples=edge_excursion()
    for s in samples[21:]:s['diameter']=5
    assert not analyze_dribbling(samples,1000,DrillSetup())['turns']


def test_predictions_cannot_confirm_edge_return():
    samples=edge_excursion()
    for s in samples[21:]:s['status']='predicted'
    assert not analyze_dribbling(samples,1000,DrillSetup())['turns']


def test_crop_boundary_is_not_camera_exit():
    samples=edge_excursion()
    for s in samples:s['center'][0]=300+s['center'][0]*.4
    assert not analyze_dribbling(samples,1000,DrillSetup(roi=(.3,0,.8,1)))['turns']


def test_supplied_clip_three_recovers_user_reported_early_turns():
    """Regression against the user's approximate intervals, not an accuracy score."""
    import json
    from pathlib import Path
    result=json.loads((Path(__file__).resolve().parents[1]/'validation/dribbling-revision/clip-3-result.json').read_text())
    r=analyze_dribbling(result['samples'],result['video']['width'],DrillSetup.model_validate(result['dribbling']['setup']))
    inferred=[t for t in r['turns'] if t['evidence']=='inferred_edge_return']
    for time in (2.7,7.5,10,14.5,19):
        assert sum(t['time_interval']['start']-.3<=time<=t['time_interval']['end']+.3 for t in inferred)==1
    assert len(r['turns'])==15
    assert len(r['trips'])==9  # Edge inference must not fabricate timed sections.
