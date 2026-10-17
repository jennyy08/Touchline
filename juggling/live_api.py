"""Localhost WebSocket transport. One frame request → one reply; no frame queue."""
import asyncio
import io
import json
import math
import struct
from urllib.parse import urlparse
import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .live import LiveAnalyzer

MAX_PACKET = 1024 * 1024


def decode_packet(packet, previous):
    if len(packet) <= 8 or len(packet) > MAX_PACKET:
        raise ValueError('Frame must contain a timestamp and a JPEG under 1 MB.')
    timestamp = struct.unpack('<d', packet[:8])[0]
    if not math.isfinite(timestamp) or timestamp < 0 or timestamp > 3600:
        raise ValueError('Timestamp must be finite seconds between 0 and 3600.')
    if previous is not None and timestamp <= previous:
        raise ValueError('Frame timestamps must strictly increase.')
    try:
        # Check dimensions before allocating the decoded image.
        with Image.open(io.BytesIO(packet[8:])) as header:
            width, height = header.size
            if header.format != 'JPEG' or min(width,height) < 16 or max(width,height)>1280 or width*height>921600:
                raise ValueError('Use JPEG frames no larger than 1280×720 pixels (or portrait equivalent).')
        image = cv2.imdecode(np.frombuffer(packet[8:], dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('JPEG could not be decoded.')
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid JPEG frame.') from exc
    return timestamp, image


def make_router(claim, release, executor, models):
    router = APIRouter()

    @router.websocket('/api/live')
    async def live(socket: WebSocket):
        # Browser origin must match this local server. CLI clients omit Origin.
        origin = socket.headers.get('origin')
        host = socket.headers.get('host')
        local_host = urlparse('//' + (host or '')).hostname in ('127.0.0.1', 'localhost', '::1')
        if not local_host or (origin and (urlparse(origin).netloc != host or urlparse(origin).scheme not in ('http','https'))):
            await socket.close(code=1008)
            return
        await socket.accept()
        if not claim():
            await socket.send_json({'type':'error','message':'Another upload or live session is running.'})
            await socket.close(code=1013)
            return
        loop = asyncio.get_running_loop()
        try:
            await socket.send_json({'type':'loading'})
            # Client chooses the documented optional foot schedule; defaults stay fast.
            start = await asyncio.wait_for(socket.receive_text(), timeout=15)
            if len(start)>256:
                raise ValueError('Invalid start message.')
            options = json.loads(start)
            if not isinstance(options,dict) or options.get('type')!='start' or options.get('feet','off') not in ('off','near','all'):
                raise ValueError('Send a start message with feet off, near or all.')
            analyzer = await loop.run_in_executor(executor, lambda: LiveAnalyzer(models, options.get('feet','off')))
            await socket.send_json({'type':'ready','max_width':640,'fps_ceiling':30,'audio':False})
            previous = None
            while True:
                message = await asyncio.wait_for(socket.receive(), timeout=30)
                if message['type']=='websocket.disconnect':
                    break
                packet = message.get('bytes')
                if packet is not None:
                    timestamp, image = decode_packet(packet, previous)
                    reply = await loop.run_in_executor(executor, analyzer.process, image, timestamp)
                    previous = timestamp
                    await socket.send_json(reply)
                else:
                    text = message.get('text','')
                    if len(text)>128 or json.loads(text) != {'type':'stop'}:
                        raise ValueError('Send a JPEG frame or a stop message.')
                    # Let the final outgoing window expire without inventing frames.
                    await asyncio.sleep(analyzer.config.velocity_window_seconds)
                    await socket.send_json(analyzer.finish())
                    await socket.close(code=1000)
                    break
        except WebSocketDisconnect:
            pass
        except (ValueError, KeyError, asyncio.TimeoutError) as exc:
            try:
                await socket.send_json({'type':'error','message':str(exc) or 'Session timed out. Start again.'})
                await socket.close(code=1008)
            except (RuntimeError, WebSocketDisconnect):
                pass
        except Exception:
            import logging
            logging.exception('Live analysis failed')
            try:
                await socket.send_json({'type':'error','message':'Live analysis failed. Check the server terminal and restart the session.'})
                await socket.close(code=1011)
            except (RuntimeError, WebSocketDisconnect):
                pass
        finally:
            release()

    return router
