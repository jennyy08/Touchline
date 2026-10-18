"""Run repeatable, offline side-to-side analysis on supplied development clips.

Example:
.venv/bin/python scripts/validate_dribbling.py ~/Downloads/side2side{1,2,3}.mov \
  --roi 0 .42 1 1 --markers .19 .835 --reach

Outputs observations, not accuracy scores: these clips do not yet have an
independently labelled set of turn/crossing events.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from juggling.pipeline import analyze
from juggling.dribbling import DrillSetup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('clips',type=Path,nargs='+')
    p.add_argument('--roi',type=float,nargs=4,default=[0,0,1,1])
    p.add_argument('--markers',type=float,nargs=2)
    p.add_argument('--reach',action='store_true')
    p.add_argument('--output',type=Path,default=Path('.runtime/dribbling-validation'))
    args=p.parse_args()
    setup=DrillSetup(roi=args.roi,markers=args.markers,require_markers=args.reach)
    summary=[]
    for i,source in enumerate(args.clips,1):
        r=analyze(source,args.output/f'clip-{i}',Path('models'),drill_setup=setup)
        d=r['dribbling']
        row={'clip':source.name,'frames':r['video']['frames'],'runtime_seconds':r['runtime_seconds'],
             'tracking':r['tracking_summary'],'turns':len(d['turns']), 'review_windows':len(d['review_windows']),
             'trips':len(d['trips']),'slower_trips':sum(t['slower'] for t in d['trips'])}
        summary.append(row); print(json.dumps(row),flush=True)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
