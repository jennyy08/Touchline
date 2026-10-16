"""Make a static evidence plot from saved results; no model inference required."""
import argparse
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path('.runtime/matplotlib').resolve()))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('--result', type=Path, default=Path('validation/final-result.json'))
p.add_argument('--reference', type=Path, default=Path('validation/manual-review.json'))
p.add_argument('--output', type=Path, default=Path('validation/trajectory.png'))
a = p.parse_args()
r, ref = json.loads(a.result.read_text()), json.loads(a.reference.read_text())
fig, (ax, events) = plt.subplots(2, 1, figsize=(13, 6), sharex=True,
                                gridspec_kw={'height_ratios': [3, 1.3]})
for state, color, marker in [('detector', '#237744', '.'), ('appearance', '#189eaa', '.'), ('predicted', '#bc7618', 'x')]:
    samples = [s for s in r['samples'] if s.get('source') == state or s['status'] == state]
    ax.scatter([s['time'] for s in samples], [s['center'][1] for s in samples],
               s=10, c=color, marker=marker, label=state.title())
for gap in r['tracking_gaps']:
    ax.axvspan(gap['start'], max(gap['start']+.02, gap['end']), color='#f5b04b', alpha=.12)
ax.invert_yaxis()
ax.set_ylabel('Ball center y (pixels; down is positive)')
ax.set_title('Supplied clip: observed evidence and event-level comparison', loc='left')
ax.legend(loc='upper right')
manual = [e['time'] for e in ref['events'] if e['label'] == 'touch']
counted = [e['time'] for e in r['events'] if e['status'] == 'counted']
review = [e['time'] for e in r['events'] if e['status'] == 'review']
events.scatter(manual, [2]*len(manual), color='#303e59', marker='|', s=150)
events.scatter(counted, [1]*len(counted), color='#237744', marker='|', s=150)
events.scatter(review, [0]*len(review), color='#bc7618', marker='|', s=150)
for interval in ref['uncertain_intervals']:
    events.axvspan(interval['start'], interval['end'], color='gray', alpha=.18)
events.set_yticks([0, 1, 2], [f'Review candidates ({len(review)})', f'Automatic count ({len(counted)})', f'Visible reference ({len(manual)})'])
events.set_ylim(-.6, 2.6)
events.set_xlabel('Presentation time (seconds)')
events.set_xlim(0, r['video']['duration'])
for axes in (ax, events):
    axes.grid(alpha=.15)
    axes.spines[['top','right']].set_visible(False)
fig.tight_layout()
fig.savefig(a.output, dpi=150)
print(a.output)
