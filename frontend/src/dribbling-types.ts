import type { Result } from "./types";
export interface Setup {
  roi: number[];
  markers: number[] | null;
  require_markers: boolean;
}
export interface Turn {
  id: string;
  time: number;
  side: string;
  marker_status: string;
  evidence?: "visible_reversal" | "inferred_edge_return";
  time_interval?: { start: number; end: number };
}
export interface Trip {
  id: string;
  start: number;
  end: number;
  direction: string;
  duration: number;
  speed: number;
  relative_speed: number | null;
  slower: boolean;
}
export interface DribbleResult extends Result {
  drill: "side_to_side";
  dribbling: {
    setup: Setup;
    turns: Turn[];
    trips: Trip[];
    trip_basis: string;
    pace_gates: number[] | null;
    review_windows?: {
      start: number;
      end: number;
      side: string;
      reason: string;
    }[];
    notes: string[];
  };
}
