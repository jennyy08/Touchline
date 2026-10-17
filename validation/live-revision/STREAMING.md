# Causal visual counter

The webcam and `count_touches()` now share `StreamingCounter`. Inference still
uses the upload model settings for uploads; only the counter implementation is
shared. Historical benchmark files describe the earlier whole-clip counter.

Each observed candidate waits 0.14 seconds for outgoing motion. The floor is
estimated from stable foot landmarks received in the preceding five seconds,
with the existing ankle fallback. Contact support uses adjacent observations
within 0.075 seconds rather than source-frame-number adjacency. Predictions do
not supply touch evidence, and long gaps/segments remain uncounted or flagged.
Confirmed events are immutable; the first candidate wins inside the debounce
interval instead of replacing an already displayed event with a stronger one.

At EOF/Stop, `finish()` closes the last window with existing observations only.
It still requires two outgoing observations or the explicit top-exit rule. Live
transport waits one window after Stop; EOF needs no wall-clock sleep. These
late events carry `confirmation_context: end_of_stream` and a confirmation time
that can fall beyond the recording duration. This matters for the original
clip's final touch: only 0.067 seconds of footage follows it, but two real
outgoing observations support it. No predicted or fabricated positions are used.

## Saved-sample regression

Run `.venv/bin/python scripts/validate_streaming.py`.

| Clip | Previous visual | Causal visual | Previous with audio | Causal visual + offline audio |
|---|---:|---:|---:|---:|
| Original | 26 | 26 | 26 | 26 |
| 1 | 16 | 16 | 16 | 16 |
| 2 | 29 | 29 | 29 | 29 |
| 3 | 21 | 21 | 21 | 21 |
| 4 | 12 | 12 | 13 | 13 |
| 5 | 21 | 21 | 25 | 25 |
| 6 | 20 | 20 | 23 | 23 |

Incremental and offline-wrapper events are identical on all seven saved sample
sets. This validates counter equivalence on identical evidence, not detector
accuracy or real-time frame dropping. Audio remains an offline enrichment using
future clip information; these audio-assisted counts are not live counts.
Full causal event records are in `streaming-regression.json`. Compared with previous
visual decisions (before audio enrichment), six clips have identical event times,
statuses and reasons. Clip 2 has one touch 0.033 seconds earlier (15.068 instead
of 15.102 seconds) because causal debouncing keeps the first candidate. No other
visual decision changes were found; this comparison is against prior predictions,
not new ground-truth labels.

Six new tests cover confirmation timing, immutable decisions, nonconsecutive
source IDs, unavailable/future floor evidence, unfinished tails, explicit EOF,
invalid timestamps and floor expiry. All 76 Python tests pass at this milestone.
