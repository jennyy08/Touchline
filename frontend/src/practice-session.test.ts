import { describe, expect, it } from "vitest";
import {
  planSession,
  practiceSummary,
  readHistory,
  saveSession,
} from "./practice-session";

function memoryStorage() {
  let value: string | null = null;
  return {
    getItem: () => value,
    setItem: (_key: string, next: string) => {
      value = next;
    },
    removeItem: () => {
      value = null;
    },
  };
}
describe("guided session plan", () => {
  it("fills each selected length exactly, including rests", () => {
    for (const minutes of [5, 10, 15] as const) {
      const stages = planSession(minutes, "mix");
      expect(stages.reduce((n, s) => n + s.seconds, 0)).toBe(minutes * 60);
      expect(stages[0].kind).toBe("practice");
      expect(stages.at(-1)?.kind).toBe("practice");
      expect(stages.filter((s) => s.kind === "rest")).toHaveLength(
        minutes === 5 ? 1 : 2,
      );
    }
  });
  it("puts the chosen focus first while keeping unique drills", () => {
    const plan = planSession(10, "toe-taps").filter(
      (s) => s.kind === "practice",
    );
    expect(plan[0]).toMatchObject({ drillId: "toe-taps" });
    expect(new Set(plan.map((s) => s.drillId)).size).toBe(3);
  });
});
describe("local practice history", () => {
  const entry = {
    id: "a",
    completedAt: "2026-11-04T12:00:00.000Z",
    plannedMinutes: 5 as const,
    focus: "mix" as const,
    practiceSeconds: 270,
    completedDrills: ["juggling", "side-to-side"],
  };
  it("saves only validated completed sessions and aggregates practiced time", () => {
    const storage = memoryStorage();
    expect(saveSession(entry, storage)).toBe(true);
    expect(
      saveSession({ ...entry, id: "b", practiceSeconds: -1 }, storage),
    ).toBe(false);
    expect(readHistory(storage)).toEqual([entry]);
    expect(practiceSummary(readHistory(storage))).toMatchObject({
      sessions: 1,
      minutes: 5,
    });
  });
  it("handles corrupt saved data and blocked storage without inventing progress", () => {
    const storage = memoryStorage();
    storage.setItem("", "not json");
    expect(readHistory(storage)).toEqual([]);
    expect(
      saveSession(entry, {
        getItem: storage.getItem,
        setItem: () => {
          throw Error("quota");
        },
      }),
    ).toBe(false);
  });
});
