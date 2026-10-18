import template from "./session-story.html?raw";
import type { DribbleResult, Turn } from "./dribbling-types";
import {
  sessionInsights,
  signaturePath,
  signaturePoints,
} from "./session-insights";
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const set = (id: string, value: string) => {
  $(id).textContent = value;
};
const ns = "http://www.w3.org/2000/svg";
type Saved = {
  hash: string;
  setup: string;
  deviation: number | null;
  turns: Turn[];
  duration: number;
};

/** Presentation controller. Reads analysis; never changes its events or measurements. */
export class SessionStory {
  private result: DribbleResult | null = null;
  private frame = 0;
  private readonly reduced = matchMedia("(prefers-reduced-motion: reduce)");
  constructor(
    private video: HTMLVideoElement,
    private seek: (time: number) => void,
  ) {
    $("story-mount").innerHTML = template;
    const schedule = () => {
      if (!this.frame)
        this.frame = requestAnimationFrame(() => {
          this.frame = 0;
          this.paintScroll();
        });
    };
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    this.reduced.addEventListener("change", schedule);
    document.querySelectorAll<HTMLAnchorElement>(".story-link").forEach(
      (link) =>
        (link.onclick = (e) => {
          e.preventDefault();
          document.querySelector(link.hash)?.scrollIntoView({
            behavior: this.reduced.matches ? "auto" : "smooth",
          });
        }),
    );
    $("focus-mode").onclick = () =>
      this.focus(!$("video-workspace").classList.contains("focused"));
    addEventListener("keydown", (e) => {
      if (
        e.key === "Escape" &&
        $("video-workspace").classList.contains("focused")
      )
        this.focus(false);
    });
    $("practice-again").onclick = () => $("new-upload").click();
    $("play-pause").onclick = () => {
      if (video.paused)
        video
          .play()
          .catch(() =>
            set("friendly-status", "Press play to start the replay."),
          );
      else video.pause();
    };
    const playState = () => {
      set("play-pause", video.paused ? "Play" : "Pause");
      $("play-pause").setAttribute(
        "aria-label",
        video.paused ? "Play video" : "Pause video",
      );
    };
    video.addEventListener("play", playState);
    video.addEventListener("pause", playState);
    video.addEventListener("timeupdate", () => this.playback());
    video.addEventListener("seeked", () => this.playback());
    $<HTMLInputElement>("replay-scrub").oninput = () =>
      this.seek(Number($<HTMLInputElement>("replay-scrub").value));
    video.controls = false;
  }
  private focus(enabled: boolean) {
    $("video-workspace").classList.toggle("focused", enabled);
    $("focus-mode").setAttribute("aria-pressed", String(enabled));
    set("focus-mode", enabled ? "Exit focus" : "Focus mode");
    // Keep keyboard navigation inside the expanded replay until it is closed.
    document
      .querySelectorAll<HTMLElement>(
        ".app-header, #story-mount, .progress-close, main > footer",
      )
      .forEach((element) => {
        element.inert = enabled;
      });
    if (enabled)
      $("video-workspace").scrollIntoView({ block: "start", behavior: "auto" });
    $("focus-mode").focus();
  }
  load(result: DribbleResult) {
    this.result = result;
    const d = result.dribbling,
      i = sessionInsights(result);
    set(
      "hero-turns",
      d.turns.length ? `${d.turns.length} turns.` : "You showed up.",
    );
    set("hero-duration", `${Math.round(result.video.duration)} sec`);
    set("hero-split", `${d.turns.length - i.inferred} / ${i.inferred}`);
    set(
      "rhythm-copy",
      i.deviation === null
        ? "A few more clearly visible sections will help us compare your pace. For now, use the replay to notice how each change of direction feels."
        : i.slow.length
          ? "Your pace varied in a few places. Take a closer look at the slower sections and decide whether the change was intentional."
          : "Your measured sections stayed above the pace-dip threshold. Watch them back and see which movements felt most repeatable.",
    );
    set(
      "rhythm-number",
      i.deviation === null
        ? "Still taking shape"
        : `${Math.round(i.deviation)}%`,
    );
    set(
      "rhythm-caption",
      i.deviation === null
        ? "Not enough comparable sections yet"
        : `typical difference from your median pace · ${i.comparable} measured sections`,
    );
    $("rhythm-bars").replaceChildren();
    d.trips.forEach((trip, index) => {
      const bar = document.createElement("button");
      bar.style.height = `${Math.max(12, Math.min(100, (trip.relative_speed ?? 1) * 60))}%`;
      bar.className = trip.slower ? "pace-dip" : "";
      bar.setAttribute(
        "aria-label",
        `Replay section ${index + 1}, ${trip.start.toFixed(1)} seconds`,
      );
      bar.title = `Section ${index + 1} · ${trip.relative_speed === null ? "pace comparison unavailable" : Math.round(trip.relative_speed * 100) + "% of typical pace"}`;
      bar.onclick = () => {
        $("video-workspace").scrollIntoView({
          behavior: this.reduced.matches ? "auto" : "smooth",
        });
        this.seek(trip.start);
      };
      $("rhythm-bars").append(bar);
    });
    const both = i.leftSpeed !== null && i.rightSpeed !== null;
    set(
      "balance-copy",
      both
        ? "Here’s how your typical sideways ball speed compares in each direction. Different doesn’t automatically mean worse."
        : "We need at least three measured sections in each direction for a useful comparison. Your missing side stays unscored.",
    );
    const largest = Math.max(i.leftSpeed ?? 0, i.rightSpeed ?? 0, 0.001);
    for (const side of ["left", "right"] as const) {
      const value = side === "left" ? i.leftSpeed : i.rightSpeed;
      set(
        `balance-${side}-value`,
        value === null ? "Not enough data" : `${value.toFixed(2)} widths/s`,
      );
      $(`balance-${side}`).style.width =
        value === null ? "0%" : `${(value / largest) * 70}%`;
    }
    const points = signaturePoints(d.turns, result.video.duration),
      path = signaturePath(points);
    document.getElementById("signature-base")!.setAttribute("d", path);
    document.getElementById("signature-progress")!.setAttribute("d", path);
    const nodes = document.getElementById("signature-nodes")!;
    nodes.replaceChildren();
    points.forEach((point, index) => {
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("cx", String(point.x));
      circle.setAttribute("cy", String(point.y));
      circle.setAttribute("r", "7");
      circle.setAttribute("class", point.inferred ? "inferred" : "");
      nodes.append(circle);
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", String(point.x + (point.x < 270 ? 20 : -40)));
      label.setAttribute("y", String(point.y + 5));
      label.textContent = String(index + 1).padStart(2, "0");
      nodes.append(label);
    });
    set(
      "growth-total",
      `${d.turns.length} estimated turns. A reference for next time.`,
    );
    set(
      "coach-message",
      i.slow.length
        ? `You’ve put in the practice. ${i.slow.length === 1 ? "One measured section moved" : `${i.slow.length} measured sections moved`} more slowly than your usual pace in that direction. Replay ${i.slow[0].start.toFixed(1)}–${i.slow[0].end.toFixed(1)} seconds: was it a deliberate pause, or a moment you’d like to make smoother?`
        : "You’ve made time for practice. Pick one turn that felt comfortable, replay it, and try to carry that same feeling into your next attempt.",
    );
    set(
      "went-well",
      i.reached
        ? `The ball visibly reached a marker on ${i.reached} of ${i.assessed} assessed turns. The remaining turns need their own review.`
        : d.turns.length
          ? `You completed a session with ${d.turns.length} estimated changes of direction. That gives you specific moments to learn from.`
          : "You recorded your practice. Even without a reliable turn count, the replay is useful for noticing what felt comfortable.",
    );
    this.compare({
      hash: result.video.sha256,
      setup: JSON.stringify({ setup: d.setup, basis: d.trip_basis }),
      deviation: i.deviation,
      turns: d.turns,
      duration: result.video.duration,
    });
    $<HTMLInputElement>("replay-scrub").max = String(result.video.duration);
    requestAnimationFrame(() => this.paintScroll());
  }
  private compare(current: Saved) {
    set("growth-title", "Your starting line.");
    set(
      "growth-copy",
      "A little more awareness today. Something specific to work on next time.",
    );
    set(
      "comparison-copy",
      "No earlier comparable session is saved in this browser yet. This is your baseline, not a progress score.",
    );
    document.getElementById("signature-previous")!.removeAttribute("d");
    try {
      const raw = JSON.parse(
        localStorage.getItem("touchline:story-sessions") ?? "[]",
      );
      const saved: Saved[] = Array.isArray(raw)
        ? raw.filter(
            (v: Saved) =>
              v &&
              typeof v.hash === "string" &&
              typeof v.setup === "string" &&
              Array.isArray(v.turns) &&
              typeof v.duration === "number" &&
              (v.deviation === null || Number.isFinite(v.deviation)),
          )
        : [];
      const previous = saved.find(
        (s) => s.hash !== current.hash && s.setup === current.setup,
      );
      if (previous) {
        set("growth-title", "Another session in your story.");
        const change = current.turns.length - previous.turns.length;
        let comparison = `${change === 0 ? "The same number of" : `${Math.abs(change)} ${change > 0 ? "more" : "fewer"}`} estimated turns than your last comparable session. Clip length affects this total.`;
        if (current.deviation !== null && previous.deviation !== null) {
          const difference = previous.deviation - current.deviation;
          comparison += ` Typical pace variation is ${Math.abs(difference).toFixed(1)} percentage points ${difference >= 0 ? "lower" : "higher"}.`;
        }
        set("comparison-copy", comparison);
        document
          .getElementById("signature-previous")!
          .setAttribute(
            "d",
            signaturePath(signaturePoints(previous.turns, previous.duration)),
          );
        set(
          "growth-copy",
          "Your earlier signature appears in muted green. Both paths are normalized to session length; they aren’t physical routes.",
        );
      }
      localStorage.setItem(
        "touchline:story-sessions",
        JSON.stringify(
          [current, ...saved.filter((s) => s.hash !== current.hash)].slice(
            0,
            12,
          ),
        ),
      );
    } catch {
      set(
        "comparison-copy",
        "Session history is unavailable in this browser. Your current analysis and replay still work.",
      );
    }
  }
  selectAt(time: number) {
    if (!this.result) return;
    const turn = this.result.dribbling.turns.find(
      (t) => Math.abs(t.time - time) < 0.02,
    );
    if (turn) this.detail(turn);
  }
  private detail(turn: Turn) {
    const interval = turn.time_interval;
    set(
      "turn-detail-title",
      `${turn.side === "left" ? "Left" : "Right"} turn · ${interval ? `${interval.start.toFixed(1)}–${interval.end.toFixed(1)}s` : `${turn.time.toFixed(1)}s`}`,
    );
    set(
      "turn-detail-copy",
      interval
        ? "The ball left this edge and came back inward. This counts as a turn; the exact moment happened out of view."
        : turn.marker_status === "reached"
          ? "The ball visibly reached your marker here. Replay the approach and the change of direction."
          : turn.marker_status === "near"
            ? "The ball turned close to your marker. Check the replay before judging how far it reached."
            : turn.marker_status === "short"
              ? "The ball appeared to turn before reaching the marker. If reaching it was your goal, give yourself a little more room next time."
              : "A visible change of direction. Marker reach wasn’t assessed for this turn.",
    );
  }
  private playback() {
    if (!this.result) return;
    const time = this.video.currentTime;
    $<HTMLInputElement>("replay-scrub").value = String(time);
    set(
      "playback-time",
      `${Math.floor(time / 60)}:${String(Math.floor(time % 60)).padStart(2, "0")}`,
    );
    const turns = this.result.dribbling.turns;
    const active = [...turns].reverse().find((t) => t.time <= time);
    document
      .querySelectorAll<HTMLElement>("#turn-timeline button")
      .forEach((el) =>
        el.setAttribute(
          "aria-pressed",
          String(el.dataset.turnId === active?.id),
        ),
      );
    if (active) this.detail(active);
    const samples = this.result.samples;
    let lo = 0,
      hi = samples.length - 1;
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2);
      if (samples[mid].time <= time) lo = mid;
      else hi = mid - 1;
    }
    set(
      "friendly-status",
      samples[lo]?.status === "observed"
        ? "Ball in view"
        : "We briefly lost sight of the ball.",
    );
  }
  private paintScroll() {
    if (!this.result || $("results").hidden) return;
    const host = $("session-narrative"),
      rect = host.getBoundingClientRect();
    const progress = Math.max(
      0,
      Math.min(1, (innerHeight * 0.6 - rect.top) / rect.height),
    );
    const path = document.getElementById(
      "signature-progress",
    ) as unknown as SVGPathElement;
    const length = path.getTotalLength();
    path.style.strokeDasharray = String(length);
    path.style.strokeDashoffset = String(
      this.reduced.matches ? 0 : length * (1 - progress),
    );
    const point = path.getPointAtLength(length * progress);
    const dot = document.getElementById("signature-point")!;
    dot.setAttribute("cx", String(point.x));
    dot.setAttribute("cy", String(point.y));
    dot.setAttribute("visibility", this.reduced.matches ? "hidden" : "visible");
    $("video-workspace").style.setProperty(
      "--arrival",
      String(
        Math.max(
          0,
          Math.min(
            1,
            (innerHeight - $("video-workspace").getBoundingClientRect().top) /
              innerHeight,
          ),
        ),
      ),
    );
  }
}
