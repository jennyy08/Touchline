"""Replay local videos through the actual WebSocket, dropping stale frames.

JPEGs are prepared before timing. This tests localhost transport and inference,
not camera capture/JPEG encoding, microphone, or browser rendering latency.
"""
import argparse
from bisect import bisect_right
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import struct
import sys
import time
import cv2
import numpy as np
from websockets.sync.client import connect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_live import sources, TOTALS
from juggling.video import decode
from juggling.config import Config
from juggling.counting import count_touches
from juggling.evaluation import compare


def stats(values):
    return {'mean_ms':float(np.mean(values))*1000,'p95_ms':float(np.percentile(values,95))*1000} if values else None


def run(path, url, realtime, feet):
    frames=[]
    for frame in decode(path):
        height,width=frame.image.shape[:2]
        ratio=min(1,640/max(height,width))
        image=cv2.resize(frame.image,(round(width*ratio),round(height*ratio)))
        jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,85])[1].tobytes()
        frames.append((frame.time,struct.pack('<d',frame.time)+jpeg))
    times=[t for t,_ in frames]
    samples=[]; replies=[]; rtts=[]; delays=[]
    with connect(url,proxy=None,max_size=2*1024*1024,open_timeout=60) as ws:
        assert json.loads(ws.recv())['type']=='loading'
        ws.send(json.dumps({'type':'start','feet':feet}))
        ready=json.loads(ws.recv(timeout=90))
        if ready['type']!='ready':raise RuntimeError(ready)
        started=time.perf_counter(); previous=-1
        while previous<len(frames)-1:
            if realtime:
                elapsed=time.perf_counter()-started
                if elapsed>times[-1]:break
                index=max(previous+1,bisect_right(times,elapsed)-1)
                wait=times[index]-(time.perf_counter()-started)
                if wait>0:time.sleep(wait)
            else:index=previous+1
            sent=time.perf_counter()
            ws.send(frames[index][1])
            reply=json.loads(ws.recv(timeout=30))
            if reply['type']!='frame':raise RuntimeError(reply)
            received=time.perf_counter()
            rtts.append(received-sent)
            for event in reply['new_events']:
                if realtime:delays.append(received-started-event['time'])
            samples.append(reply['sample']);replies.extend(reply['new_events']);previous=index
        ws.send(json.dumps({'type':'stop'}))
        final=json.loads(ws.recv(timeout=30))
        for event in final['new_events']:
            if realtime:delays.append(time.perf_counter()-started-event['time'])
        elapsed=time.perf_counter()-started
    config=replace(Config(),image_size=320,pose_size=320,audio_enabled=False,
                   foot_model='' if feet=='off' else Config().foot_model)
    offline=count_touches(samples,config)
    if final['events']!=offline['events']:raise AssertionError('WebSocket and offline wrapper differ on identical samples')
    return {'source':path.name,'video_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'realtime':realtime,'feet':feet,'decoded_frames':len(frames),
            'processed_frames':len(samples),'dropped_frames':len(frames)-len(samples),
            'elapsed_seconds':elapsed,'processed_fps':len(samples)/elapsed,
            'count':final['count'],'feet_runs':reply.get('feet_runs',0),
            'foot_fraction':reply.get('feet_runs',0)/max(1,len(samples)),
            'round_trip':stats(rtts),
            'confirmation_delay':stats(delays),'wrapper_events_identical':True,
            'events':final['events'],'samples':samples}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='ws://127.0.0.1:8001/api/live')
    parser.add_argument('--clips',type=int,nargs='+',default=list(range(7)))
    parser.add_argument('--feet',choices=['off','near','all'],default='off')
    parser.add_argument('--all-frames',action='store_true',help='Do not simulate real-time dropping')
    parser.add_argument('--videos',type=Path,default=Path.home()/'Downloads')
    parser.add_argument('--output',type=Path,default=Path('validation/live-revision/websocket-replay.json'))
    args=parser.parse_args();paths=sources(args.videos);results=[]
    for clip in args.clips:
        report=run(paths[clip],args.url,not args.all_frames,args.feet)
        # Keep samples local for further numerical inspection; commit compact metrics/events.
        cache=Path('.runtime/live-replay');cache.mkdir(parents=True,exist_ok=True)
        (cache/f'clip-{clip}-{args.feet}-{not args.all_frames}.json').write_text(json.dumps(report))
        report.pop('samples');report.update(clip=clip,reference_total=TOTALS[clip])
        if clip == 0:
            reference=json.loads((Path(__file__).resolve().parents[1]/'validation/manual-review.json').read_text())
            report['original_event_comparison']=compare({
                **report,'video':{'sha256':report['video_sha256']},'tracking_summary':{},
                'runtime_seconds':report['elapsed_seconds'],
                'config':replace(Config(),image_size=320,pose_size=320,audio_enabled=False,
                                 foot_model='' if args.feet=='off' else Config().foot_model).to_dict(),
            },reference)
        results.append(report);args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(results,indent=2)+'\n')
        print({k:v for k,v in report.items() if k not in ('events','original_event_comparison')},flush=True)


if __name__=='__main__':main()
