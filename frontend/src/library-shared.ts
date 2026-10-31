export const header = `<header class="library-nav"><a class="wordmark" href="/">TOUCHLINE<span>/</span></a><nav aria-label="Main navigation"><a href="/#drills">The drills</a><a href="/live.html">Live juggling ↗</a></nav></header>`;
export const footer = `<footer class="library-footer"><a class="wordmark" href="/">TOUCHLINE<span>/</span></a><p>Your space. Your practice.</p><span>Local video analysis · Experimental estimates</span></footer>`;

/** Pointer previews are optional; keyboard and touch users get an explicit button. */
export function setupPreviews(root: HTMLElement) {
  const videos = [
    ...root.querySelectorAll<HTMLVideoElement>("video[data-preview]"),
  ];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  for (const video of videos) {
    const container = video.closest<HTMLElement>(".preview")!;
    const button = container.querySelector<HTMLButtonElement>("button")!;
    const status = container.querySelector<HTMLElement>(".preview-status")!;
    const hoverTarget =
      container.closest<HTMLElement>(".drill-card") ?? container;
    let pinned = false,
      wanted = false;
    const pause = () => {
      wanted = false;
      video.pause();
      button.textContent = "Play preview";
      button.setAttribute("aria-pressed", "false");
    };
    const play = async () => {
      wanted = true;
      status.textContent = "";
      for (const other of videos) if (other !== video) other.pause();
      try {
        await video.play();
        if (!wanted) {
          video.pause();
          return;
        }
        if (!video.paused) {
          button.textContent = "Pause preview";
          button.setAttribute("aria-pressed", "true");
        }
      } catch (error) {
        if (
          wanted &&
          !(error instanceof DOMException && error.name === "AbortError")
        )
          status.textContent =
            "Preview unavailable. You can still open the drill.";
      }
    };
    button.onclick = () => {
      pinned = video.paused;
      if (pinned) void play();
      else pause();
    };
    hoverTarget.addEventListener("pointerenter", (event) => {
      if (event.pointerType === "mouse" && !reduced.matches) void play();
    });
    hoverTarget.addEventListener("pointerleave", () => {
      if (!pinned) pause();
    });
    video.addEventListener("pause", () => {
      button.textContent = "Play preview";
      button.setAttribute("aria-pressed", "false");
    });
    video.addEventListener("error", () => {
      status.textContent =
        "Preview unavailable. Open the drill for instructions.";
    });
    new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) {
        pinned = false;
        pause();
      }
    }).observe(container);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        pinned = false;
        pause();
      }
    });
  }
}
