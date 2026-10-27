from copy import deepcopy
from juggling.toe_observations import reject_toe_spikes
from test_toe_taps import sample


def spike():
    return [sample(.0,-50),sample(.03,110,x=180),sample(.06,-50)]


def test_isolated_jump_is_removed_without_interpolating_or_mutating():
    seq=spike();original=deepcopy(seq)
    filtered,rejected=reject_toe_spikes(seq)
    assert filtered[1]['pose']=={}
    assert filtered[0] is seq[0] and filtered[2] is seq[2]
    assert seq==original
    assert rejected==[dict(frame=3,time=.03,side='left',reason='isolated_toe_jump')]


def test_consistent_departure_is_retained():
    seq=[sample(0,-50),sample(.03,110,x=180),sample(.06,110,x=180),sample(.09,-50)]
    assert reject_toe_spikes(seq)[1]==[]


def test_missing_ball_long_gap_or_new_segment_cannot_validate_a_spike():
    for field,value in [('status','predicted'),('time',.2),('segment',1)]:
        seq=spike();seq[2][field]=value
        assert reject_toe_spikes(seq)[1]==[]
