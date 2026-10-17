"""Compare cached CPU/MPS body landmarks, without asserting ground-truth accuracy."""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('.runtime/live-benchmark'))
    parser.add_argument('--output', type=Path, default=Path('validation/live-revision/benchmark/pose-parity.json'))
    args = parser.parse_args()
    reports = []
    for clip in range(7):
        paths = [args.cache / f'{device}-clip-{clip}.json' for device in ('cpu', 'mps')]
        if not all(path.exists() for path in paths):
            continue
        cpu, mps = [json.loads(path.read_text()) for path in paths]
        if cpu['key']['video_sha256'] != mps['key']['video_sha256']:
            raise ValueError('Cannot compare different videos')
        distances = []
        missing = 0
        for a, b in zip(cpu['rows'], mps['rows'], strict=True):
            if a['frame'] != b['frame'] or a['time'] != b['time']:
                raise ValueError('Frames do not align')
            missing += len(a['pose'].keys() ^ b['pose'].keys())
            for name in a['pose'].keys() & b['pose'].keys():
                distances.append(float(np.linalg.norm(np.subtract(a['pose'][name], b['pose'][name]))))
        reports.append({
            'clip': clip, 'frames': len(cpu['rows']),
            'video_sha256': cpu['key']['video_sha256'],
            'landmark_presence_differences': missing,
            'compared_landmarks': len(distances),
            'median_difference_pixels': float(np.median(distances)) if distances else None,
            'p95_difference_pixels': float(np.percentile(distances, 95)) if distances else None,
            'max_difference_pixels': max(distances, default=None),
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'note': 'Backend agreement only; neither backend is a ground-truth pose reference.',
        'clips': reports,
    }, indent=2) + '\n')
    print(f'Compared {len(reports)} clips')


if __name__ == '__main__':
    main()
