import numpy as np
import pytest
from juggling.config import Config
from juggling.counting import count_touches
from juggling.feet import FootDetector, crop_transform
from test_counting import trajectory


def test_missing_foot_model_does_not_download(tmp_path):
    with pytest.raises(ValueError, match="download_models.py"):
        FootDetector(tmp_path / "missing.onnx")


def test_crop_keeps_aspect_ratio_and_centres_the_person():
    matrix, center, scale = crop_transform([100, 200, 300, 800], (288, 384))
    assert np.allclose(scale[0] / scale[1], 288 / 384)
    assert scale[1] == pytest.approx(600 * 1.25)  # tall box: height sets the scale
    mapped = matrix @ np.array([200, 500, 1])
    assert np.allclose(mapped, [144, 192])


def foot_trajectory(heel, toe):
    """Ball bottoms out at (50, 100); only heel/toe (plus a far standing ankle) are known."""
    samples = trajectory()
    for s in samples:
        s["pose"] = {"right_ankle": [150., 180.], "right_heel": [140., 185.], "right_big_toe": [165., 185.],
                     "left_heel": heel, "left_big_toe": toe}  # right foot planted on the floor
    return samples


def test_detected_foot_under_ball_counts_as_foot():
    result = count_touches(foot_trajectory([35., 112.], [65., 110.]), Config())
    assert result["estimated_count"] == 1
    assert result["events"][0]["body_part"] == "left_foot"


def test_detected_foot_far_from_ball_is_not_support():
    result = count_touches(foot_trajectory([95., 150.], [125., 150.]), Config())
    assert result["estimated_count"] == 0
    assert result["events"][0]["reason"] == "contact_not_supported"


def test_supporting_foot_wins_label_over_nearer_knee():
    samples = foot_trajectory([35., 112.], [65., 110.])
    for s in samples:
        s["pose"]["left_knee"] = list(s["center"])  # knee projected onto the ball in 2D
    assert count_touches(samples, Config())["events"][0]["body_part"] == "left_foot"


def test_knee_touch_with_foot_hanging_below_stays_knee():
    samples = foot_trajectory([35., 170.], [65., 170.])
    for s in samples:
        s["pose"]["left_knee"] = [50., 105.]
    assert count_touches(samples, Config())["events"][0]["body_part"] == "left_knee"


def test_detected_foot_replaces_ankle_estimate():
    # Ankle-only estimate would support this ball; detected toes pointing away do not.
    samples = trajectory()
    for s in samples:
        s["center"][0] = 80.
        s["pose"] = {"right_ankle": [150., 180.], "left_ankle": [50., 115.], "left_knee": [50., 55.],
                     "left_heel": [50., 118.], "left_big_toe": [20., 118.]}
    assert count_touches(samples, Config())["estimated_count"] == 0
