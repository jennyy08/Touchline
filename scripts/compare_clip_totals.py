"""Compare user-supplied totals without claiming event-level accuracy.

Run after saving clip-N-reference.json and clip-N-result.json in a directory.
Optionally include clip-N-edge-guard-result.json for a before/after comparison.
"""
import argparse
import json
from pathlib import Path


def summarize(root):
    rows = []
    for path in sorted(root.glob('clip-*-reference.json')):
        reference = json.loads(path.read_text())
        prefix = path.name.removesuffix('-reference.json')
        for variant, suffix in [('baseline', '-result.json'), ('edge_guard', '-edge-guard-result.json')]:
            result_path = root / (prefix + suffix)
            if not result_path.exists():
                continue
            result = json.loads(result_path.read_text())
            if reference['video_sha256'] != result['video']['sha256']:
                raise ValueError(f'Wrong video for {result_path}')
            rows.append({'clip': prefix, 'variant': variant,
                         'reference_total': reference['touch_count'],
                         'automatic_total': result['estimated_count'],
                         'signed_total_difference': result['estimated_count'] - reference['touch_count'],
                         'review_candidates': sum(e['status'] == 'review' for e in result['events']),
                         'tracking_summary': result['tracking_summary'],
                         'runtime_seconds': result['runtime_seconds'],
                         'event_precision': None, 'event_recall': None})
    return {'limitation': 'Totals only: extra and missed events can cancel. No event-level metrics without timestamp labels.',
            'comparisons': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = summarize(args.directory)
    (args.directory / 'total-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
