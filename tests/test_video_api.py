import time
from pathlib import Path
import av
import numpy as np
import pytest
from fastapi.testclient import TestClient
from juggling.video import Frame, PlaybackWriter, decode
from juggling.detection import load_model
from juggling import api


def test_vfr_roundtrip_preserves_frame_timing(tmp_path):
    path = tmp_path / 'playback.mp4'
    writer = PlaybackWriter(path, 160, 100)
    times = [0., .03, .07, .10, .16]
    for i, t in enumerate(times):
        writer.write(Frame(i, t, np.full((100, 160, 3), i * 30, dtype=np.uint8)))
    writer.close()
    frames = list(decode(path))
    assert [f.time for f in frames] == pytest.approx(times, abs=1/90000)
    assert frames[0].image.shape == (100, 160, 3)


def test_corrupt_video_is_actionable(tmp_path):
    path = tmp_path / 'bad.mov'; path.write_bytes(b'not video')
    with pytest.raises(ValueError, match='decode'):
        list(decode(path))


def test_missing_model_does_not_download(tmp_path):
    with pytest.raises(ValueError, match='download_models.py'):
        load_model(tmp_path / 'missing.pt')


def test_upload_error_progress_and_unknown_job(monkeypatch, tmp_path):
    monkeypatch.setattr(api, 'JOB_ROOT', tmp_path)
    monkeypatch.setattr(api, 'busy', False)
    def fail(*args, **kwargs):
        raise ValueError('Cannot decode this video. Try MP4.')
    monkeypatch.setattr(api, 'analyze', fail)
    with TestClient(api.app) as client:
        assert client.get('/api/jobs/missing').status_code == 404
        assert client.post('/api/jobs', files={'file': ('empty.mov', b'')}).status_code == 400
        response = client.post('/api/jobs', files={'file': ('bad.mov', b'bad')})
        assert response.status_code == 202
        job_id = response.json()['id']
        for _ in range(100):
            state = client.get(f'/api/jobs/{job_id}').json()
            if state['stage'] == 'error':
                break
            time.sleep(.01)
        assert state['stage'] == 'error'
        assert 'decode' in state['error']
        assert client.get(f'/api/jobs/{job_id}/result').status_code == 409


def test_busy_and_upload_size_limit(monkeypatch):
    with TestClient(api.app) as client:
        monkeypatch.setattr(api, 'busy', True)
        assert client.post('/api/jobs', files={'file': ('x.mp4', b'x')}).status_code == 409
        monkeypatch.setattr(api, 'busy', False)
        monkeypatch.setattr(api, 'MAX_BYTES', 3)
        assert client.post('/api/jobs', files={'file': ('x.mp4', b'four')}).status_code == 413
        assert not api.busy


def test_drill_setup_validation_does_not_claim_worker(monkeypatch):
    monkeypatch.setattr(api, 'busy', False)
    with TestClient(api.app) as client:
        for data in ({'drill':'unknown'}, {'drill':'side_to_side','setup':'bad'},
                     {'drill':'side_to_side','setup':'{"require_markers":true}'}):
            response=client.post('/api/jobs',files={'file':('test.mov',b'test')},data=data)
            assert response.status_code==422
            assert not api.busy
