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

def test_lateral_departure_rearms_even_inside_vertical_release_margin():
    seq=cycle()[:3]+[sample(.2,-50,x=71),sample(.26,-50,x=71),sample(.34,-50),sample(.4,-50)]
    assert count_toe_taps(seq)['estimated_count']==2


def test_longer_observed_contact_wins_over_nearby_short_candidate():
    seq=[sample(0,30),sample(.03,-50),sample(.09,-50),sample(.12,30),
         sample(.18,-50),sample(.21,-50),sample(.24,-50),sample(.27,-50),sample(.3,-50)]
    r=count_toe_taps(seq)
    assert r['estimated_count']==1
    assert r['events'][0]['time']==.18


def test_toe_floor_jump_with_stable_ankle_does_not_invent_release():
    seq=[sample(0,30),sample(.04,-50),sample(.07,10),
         dict(sample(.1,-50),pose={}),sample(.14,-50),sample(.18,30)]
    for s in seq:
        if s['pose']: s['pose']['left_ankle']=[0,-70 if s['time']<.18 else 0]
    r=count_toe_taps(seq)
    assert r['estimated_count']==1
    assert r['events'][0]['time']==.04


def test_ankle_alone_never_confirms_contact():
    seq=[sample(0,30),sample(.04,-50)]
    seq += [dict(sample(t,-50),pose={'left_ankle':[0,-70]}) for t in [.07,.1,.14,.18]]
    assert count_toe_taps(seq)['estimated_count']==0

def test_alternate_views_do_not_duplicate_the_same_contact():
    from juggling.toe_taps import analyze_toe_taps
    seq=[dict(s,motion_pose=s['pose'],detail_pose=s['pose']) for s in cycle()]
    r=analyze_toe_taps(seq)
    assert r['estimated_count']==1


def test_separated_alternate_contact_has_explicit_provenance():
    from juggling.toe_taps import analyze_toe_taps
    seq=cycle()+[dict(s,pose={},motion_pose=s['pose']) for s in cycle(.5)]
    r=analyze_toe_taps(seq)
    assert r['estimated_count']==2
    assert r['events'][1]['observation_view']=='motion_pose'
    assert r['events'][1]['body_part'] is None


def test_predicted_ball_is_not_contact_evidence_in_any_view():
    from juggling.toe_taps import analyze_toe_taps
    seq=[dict(s,status='predicted',motion_pose=s['pose'],detail_pose=s['pose']) for s in cycle()]
    assert analyze_toe_taps(seq)['estimated_count']==0


def test_close_reacquired_candidate_is_review_only():
    from juggling.toe_taps import analyze_toe_taps
    seq=[sample(0,30,status='predicted'),sample(.03,30),sample(.06,30),
         sample(.12,30),sample(.18,30),sample(.21,30),sample(.24,-50),sample(.30,-50)]
    for s in seq:
        s['motion_pose']={'left_big_toe':[0,-50 if .06<=s['time']<=.18 else 30]}
    r=analyze_toe_taps(seq)
    assert r['estimated_count']==1
    assert sum(e['status']=='review' for e in r['events'])==1


def test_short_ball_occlusion_preserves_only_observed_off_ball_context():
    seq=[sample(0,30),sample(.03,-50,status='predicted'),sample(.06,-50,status='predicted'),
         sample(.1,-50),sample(.16,-50),sample(.19,30)]
    r=count_toe_taps(seq)
    assert r['estimated_count']==1
    e=r['events'][0]
    assert e['time']==.1 and e['confirmed_time']==.16
    assert e['contact_end']==.16 and e['departure_time']==.19


def test_gap_does_not_supply_an_entry_or_partial_contact_evidence():
    # A held pose must not become a fresh tap after the ball reappears.
    held=[sample(0,-50),sample(.03,-50,status='predicted'),sample(.1,-50),sample(.16,-50)]
    assert count_toe_taps(held)['estimated_count']==0
    # One observation on either side of the gap cannot be combined to confirm.
    partial=[sample(0,30),sample(.03,-50),sample(.06,-50,status='predicted'),sample(.1,-50),sample(.16,30)]
    assert count_toe_taps(partial)['estimated_count']==0


def test_reacquisition_must_be_short_local_and_similarly_sized():
    for mode in ('long','moved','resized'):
        seq=[sample(0,30),sample(.03,-50,status='predicted'),sample(.1,-50),sample(.16,-50)]
        if mode=='long':seq[2]['time']=.3;seq[3]['time']=.36
        for s in seq[2:]:
            if mode=='moved':s['center']=[300,0];s['pose']['left_big_toe']=[300,-50]
            if mode=='resized':s['diameter']=200;s['pose']['left_big_toe']=[0,-100]
        assert count_toe_taps(seq)['estimated_count']==0


def test_already_confirmed_hold_does_not_count_again_after_gap():
    seq=cycle()[:3]+[sample(.18,-50,status='predicted'),sample(.21,-50),sample(.27,-50)]
    assert count_toe_taps(seq)['estimated_count']==1


def test_one_frame_id_jump_does_not_split_two_observed_contact_frames():
    seq=[sample(0,30),sample(.03,-50),sample(.06,110,x=180),sample(.09,-50),sample(.12,30)]
    r=count_toe_taps(seq)
    assert r['estimated_count']==1
    assert r['events'][0]['time']==.03
    assert r['toe_taps']['rejected_toe_observations'][0]['time']==.06


def test_brief_release_during_hold_merges_contact_evidence():
    seq = [sample(0,30),sample(.03,-50),sample(.06,-50),sample(.09,-50),
           sample(.12,-50),sample(.15,30),sample(.18,-50),sample(.21,-50),
           sample(.24,-50),sample(.27,-50)]
    r = count_toe_taps(seq)
    assert r['estimated_count'] == 1
    assert r['events'][0]['contact_end'] == .27
    assert r['events'][0]['interrupted_entry_times'] == [.18]


def test_clear_departure_keeps_separate_same_foot_contacts():
    seq = [sample(0,30),sample(.03,-50),sample(.06,-50),sample(.09,-50),
           sample(.12,30),sample(.15,30),sample(.18,30),sample(.21,30),
           sample(.24,30),sample(.27,-50),sample(.30,-50),sample(.33,-50)]
    assert count_toe_taps(seq)['estimated_count'] == 2


def test_alternate_view_cannot_readd_interrupted_hold():
    from juggling.toe_taps import analyze_toe_taps
    seq = [sample(i*.03, 30 if i == 0 or i in (5,10) else -50) for i in range(15)]
    for i,s in enumerate(seq):
        s['motion_pose'] = {'left_big_toe': [0,30 if i < 11 else -50]}
    r = analyze_toe_taps(seq)
    assert r['estimated_count'] == 1


def test_interrupted_contact_merge_does_not_bridge_unobserved_ball():
    seq = [sample(0,30),sample(.03,-50),sample(.06,-50),sample(.09,-50),
           sample(.12,-50),sample(.14,-50,status='predicted'),
           sample(.15,30),sample(.18,-50),sample(.21,-50),sample(.24,-50)]
    r = count_toe_taps(seq)
    assert all(not e.get('interrupted_entry_times') for e in r['events'])
