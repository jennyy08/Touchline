"""Summarize complete per-clip benchmark outputs without inventing live accuracy."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    args=p.parse_args();groups=defaultdict(list)
    for path in sorted(args.directory.glob('*-clip-*.json')):
        for row in json.loads(path.read_text()):
            s=row['settings'];groups[(s['device'],s['image_size'],s['fps'],s['feet'])].append(row)
    summary=[]
    for key,rows in sorted(groups.items()):
        rows.sort(key=lambda r:r['clip'])
        if [r['clip'] for r in rows]!=list(range(7)):
            continue  # Partial runs are not seven-clip comparisons.
        frames=sum(r['sampled_frames'] for r in rows)
        mean=sum(r['stage_timing']['service']['mean_ms']*r['sampled_frames'] for r in rows)/frames
        slowest=max(r['stage_timing']['service']['p95_ms'] for r in rows)
        summary.append({'device':key[0],'ball_input':key[1],'fps':key[2],'feet':key[3],
            'total_counts':[r['estimated_count'] for r in rows],
            'video_counts':[r['video_only_count'] for r in rows],
            'sum_absolute_total_difference':sum(abs(r['signed_difference']) for r in rows),
            'sum_absolute_video_difference':sum(abs(r['video_only_count']-r['reference_total']) for r in rows),
            'mean_service_ms':mean,'slowest_clip_p95_service_ms':slowest,
            'estimated_service_capacity_fps':1000/mean,
            'meets_target_period_at_slowest_clip_p95':slowest<=1000/key[2],
            'foot_fraction':sum(r['feet_runs'] for r in rows)/frames,
            'original_matches':rows[0]['original_event_comparison']['matched'],
            'original_unmatched':len(rows[0]['original_event_comparison']['false_positives']),
            'stage_mean_ms':{stage:sum(r['stage_timing'][stage]['mean_ms']*r['sampled_frames'] for r in rows)/frames
                             for stage in ('decode','ball','pose','feet','tracking')}})
    (args.directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    text=['# Benchmark matrix','',
          'Reference totals: original / clips 1–6 = **26 / 16 / 29 / 21 / 13 / 25 / 23**.',
          'Counts include offline audio evidence. These are not streaming/live results; sum absolute total difference is not an event-error count.',
          'Body pose stays at 640; input size below changes the ball detector only. Foot inference is always ONNX CPU, including MPS rows.',
          'Service milliseconds add measured stage costs; they exclude browser/network/queueing and the later counter/audio decisions.',
          '', '| Device | Ball input | FPS | Feet | Video counts | With offline audio | Sum absolute difference | Mean ms | Worst clip p95 ms | Foot frames |',
          '|---|---:|---:|---|---|---|---:|---:|---:|---:|']
    for r in summary:
        counts='/'.join(map(str,r['total_counts'])); video='/'.join(map(str,r['video_counts']))
        text.append(f"| {r['device']} | {r['ball_input']} | {r['fps']} | {r['feet']} | {video} | {counts} | {r['sum_absolute_total_difference']} | {r['mean_service_ms']:.1f} | {r['slowest_clip_p95_service_ms']:.1f} | {r['foot_fraction']:.0%} |")
    (args.directory/'MATRIX.md').write_text('\n'.join(text)+'\n')
    print(f'{len(summary)} complete seven-clip profiles written')


if __name__=='__main__':main()
