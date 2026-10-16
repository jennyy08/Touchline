"""Explainable contact candidates from observed motion, never a black-box count."""
import numpy as np


def distance_to_segment(point, a, b):
    p, a, b = map(lambda v: np.asarray(v, dtype=float), (point, a, b))
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


def stable_heights(samples, names, offset_diameters):
    """Image heights of landmarks that stay nearly still between frames (a planted foot)."""
    stable = []
    for a, b in zip(samples, samples[1:]):
        dt = b["time"] - a["time"]
        for key in names:
            if key in a["pose"] and key in b["pose"] and b["diameter"]:
                diameter = b["diameter"]
                if np.linalg.norm(np.array(b["pose"][key]) - a["pose"][key]) < diameter * dt * 0.8:
                    stable.append(b["pose"][key][1] + diameter * offset_diameters)
    return stable


def estimate_floor(samples):
    """Floor height in the image from planted feet; perspective makes this approximate.

    Planted heels and toes sit on the floor, so they give the floor line directly. Ankles sit
    above the sole, so the ankle fallback adds an estimated ankle height.
    """
    sole = [f"{side}_{part}" for side in ("left", "right") for part in ("heel", "big_toe", "small_toe")]
    stable = stable_heights(samples, sole, 0.0)
    if len(stable) < 5:
        stable = stable_heights(samples, ("left_ankle", "right_ankle"), 0.18)
    return float(np.percentile(stable, 90)) if len(stable) >= 5 else None


def foot_distance(point, diameter, ankle, knee, config):
    """Distance from the ball to an estimated foot, not just the ankle point.

    COCO ankles sit at the heel/ankle joint; an extended foot reaches further. Without a
    toe landmark the toe direction is unknown, so the foot is a horizontal segment on both
    sides of the ankle, sized from shin length. It only applies when the ball is below the
    knee and not clearly below the ankle, so a thigh-height ball cannot match a foot.
    """
    if not knee:
        return None
    if point[1] < knee[1] or point[1] > ankle[1] + diameter * 0.5:
        return None
    reach = config.foot_length_shin_ratio * float(np.linalg.norm(np.subtract(ankle, knee)))
    return distance_to_segment(point, [ankle[0] - reach, ankle[1]], [ankle[0] + reach, ankle[1]])


def detected_foot_distance(point, pose, side):
    """Distance to the detected foot outline (heel, big toe, small toe), or None if absent."""
    heel, big, small = (pose.get(f"{side}_{name}") for name in ("heel", "big_toe", "small_toe"))
    edges = [(a, b) for a, b in ((heel, big), (heel, small), (big, small)) if a and b]
    return min(distance_to_segment(point, a, b) for a, b in edges) if edges else None


def leg_distances(sample, config):
    """Every available (distance, body part) option for one observed frame."""
    point, diameter, pose = sample["center"], sample["diameter"], sample["pose"]
    options = []
    for side in ("left", "right"):
        ankle, knee, hip = (pose.get(side + "_" + joint) for joint in ("ankle", "knee", "hip"))
        detected = detected_foot_distance(point, pose, side)
        if detected is not None:
            options.append((detected / diameter, side + "_foot"))
        if ankle:
            options.append((float(np.linalg.norm(np.subtract(point, ankle))) / diameter, side + "_foot"))
            # The ankle-based estimate is only a fallback when heel/toe points are missing.
            foot = foot_distance(point, diameter, ankle, knee, config) if detected is None else None
            if foot is not None:
                options.append((foot / diameter, side + "_foot"))
        if knee:
            options.append((float(np.linalg.norm(np.subtract(point, knee))) / diameter, side + "_knee"))
        if knee and hip:
            options.append((distance_to_segment(point, knee, hip) / diameter, side + "_thigh"))
    return options


def classify(sample, floor, config, neighbors=()):
    """Floor check on the contact frame, then leg support over contact ±1 observed frame.

    Each neighbor is compared with its own ball position, because single-frame landmarks
    jitter or vanish on a fast kicking leg. Wrists are deliberately ignored: a nearby
    projected arm does not establish or block a touch in juggling.
    """
    point, diameter = sample["center"], sample["diameter"]
    if floor is None:
        return "review", "floor_unknown", None
    if point[1] + diameter / 2 >= floor - diameter * 0.12:
        return "review", "possible_floor_contact", None
    options = [o for s in (sample, *neighbors) for o in leg_distances(s, config)]
    if not options:
        return "review", "missing_leg_landmarks", None
    nearest = min(options)
    if nearest[0] > config.contact_diameters:
        return "review", "contact_not_supported", None
    # In a front view a ball on a raised foot also overlaps the knee in 2D, so a supporting
    # foot wins the label. A genuine knee/thigh touch leaves the foot hanging well below.
    feet = [o for o in options if o[1].endswith("_foot") and o[0] <= config.contact_diameters]
    return "counted", "observed_reversal_near_leg", (min(feet) if feet else nearest)[1]


def top_clipped(sample, config):
    return sample["box"][1] <= max(2.0, config.edge_margin_diameters * sample["diameter"])


def top_exit_after(samples, position, after, config):
    """True when the only outgoing observation is cut off by the top edge and the ball then
    leaves view (no further observation). Predictions after the exit are not evidence."""
    if len(after) != 1 or not after[0].get("box") or not top_clipped(after[0], config):
        return False
    following = position[after[0]["frame"]] + 1
    return following >= len(samples) or samples[following]["status"] != "observed"


def find_stops(samples, config):
    """Intervals where the observed ball stays nearly still, e.g. a catch or a ball at rest.

    Purely informational: stops never add or remove counted touches.
    """
    stops, run = [], []

    def close(run):
        if run and run[-1]["time"] - run[0]["time"] >= config.stop_seconds:
            stops.append({"start": run[0]["time"], "end": run[-1]["time"],
                          "start_frame": run[0]["frame"], "end_frame": run[-1]["frame"],
                          "reason": "ball_stationary"})

    for s in samples:
        if s["status"] != "observed":
            continue
        if run and (s["segment"] != run[-1]["segment"] or s["time"] - run[-1]["time"] > config.stop_gap_seconds
                    or np.linalg.norm(np.subtract(s["center"], run[0]["center"]))
                    > config.stop_radius_diameters * run[0]["diameter"]):
            close(run)
            # Restart from the latest still-compatible anchor so slow drifts are not merged.
            run = [s]
        else:
            run.append(s)
    close(run)
    return stops


def count_touches(samples, config):
    floor = estimate_floor(samples)
    position = {s["frame"]: i for i, s in enumerate(samples)}
    observed = [s for s in samples if s["status"] == "observed"]
    candidates = []
    for i, sample in enumerate(observed):
        t, y, diameter = sample["time"], sample["center"][1], sample["diameter"]
        before = [s for s in observed[max(0, i - 8):i] if t - s["time"] <= config.velocity_window_seconds + 1e-6
                  and s["segment"] == sample["segment"]]
        after = [s for s in observed[i + 1:i + 9] if s["time"] - t <= config.velocity_window_seconds + 1e-6
                 and s["segment"] == sample["segment"]]
        top_exit = top_exit_after(samples, position, after, config)
        if len(before) < 2 or (len(after) < 2 and not top_exit):
            continue
        # A local bottom of the arc, not the upper flight apex.
        if any(s["center"][1] > y for s in before[-2:] + after[:2]):
            continue
        incoming = np.polyfit([s["time"] - t for s in before] + [0.],
                              [s["center"][1] for s in before] + [y], 1)[0] / diameter
        if top_exit:
            # A top-clipped box shrinks from above, dragging its center down; its bottom edge
            # still follows the ball, so measure the outgoing motion from bottom edges.
            outgoing = (after[0]["box"][3] - sample["box"][3]) / (after[0]["time"] - t) / diameter
        else:
            outgoing = np.polyfit([0.] + [s["time"] - t for s in after],
                                  [y] + [s["center"][1] for s in after], 1)[0] / diameter
        if incoming < config.min_velocity_diameters or outgoing > -config.min_velocity_diameters:
            continue
        neighbors = [s for s in (before[-1:] + after[:1]) if abs(s["frame"] - sample["frame"]) == 1]
        status, reason, body_part = classify(sample, floor, config, neighbors)
        evidence = before + [sample] + after
        # A gap surrounding contact means that the reversal is only approximately located.
        if max(b["time"] - a["time"] for a, b in zip(evidence, evidence[1:])) > 0.075:
            status, reason = "review", "gap_near_contact"
        event = {"id": f"event-{sample['frame']}", "frame": sample["frame"], "time": t,
                 "status": status, "reason": reason, "body_part": body_part,
                 "evidence_sources": sorted({s.get("source", "detector") for s in evidence}),
                 "incoming_diameters_per_second": float(incoming),
                 "outgoing_diameters_per_second": float(outgoing)}
        if top_exit:
            event["evidence"] = ["top_exit"]
        if candidates and t - candidates[-1]["time"] < config.debounce_seconds:
            old = candidates[-1]
            if incoming - outgoing > old["incoming_diameters_per_second"] - old["outgoing_diameters_per_second"]:
                candidates[-1] = event
        else:
            candidates.append(event)
    # A ball resting before the first touch (before the pickup) is not a stop in juggling.
    first_touch = next((e["time"] for e in candidates if e["status"] == "counted"), None)
    stops = [s for s in find_stops(samples, config) if first_touch is not None and s["end"] > first_touch]
    return {"events": candidates, "estimated_count": sum(e["status"] == "counted" for e in candidates),
            "floor_y": floor, "stops": stops}
