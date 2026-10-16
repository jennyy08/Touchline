import numpy as np
from juggling.audio import onset_strengths, onsets, pick_peaks
from juggling.config import Config
from juggling.counting import add_audio_evidence
from juggling.video import Frame, PlaybackWriter


def test_clicks_become_onsets_at_their_times():
    rate = 44100
    rng = np.random.default_rng(0)
    signal = rng.normal(0, .002, rate * 3).astype(np.float32)
    for t in (.5, 1.25, 2.0):
        i = int(t * rate)
        signal[i:i + 400] += rng.normal(0, .5, 400) * np.exp(-np.arange(400) / 80)
    found = pick_peaks(*onset_strengths(signal, rate), minimum=3)
    assert len(found) == 3 and all(abs(a - b) < .03 for (a, _), b in zip(found, (.5, 1.25, 2.0)))


def test_video_without_audio_has_no_onsets(tmp_path):
    path = tmp_path / "silent.mp4"
    writer = PlaybackWriter(path, 64, 48)
    for i in range(10):
        writer.write(Frame(i, i / 30, np.zeros((48, 64, 3), np.uint8)))
    writer.close()
    assert onsets(path) == []


def juggle(out_of_view=(2.4, 3.1), until=4.0):
    """Ball visible except while out of view; seen touches every 0.5 s outside that interval."""
    samples, events = [], []
    for i, t in enumerate(np.arange(0, until, 1 / 30)):
        hidden = out_of_view[0] <= t <= out_of_view[1]
        samples.append({"frame": i, "time": float(t), "status": "lost" if hidden else "observed",
                        "center": None if hidden else [50., 60.], "box": None if hidden else [40., 50., 60., 70.],
                        "diameter": 20., "segment": 0, "pose": {}})
    for k, t in enumerate(np.arange(.5, until, .5)):
        if not out_of_view[0] - .05 <= t <= out_of_view[1] + .05:
            events.append({"id": f"e{k}", "frame": int(t * 30), "time": float(t), "status": "counted",
                           "reason": "observed_reversal_near_leg", "body_part": "left_foot",
                           "evidence_sources": ["detector"]})
    return {"events": events, "estimated_count": len(events), "floor_y": 200., "stops": []}, samples


def thumps(result, extra):
    return [(e["time"] + .03, 6.) for e in result["events"]] + extra  # +0.03 s sound lag


def test_strong_thump_in_rhythm_while_out_of_view_is_a_heard_touch():
    result, samples = juggle()
    out = add_audio_evidence(result, samples, thumps(result, [(2.53, 12.), (3.03, 12.)]), Config())
    heard = [e for e in out["events"] if e["reason"] == "heard_ball_out_of_view"]
    assert [round(e["time"], 2) for e in heard] == [2.5, 3.0]
    assert out["heard_count"] == 2 and out["seen_count"] == result["estimated_count"]
    assert out["estimated_count"] == result["estimated_count"] + 2
    assert result["estimated_count"] == len(result["events"])  # input untouched


def test_weak_or_off_rhythm_thumps_are_ignored():
    result, samples = juggle()
    weak = add_audio_evidence(result, samples, thumps(result, [(2.53, 5.)]), Config())
    late = add_audio_evidence(result, samples, thumps(result, [(3.33, 12.)]), Config(rhythm_max_beats=1.4))
    assert weak["heard_count"] == 0 and late["heard_count"] == 0


def test_thump_with_ball_never_returning_is_end_of_run():
    result, samples = juggle(out_of_view=(2.4, 4.0))
    out = add_audio_evidence(result, samples, thumps(result, [(2.53, 12.)]), Config())
    assert out["heard_count"] == 0


def test_thump_with_ball_visibly_on_the_floor_is_not_heard_touch():
    result, samples = juggle()
    for s in samples:
        if 2.4 <= s["time"] <= 2.7:
            s.update(status="observed", center=[50., 190.], box=[40., 180., 60., 200.])
    out = add_audio_evidence(result, samples, thumps(result, [(2.58, 12.)]), Config())
    assert out["heard_count"] == 0


def test_no_heard_touch_before_the_first_seen_touch():
    result, samples = juggle()
    out = add_audio_evidence(result, samples, thumps(result, [(0.1, 15.)]), Config())
    assert out["heard_count"] == 0


def test_sound_confirms_gap_flag_but_never_a_floor_flag():
    result, samples = juggle()
    result["events"][1].update(status="review", reason="gap_near_contact", leg_supported=True)
    result["events"][2].update(status="review", reason="possible_floor_contact")
    out = add_audio_evidence(result, samples, thumps(result, []), Config())
    reasons = {e["id"]: e["reason"] for e in out["events"]}
    assert reasons["e1"] == "gap_confirmed_by_sound"
    assert out["heard_count"] == 0  # the ball was seen; sound only confirmed it
    assert reasons["e2"] == "possible_floor_contact"


def test_no_audio_leaves_video_result_unchanged():
    result, samples = juggle()
    out = add_audio_evidence(result, samples, [], Config())
    assert out["estimated_count"] == result["estimated_count"] and out["heard_count"] == 0
