import cv2
import numpy as np
from juggling.appearance import AppearanceBridge
from juggling.config import Config


def scene(x=60, y=60, blur=False, visible=True):
    image = np.full((200, 220, 3), 235, np.uint8)
    if visible:
        # Fixed textured object: correspondence, not color thresholding.
        texture = np.random.default_rng(42).integers(30, 220, (40, 40), dtype=np.uint8)
        texture = cv2.GaussianBlur(texture, (3, 3), 0)
        image[y:y+40, x:x+40] = texture[:, :, None]
        if blur:
            image = cv2.GaussianBlur(image, (3, 3), 0)
    return image


def seeded():
    bridge = AppearanceBridge(Config())
    bridge.propose(0, scene(), [])
    bridge.accept(0, {'status': 'observed', 'source': 'detector', 'box': [60,60,100,100]})
    return bridge


def test_image_match_recovers_motion_and_blur_without_detector():
    proposal = seeded().propose(.033, scene(68, 75, blur=True), [])
    assert len(proposal) == 1
    assert proposal[0]['source'] == 'appearance'
    assert np.allclose(proposal[0]['box'], [68,75,108,115], atol=2)


def test_blank_frame_cannot_become_an_observation():
    assert seeded().propose(.033, scene(visible=False), []) == []


def test_appearance_cannot_extend_itself_indefinitely():
    bridge = seeded()
    for i in range(1, 8):
        t = i * .033
        proposal = bridge.propose(t, scene(), [])
        assert proposal
        bridge.accept(t, {'status': 'observed', 'source': 'appearance', 'box': proposal[0]['box']})
    assert bridge.propose(.27, scene(), []) == []


def test_long_frame_gap_requires_detector_reacquisition():
    assert seeded().propose(.2, scene(), []) == []


def test_good_detector_box_is_not_overridden():
    detections = [{'box': [68,75,108,115], 'score': .7}]
    assert seeded().propose(.033, scene(68,75), detections) == detections


def test_inflated_box_is_repaired_only_with_image_agreement():
    detections = [{'box': [65,70,115,135], 'score': .4}]
    result = seeded().propose(.033, scene(68,75), detections)
    assert result[0]['source'] == 'appearance'
    assert np.allclose(result[0]['box'], [68,75,108,115], atol=2)


def test_no_template_without_a_detector_anchor():
    assert AppearanceBridge(Config()).propose(0, scene(), []) == []


def test_same_background_color_with_different_texture_is_rejected():
    image = scene(visible=False)
    texture = np.random.default_rng(999).integers(30, 220, (40,40), dtype=np.uint8)
    image[60:100,60:100] = cv2.GaussianBlur(texture, (3,3), 0)[:, :, None]
    assert seeded().propose(.033, image, []) == []


def test_edge_observation_clears_template_until_interior_detector_returns():
    bridge = seeded()
    bridge.propose(.033, scene(0, 60), [])
    bridge.accept(.033, {'status': 'observed', 'source': 'detector', 'box': [0,60,40,100]})
    assert bridge.propose(.066, scene(10,60), []) == []
    bridge.accept(.066, {'status': 'observed', 'source': 'detector', 'box': [10,60,50,100]})
    assert bridge.propose(.099, scene(15,60), [])


def test_appearance_at_top_edge_cannot_seed_another_match():
    bridge = seeded()
    bridge.propose(.033, scene(60,0), [])
    bridge.accept(.033, {'status': 'observed', 'source': 'appearance', 'box': [60,0,100,40]})
    assert bridge.propose(.066, scene(60,10), []) == []
