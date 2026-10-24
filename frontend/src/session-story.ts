import template from "./session-story.html?raw";
import type { DribbleResult, Turn } from "./dribbling-types";
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const set = (id: string, value: string) => {
  $(id).textContent = value;
};
/** Presentation controller. Reads analysis; never changes its events or measurements. */
export class SessionStory {
  private result: DribbleResult | null = null;
  private frame = 0;
  private progress = 0.12;
  private lastPaint = 0;
  private readonly reduced = matchMedia("(prefers-reduced-motion: reduce)");
  constructor(
    private video: HTMLVideoElement,
    private seek: (time: number) => void,
  ) {
    $("story-mount").innerHTML = template;
    const schedule = () => {
      if (!this.frame)
        this.frame = requestAnimationFrame((time) => this.paintScroll(time));
    };
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    this.reduced.addEventListener("change", schedule);
    schedule();
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
        ".app-header, #story-mount, .practice-close, main > footer",
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
    $("story-mount").hidden = true;
    $<HTMLInputElement>("replay-scrub").max = String(result.video.duration);
    $("video-workspace").style.setProperty("--arrival", "1");
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
  /** Ease toward scroll position; stop scheduling frames once settled or off screen. */
  private paintScroll(time: number) {
    this.frame = 0;
    const host = $("story-mount");
    const rect = host.getBoundingClientRect();
    if (host.hidden || rect.bottom < 0 || rect.top > innerHeight) {
      this.lastPaint = 0;
      return;
    }
    // Map the visible scroll position to the shared two-section route.
    const routeTop = rect.top + scrollY;
    const available = Math.max(
      1,
      document.documentElement.scrollHeight - innerHeight,
    );
    const finishAt = Math.min(
      available,
      routeTop + rect.height - innerHeight * 0.65,
    );
    const target = Math.max(
      0.12,
      Math.min(1, 0.12 + (scrollY / Math.max(1, finishAt)) * 0.88),
    );
    const elapsed = this.lastPaint ? Math.min(64, time - this.lastPaint) : 16;
    this.lastPaint = time;
    this.progress += (target - this.progress) * (1 - Math.exp(-elapsed / 120));
    if (Math.abs(target - this.progress) < 0.0001) this.progress = target;
    const path = document.getElementById(
      "signature-progress",
    ) as unknown as SVGPathElement;
    const length = path.getTotalLength();
    path.style.strokeDasharray = String(length);
    path.style.strokeDashoffset = String(
      this.reduced.matches ? 0 : length * (1 - this.progress),
    );
    const point = path.getPointAtLength(length * this.progress);
    const dot = document.getElementById("signature-point")!;
    dot.setAttribute("cx", String(point.x));
    dot.setAttribute("cy", String(point.y));
    dot.setAttribute("visibility", this.reduced.matches ? "hidden" : "visible");
    if (!this.reduced.matches && Math.abs(target - this.progress) > 0.0001)
      this.frame = requestAnimationFrame((next) => this.paintScroll(next));
    else this.lastPaint = 0;
  }
}
