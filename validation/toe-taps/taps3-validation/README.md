# taps3 fresh validation — 2026-10-26

Ran the original `/Users/jennyyuan/Downloads/taps3.mov` through the current local pipeline using `scripts/analyze_toe_taps.py`. Result: **23 counted events**, runtime **119.87 seconds**, 399 decoded frames; 348 observed ball samples, 19 predicted, 32 lost. Full playback and sample data are in ignored `.runtime/toe-taps/taps3-validation/`.

This supersedes the earlier cached recount of 22 counted events plus one review candidate. The serialized configuration is identical, but fresh detections/tracking differ (cached: 344 observed, 16 predicted, 39 lost). The source of that inference difference has not been isolated; reproducibility remains an issue to investigate. Do not use the cached 22-event replay as evidence of this fresh run.

## Visual checks

Reviewed sequences sampled at 0.1-second intervals across the entire clip, including full-width checks near the left edge. These are approximate contact observations, not frame-accurate reference labels.

- Visible alternating contacts around **6.4, 6.8 and 7.6 seconds** have no nearby automatic event. The algorithm jumps from 6.233 to 7.167 to 8.667 seconds. These are missed visible contacts, not solely offscreen losses.
- Events at **12.235 and 12.402 seconds** appear to split one sustained final ball control into two counts. Samples show the same shoe remaining on the ball during roughly 12.2–12.5. Both events use the primary pose view and the same anatomical foot; the first reports departure at 12.368. This suggests a false contact-release/re-entry signal, rather than simply an alternate-view duplicate.
- Ball/contact visibility is insufficient near **8.0–8.5 and 9.1–9.8 seconds** as the action crosses the left image boundary. Hidden contacts cannot be verified or reconstructed from cadence. Some edge contacts outside these intervals are also partially cropped.
- The events around 5.87 and 6.23 occur later than the apparent visual contacts around 5.7 and 6.0. Timing error and missing events must be distinguished when reviewing these.

No verified full-clip total or accuracy percentage is claimed. A full event-level score needs completed reference annotations, particularly decisions about the partly hidden edge contacts. Existing manual-review import/export can collect those corrections. The user has not supplied a total for taps3 (the earlier 21 belonged to a different juggling clip).

## Recommended follow-up

Investigate sustained-contact fragmentation at the end and missing toe evidence around 6.4–7.6. Keep offscreen contacts separate from visible failures. Repeat fresh inference to isolate why cached and fresh tracking differ before treating a one-count improvement as stable. No algorithm thresholds were changed for this validation and nothing was pushed.
