"""Compare two analyses of the same original input, independently of accuracy.

PYTHONPATH=. .venv/bin/python scripts/compare_inference.py before/result.json after/result.json
"""
import argparse
import json
from pathlib import Path
from juggling.provenance import compare_observations

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('before', type=Path)
parser.add_argument('after', type=Path)
args = parser.parse_args()
print(json.dumps(compare_observations(json.loads(args.before.read_text()),
                                      json.loads(args.after.read_text())), indent=2))
