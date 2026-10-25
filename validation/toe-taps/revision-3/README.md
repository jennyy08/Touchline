# Revision 3: user-reported missed contacts

This revision targets the user's missed-contact intervals around 1.1–1.6,
4.3–4.8 (screen-left foot), and 10.5–11.3 seconds in taps1. It reuses the
original detector observations and the approximate visual reference in
`../revision-2/reference.json`; no model downloads or inference changes.

| Counter | Count | Matched | Missed | Extra |
|---|---:|---:|---:|---:|
| Revision 2 | 31 | 30 | 3 | 1 |
| Revision 3 | 33 | 33 | 0 | 0 |

One-to-one matching uses ±0.15 seconds. This is a development-set comparison
against coarse, non-blind labels, not proof of general accuracy. The total 33
was supplied by the user. No target total or clip-specific times enter code.

Changes:
- All toes leaving the horizontal contact zone rearms that foot. Vertical
  hysteresis remains. Previously a toe just outside the zone could prevent
  the next approach being recognized. The recovered event is at 1.133s.
- Merged candidates prefer sustained contact and then more observed in-zone
  frames. This selects 4.733s instead of the short 4.567s landmark excursion.
  Counts alone hid this error; the timestamp comparison exposes the change.
- A sudden downward toe-to-ankle offset change (>0.5 ball diameters) with a
  relatively stable ankle (<0.25 diameters movement) is treated as a missing
  toe observation, not a release. Short-gap rules still apply, and ankle
  observations alone cannot confirm a tap. Two observed contact frames plus
  departure now support the event at 11.002s.

An initial version rejected offset jumps in any direction. It recovered the
late event but lost the real 4.0s event, so was rejected. The retained filter
only rejects downward inconsistencies. This heuristic can still reject real
foot articulation or merge very fast distinct contacts; it needs held-out
clips with event labels. Support frames are evidence counts, not confidence.

Other clip totals: taps2 stays 27; taps3 changes 20→19. Those events have not
been independently labeled, so this may represent improvement or regression.
Original and revision-2 jobs remain available. New local replay jobs are
`taps-v3-1`, `taps-v3-2`, `taps-v3-3`. Counter-only reruns do not measure new
inference runtime; result runtime fields retain the original pipeline runtime.

Playback recovery reloads the media decoder after a hidden/visible transition
or browser back-forward restoration, preserving position, speed and playback
intent. A Refresh video button provides the same recovery manually. The
reported host-preview black-screen failure has not been reliably reproduced;
this is a recovery mechanism, not a confirmed diagnosis of the host bug.

Validation: 126 Python tests and 17 frontend tests pass; TypeScript/Vite build
passes. Browser check confirmed the 33-event replay, event seeking, visible
video after manual refresh, and restoration of paused time at 4.433333s.
Lifecycle tests cover hidden/visible recovery, restoring speed, resuming an
already-playing clip, and cancelling restoration when a different clip loads.
