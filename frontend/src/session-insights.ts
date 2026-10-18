import type { DribbleResult } from "./dribbling-types";
export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b),
    mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
export function sessionInsights(result: DribbleResult) {
  const { turns, trips } = result.dribbling;
  const ratios = trips
    .map((t) => t.relative_speed)
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const deviation =
    ratios.length >= 3
      ? median(ratios.map((v) => Math.abs(v - 1) * 100))
      : null;
  const left = trips.filter((t) => t.direction === "left"),
    right = trips.filter((t) => t.direction === "right");
  const leftSpeed = left.length >= 3 ? median(left.map((t) => t.speed)) : null;
  const rightSpeed =
    right.length >= 3 ? median(right.map((t) => t.speed)) : null;
  const slow = trips.filter((t) => t.slower);
  const assessed = turns.filter((t) => t.marker_status !== "not_assessed");
  const reached = assessed.filter((t) => t.marker_status === "reached").length;
  const inferred = turns.filter(
    (t) => t.evidence === "inferred_edge_return",
  ).length;
  return {
    deviation,
    comparable: ratios.length,
    leftSpeed,
    rightSpeed,
    slow,
    assessed: assessed.length,
    reached,
    inferred,
  };
}
export function signaturePoints(
  turns: DribbleResult["dribbling"]["turns"],
  duration: number,
) {
  return turns.map((t) => ({
    x: t.side === "left" ? 90 : 450,
    y: 80 + Math.min(1, Math.max(0, t.time / Math.max(duration, 0.01))) * 1800,
    inferred: t.evidence === "inferred_edge_return",
  }));
}
export function signaturePath(points: { x: number; y: number }[]) {
  let d = "M 270 0",
    previous = { x: 270, y: 0 };
  for (const point of points) {
    const middle = (previous.y + point.y) / 2;
    d += ` C ${previous.x} ${middle}, ${point.x} ${middle}, ${point.x} ${point.y}`;
    previous = point;
  }
  return d + ` C ${previous.x} 1960, 40 1940, 40 2000`;
}
