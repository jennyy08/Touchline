from dataclasses import replace
import pytest
from juggling.config import Config
from juggling.counting import count_touches
from juggling.streaming import StreamingCounter
from test_counting import trajectory


def test_no_event_before_outgoing_window_and_no_later_revision():
    counter = StreamingCounter(Config())
    samples = trajectory()
    for s in samples[:20]:
        events = counter.update(s)
        assert not events
    events = counter.update(samples[20])
    assert len(events) == 1
    assert events[0]['confirmed_at'] >= events[0]['time'] + .14
    saved = dict(events[0])
    for s in samples[21:]:
        counter.update(s)
    assert counter.events == [saved]


def test_wrapper_and_incremental_identical_with_irregular_source_ids():
    samples = trajectory()
    for s in samples:
        s['frame'] *= 3  # IDs are not a measure of time adjacency.
    counter = StreamingCounter(Config())
    for s in samples:
        counter.update(s)
    counter.finish()
    assert count_touches(samples, Config())['events'] == counter.events
    assert counter.result()['estimated_count'] == 1


def test_future_floor_cannot_reclassify_confirmed_candidate():
    samples = trajectory(pose=False)
    counter = StreamingCounter(Config())
    for s in samples[:21]:
        counter.update(s)
    assert counter.events[0]['reason'] == 'floor_unknown'
    for s in trajectory()[21:]:
        counter.update(s)
    assert counter.events[0]['reason'] == 'floor_unknown'
    assert counter.result()['estimated_count'] == 0


def test_unfinished_tail_is_not_flushed_as_a_touch():
    assert count_touches(trajectory()[:17], Config())['estimated_count'] == 0


def test_timestamp_rejection_and_floor_expires():
    counter = StreamingCounter(Config())
    for s in trajectory():
        counter.update(s)
    assert counter.floor is not None
    with pytest.raises(ValueError):
        counter.update(trajectory()[-1])
    s = trajectory()[-1] | {'time': 7., 'frame': 90, 'pose': {}, 'status': 'lost'}
    counter.update(s)
    assert counter.floor is None
    assert len(counter.samples) == 1


def test_finish_uses_existing_tail_evidence_without_inventing_frames():
    counter = StreamingCounter(Config())
    for s in trajectory()[:19]:
        counter.update(s)
    assert not counter.events
    events = counter.finish()
    assert len(events) == 1
    assert events[0]['confirmation_context'] == 'end_of_stream'
    assert counter.finish() == []
    with pytest.raises(ValueError):
        counter.update(trajectory()[20])
