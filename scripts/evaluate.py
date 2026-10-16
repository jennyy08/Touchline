import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from juggling.evaluation import compare
p=argparse.ArgumentParser()
p.add_argument('result',type=Path);p.add_argument('--reference',type=Path,default=Path('validation/manual-review.json'))
p.add_argument('--output',type=Path)
a=p.parse_args();report=compare(json.loads(a.result.read_text()),json.loads(a.reference.read_text()))
if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:(len(v) if k in ['false_positives','misses','unverifiable_predictions'] else v) for k,v in report.items() if k not in ['matches','config','uncertain_intervals']},indent=2))
