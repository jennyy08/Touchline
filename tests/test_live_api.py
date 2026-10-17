import struct
from types import SimpleNamespace
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from juggling import api, live_api
from juggling.config import Config
from juggling.counting import count_touches
from juggling.streaming import StreamingCounter
from test_counting import trajectory

JPEG = cv2.imencode('.jpg', np.zeros((32,32,3),dtype=np.uint8))[1].tobytes()


class FakeAnalyzer:
    """Transport tests use deterministic observations, not pretrained inference."""
    def __init__(self, models, feet):
        self.counter = StreamingCounter(Config())
        self.config = SimpleNamespace(velocity_window_seconds=0)
        self.samples = trajectory()
        self.index = 0

    def process(self, image, timestamp):
        sample = self.samples[self.index] | {'time':timestamp}
        self.index += 1
        events = self.counter.update(sample)
        return {'type':'frame','sample':sample,'new_events':events,
                'count':self.counter.result()['estimated_count']}

    def finish(self):
        events = self.counter.finish()
        return {'type':'stopped','count':self.counter.result()['estimated_count'],
                'new_events':events,'events':self.counter.events}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(live_api,'LiveAnalyzer',FakeAnalyzer)
    with TestClient(api.app, base_url='http://127.0.0.1') as client:
        yield client
    assert not api.busy


def ready(ws):
    assert ws.receive_json()['type']=='loading'
    ws.send_json({'type':'start'})
    assert ws.receive_json()['type']=='ready'


def test_stream_matches_offline_and_disconnect_releases_worker(client):
    with client.websocket_connect('ws://127.0.0.1/api/live') as ws:
        ready(ws)
        for s in trajectory():
            ws.send_bytes(struct.pack('<d',s['time'])+JPEG)
            assert ws.receive_json()['type']=='frame'
        ws.send_json({'type':'stop'})
        result=ws.receive_json()
        expected=count_touches(trajectory(),Config())
        assert result['count']==expected['estimated_count']==1
        assert result['events']==expected['events']
    with client.websocket_connect('ws://127.0.0.1/api/live') as ws:
        ready(ws)


def test_session_and_upload_rejected_while_live(client):
    with client.websocket_connect('ws://127.0.0.1/api/live') as first:
        ready(first)
        with client.websocket_connect('ws://127.0.0.1/api/live') as second:
            assert 'Another' in second.receive_json()['message']
        assert client.post('/api/jobs',files={'file':('x.mov',b'abc')}).status_code==409


@pytest.mark.parametrize('packet', [b'broken',struct.pack('<d',float('nan'))+JPEG,
                                      struct.pack('<d',1)+b'not a jpeg', b'x'*(live_api.MAX_PACKET+1)], ids=['short','nan','corrupt','oversize'])
def test_bad_frames_release_session(client,packet):
    with client.websocket_connect('ws://127.0.0.1/api/live') as ws:
        ready(ws)
        ws.send_bytes(packet)
        assert ws.receive_json()['type']=='error'


def test_repeated_timestamp_rejected(client):
    with client.websocket_connect('ws://127.0.0.1/api/live') as ws:
        ready(ws)
        packet=struct.pack('<d',0)+JPEG
        ws.send_bytes(packet); assert ws.receive_json()['type']=='frame'
        ws.send_bytes(packet); assert 'increase' in ws.receive_json()['message']


def test_missing_model_is_actionable(client,monkeypatch):
    def missing(*args):
        raise ValueError('Missing model yolo11s.pt. Run scripts/download_models.py.')
    monkeypatch.setattr(live_api,'LiveAnalyzer',missing)
    with client.websocket_connect('ws://127.0.0.1/api/live') as ws:
        assert ws.receive_json()['type']=='loading'
        ws.send_json({'type':'start'})
        assert 'Missing model' in ws.receive_json()['message']


def test_foreign_browser_origin_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('ws://127.0.0.1/api/live',headers={'origin':'https://example.com'}):
            pass


def test_large_dimensions_rejected_before_decode():
    jpeg=cv2.imencode('.jpg',np.zeros((800,1300,3),dtype=np.uint8))[1].tobytes()
    with pytest.raises(ValueError,match='no larger'):
        live_api.decode_packet(struct.pack('<d',0)+jpeg,None)


def test_nonlocal_host_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('ws://example.com/api/live'):
            pass
