"""One-to-one, timestamp-based event matching with explicit uncertainty exclusions."""
from functools import lru_cache


def compare(result, reference, tolerance=.10):
    if reference.get("video_sha256") and reference["video_sha256"] != result.get("video", {}).get("sha256"):
        raise ValueError("Reference annotations belong to a different video.")
    intervals = reference.get('uncertain_intervals', [])
    def uncertain(time):
        return any(i['start'] <= time <= i['end'] for i in intervals)
    predictions = sorted([e for e in result['events'] if e['status'] == 'counted'], key=lambda e:e['time'])
    # Known labeled contacts remain evaluable even at an uncertain interval boundary.
    truth = sorted([e for e in reference['events'] if e['label'] == 'touch'], key=lambda e:e['time'])
    @lru_cache(None)
    def solve(i, j):
        if i == len(predictions) or j == len(truth):
            return ()
        options = [solve(i + 1, j), solve(i, j + 1)]
        if abs(predictions[i]['time'] - truth[j]['time']) <= tolerance + 1e-9:
            options.append(((i, j),) + solve(i + 1, j + 1))
        return min(options, key=lambda pairs:(-len(pairs),sum(abs(predictions[a]['time']-truth[b]['time']) for a,b in pairs)))
    pairs = solve(0, 0)
    matched_p, matched_t = {i for i,_ in pairs}, {j for _,j in pairs}
    matches = [{'predicted_time': predictions[i]['time'], 'reference_time': truth[j]['time'],
                'predicted_frame': predictions[i]['frame'], 'reference_frame': truth[j].get('frame'),
                'error_seconds': predictions[i]['time'] - truth[j]['time']} for i,j in pairs]
    unmatched = [e for i,e in enumerate(predictions) if i not in matched_p]
    return {'tolerance_seconds':tolerance,'estimated_count':len(predictions),'reference_visible_count':len(truth),
            'matched':len(pairs),'false_positives':[e for e in unmatched if not uncertain(e['time'])],
            'unverifiable_predictions':[e for e in unmatched if uncertain(e['time'])],
            'misses':[e for j,e in enumerate(truth) if j not in matched_t], 'matches':matches,
            'mean_absolute_timing_error':sum(abs(m['error_seconds']) for m in matches)/len(matches) if matches else None,
            'tracking_summary':result['tracking_summary'], 'runtime_seconds':result['runtime_seconds'],
            'config':result['config'], 'uncertain_intervals':intervals}
