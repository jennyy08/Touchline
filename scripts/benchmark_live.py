"""Measure inference stages, then replay a timestamp-based live-settings matrix.

No webcam/endpoints or production-default changes. Cached foot inference is charged
only to frames selected by the causal scheduler. Timings are service-time estimates,
not measured browser latency. Counts still use the existing offline counter/audio.
"""
import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from juggling.config import Config
from juggling.detection import BallDetector
from juggling.pose import PoseDetector
from juggling.video import decode
from juggling.audio import onsets
from juggling.tracking import BallTracker
from juggling.appearance import AppearanceBridge
from juggling.counting import count_touches, add_audio_evidence
from juggling.evaluation import compare
from juggling.live_settings import LiveSettings, FrameGate, FootSchedule

ROOT = Path(__file__).resolve().parents[1]
SIZES = (640, 480, 320)
TOTALS = (26, 16, 29, 21, 13, 25, 23)


def sources(directory):
    paths = [directory / 'Movie on 2026-10-16 at 2.02\u202fAM.mov']
    for n in range(1, 7):
        ref = json.loads((ROOT / f'validation/audio-revision/clip-{n}-reference.json').read_text())
        paths.append(directory / ref['filename'].replace('\\u202f', '\u202f'))
    return paths


def timed(device, function):
    if device == 'mps': torch.mps.synchronize()
    start = time.perf_counter()
    value = function()
    if device == 'mps': torch.mps.synchronize()
    return value, (time.perf_counter()-start)*1000


def stats(values):
    if not values: return {'mean_ms': 0., 'p50_ms': 0., 'p95_ms': 0.}
    return dict(zip(('mean_ms','p50_ms','p95_ms'),map(float,(np.mean(values),np.percentile(values,50),np.percentile(values,95)))))


def fingerprint(source, device):
    h = hashlib.sha256(source.read_bytes()).hexdigest()
    code = hashlib.sha256(b''.join((ROOT / f'juggling/{p}.py').read_bytes() for p in ('detection','pose','feet','video'))).hexdigest()
    weights = {name: hashlib.sha256((ROOT/'models'/name).read_bytes()).hexdigest()
               for name in (Config().detector, Config().pose_model, Config().foot_model)}
    return {'video_sha256':h,'device':device,'sizes':list(SIZES),'config':Config(device=device).to_dict(),
            'code':code,'weights':weights,'torch':torch.__version__,'machine':platform.platform()}


def collect(source, device, ball, pose, cache_path, key):
    rows=[]; iterator=iter(decode(source)); start=time.perf_counter()
    while True:
        before=time.perf_counter()
        try: frame=next(iterator)
        except StopIteration: break
        decode_ms=(time.perf_counter()-before)*1000
        body, body_ms=timed(device,lambda:pose.detect_body(frame.image))
        landmarks,box=body
        feet,feet_ms=timed('cpu',lambda:pose.feet.detect(frame.image,box,pose.config.landmark_threshold)) if box is not None else ({},0.)
        detections={}; ball_ms={}
        for size in SIZES:
            ball.config=replace(ball.config,image_size=size)
            detections[str(size)],ball_ms[str(size)]=timed(device,lambda:ball.detect(frame.image))
        rows.append({'frame':frame.index,'time':frame.time,'pose':landmarks,'box':box,'feet':feet,
                     'detections':detections,'ms':{'decode':decode_ms,'pose':body_ms,'feet':feet_ms,'ball':ball_ms}})
        if (frame.index+1)%120==0: print(f'{device} {source.name}: {frame.index+1} frames',flush=True)
    payload={'key':key,'rows':rows,'collection_seconds':time.perf_counter()-start}
    cache_path.write_text(json.dumps(payload))
    return payload


def evaluate(source, clip, device, payload, output):
    heard=onsets(source)
    configurations=[LiveSettings(device=device,image_size=s,fps=f,feet=m) for s in SIZES for f in (30,15) for m in ('off','all','near')]
    cases=[]
    for setting in configurations:
        config=replace(Config(),device=device,image_size=setting.image_size)
        cases.append({'settings':setting,'config':config,'gate':FrameGate(setting.fps),'schedule':FootSchedule(setting),
                      'tracker':BallTracker(config),'appearance':AppearanceBridge(config),'samples':[],
                      'times':{k:[] for k in ('decode','ball','pose','feet','tracking','service')},'feet_runs':0})
    for frame,row in zip(decode(source),payload['rows'],strict=True):
        if frame.index!=row['frame'] or abs(frame.time-row['time'])>1e-6: raise ValueError('Cache timestamps mismatch')
        tracked_this_frame = {}
        for case in cases:
            if not case['gate'].accept(frame.time): continue
            setting=case['settings']; track_key=(setting.image_size,setting.fps)
            if track_key not in tracked_this_frame:
                start=time.perf_counter(); tracker=case['tracker']; appearance=case['appearance']
                proposals=appearance.propose(frame.time,frame.image,tracker.filter_detections(frame.time,row['detections'][str(setting.image_size)]))
                track=tracker.update(frame.time,proposals); appearance.accept(frame.time,track)
                tracked_this_frame[track_key]=(track,(time.perf_counter()-start)*1000)
            track,tracking_ms=tracked_this_frame[track_key]
            start=time.perf_counter()
            run_feet=case['schedule'].decide(frame.time,track,row['pose'],row['box'])
            tracking_ms+=(time.perf_counter()-start)*1000
            pose=dict(row['pose']);foot_ms=0.
            if run_feet:
                pose.update(row['feet']);foot_ms=row['ms']['feet'];case['feet_runs']+=1
            case['samples'].append({'frame':frame.index,'time':frame.time,**track,'pose':pose})
            costs={'decode':row['ms']['decode'],'ball':row['ms']['ball'][str(setting.image_size)],
                   'pose':row['ms']['pose'],'feet':foot_ms,'tracking':tracking_ms}
            costs['service']=sum(costs.values())
            for stage,value in costs.items():case['times'][stage].append(value)
    report=[]
    for case in cases:
        start=time.perf_counter();visual=count_touches(case['samples'],case['config'])
        result=add_audio_evidence(visual,case['samples'],heard,case['config'])
        row={'clip':clip,'video_sha256':payload['key']['video_sha256'],'reference_total':TOTALS[clip],'settings':asdict(case['settings']),
             'sampled_frames':len(case['samples']),'decoded_frames':len(payload['rows']),
             'feet_runs':case['feet_runs'],'foot_fraction':case['feet_runs']/max(1,len(case['samples'])),
             'video_only_count':visual['estimated_count'],'estimated_count':result['estimated_count'],
             'seen_count':result['seen_count'],'heard_count':result['heard_count'],
             'signed_difference':result['estimated_count']-TOTALS[clip],
             'tracking_summary':dict(Counter(s['status'] for s in case['samples'])),
             'stage_timing':{k:stats(v) for k,v in case['times'].items()},
             'counter_audio_merge_ms':(time.perf_counter()-start)*1000}
        row['estimated_service_fps']=1000/row['stage_timing']['service']['mean_ms']
        if clip==0:
            reference=json.loads((ROOT/'validation/manual-review.json').read_text())
            evaluation=compare({**result,'video':{'sha256':payload['key']['video_sha256']},
                                'tracking_summary':row['tracking_summary'],'config':case['config'].to_dict(),
                                'runtime_seconds':0},reference)
            row['original_event_comparison']={k:evaluation[k] for k in ('matched','false_positives','misses','mean_absolute_timing_error')}
        report.append(row)
    (output/f'{device}-clip-{clip}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(device,clip,[(r['settings']['image_size'],r['settings']['fps'],r['settings']['feet'],r['estimated_count']) for r in report],flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--videos',type=Path,default=Path.home()/'Downloads')
    p.add_argument('--devices',nargs='+',choices=['cpu','mps'],default=['cpu','mps'])
    p.add_argument('--clips',type=int,nargs='+',default=list(range(7)))
    p.add_argument('--cache',type=Path,default=ROOT/'.runtime/live-benchmark')
    p.add_argument('--output',type=Path,default=ROOT/'validation/live-revision/benchmark')
    args=p.parse_args();args.cache.mkdir(parents=True,exist_ok=True);args.output.mkdir(parents=True,exist_ok=True)
    paths=sources(args.videos)
    for device in args.devices:
        if device=='mps' and not torch.backends.mps.is_available():
            print('MPS unavailable in this process; no GPU results fabricated.',flush=True);continue
        start=time.perf_counter();config=Config(device=device);ball=BallDetector(ROOT/'models',config);pose=PoseDetector(ROOT/'models',config)
        loading=time.perf_counter()-start
        frame=next(decode(paths[args.clips[0]]))
        # Warm each shape and both pose models; cold startup is recorded separately.
        warm=time.perf_counter()
        for _ in range(3):
            pose.detect(frame.image)
            for size in SIZES:
                ball.config=replace(config,image_size=size);ball.detect(frame.image)
        if device=='mps':torch.mps.synchronize()
        (args.output/f'{device}-environment.json').write_text(json.dumps({'platform':platform.platform(),'torch':torch.__version__,
            'cpu_threads':torch.get_num_threads(),'mps_available':torch.backends.mps.is_available(),
            'load_seconds':loading,'warmup_seconds':time.perf_counter()-warm,'foot_provider':'CPUExecutionProvider',
            'method':'Sequential original-frame inference; cached causal scheduling; no browser/streaming latency measured'},indent=2))
        for clip in args.clips:
            source=paths[clip];key=fingerprint(source,device);cache=args.cache/f'{device}-clip-{clip}.json'
            expected=json.loads((ROOT/f'validation/audio-revision/clip-{clip}-result.json').read_text())['video']['sha256']
            if key['video_sha256']!=expected: raise ValueError(f'Reference hash mismatch: {source}')
            payload=json.loads(cache.read_text()) if cache.exists() else None
            if not payload or payload['key']!=key:payload=collect(source,device,ball,pose,cache,key)
            evaluate(source,clip,device,payload,args.output)


if __name__=='__main__':main()
