"""Compare causal visual counting with saved historical results, without inference."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from juggling.config import Config
from juggling.counting import count_touches, add_audio_evidence
from juggling.streaming import StreamingCounter

root = Path(__file__).resolve().parents[1]
rows = []
for clip in range(7):
    baseline = json.loads((root / f'validation/audio-revision/clip-{clip}-result.json').read_text())
    config = Config(**baseline['config'])
    samples = baseline['samples']
    stream = StreamingCounter(config)
    for sample in samples:
        stream.update(sample)
    stream.finish()
    batch = count_touches(samples, config)
    assert batch['events'] == stream.events
    onsets = [(o['time'], o['strength']) for o in baseline['audio']['onsets']]
    enriched = add_audio_evidence(batch, samples, onsets, config)
    old_visual = sum(e['status']=='counted' and e['reason']=='observed_reversal_near_leg' for e in baseline['events'])
    old_decisions = [(e['time'], 'review' if e['reason']=='gap_confirmed_by_sound' else e['status'],
                      'gap_near_contact' if e['reason']=='gap_confirmed_by_sound' else e['reason'])
                     for e in baseline['events'] if e['reason']!='heard_ball_out_of_view']
    new_decisions = [(e['time'],e['status'],e['reason']) for e in batch['events']]
    changes = {'removed':sorted(set(old_decisions)-set(new_decisions)),
               'added':sorted(set(new_decisions)-set(old_decisions))}
    rows.append({'visual_decision_changes_from_previous':changes,'clip':clip, 'old_visual_count':old_visual,
                 'streaming_visual_count':batch['estimated_count'],
                 'old_with_audio':baseline['estimated_count'],
                 'causal_visual_with_offline_audio':enriched['estimated_count'],
                 'streaming_equals_wrapper':True, 'events':batch['events']})
output = root / 'validation/live-revision/streaming-regression.json'
output.write_text(json.dumps(rows, indent=2)+'\n')
for r in rows:
    print({k:v for k,v in r.items() if k!='events'})
