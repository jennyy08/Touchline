import { drills } from "./drill-catalog";
import { header, footer, setupPreviews } from "./library-shared";
import "./library.css";
import "./session.css";
const app = document.querySelector<HTMLElement>("#app")!;
app.innerHTML = `${header}<main id="main"><section class="library-hero"><div class="hero-copy"><p class="overline">A LITTLE ROOM. A LOT TO WORK ON.</p><h1>Your space.<br><em>Your practice.</em></h1><p class="intro">A ball, a bit of time, and one thing to get better at. Find a drill, give it a go, and take a closer look at your practice.</p><a class="action" href="#drills">Find your next drill <span aria-hidden="true">↘</span></a><p class="small-note">For players building their basics—and building on them.</p></div><div class="route-art" aria-hidden="true"><svg viewBox="0 0 400 640"><path id="practice-route" d="M280 30 C30 30 30 210 230 210 S420 410 160 410 S50 570 280 610"/><circle cx="280" cy="30" r="6"/><circle cx="280" cy="610" r="6"/><g id="route-ball"><circle r="24"/><path d="M-7 -10 L8 -10 L14 4 L0 14 L-14 4 Z"/></g></svg><span>ONE TOUCH AT A TIME.</span></div></section><section class="session-invite"><div><p class="overline">PRACTICE WITH A PLAN</p><h2>A few minutes.<br><em>A place to start.</em></h2><p>Pick a focus and follow a short session through the drills. Take your time, then come back to see what you practiced.</p></div><a class="action" href="/session.html">Start a guided session ↗</a></section><section id="drills" class="drill-library"><div class="section-heading"><div><p class="overline">THE PRACTICE LIBRARY / 01—${String(drills.length).padStart(2, "0")}</p><h2>What are you<br><em>working on?</em></h2></div><p>Start with something simple. Practice at your pace, then use a recording to see what happened.<br><span class="small-note">Hover to preview · tap Play on mobile</span></p></div><div class="drill-grid">${drills.map((d, i) => `<article class="drill-card"><div class="preview"><video data-preview muted loop playsinline preload="none" poster="${d.poster}" src="${d.preview}" aria-label="${d.name} practice preview"></video><button class="preview-control" aria-pressed="false" aria-label="Play or pause ${d.name} preview">Play preview</button><span class="preview-status" role="status"></span></div><div class="card-heading"><span class="card-number">0${i + 1}</span><p class="overline">${d.focus}</p></div><h3><a href="/drill.html?id=${d.id}">${d.name}<span aria-hidden="true">↗</span></a></h3><p>${d.description}</p><div class="card-bottom"><span>${d.equipment}</span><a href="/drill.html?id=${d.id}">Open drill <span aria-hidden="true">→</span></a></div></article>`).join("")}</div><p class="library-note">Practice clips show the movement—not a perfect attempt. Analysis is available for all three drills; live analysis is currently for juggling.</p></section></main>${footer}`;
setupPreviews(app);
const path = document.querySelector<SVGPathElement>("#practice-route")!;
const ball = document.querySelector<SVGGElement>("#route-ball")!;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
let scheduled = false;
function positionBall() {
  const hero = document.querySelector<HTMLElement>(".library-hero")!;
  const progress = reduced.matches
    ? 0.2
    : Math.min(1, Math.max(0, scrollY / Math.max(hero.offsetHeight, 1)));
  const point = path.getPointAtLength(path.getTotalLength() * progress);
  ball.setAttribute(
    "transform",
    `translate(${point.x} ${point.y}) rotate(${progress * 300})`,
  );
  scheduled = false;
}
addEventListener(
  "scroll",
  () => {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(positionBall);
    }
  },
  { passive: true },
);
addEventListener("resize", positionBall);
positionBall();

// The home content mounts asynchronously; apply deep links after it exists.
if (location.hash === "#drills")
  requestAnimationFrame(() =>
    document.getElementById("drills")?.scrollIntoView(),
  );
