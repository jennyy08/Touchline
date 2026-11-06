import { drills } from "./drill-catalog";

export type SessionMinutes = 5 | 10 | 15;
export type SessionFocus = "mix" | "juggling" | "side-to-side" | "toe-taps";
export type SessionStage =
  | { kind: "practice"; drillId: string; seconds: number }
  | { kind: "rest"; seconds: number };
export interface CompletedSession {
  id: string;
  completedAt: string;
  plannedMinutes: SessionMinutes;
  focus: SessionFocus;
  practiceSeconds: number;
  completedDrills: string[];
}
const ids = drills.map((d) => d.id);
const STORAGE_KEY = "touchline:practice-sessions:v1";

/** Timed guidance, not a technique assessment or an adaptive recommendation. */
export function planSession(
  minutes: SessionMinutes,
  focus: SessionFocus,
): SessionStage[] {
  const total = minutes * 60;
  const count = minutes === 5 ? 2 : 3;
  const selected =
    focus === "mix"
      ? ids.slice(0, count)
      : [focus, ...ids.filter((id) => id !== focus)].slice(0, count);
  const rest = 30;
  const practiceTotal = total - rest * (count - 1);
  const base = Math.floor(practiceTotal / count);
  const stages: SessionStage[] = [];
  for (let i = 0; i < count; i++) {
    stages.push({
      kind: "practice",
      drillId: selected[i],
      seconds: base + (i === count - 1 ? practiceTotal - base * count : 0),
    });
    if (i < count - 1) stages.push({ kind: "rest", seconds: rest });
  }
  return stages;
}

function isCompletedSession(value: unknown): value is CompletedSession {
  if (!value || typeof value !== "object") return false;
  const s = value as Partial<CompletedSession>;
  return (
    typeof s.id === "string" &&
    s.id.length > 0 &&
    typeof s.completedAt === "string" &&
    !Number.isNaN(Date.parse(s.completedAt)) &&
    [5, 10, 15].includes(s.plannedMinutes as number) &&
    ["mix", ...ids].includes(s.focus as string) &&
    typeof s.practiceSeconds === "number" &&
    Number.isFinite(s.practiceSeconds) &&
    s.practiceSeconds >= 0 &&
    s.practiceSeconds <= 15 * 60 &&
    Array.isArray(s.completedDrills) &&
    s.completedDrills.every((id) => ids.includes(id))
  );
}
export function readHistory(
  storage: Pick<Storage, "getItem"> = localStorage,
): CompletedSession[] {
  try {
    const parsed: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed)
      ? parsed.filter(isCompletedSession).slice(-200)
      : [];
  } catch {
    return [];
  }
}
export function saveSession(
  session: CompletedSession,
  storage: Pick<Storage, "getItem" | "setItem"> = localStorage,
): boolean {
  if (!isCompletedSession(session)) return false;
  try {
    const history = readHistory(storage);
    history.push(session);
    storage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-200)));
    return true;
  } catch {
    return false;
  }
}
export function clearHistory(
  storage: Pick<Storage, "removeItem"> = localStorage,
): boolean {
  try {
    storage.removeItem(STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
export function practiceSummary(history: CompletedSession[]) {
  return {
    sessions: history.length,
    seconds: Math.round(history.reduce((n, s) => n + s.practiceSeconds, 0)),
    minutes: Math.round(
      history.reduce((n, s) => n + s.practiceSeconds, 0) / 60,
    ),
    lastCompleted: history.length
      ? history[history.length - 1].completedAt
      : null,
  };
}
