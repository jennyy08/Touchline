# Revision 6: interrupted-contact merging

A confirmed same-foot contact can be fragmented by a brief landmark excursion.
Merge adjacent candidate evidence when the next entry is less than the existing
0.22-second debounce apart, the evidence gap is at most 0.08 seconds, and all
intervening ball samples are observed. Preserve interrupted entry timestamps.
Alternate views cannot add another event inside that merged contact interval.
This uses observed geometry, not an assumed rhythm or a target total.

A trial requiring sustained departure everywhere was rejected: it removed a
valid taps1 event and did not resolve the taps3 duplicate across views.

## Regression results on unchanged saved observations

| Clip | Before | After | Matches at ±0.15 s before → after |
| --- | ---: | ---: | --- |
| taps1 | 33 | 33 | 33 → 33 |
| taps2 | 31 | 31 | 31 → 31 |
| taps3 | 23 | 22 | No complete reference |

At ±0.10 s, taps1 matches improve from 31 to 32; taps2 remains 29.
References are approximate visual annotations, not frame-accurate truth.
Detailed before/after comparisons are in taps1.json and taps2.json.
Taps3's final two primary events are now one interval starting around 12.10 s;
this removes the visually identified duplicate, not a verified full-clip error.

## Remaining misses and correction to the earlier review

The earlier statement that 6.4 s was definitely a separate missed event was too
strong. The automatic event at 6.233 s has observed support through 6.667 s,
covering that interval. A timing error, a merged contact, and an actually missed
contact cannot be distinguished just from a nearest-timestamp test. More precise
video labels are needed there.

Around 6.8–7.0 s, raw toe landmarks disappear or jump between the ball and floor.
At 6.833 the primary view has no toe points; 6.867 has a brief in-zone point;
6.9 lacks that toe; 6.933 places it below the contact zone. The motion view also
places one toe more than a ball diameter laterally away. The supporting crop
is missing points. This is insufficient consistent contact evidence.

Around 7.6–7.8 s the contact approaches the left boundary. Toe observations
become incomplete before ball tracking becomes predicted at 7.8 s. Increasing
the contact radius or counting lone observations would risk false positives.
Diagnostic samples are preserved in missed-contact-observations.json.

No hidden contacts are invented. Full taps3 accuracy remains unverified.
The interruption rule can merge genuinely rapid repeated same-foot contacts;
that is a known tradeoff to test on new footage. No custom model training.

147 Python tests pass, including new tests for interrupted holds, clear
separate contacts, and alternate-view duplication. No frontend changes.

Fresh full-pipeline taps3 run: 21 counted, 113.0 seconds. Event records identical to the revised cached-observation recount: False. Recount with the final observed-gap guard also gives identical events. This confirms the new counter on fresh inference for this run; it does not establish inference determinism across environments.

The fresh run counts 21 plus one review candidate (6.967 s), while the fixed
previous observations count 22. Fresh ball tracking matches the older cached
344/16/39 observed/predicted/lost split. Around the boundary return, the previous
observations produced two counts at 8.667 and 8.900 s; fresh inference produces
one at 8.800 s. Thus the fresh total difference must not be attributed solely
to the counting change. The final duplicate is removed in both observation sets.
The existing running server and saved browser jobs have not been restarted or
rewritten; restart the backend and run a new analysis to use revision 6.
