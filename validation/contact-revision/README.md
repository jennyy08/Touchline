# Contact revision: foot reach, no wrist veto, top exits, stop markers

This revision changes contact classification only (`juggling/counting.py`, new fields in `juggling/config.py`). Detection, pose, appearance and tracking are unchanged: the full reruns produced tracking samples identical to `validation/tracking-revision/`. User totals stay 26 for the original clip and 16/29/21 for the three additional clips. The player confirmed that every touch in these clips was a foot touch and none was a hand touch. The clips were **not** recounted.

## Changes

- **Wrist check removed.** A wrist landmark within 0.65 ball diameters used to send an event to review, even with a leg right there. In juggling, a nearby projected arm says nothing about the contact, so wrists neither create nor block a touch.
- **Leg support over contact ±1 frame.** Each adjacent observed frame is compared with its own ball position. Pose landmarks jitter or vanish on a fast kicking leg.
- **Estimated foot.** COCO ankles are not toes. A horizontal segment either side of each ankle, with half-length `foot_length_shin_ratio` (0.6) × knee–ankle length, approximates the foot. It only applies between knee height and just below the ankle, so a thigh-height ball cannot match a foot. The global `contact_diameters` (1.15) is unchanged. The 0.6 ratio is a rough anatomical proportion (foot ≈ 0.6 × shin). It was chosen before measuring and has not been varied.
- **Top exits.** If the only outgoing observation is a box cut off by the top edge and the ball then leaves view, outgoing motion uses the box bottom edge (a clipped box's center is biased downward). The event is tagged `evidence: ["top_exit"]`. Predicted positions remain non-evidence.
- **Stop markers.** `stops: [{start, end, start_frame, end_frame, reason}]` lists intervals where the observed ball stays within 0.5 diameters for ≥ 1.0 s (e.g. a catch). Stops never change the count. The UI shows them as blue timeline spans and "STOPPED" rows. Older results without `stops` still load.

## Results

| Clip | User total | Tracking revision | Contact revision | Still in review |
|---|---:|---:|---:|---|
| Original | 26 | 24 | 26 | none |
| 1 / 12.26 PM | 16 | 15 | 16 | none |
| 2 / 12.28 PM | 29 | 24 | 29 | none |
| 3 / 12.29 PM | 21 | 18 | 20 | 3.835 s `contact_not_supported` |

**Original (timestamp reference):** 26 one-to-one matches within ±0.10 s, 0 unmatched counted events, 0 misses (`original-evaluation.json`). The reference times are approximate (about 1–2 frames), so the mean timing difference of ~0.006 s is not a sub-frame accuracy claim.

**Clips 1–3:** totals only. Matching totals cannot rule out a miss cancelling an extra. All four clips have now shaped design decisions twice, so they are regression examples, not an independent accuracy test. No stops were reported on any clip. None contains a catch, so this only checks for false stops.

## Every newly counted event, inspected

| Clip | Time / frame | Before | Cause | Sheet | Visual verdict |
|---|---|---|---|---|---|
| 0 | 6.600 s / 198 | not a candidate | top exit | `original-top-exit.jpg` | Sole meets ball, ball leaves top edge |
| 0 | 7.267 s / 218 | hand flag | wrist removed | `original-wrist-7267.jpg` | Foot contact; matches reference 7.233 s |
| 1 | 7.935 s / 238 | leg flag | foot zone + neighbor frame | `clip-1-foot-7935.jpg` | Extended right foot under ball |
| 2 | 8.968 s / 269 | hand flag | wrist removed | `clip-2-wrist-8968-9602.jpg` | Raised foot under ball |
| 2 | 9.602 s / 288 | hand flag | wrist removed | same | Foot under ball; arm nearby |
| 2 | 10.168 s / 305 | hand flag | wrist removed | `clip-2-wrist-10168-14135.jpg` | Foot under ball |
| 2 | 14.135 s / 424 | hand flag | wrist removed | same | Sole directly under ball |
| 2 | 15.602 s / 468 | leg flag | foot zone + neighbor frame | `clip-2-foot-15602.jpg` | Extended right foot at ball |
| 3 | 3.368 s / 101 | leg flag | neighbor frame (ankle at 1.01 diameters in frame 102) | `clip-3-neighbor-3368.jpg` | Extended foot under ball |
| 3 | 10.202 s / 306 | hand flag | wrist removed | `clip-3-wrist-10202.jpg` | Foot rising into ball |

Each foot-zone count was checked with the zone disabled (`foot_length_shin_ratio=0`): clip 1 at 7.935 s and clip 2 at 15.602 s depend on it, while clip 3 at 3.368 s counts from the neighbor frame alone.

**Remaining review, clip 3 at 3.835 s / frame 115** (`clip-3-unresolved-3835.jpg`): the frame shows the kicking foot's sole at the ball, but both ankle landmarks are placed on the standing foot. The nearest knee is 1.3 diameters away. This is a pose failure, so it stays uncounted. Fixing it needs better foot evidence, not a wider threshold.

## Known limits

- **Body-part labels are unreliable.** Seven of the ten newly counted foot touches (and many earlier counted ones) are labelled knee or thigh, because the label is just the nearest landmark and a high-raised foot sits near knee height. The label does not affect counting, but it should not be trusted. A real foot/toe landmark (e.g. a pose model with heel/toe points) is the clearest next step.
- No real knee/thigh, catch, hand-contact or floor-bounce clip has been tested. These rely on synthetic tests only.
- Without a toe direction, the foot zone extends on both sides of the ankle. That could support a ball beside the heel.
- Top-exit counting accepts a single outgoing observation. Any brief exit through the top edge after a downward-to-upward reversal near a leg can count.

## Verification

Python: 44 tests pass, including wrist-on-ball still counting, extended foot, far ball, thigh height, neighbor-frame support, top exit vs non-clipped single sample, held ball (one stop, not counted), and short pause/ordinary juggle (no stop). Frontend: 5 tests, TypeScript check, Prettier and production build pass. Full reruns took 43.1 / 31.7 / 45.1 / 34.9 s (single runs on this Mac, not benchmarks).
