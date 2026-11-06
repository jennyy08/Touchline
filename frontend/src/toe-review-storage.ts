import { parseReview } from "./review";
import type { Result, Review } from "./types";

const key = (sha256: string) => `touchline:toe-taps:review:${sha256}`;

/** Reviews are keyed by the original video, so re-uploading it restores edits. */
export function loadToeReview(
  result: Result,
  storage: Pick<Storage, "getItem"> = localStorage,
): Review | null {
  const saved = storage.getItem(key(result.video.sha256));
  return saved ? parseReview(saved, result) : null;
}

export function saveToeReview(
  review: Review,
  storage: Pick<Storage, "setItem"> = localStorage,
): void {
  storage.setItem(key(review.video_sha256), JSON.stringify(review));
}
