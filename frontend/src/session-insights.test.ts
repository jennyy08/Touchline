import { describe, it, expect } from "vitest";
import {
  sessionInsights,
  signaturePoints,
  signaturePath,
  median,
} from "./session-insights";
import type { DribbleResult } from "./dribbling-types";
const result = (trips: unknown[] = [], turns: unknown[] = []) =>
  ({ dribbling: { trips, turns } }) as DribbleResult;
const trip = (direction: string, ratio: number | null, speed = 1) => ({
  direction,
  relative_speed: ratio,
  speed,
  slower: ratio !== null && ratio < 0.75,
});
describe("session story evidence", () => {
  it("does not invent consistency or directional comparisons from sparse data", () => {
    const i = sessionInsights(
      result([trip("left", null), trip("right", null)]),
    );
    expect(i.deviation).toBeNull();
    expect(i.leftSpeed).toBeNull();
    expect(i.rightSpeed).toBeNull();
  });
  it("uses deviations from same-direction medians, not model confidence", () => {
    const i = sessionInsights(
      result([
        trip("left", 0.7),
        trip("left", 1),
        trip("left", 1.2),
        trip("right", null),
      ]),
    );
    expect(i.deviation).toBeCloseTo(20);
    expect(i.comparable).toBe(3);
    expect(i.slow).toHaveLength(1);
    expect(i.rightSpeed).toBeNull();
  });
  it("keeps inferred and near-marker events out of reached totals", () => {
    const i = sessionInsights(
      result(
        [],
        [
          { marker_status: "reached" },
          { marker_status: "near" },
          { marker_status: "not_assessed", evidence: "inferred_edge_return" },
        ],
      ),
    );
    expect(i.assessed).toBe(2);
    expect(i.reached).toBe(1);
    expect(i.inferred).toBe(1);
  });
  it("maps real event order and direction to a schematic without fabricating nodes", () => {
    const points = signaturePoints(
      [
        { time: 1, side: "left" },
        { time: 3, side: "right", evidence: "inferred_edge_return" },
      ] as never,
      4,
    );
    expect(points).toHaveLength(2);
    expect(points[0].x).toBeLessThan(points[1].x);
    expect(points[0].y).toBeLessThan(points[1].y);
    expect(points[1].inferred).toBe(true);
    expect(signaturePath(points)).toContain("M 270 0");
    expect(signaturePath([])).not.toContain("NaN");
  });
  it("calculates a true median for odd and even series", () => {
    expect(median([])).toBeNull();
    expect(median([3, 1, 2])).toBe(2);
    expect(median([1, 3])).toBe(2);
  });
});
