from juggling.toe_taps import count_toe_taps

def sample(t,y,x=0,status='observed',side='left'):
    return dict(frame=round(t*100),time=t,status=status,center=[0,0],diameter=100,
                pose={side+'_big_toe':[x,y]})

def cycle(start=0,side='left'):
    return [sample(start,30,side=side), sample(start+.1,-50,side=side),
            sample(start+.15,-50,side=side),sample(start+.2,30,side=side)]

def test_entry_release_counts_once():
    r=count_toe_taps(cycle()); assert r['estimated_count']==1
    assert r['events'][0]['time']==.1

def test_initial_contact_is_excluded_and_observed_entry_then_hold_counts_once():
    assert count_toe_taps([sample(t,-50) for t in [0,.05,.1,.15,.2]])['estimated_count']==0
    assert count_toe_taps([sample(0,30)]+[sample(i*.05,-50) for i in range(1,30)]+[sample(1.5,30)])['estimated_count']==1

def test_predicted_and_missing_foot_break_cycle():
    for replacement in [sample(.15,-50,status='predicted'),dict(sample(.15,-50),pose={})]:
        seq=cycle();seq[2]=replacement
        assert count_toe_taps(seq)['estimated_count']==0

def test_confirmed_final_contact_does_not_need_departure():
    assert count_toe_taps(cycle()[:3])['estimated_count']==1
    assert count_toe_taps(cycle()[:2])['estimated_count']==0

def test_long_gap_before_confirmation_does_not_count():
    seq=[sample(0,30),sample(.1,-50),sample(.5,-50),sample(.55,-50),sample(.6,30)]
    assert count_toe_taps(seq)['estimated_count']==0

def test_floor_and_side_foot_do_not_count():
    assert count_toe_taps([sample(t,30) for t in [0,.1,.2,.3]])['estimated_count']==0
    assert count_toe_taps([dict(s,pose={'left_big_toe':[150,-50]}) for s in cycle()])['estimated_count']==0

def test_single_frame_glitch_does_not_count():
    assert count_toe_taps([sample(0,30),sample(.05,-50),sample(.1,30)])['estimated_count']==0

def test_irregular_timestamps_and_repeated_same_foot():
    seq=cycle()+cycle(.5)
    assert count_toe_taps(seq)['estimated_count']==2

def test_overlapping_foot_ids_merge_without_discarding_contact():
    seq=cycle()
    for s in seq:s['pose']['right_big_toe']=s['pose']['left_big_toe']
    r=count_toe_taps(seq)
    assert r['estimated_count']==1 and len(r['events'])==1
    assert r['events'][0]['foot_identity_ambiguous']
    assert r['events'][0]['body_part'] is None

def test_short_toe_dropout_preserves_arming_but_is_not_contact_evidence():
    seq=[sample(0,30),dict(sample(.03,30),pose={}),sample(.06,-50),sample(.12,-50)]
    assert count_toe_taps(seq)['estimated_count']==1
    seq=[sample(0,30),sample(.03,-50),dict(sample(.06,-50),pose={}),sample(.1,-50)]
    assert count_toe_taps(seq)['estimated_count']==0

def test_fast_two_frame_contact_can_be_confirmed_by_departure():
    seq=[sample(0,30),sample(.03,-50),sample(.06,-50),sample(.1,30)]
    assert count_toe_taps(seq)['estimated_count']==1
