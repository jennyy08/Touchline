import pytest
from juggling.live_settings import FrameGate, FootSchedule, LiveSettings


def track(y=50, status='observed', segment=0):
    return {'status':status,'center':[50,y] if status=='observed' else None,
            'diameter':20 if status=='observed' else None,'segment':segment}


def test_timestamp_sampling_handles_jitter_without_halving_30fps():
    times=[i/30 + (0.001 if i%3 else 0) for i in range(30)]
    gate=FrameGate(30)
    assert sum(gate.accept(t) for t in times)==30
    gate=FrameGate(15)
    assert sum(gate.accept(t) for t in times)==15


def test_sampling_is_time_based_across_long_capture_gap():
    gate=FrameGate(15)
    assert [gate.accept(t) for t in (4.,4.01,4.07,5.3,5.31)]==[True,False,True,True,False]
    with pytest.raises(ValueError):gate.accept(5.0)


def test_near_schedule_uses_descent_and_periodic_floor_refresh():
    scheduler=FootSchedule(LiveSettings(feet='near'))
    pose={'left_ankle':[50,100]};box=[0,0,200,200]
    assert scheduler.decide(0,track(50),pose,box)  # floor refresh
    assert not scheduler.decide(.033,track(40),pose,box)  # ascending
    assert scheduler.decide(.066,track(60),pose,box)  # descending near leg
    assert not scheduler.decide(.1,track(20),pose,box)
    assert scheduler.decide(.6,track(10),pose,box)  # refresh without descent


def test_gap_does_not_supply_velocity_or_stale_foot_evidence():
    scheduler=FootSchedule(LiveSettings(feet='near'))
    pose={'left_ankle':[50,100]};box=[0,0,200,200]
    scheduler.decide(0,track(),pose,box)
    assert not scheduler.decide(.03,track(status='predicted'),pose,box)
    assert not scheduler.decide(.06,track(70),pose,box)
    assert not scheduler.decide(.09,track(80,segment=1),pose,box)


def test_no_person_and_disabled_feet_never_run_model():
    for mode in ('all','near','off'):
        assert not FootSchedule(LiveSettings(feet=mode)).decide(0,track(),{},None)
    assert not FootSchedule(LiveSettings(feet='off')).decide(0,track(),{},[0,0,100,100])


def test_long_observation_gap_does_not_trigger_near_contact_schedule():
    scheduler = FootSchedule(LiveSettings(feet='near'))
    pose = {'left_ankle': [50, 100]}
    box = [0, 0, 200, 200]
    assert scheduler.decide(0, track(50), pose, box)
    # Still before the floor-refresh deadline, but too late to infer descent.
    assert not scheduler.decide(.3, track(60), pose, box)
    assert scheduler.decide(.33, track(70), pose, box)
