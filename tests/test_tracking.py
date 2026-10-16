from juggling.config import Config
from juggling.tracking import BallTracker


def ball(x=50):
    return [{"box": [x - 10, 40, x + 10, 60], "score": .8}]


def test_short_prediction_then_lost():
    tracker = BallTracker(Config())
    assert tracker.update(0, ball())["status"] == "observed"
    assert tracker.update(.1, [])["status"] == "predicted"
    assert tracker.update(.16, [])["status"] == "lost"


def test_implausible_jump_is_not_associated():
    tracker = BallTracker(Config())
    initial = tracker.update(0, ball())
    assert tracker.update(.03, ball(500))["status"] == "predicted"
    reacquired = tracker.update(.2, ball(500))
    assert reacquired["status"] == "observed"
    assert reacquired["segment"] != initial["segment"]


def test_plausible_motion_keeps_identity():
    tracker = BallTracker(Config())
    a = tracker.update(0, ball())
    b = tracker.update(.03, ball(55))
    assert b["segment"] == a["segment"]
    assert b["center"] == [55, 50]
