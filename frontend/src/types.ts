export type Point = [number, number];
export interface Sample {
  frame: number;
  time: number;
  status: "observed" | "predicted" | "lost";
  source?: "detector" | "appearance" | null;
  box: number[] | null;
  center: Point | null;
  diameter: number | null;
  segment: number;
  pose: Record<string, Point>;
}
export interface Touch {
  id: string;
  frame: number;
  time: number;
  status: "counted" | "review";
  reason: string;
  body_part: string | null;
}
export interface Result {
  schema_version: 1;
  video: {
    sha256: string;
    width: number;
    height: number;
    frames: number;
    duration: number;
    nominal_fps: number;
  };
  estimated_count: number;
  events: Touch[];
  samples: Sample[];
  tracking_gaps: { start: number; end: number }[];
  tracking_summary: Record<string, number>;
  runtime_seconds: number;
  warnings: string[];
  floor_y: number | null;
}
export const labels = [
  "touch",
  "floor",
  "pickup",
  "hand",
  "uncertain",
] as const;
export type Label = (typeof labels)[number];
export interface ReviewEvent {
  id: string;
  time: number;
  label: Label;
  note: string;
}
export interface Review {
  schema_version: 1;
  video_sha256: string;
  events: ReviewEvent[];
  uncertain_intervals?: { start: number; end: number; note: string }[];
}
