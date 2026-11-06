import { describe, expect, it } from "vitest";
import { seedReview } from "./review";
import { loadToeReview, saveToeReview } from "./toe-review-storage";
import type { Result } from "./types";

const result = {
  video: { sha256: "clip-a", duration: 3 },
  events: [{ id: "tap", time: 1, status: "counted", reason: "observed" }],
} as Result;

describe("toe-tap review storage", () => {
  it("restores edits only for the same original video", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => { values.set(key, value); },
    };
    const review = seedReview(result);
    review.events[0].time = 1.25;
    saveToeReview(review, storage);
    expect(loadToeReview(result, storage)).toEqual(review);
    expect(loadToeReview({ ...result, video: { ...result.video, sha256: "clip-b" } }, storage)).toBeNull();
  });

  it("rejects a corrupted saved review instead of displaying it as a correction", () => {
    expect(() => loadToeReview(result, { getItem: () => "not JSON" })).toThrow();
  });
});
