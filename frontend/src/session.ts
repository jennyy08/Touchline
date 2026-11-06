import { drills, findDrill } from "./drill-catalog";
import { header, footer } from "./library-shared";
import {
  clearHistory,
  planSession,
  practiceSummary,
  readHistory,
  saveSession,
  type CompletedSession,
  type SessionFocus,
  type SessionMinutes,
  type SessionStage,
} from "./practice-session";
import "./library.css";
import "./session.css";

const app = document.querySelector<HTMLElement>("#app")!;
app.innerHTML = `${header}<main class="session-page"><a class="back-link" href="/#drills">← Practice library</a><section class="session-heading"><p class="overline">GUIDED PRACTICE</p><h1>Show up.<br><em>Start small.</em></h1><p class="intro">Pick a focus and a few minutes. Follow the timer through each drill, take a rest, then see what you practiced.</p></section><section id="session-setup" class="session-setup"><div><h2>Make it yours.</h2><p>The session gives you a plan. You choose the pace, and you can pause or move on early.</p></div><div class="session-options"><label for="session-length">Time you have</label><select id="session-length"><option value="5">5 minutes</option><option value="10" selected>10 minutes</option><option value="15">15 minutes</option></select><label for="session-focus">Focus</label><select id="session-focus"><option value="mix">A bit of everything</option>${drills.map((d) => `<option value="${d.id}">${d.name}</option>`).join("")}</select><div id="session-plan" class="session-plan"></div><button id="begin-session" class="action">Begin session →</button></div></section><section id="active-session" class="active-session" hidden><div class="session-progress"><span id="stage-index"></span><span id="stage-progress"></span></div><p id="stage-kind" class="overline"></p><h2 id="stage-title"></h2><p id="stage-description"></p><div id="stage-instructions"></div><output id="stage-clock" aria-label="Time remaining">0:00</output><div class="session-actions"><button id="toggle-stage" class="action">Start timer</button><button id="advance-stage" class="quiet-button">Move on early</button></div><p id="stage-status" role="status"></p><a id="stage-drill-link" class="quiet-link" href="/#drills" target="_blank" rel="noopener">View drill setup in a new tab ↗</a></section><section id="session-finished" class="session-finished" hidden><p class="overline">SESSION COMPLETE</p><h2 id="finished-title">Nice work<br><em>showing up.</em></h2><p id="finished-summary"></p><p id="save-status" role="status"></p><div class="session-actions"><button id="another-session" class="action">Plan another session →</button><a class="quiet-link" href="/#drills">Browse drills ↗</a></div></section><section id="history" class="session-history"><div class="history-heading"><div><p class="overline">YOUR PRACTICE / THIS BROWSER</p><h2>The work adds up.</h2></div><button id="clear-history" class="quiet-button" hidden>Clear history</button></div><div id="history-summary" class="history-summary"></div><div id="history-list" class="history-list"></div><p class="small-note">Completed sessions are saved only in this browser. Video analysis and corrected event counts are separate.</p></section></main>${footer}`;
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const length = $<HTMLSelectElement>("session-length"),
  focus = $<HTMLSelectElement>("session-focus");
const clock = $<HTMLOutputElement>("stage-clock");
let stages: SessionStage[] = [],
  stage = 0,
  remaining = 0,
  deadline = 0,
  running = false,
  elapsed = 0;
let practiced = 0,
  completed: string[] = [],
  chosenMinutes: SessionMinutes = 10,
  chosenFocus: SessionFocus = "mix";
function formatSeconds(seconds: number) {
  const s = Math.ceil(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
function showPlan() {
  const selected = planSession(
    Number(length.value) as SessionMinutes,
    focus.value as SessionFocus,
  );
  $("session-plan").replaceChildren(
    ...selected
      .filter((s) => s.kind === "practice")
      .map((s, i) => {
        const row = document.createElement("p");
        row.textContent = `0${i + 1}  ${findDrill(s.drillId)?.name} · ${formatSeconds(s.seconds)}`;
        return row;
      }),
  );
  const rest = document.createElement("p");
  rest.className = "small-note";
  rest.textContent =
    "30 seconds of rest between drills · pause whenever you need";
  $("session-plan").append(rest);
}
length.onchange = showPlan;
focus.onchange = showPlan;
showPlan();
function renderClock() {
  clock.value = formatSeconds(remaining / 1000);
  $("toggle-stage").textContent = running
    ? "Pause timer"
    : elapsed > 0
      ? "Resume timer"
      : "Start timer";
}
function recordElapsed() {
  if (!running) return;
  const now = performance.now();
  const delta = Math.max(0, remaining - (deadline - now));
  elapsed += Math.min(remaining, delta);
  remaining = Math.max(0, deadline - now);
  running = false;
}
function pause() {
  recordElapsed();
  renderClock();
  $("stage-status").textContent = "Paused. Take the time you need.";
}
function renderStage() {
  const current = stages[stage];
  remaining = current.seconds * 1000;
  elapsed = 0;
  running = false;
  const isPractice = current.kind === "practice";
  const drill = isPractice ? findDrill(current.drillId) : null;
  $("stage-index").textContent = `STEP ${stage + 1} / ${stages.length}`;
  $("stage-progress").textContent =
    `${Math.round((stage / stages.length) * 100)}% through your plan`;
  $("stage-kind").textContent = isPractice ? "PRACTICE" : "REST";
  $("stage-title").textContent = drill?.name ?? "Take a breather.";
  $("stage-description").textContent =
    drill?.description ?? "Have some water. Your next drill is coming up.";
  const instructions = $("stage-instructions");
  instructions.replaceChildren();
  if (drill) {
    const list = document.createElement("ol");
    for (const step of drill.steps) {
      const item = document.createElement("li");
      item.textContent = step;
      list.append(item);
    }
    instructions.append(list);
  }
  const link = $<HTMLAnchorElement>("stage-drill-link");
  link.hidden = !drill;
  link.href = drill ? `/drill.html?id=${drill.id}` : "/#drills";
  $("stage-status").textContent = isPractice
    ? "Start when you’re ready."
    : "Rest, then continue when you’re ready.";
  $("advance-stage").textContent =
    stage === stages.length - 1 ? "Finish session early" : "Move on early";
  renderClock();
}
function finishStage() {
  recordElapsed();
  const current = stages[stage];
  if (current.kind === "practice" && elapsed >= 1000) {
    practiced += elapsed / 1000;
    completed.push(current.drillId);
  }
  if (stage === stages.length - 1) {
    finishSession();
    return;
  }
  stage++;
  renderStage();
}
function showHistory() {
  const history = readHistory(),
    summary = practiceSummary(history);
  $("history-summary").textContent = history.length
    ? `${summary.sessions} completed session${summary.sessions === 1 ? "" : "s"} · ${formatSeconds(summary.seconds)} practiced`
    : "Your completed sessions will appear here.";
  $("clear-history").hidden = !history.length;
  const list = $("history-list");
  list.replaceChildren();
  for (const session of [...history].reverse()) {
    const row = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = new Date(session.completedAt).toLocaleDateString(
      undefined,
      { year: "numeric", month: "short", day: "numeric" },
    );
    const details = document.createElement("span");
    details.textContent = `${formatSeconds(session.practiceSeconds)} practiced · ${session.completedDrills.map((id) => findDrill(id)?.name ?? id).join(", ")}`;
    row.append(title, details);
    list.append(row);
  }
}
function finishSession() {
  $("active-session").hidden = true;
  $("session-finished").hidden = false;
  $("finished-title").textContent =
    practiced >= 10 ? "Nice work showing up." : "Session ended.";
  $("finished-summary").textContent =
    `${formatSeconds(practiced)} practiced across ${completed.length} drill${completed.length === 1 ? "" : "s"}.`;
  let message =
    "No practice time was recorded, so this session wasn’t added to history.";
  if (practiced >= 10) {
    const entry: CompletedSession = {
      id: crypto.randomUUID(),
      completedAt: new Date().toISOString(),
      plannedMinutes: chosenMinutes,
      focus: chosenFocus,
      practiceSeconds: Math.round(practiced),
      completedDrills: completed,
    };
    message = saveSession(entry)
      ? "Saved to your practice history in this browser."
      : "Couldn’t save in this browser. Your session is complete, but it won’t appear in history.";
  }
  $("save-status").textContent = message;
  showHistory();
}
$("begin-session").onclick = () => {
  chosenMinutes = Number(length.value) as SessionMinutes;
  chosenFocus = focus.value as SessionFocus;
  stages = planSession(chosenMinutes, chosenFocus);
  stage = 0;
  practiced = 0;
  completed = [];
  $("session-setup").hidden = true;
  $("session-finished").hidden = true;
  $("active-session").hidden = false;
  renderStage();
  $("active-session").scrollIntoView({ behavior: "smooth" });
};
$("toggle-stage").onclick = () => {
  if (running) pause();
  else {
    deadline = performance.now() + remaining;
    running = true;
    $("stage-status").textContent = "Keep your own pace.";
    renderClock();
  }
};
$("advance-stage").onclick = finishStage;
$("another-session").onclick = () => {
  $("session-finished").hidden = true;
  $("session-setup").hidden = false;
  $("session-setup").scrollIntoView({ behavior: "smooth" });
};
$("clear-history").onclick = () => {
  if (!confirm("Clear your practice history from this browser?")) return;
  if (clearHistory()) showHistory();
  else
    $("history-summary").textContent =
      "Couldn’t clear history in this browser.";
};
setInterval(() => {
  if (!running) return;
  if (performance.now() >= deadline) {
    finishStage();
    return;
  }
  clock.value = formatSeconds(Math.max(0, deadline - performance.now()) / 1000);
}, 200);
document.addEventListener("visibilitychange", () => {
  if (document.hidden && running) pause();
});
showHistory();
