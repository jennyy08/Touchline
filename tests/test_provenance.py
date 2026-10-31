from copy import deepcopy
import pytest
from juggling.provenance import compare_observations, file_sha256


def result():
    return {'video': {'sha256': 'same'}, 'samples': [
        {'frame':0,'time':0.,'status':'observed','box':[1,2,3,4],'pose':{}}],
        'events': [], 'estimated_count':0, 'config':{}}


def test_unknown_provenance_is_not_reported_as_matching():
    report = compare_observations(result(), result())
    assert report['observations_identical']
    assert report['provenance_identical'] is None
    assert not report['provenance_available']


def test_ball_change_is_separate_from_pose_and_event_changes():
    a = result(); b = deepcopy(a); b['samples'][0]['box'][0] += .001
    report = compare_observations(a,b)
    assert report['changed_frames']['box'] == [0]
    assert report['changed_frames']['pose'] == []
    assert report['events_identical']
    assert not report['observations_identical']


def test_reject_different_input_or_timestamps():
    a = result(); b = deepcopy(a); b['video']['sha256'] = 'other'
    with pytest.raises(ValueError, match='different input'): compare_observations(a,b)
    b = deepcopy(a); b['samples'][0]['time'] = .01
    with pytest.raises(ValueError, match='timestamps'): compare_observations(a,b)


def test_model_digest_tracks_contents(tmp_path):
    p = tmp_path/'weights'; p.write_bytes(b'first'); first = file_sha256(p)
    p.write_bytes(b'second'); assert file_sha256(p) != first
    assert len(first) == 64
