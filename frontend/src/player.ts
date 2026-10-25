import { VideoRecovery } from "./video-recovery";
import type { Point, Result, Sample } from "./types";
export function sampleIndex(result: Result, time: number): number {
  let lo = 0,
    hi = result.samples.length - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (result.samples[mid].time <= time + 0.0001) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}
export function observationLabel(sample: Sample): string {
  if (sample.status === "lost") return "Tracking lost";
  if (sample.status === "predicted") return "Predicted · not evidence";
  return sample.source === "appearance"
    ? "Ball matched by appearance"
    : "Ball detected";
}

export class AnnotatedPlayer {
  result: Result | null = null;
  enabled = true;
  private presentedTime = 0;
  private recovery: VideoRecovery;
  private hasFrameCallbacks = false;
  constructor(
    public video: HTMLVideoElement,
    private canvas: HTMLCanvasElement,
    private status: HTMLElement,
  ) {
    this.recovery = new VideoRecovery(video);
    document.addEventListener("visibilitychange", () =>
      this.recovery.visibility(document.hidden));
    window.addEventListener("pageshow", (event) => {
      if (event.persisted) this.recovery.refresh();
    });
    video.addEventListener("seeked", () => { this.presentedTime = video.currentTime; });
    // Use the timestamp of the displayed frame, not the advancing audio clock.
    this.hasFrameCallbacks =
      typeof video.requestVideoFrameCallback === "function";
    if (this.hasFrameCallbacks) {
      const presented: VideoFrameRequestCallback = (_now, metadata) => {
        this.presentedTime = metadata.mediaTime;
        video.requestVideoFrameCallback(presented);
      };
      video.requestVideoFrameCallback(presented);
    }
    const loop = () => {
      this.draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  load(result: Result, url: string) {
    this.recovery.cancel();
    this.result = result;
    this.presentedTime = 0;
    this.canvas.width = result.video.width;
    this.canvas.height = result.video.height;
    this.video.src = url;
  }
  refreshVideo() {
    this.recovery.refresh();
  }
  step(delta: number) {
    if (!this.result) return;
    this.video.pause();
    const i = sampleIndex(this.result, this.video.currentTime);
    this.video.currentTime =
      this.result.samples[
        Math.max(0, Math.min(this.result.samples.length - 1, i + delta))
      ].time + 0.00001;
  }
  seek(time: number) {
    this.video.pause();
    this.video.currentTime = Math.max(0, time);
  }
  draw() {
    const r = this.result,
      c = this.canvas,
      ctx = c.getContext("2d");
    if (!r || !ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);
    const i = sampleIndex(
        r,
        this.hasFrameCallbacks ? this.presentedTime : this.video.currentTime,
      ),
      s = r.samples[i];
    this.status.textContent = `${observationLabel(s)} · frame ${s.frame} · ${s.time.toFixed(3)}s`;
    this.status.dataset.state = s.status;
    this.status.dataset.source = s.source ?? "";
    if (!this.enabled) return;
    const scale = c.width / 900;
    ctx.lineWidth = 2.2 * scale;
    ctx.strokeStyle =
      s.status !== "observed"
        ? "#ffbd66"
        : s.source === "appearance"
          ? "#49ded4"
          : "#b8f96a";
    ctx.setLineDash(s.status === "predicted" ? [8 * scale, 5 * scale] : []);
    if (s.box) {
      const [x1, y1, x2, y2] = s.box;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
    ctx.setLineDash([]);
    ctx.beginPath();
    let connected = false;
    for (const p of r.samples.slice(Math.max(0, i - 10), i + 1)) {
      if (!p.center || p.segment !== s.segment || p.status !== "observed") {
        connected = false;
        continue;
      }
      if (connected) ctx.lineTo(...p.center);
      else ctx.moveTo(...p.center);
      connected = true;
    }
    ctx.stroke();
    ctx.strokeStyle = "#9ed4ff";
    ctx.fillStyle = "#9ed4ff";
    for (const side of ["left", "right"]) {
      const pts = ["hip", "knee", "ankle"].map((k) => s.pose[`${side}_${k}`]);
      ctx.beginPath();
      pts.forEach((p, j) => {
        if (!p) return;
        if (j && pts[j - 1]) ctx.lineTo(...p);
        else ctx.moveTo(...p);
      });
      ctx.stroke();
      for (const p of pts) {
        if (p) {
          ctx.beginPath();
          ctx.arc(...p, 3 * scale, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      // Detected foot outline (heel → big toe → small toe → heel), when available.
      const foot = ["heel", "big_toe", "small_toe"]
        .map((k) => s.pose[`${side}_${k}`])
        .filter((p): p is Point => Boolean(p));
      if (foot.length >= 2) {
        ctx.beginPath();
        ctx.moveTo(...foot[0]);
        for (const p of foot.slice(1)) ctx.lineTo(...p);
        if (foot.length === 3) ctx.closePath();
        ctx.stroke();
      }
    }
    // Alternate observations remain inspectable without replacing the raw pose.
    const supporting = r.events.find((e) =>
      e.observation_view && e.observation_view !== "pose" && Math.abs(e.time - s.time) < .2);
    if (supporting && supporting.observation_view !== "pose") {
      const view = supporting.observation_view;
      const points = view ? s[view] : undefined;
      ctx.strokeStyle = view === "motion_pose" ? "#49ded4" : "#ffbd66";
      ctx.lineWidth = 4 * scale;
      ctx.setLineDash([5 * scale, 3 * scale]);
      for (const side of ["left", "right"]) {
        const foot = ["heel", "big_toe", "small_toe"]
          .map((name) => points?.[`${side}_${name}`]).filter((p): p is Point => Boolean(p));
        if (foot.length < 2) continue;
        ctx.beginPath(); ctx.moveTo(...foot[0]);
        for (const p of foot.slice(1)) ctx.lineTo(...p);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    const event = r.events.find((e) => Math.abs(e.time - s.time) < 0.09);
    if (event) {
      ctx.fillStyle = event.status === "counted" ? "#b8f96a" : "#ffbd66";
      ctx.font = `bold ${20 * scale}px sans-serif`;
      ctx.fillText(
        event.reason === "heard_ball_out_of_view"
          ? "HEARD TOUCH · BALL OUT OF VIEW"
          : event.status === "counted"
            ? "ESTIMATED TOUCH"
            : "REVIEW CONTACT",
        20 * scale,
        35 * scale,
      );
    }
  }
}
