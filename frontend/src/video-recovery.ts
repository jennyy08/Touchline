/** Restart the media decoder without losing the user's playback position. */
export class VideoRecovery {
  private pending: (() => void) | null = null;
  private hidden = false;
  constructor(private video: HTMLVideoElement) {
    video.addEventListener('error', () => this.cancel());
  }

  cancel() {
    if (this.pending) this.video.removeEventListener('loadedmetadata', this.pending);
    this.pending = null;
  }

  visibility(hidden: boolean) {
    if (hidden) this.hidden = true;
    else if (this.hidden) {
      this.hidden = false;
      this.refresh();
    }
  }

  refresh() {
    const v = this.video;
    if (!v.getAttribute('src') || this.pending) return;
    const time = v.currentTime;
    const resume = !v.paused && !v.ended;
    const rate = v.playbackRate;
    this.pending = () => {
      this.pending = null;
      v.currentTime = Number.isFinite(v.duration)
        ? Math.min(time, Math.max(0, v.duration - .001)) : time;
      v.playbackRate = rate;
      // Browsers may require a user gesture before resuming after backgrounding.
      if (resume) void v.play().catch(() => {});
    };
    v.addEventListener('loadedmetadata', this.pending, { once: true });
    v.load();
  }
}
