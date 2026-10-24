# Revision 2: recover observed contacts, not a target total

User reference: taps1 contains **33 taps**. This was used as a total check, not
as an input to counting, timing, interpolation or threshold selection.

## Event comparison

Reviewed sequential 0.1-second frames through the active portion of taps1,
including shoe/ball crops. `reference.json` contains 33 approximate visual
contact times. This is a coarse development reference informed by the known
user total, not blind annotation or frame-accurate proof. Timing tolerance is
±0.15 seconds. Contact timing and hidden sole contact remain uncertain.

| Version | Automatic total | Matched reference events | Misses | Extra events |
|---|---:|---:|---:|---:|
| Previous | 23 | 22 | 11 | 1 |
| Revised | 31 | 30 | 3 | 1 |

Remaining misses: approximately 1.20, 4.75, 11.00 seconds. Remaining extra:
4.57 seconds. The extra is close to a real contact but outside the exploratory
tolerance; inspect it rather than declaring the total nearly correct.
The missed 1.2s contact coincides with an identity change between shoe landmarks.
At 4.75s an earlier candidate is selected; at 11s the short near-ball motion is
not cleanly rearmed/confirmed. Further changes need better spatial identity
tracking or stronger contact evidence, not a forced alternating schedule.

## Changes and rejected alternatives

- Short toe-only gaps (up to 0.12s) retain state, but missing frames contribute
  no confirmation duration. Missing ball observations still reset the cycle.
- Multiple in-zone observations can confirm an approach before departure, so
  a final tap followed by holding the ball is not automatically thrown away.
- The original quick entry/release evidence remains available; sustained-only
  counting regressed some previously found fast contacts.
- Near-simultaneous approaches are merged, with contributing times retained.
  A foot-ID conflict clears the anatomical label instead of discarding both
  events. This can merge distinct very fast taps; it is an explicit limitation.
- Within a merged group, sustained evidence is preferred over a brief excursion.
  Choosing the first event increased the total to 31 but yielded only 27 matches
  and 4 extras; it was rejected. The final selection has 30 matches and 1 extra.
- Three-frame smoothing and stricter departure rearming were tried on cached
  observations but did not improve the early reviewed interval and were not kept.

No cadence filling, target count, audio events, new detector, or model training.
Counts for taps2 and taps3 change from 13→27 and 16→20. Those additional events
have **not** been manually validated; these totals are not evidence of accuracy.
Original samples, playback, and results are preserved. Revised results are in
`.runtime/toe-taps/revision-2`; original server jobs remain accessible separately.

122 backend and 14 frontend tests pass. Regression cases cover a confirmed final
hold, an initial held pose, short toe-only gaps, long gaps, predicted ball
exclusion, quick entry/release, duplicate foot IDs and repeated same-foot taps.
