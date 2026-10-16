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


def test_wrist_on_ball_never_blocks_a_supported_touch():
    samples = trajectory()
    for s in samples:
        s["pose"]["left_wrist"] = list(s["center"])
    result = count_touches(samples, Config())
    assert result["estimated_count"] == 1
    assert result["events"][0]["reason"] == "observed_reversal_near_leg"


def extended_foot(ball_x):
    # Ankle at (50,115), knee 60 px above: estimated foot reaches 36 px either side.
    samples = trajectory()
    for s in samples:
        s["center"][0] = ball_x
        s["pose"] = {"left_ankle": [50., 115.], "left_knee": [50., 55.]}
    return samples


def test_extended_foot_beyond_ankle_distance_counts():
    # Ball 30 px (1.5 diameters) from the ankle, but beside the estimated foot.
    result = count_touches(extended_foot(80.), Config())
    assert result["estimated_count"] == 1
    assert result["events"][0]["body_part"] == "left_foot"


def test_ball_far_from_any_leg_stays_review():
    result = count_touches(extended_foot(130.), Config())
    assert result["estimated_count"] == 0
    assert result["events"][0]["reason"] == "contact_not_supported"


def test_thigh_height_ball_does_not_match_foot_zone():
    samples = trajectory(ys=[60 - abs(t - .5) * 100 for t in np.arange(31) / 30])
    for s in samples:
        s["pose"] = {"left_ankle": [50., 160.], "left_knee": [50., 75.], "left_hip": [50., 20.]}
    result = count_touches(samples, Config())
    assert result["events"][0]["body_part"] == "left_thigh"


def test_neighbor_frame_landmarks_support_contact():
    samples = trajectory()
    contact = 15
    for s in samples:
        s["pose"] = {"right_ankle": [150., 180.]}  # Far standing foot keeps the floor estimate.
    samples[contact + 1]["pose"].update(left_ankle=[50., 115.], left_knee=[50., 75.])
    assert count_touches(samples, Config())["estimated_count"] == 1


def top_exit(exit_rows=True, side=False):
    """Reversal at frame 15, one observed top-clipped frame, then the ball leaves view."""
    times = np.arange(31) / 30
    samples = trajectory(times, [40 + 60 * (t / .5) if t <= .5 else 40 for t in times])
    for s in samples:
        x, y = s["center"]
        s["box"] = [x - 10, y - 10, x + 10, y + 10]
        s["pose"]["left_knee"] = [50., 40.]
    contact, clipped = samples[15], samples[16]
    clipped["center"], clipped["box"] = [50., 40.], [40., 0., 60., 80.] if not side else [40., 30., 60., 50.]
    contact["box"] = [40., 90., 60., 110.]
    clipped["box"][3] = 80. if not side else 50.
    if side:
        clipped["box"], clipped["center"] = [0., 60., 20., 80.], [10., 70.]
    for s in samples[17:]:
        s["status"] = "predicted" if exit_rows else "observed"
    return samples


def test_contact_followed_by_top_exit_counts_with_tag():
    result = count_touches(top_exit(), Config())
    assert result["estimated_count"] == 1
    assert result["events"][0]["evidence"] == ["top_exit"]


def test_single_outgoing_sample_without_top_clip_does_not_count():
    assert count_touches(top_exit(side=True), Config())["estimated_count"] == 0


def held(seconds):
    """Falling ball that is then held still (e.g. caught) for `seconds`."""
    times = np.arange(int((.3 + seconds) * 30)) / 30
    return trajectory(times, [min(40 + 200 * t, 100) for t in times])


def test_held_ball_marks_one_stop_without_counting():
    result = count_touches(held(1.5), Config())
    assert len(result["stops"]) == 1
    assert result["stops"][0]["end"] - result["stops"][0]["start"] >= 1.0
    assert result["estimated_count"] == 0


def test_short_pause_and_ordinary_juggle_have_no_stop():
    assert count_touches(held(.4), Config())["stops"] == []
    assert count_touches(trajectory(), Config())["stops"] == []
