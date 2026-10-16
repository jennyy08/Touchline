import { describe, it, expect } from "vitest";
import { parseReview, seedReview } from "./review";
import { sampleIndex } from "./player";
import type { Result } from "./types";
const result = {
  video: { sha256: "abc", duration: 1 },
  events: [
    {
      id: "a",
      time: 0.5,
      status: "counted",
      reason: "observed_reversal_near_leg",
    },
  ],
  samples: [{ time: 0 }, { time: 0.03 }, { time: 0.09 }],
} as Result;
describe("manual review", () => {
  it("roundtrips without changing automatic events", () => {
    const review = seedReview(result);
    review.events[0].label = "floor";
    expect(parseReview(JSON.stringify(review), result).events[0].label).toBe(
      "floor",
    );
    expect(result.events[0].status).toBe("counted");
  });
  it("rejects another video and out-of-range or invalid events", () => {
    const review = seedReview(result);
    review.video_sha256 = "wrong";
    expect(() => parseReview(JSON.stringify(review), result)).toThrow();
    review.video_sha256 = "abc";
    review.events[0].time = 2;
    expect(() => parseReview(JSON.stringify(review), result)).toThrow();
    review.events[0].time = 0.5;
    review.events.push({ ...review.events[0] });
    expect(() => parseReview(JSON.stringify(review), result)).toThrow();
  });
  it("selects the presentation frame, not nominal FPS", () => {
    expect(sampleIndex(result, 0.08)).toBe(1);
    expect(sampleIndex(result, 0.09)).toBe(2);
  });
});
