"""Explainable contact candidates from observed motion, never a black-box count."""
import numpy as np


def distance_to_segment(point, a, b):
    p, a, b = map(lambda v: np.asarray(v, dtype=float), (point, a, b))
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
    return float(np.linalg.norm(p - (a + t * ab)))


def estimate_floor(samples):
    """Use ankles that stay nearly stationary; perspective makes this approximate."""
    stable = []
    for a, b in zip(samples, samples[1:]):
        dt = b["time"] - a["time"]
        for side in ("left", "right"):
            key = side + "_ankle"
            if key in a["pose"] and key in b["pose"] and b["diameter"]:
                diameter = b["diameter"]
                if np.linalg.norm(np.array(b["pose"][key]) - a["pose"][key]) < diameter * dt * 0.8:
                    stable.append(b["pose"][key][1] + diameter * 0.18)
    return float(np.percentile(stable, 90)) if len(stable) >= 5 else None


def classify(sample, floor, config):
    point, diameter, pose = sample["center"], sample["diameter"], sample["pose"]
    if floor is None:
        return "review", "floor_unknown", None
    if point[1] + diameter / 2 >= floor - diameter * 0.12:
        return "review", "possible_floor_contact", None
    for side in ("left", "right"):
        wrist = pose.get(side + "_wrist")
        if wrist and np.linalg.norm(np.array(point) - wrist) < diameter * 0.65:
            return "review", "possible_hand_contact", None
    nearest = None
    for side in ("left", "right"):
        ankle, knee, hip = (pose.get(side + "_" + joint) for joint in ("ankle", "knee", "hip"))
        options = []
        if ankle:
            options.append((float(np.linalg.norm(np.array(point) - ankle)), side + "_foot"))
        if knee:
            options.append((float(np.linalg.norm(np.array(point) - knee)), side + "_knee"))
        if knee and hip:
            options.append((distance_to_segment(point, knee, hip), side + "_thigh"))
        for option in options:
            if nearest is None or option[0] < nearest[0]:
                nearest = option
    if nearest is None:
        return "review", "missing_leg_landmarks", None
    if nearest[0] > diameter * config.contact_diameters:
        return "review", "contact_not_supported", None
    return "counted", "observed_reversal_near_leg", nearest[1]


def count_touches(samples, config):
    floor = estimate_floor(samples)
    observed = [s for s in samples if s["status"] == "observed"]
    candidates = []
    for i, sample in enumerate(observed):
        t, y, diameter = sample["time"], sample["center"][1], sample["diameter"]
        before = [s for s in observed[max(0, i - 8):i] if t - s["time"] <= config.velocity_window_seconds + 1e-6
                  and s["segment"] == sample["segment"]]
        after = [s for s in observed[i + 1:i + 9] if s["time"] - t <= config.velocity_window_seconds + 1e-6
                 and s["segment"] == sample["segment"]]
        if len(before) < 2 or len(after) < 2:
            continue
        # A local bottom of the arc, not the upper flight apex.
        if any(s["center"][1] > y for s in before[-2:] + after[:2]):
            continue
        incoming = np.polyfit([s["time"] - t for s in before] + [0.],
                              [s["center"][1] for s in before] + [y], 1)[0] / diameter
        outgoing = np.polyfit([0.] + [s["time"] - t for s in after],
                              [y] + [s["center"][1] for s in after], 1)[0] / diameter
        if incoming < config.min_velocity_diameters or outgoing > -config.min_velocity_diameters:
            continue
        status, reason, body_part = classify(sample, floor, config)
        evidence = before + [sample] + after
        # A gap surrounding contact means that the reversal is only approximately located.
        if max(b["time"] - a["time"] for a, b in zip(evidence, evidence[1:])) > 0.075:
            status, reason = "review", "gap_near_contact"
        event = {"id": f"event-{sample['frame']}", "frame": sample["frame"], "time": t,
                 "status": status, "reason": reason, "body_part": body_part,
                 "evidence_sources": sorted({s.get("source", "detector") for s in evidence}),
                 "incoming_diameters_per_second": float(incoming),
                 "outgoing_diameters_per_second": float(outgoing)}
        if candidates and t - candidates[-1]["time"] < config.debounce_seconds:
            old = candidates[-1]
            if incoming - outgoing > old["incoming_diameters_per_second"] - old["outgoing_diameters_per_second"]:
                candidates[-1] = event
        else:
            candidates.append(event)
    return {"events": candidates, "estimated_count": sum(e["status"] == "counted" for e in candidates),
            "floor_y": floor}
