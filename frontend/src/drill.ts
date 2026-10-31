import { findDrill } from "./drill-catalog";
import { header, footer, setupPreviews } from "./library-shared";
import "./library.css";
const app = document.querySelector<HTMLElement>("#app")!;
const drill = findDrill(new URLSearchParams(location.search).get("id"));
if (!drill) {
  app.innerHTML = `${header}<main class="not-found"><p class="overline">DRILL NOT FOUND</p><h1>Back to<br><em>practice.</em></h1><p>That drill isn’t in the library yet.</p><a class="action" href="/#drills">Browse the drills →</a></main>${footer}`;
} else {
  document.title = `Touchline · ${drill.name}`;
  app.innerHTML = `${header}<main class="drill-detail"><a class="back-link" href="/#drills">← All drills</a><section class="drill-intro"><div><p class="overline">${drill.focus} / BEGINNER + INTERMEDIATE</p><h1>${drill.name}<span class="accent">.</span></h1><p class="intro">${drill.description}</p><div class="detail-actions"><a class="action" href="#practice">Practice now ↓</a><a class="quiet-link" href="${drill.analysis}">Analyze a recording ↗</a></div>${drill.live ? `<p><a class="quiet-link" href="${drill.live}">Or try live webcam juggling ↗</a></p>` : ""}</div><div class="preview detail-preview"><video data-preview muted loop playsinline preload="none" poster="${drill.poster}" src="${drill.preview}" aria-label="${drill.name} demonstration"></video><button class="preview-control" aria-pressed="false">Play preview</button><span class="preview-status" role="status"></span></div></section><section class="instruction-grid"><div><p class="overline">MAKE A LITTLE SPACE</p><h2>The setup.</h2><dl><dt>Bring</dt><dd>${drill.equipment}</dd><dt>Find</dt><dd>${drill.space}</dd></dl></div><div><p class="overline">ONE THING AT A TIME</p><h2>Give it a go.</h2><ol>${drill.steps.map((s) => `<li>${s}</li>`).join("")}</ol></div></section><section id="practice" class="practice-timer"><div><p class="overline">YOUR PACE. YOUR SESSION.</p><h2>A little time<br><em>on the ball.</em></h2><p>This is an optional timer, not a recording.<br>Take a break whenever you need.</p></div><div class="timer-controls"><label for="duration">Practice length</label><select id="duration"><option value="30">30 seconds</option><option value="60" selected>60 seconds</option><option value="90">90 seconds</option></select><output id="clock" aria-label="Time remaining">1:00</output><div><button class="action" id="timer-start">Start practice</button><button class="quiet-button" id="timer-reset">Reset</button></div><p id="timer-status" role="status">Ready when you are.</p></div></section><section class="analysis-guide"><div><p class="overline">RECORD. REPLAY. TRY AGAIN.</p><h2>Take a<br><em>closer look.</em></h2><p>${drill.camera}</p><a class="action" href="${drill.analysis}">Analyze a recording ↗</a></div><div><h3>What you can inspect</h3><ul>${drill.measures.map((m) => `<li>${m}</li>`).join("")}</ul><p class="limitation">${drill.limitation}</p><p class="small-note">Uploads are processed locally. Review and correct estimates separately from the automatic result.</p></div></section></main>${footer}`;
  setupPreviews(app);
  const clock = document.querySelector<HTMLOutputElement>("#clock")!;
  const duration = document.querySelector<HTMLSelectElement>("#duration")!;
  const start = document.querySelector<HTMLButtonElement>("#timer-start")!;
  const status = document.querySelector<HTMLElement>("#timer-status")!;
  let remaining = 60000,
    deadline = 0,
    running = false;
  function render() {
    const seconds = Math.ceil(remaining / 1000);
    clock.value = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    start.textContent = running
      ? "Pause"
      : remaining === 0
        ? "Practice again"
        : remaining < Number(duration.value) * 1000
          ? "Resume"
          : "Start practice";
    duration.disabled = running;
  }
  function pause() {
    remaining = Math.max(0, deadline - performance.now());
    running = false;
    render();
  }
  start.onclick = () => {
    if (running) {
      pause();
      status.textContent = "Paused. Take your time.";
    } else {
      if (remaining === 0) remaining = Number(duration.value) * 1000;
      deadline = performance.now() + remaining;
      running = true;
      status.textContent = "Keep a comfortable pace.";
      render();
    }
  };
  function reset() {
    running = false;
    remaining = Number(duration.value) * 1000;
    status.textContent = "Ready when you are.";
    render();
  }
  document.querySelector<HTMLButtonElement>("#timer-reset")!.onclick = reset;
  duration.onchange = reset;
  setInterval(() => {
    if (!running) return;
    remaining = Math.max(0, deadline - performance.now());
    if (remaining === 0) {
      running = false;
      status.textContent =
        "Set complete. Take a breather, then try again or review a recording.";
    }
    render();
  }, 100);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && running) {
      pause();
      status.textContent = "Paused while this page was away.";
    }
  });
}
