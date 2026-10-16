import numpy as np
from juggling.config import Config
from juggling.counting import count_touches


def trajectory(times=None, ys=None, pose=True):
    times = list(times if times is not None else np.arange(31) / 30)
    ys = list(ys if ys is not None else [100 - abs(t - .5) * 100 for t in times])
    return [{"frame": i, "time": float(t), "status": "observed", "center": [50., float(y)],
             "diameter": 20., "segment": 0, "pose": {"left_ankle": [50., 115.],
             "right_ankle": [150., 180.], "left_knee": [50., 75.]} if pose else {}}
            for i, (t, y) in enumerate(zip(times, ys))]


def test_visible_contact_counts_once():
    result = count_touches(trajectory(), Config())
    assert result["estimated_count"] == 1
    assert abs(result["events"][0]["time"] - .5) < .001


def test_flight_apex_is_not_contact():
    samples = trajectory(ys=[50 + abs(t - .5) * 100 for t in np.arange(31) / 30])
    assert count_touches(samples, Config())["events"] == []


def test_floor_bounce_is_flagged_not_counted():
    samples = trajectory(ys=[175 - abs(t - .5) * 100 for t in np.arange(31) / 30])
    result = count_touches(samples, Config())
    assert result["estimated_count"] == 0
    assert result["events"][0]["reason"] == "possible_floor_contact"


def test_initial_pickup_monotonic_rise_does_not_count():
    assert count_touches(trajectory(ys=np.linspace(160, 40, 31)), Config())["events"] == []


def test_no_contact_claim_from_predicted_positions():
    samples = trajectory()
    for s in samples[11:20]:
        s["status"] = "predicted"
    assert count_touches(samples, Config())["estimated_count"] == 0


def test_gap_around_contact_requires_review():
    samples = trajectory()
    samples[13]["status"] = samples[14]["status"] = samples[16]["status"] = "predicted"
    # Insufficient observed support on one side is conservative.
    assert count_touches(samples, Config())["estimated_count"] == 0


def test_reacquisition_never_joins_two_segments():
    samples = trajectory()
    for s in samples[15:]:
        s["segment"] = 1
    assert count_touches(samples, Config())["events"] == []


def test_missing_pose_flags_review():
    result = count_touches(trajectory(pose=False), Config())
    assert result["estimated_count"] == 0
    assert result["events"][0]["status"] == "review"


def test_irregular_presentation_timestamps():
    times = np.cumsum([0.] + [.028, .038] * 15)
    middle = times[15]
    samples = trajectory(times=times, ys=[100 - abs(t - middle) * 100 for t in times])
    assert count_touches(samples, Config())["estimated_count"] == 1


def test_adjacent_jitter_contacts_are_debounced():
    times = np.arange(61) / 60
    ys = [100 - abs(t-.5)*100 for t in times]
    ys[33] = 100
    result = count_touches(trajectory(times, ys), Config(velocity_window_seconds=.07))
    assert len(result["events"]) == 1
