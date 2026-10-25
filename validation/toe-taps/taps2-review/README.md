# taps2 user feedback and diagnostic review

User reference total: **31**. Current revision-3 estimate: **27**.
The user total is authoritative feedback, not an algorithm input. It does not
establish exactly four misses: extra and missed events can cancel.

Reviewed sampled frames through the clip and closer frame sequences around
1.55–1.95, 2.85–3.20, 5.95–6.30, 10.60–10.95 and 11.55–11.95 seconds.
Potential missing contacts worth reviewing are around 1.8, 3.0, 6.1 and 10.7s.
These are diagnostic intervals, not frame-accurate reference annotations.

- 1.667–1.767s: ball samples are predicted, so the counter resets. Observed
  contact resumes around 1.8s without an observed outside-to-inside approach.
- Around 3.0s: fragmented toe observations and incorrect ankle/foot assignments
  follow another ball detection gap around 2.867–2.9s.
- Around 6.1s: toe IDs switch shoes near 5.8s, leaving the counter in a held
  contact state when the next real approach occurs.
- Around 10.7s: right-toe predictions stay within the contact zone through the
  preceding foot movement; the counter never sees the necessary departure.

The user clarified that 31 excludes the opening foot-on-ball contact and
includes the final stop/control contact. Use this rule for subsequent review.
The current counter excludes the opening pose and reports the final event at
12.302s, so this boundary convention does not explain the count discrepancy.

Experiment: assign the two toe groups to whichever ankle pairing minimizes
image-space distance, swapping only when the distance improves by >0.3 ball
diameters. This raised taps2 from 27 to 30 but introduced late false candidates;
it also changed taps1 from 33 to 35 (32 matches, 1 miss, 3 extras against its
coarse reference). Rejected; not shipped. A larger total was not improvement.

No counter or UI changes from this investigation. Revision 3 remains active.
Next technical work needs temporally stable foot identity / better foot
observations, and event-level review of taps2 before accepting a change.
Do not weaken the observed-ball requirement or add cadence-based events just
to fill this total. No independent full-clip accuracy claim is supported.
