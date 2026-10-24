"""Run the same toe-tap pipeline without the web server.

PYTHONPATH=. .venv/bin/python scripts/analyze_toe_taps.py clip.mov output-dir
"""
import argparse
from pathlib import Path
from juggling.pipeline import analyze

parser = argparse.ArgumentParser()
parser.add_argument('video', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
analyze(args.video, args.output, Path(__file__).resolve().parents[1]/'models',
        drill='toe_taps', progress=lambda **state: print(state, flush=True)
        if state.get('frames',0)%100==0 else None)
