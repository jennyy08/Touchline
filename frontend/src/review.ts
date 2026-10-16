import {
  labels,
  type Review,
  type Result,
  type Stop,
  type Touch,
} from "./types";

/** A touch supported only by sound (ball out of view), not by a visible contact. */
export const isHeard = (touch: Touch) =>
  touch.reason === "heard_ball_out_of_view";

/** Seen/heard split; older results have no audio fields, so everything counted was seen. */
export function countSplit(data: Pick<Result, "events">) {
  const counted = data.events.filter((e) => e.status === "counted");
  const heard = counted.filter(isHeard).length;
  return { seen: counted.length - heard, heard };
}

/** Results saved before stop detection have no `stops` field; treat as none. */
export const stopsOf = (data: Pick<Result, "stops">): Stop[] =>
  Array.isArray(data.stops) ? data.stops : [];
export function seedReview(result: Result): Review {
  return {
    schema_version: 1,
    video_sha256: result.video.sha256,
    events: result.events.map((e) => ({
      id: e.id,
      time: e.time,
      label: e.status === "counted" ? "touch" : "uncertain",
      note: e.reason.replaceAll("_", " "),
    })),
  };
}
export function parseReview(text: string, result: Result): Review {
  const value = JSON.parse(text);
  if (
    value.schema_version !== 1 ||
    value.video_sha256 !== result.video.sha256 ||
    !Array.isArray(value.events)
  )
    throw new Error(
      "Review must use schema version 1 and belong to this exact video.",
    );
  const ids = new Set<string>();
  for (const e of value.events) {
    if (
      typeof e.id !== "string" ||
      ids.has(e.id) ||
      typeof e.time !== "number" ||
      !Number.isFinite(e.time) ||
      e.time < 0 ||
      e.time > result.video.duration ||
      !labels.includes(e.label) ||
      typeof e.note !== "string"
    )
      throw new Error(
        "Review contains invalid timestamps, duplicate IDs, labels, or notes.",
      );
    ids.add(e.id);
  }
  if (value.uncertain_intervals !== undefined) {
    if (
      !Array.isArray(value.uncertain_intervals) ||
      value.uncertain_intervals.some(
        (i: { start: number; end: number; note: string }) =>
          !Number.isFinite(i.start) ||
          !Number.isFinite(i.end) ||
          i.start < 0 ||
          i.end < i.start ||
          i.end > result.video.duration ||
          typeof i.note !== "string",
      )
    )
      throw new Error("Invalid uncertainty intervals.");
  }
  return value as Review;
}
