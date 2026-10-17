"""Direct sequential inference for a chosen profile (no cached stage-cost estimate).

This processes recorded clips as fast as possible. It does not simulate capture
backpressure, a browser, or a streaming counter. It verifies the matrix's candidate
with only the selected models/schedule running, avoiding cross-profile interference.
"""
from dataclasses import asdict, replace
import argparse
import hashlib
import platform
from collections import Counter
import torch
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_live import sources, timed, stats, ROOT, TOTALS
from juggling.config import Config
from juggling.detection import BallDetector
from juggling.pose import PoseDetector
from juggling.video import decode
from juggling.audio import onsets
from juggling.tracking import BallTracker
from juggling.appearance import AppearanceBridge
from juggling.live_settings import LiveSettings, FrameGate, FootSchedule
from juggling.counting import count_touches, add_audio_evidence
from juggling.evaluation import compare


def run(source, clip, setting, ball, pose, config):
    tracker=BallTracker(config)
    appearance=AppearanceBridge(config)
    gate=FrameGate(setting.fps)
    schedule=FootSchedule(setting)
    costs={k:[] for k in ('decode','ball','pose','feet','tracking','service')}
    samples=[]
    feet_runs=0
    iterator=iter(decode(source))
    started=time.perf_counter()
    decoded=0
    while True:
        start=time.perf_counter()
        try:
            frame=next(iterator)
        except StopIteration:
            break
        decode_ms=(time.perf_counter()-start)*1000
        decoded+=1
        if not gate.accept(frame.time):
            continue
        detections,ball_ms=timed(setting.device,lambda:ball.detect(frame.image))
        body,pose_ms=timed(setting.device,lambda:pose.detect_body(frame.image))
        landmarks,box=body
        start=time.perf_counter()
        proposals=appearance.propose(frame.time,frame.image,tracker.filter_detections(frame.time,detections))
        track=tracker.update(frame.time,proposals)
        appearance.accept(frame.time,track)
        run_feet=schedule.decide(frame.time,track,landmarks,box)
        tracking_ms=(time.perf_counter()-start)*1000
        feet_ms=0.
        if run_feet:
            points,feet_ms=timed('cpu',lambda:pose.feet.detect(frame.image,box,config.landmark_threshold))
            landmarks.update(points)
            feet_runs+=1
        row={'decode':decode_ms,'ball':ball_ms,'pose':pose_ms,'feet':feet_ms,'tracking':tracking_ms}
        row['service']=sum(row.values())
        for key,value in row.items():costs[key].append(value)
        samples.append({'frame':frame.index,'time':frame.time,**track,'pose':landmarks})
    processing_seconds=time.perf_counter()-started
    video_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    visual=count_touches(samples,config)
    result=add_audio_evidence(visual,samples,onsets(source),config)
    report={'video_sha256':video_hash,'clip':clip,'settings':asdict(setting),'pose_input':config.pose_size,'reference_total':TOTALS[clip],
            'decoded_frames':decoded,'sampled_frames':len(samples),'feet_runs':feet_runs,
            'stage_timing':{k:stats(v) for k,v in costs.items()},
            'processing_seconds_excluding_counter_audio':processing_seconds,
            'video_only_count':visual['estimated_count'],'estimated_count':result['estimated_count'],
            'seen_count':result['seen_count'],'heard_count':result['heard_count'],
            'events':result['events']}
    if clip==0:
        reference=json.loads((ROOT/'validation/manual-review.json').read_text())
        for name, counted in (('video',visual),('with_offline_audio',result)):
            comparison=compare({**counted,'video':{'sha256':video_hash},
                                'tracking_summary':dict(Counter(s['status'] for s in samples)),
                                'runtime_seconds':processing_seconds,'config':config.to_dict()},reference)
            report[name+'_event_comparison']=comparison
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device',choices=['cpu','mps'],required=True)
    p.add_argument('--size',type=int,choices=[640,480,320],required=True)
    p.add_argument('--threads',type=int,help='Override PyTorch CPU threads after model initialization')
    p.add_argument('--pose-size',type=int,choices=[640,480,320],default=640)
    p.add_argument('--fps',type=int,choices=[30,15],required=True)
    p.add_argument('--feet',choices=['off','all','near'],required=True)
    p.add_argument('--clips',type=int,nargs='+',default=list(range(7)))
    p.add_argument('--videos',type=Path,default=Path.home()/'Downloads')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    settings=LiveSettings(device=args.device,image_size=args.size,fps=args.fps,feet=args.feet)
    config=replace(Config(),device=args.device,image_size=args.size,pose_size=args.pose_size,
                   foot_model='' if args.feet=='off' else Config().foot_model)
    start=time.perf_counter()
    ball=BallDetector(ROOT/'models',config)
    pose=PoseDetector(ROOT/'models',config)
    paths=sources(args.videos)
    first=next(decode(paths[args.clips[0]]))
    for _ in range(3):
        ball.detect(first.image)
        pose.detect(first.image)
    if args.device=='mps':torch.mps.synchronize()
    if args.threads is not None:
        if args.threads < 1: p.error('--threads must be positive')
        torch.set_num_threads(args.threads)
        for _ in range(3):
            ball.detect(first.image)
            pose.detect(first.image)
        if args.device=='mps':torch.mps.synchronize()
    startup=time.perf_counter()-start
    reports=[]
    for clip in args.clips:
        report=run(paths[clip],clip,settings,ball,pose,config)
        reports.append(report)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'platform':platform.platform(),'torch':torch.__version__,'cpu_threads':torch.get_num_threads(),
                                          'startup_warmup_seconds':startup,'clips':reports},indent=2)+'\n')
        print(clip,report['video_only_count'],report['estimated_count'],report['stage_timing']['service'],flush=True)


if __name__=='__main__':main()
