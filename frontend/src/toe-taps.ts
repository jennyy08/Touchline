import "./dribbling.css";
import "./session-story.css";
import "./toe-taps.css";
import { AnnotatedPlayer } from "./player";
import { seedReview, parseReview } from "./review";
import type { Result, Review } from "./types";
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
$("app").innerHTML =
  `<header class="app-header"><a class="brand" href="/">TOUCHLINE<span class="brand-dot">/</span></a><nav aria-label="Practice mode"><a href="/">Juggling</a><a href="/dribbling.html">Side to side</a><a href="/toe-taps.html" aria-current="page">Toe taps</a><a href="/live.html">Live</a></nav></header>
<main><div class="page-heading"><p class="chapter-kicker">TOE TAPS / EXPERIMENTAL</p><h1>Find your rhythm.</h1><p>Alternate feet on top of the ball. Upload a clip to inspect estimated taps.</p></div>
<p>Keep the ball and both feet visible, with a fixed camera. Shoe overlap can hide contacts.</p>
<form id="upload" class="file-picker"><label for="file">Practice video</label><input id="file" type="file" accept="video/*,.mov,.mp4" required/><button class="primary">Analyze toe taps ↗</button></form>
<p id="error" role="alert" hidden></p><div id="progress" role="status" hidden><p id="stage"></p><progress id="bar"></progress></div>
<section id="result" class="video-workspace" hidden><div class="workspace-heading"><h2>Your taps, on replay.</h2><button id="export">Export analysis</button></div><p id="total" class="session-summary"></p>
<div class="workspace-grid"><div><div class="video-stage"><video id="video" controls playsinline></video><canvas id="overlay"></canvas></div><div class="player-controls"><button id="previous" aria-label="Previous frame">← Frame</button><button id="next" aria-label="Next frame">Frame →</button><button id="refresh-video">Refresh video</button><label>Speed <select id="speed"><option value="1">1×</option><option value="0.5">0.5×</option><option value="0.25">0.25×</option></select></label><label><input id="tracking" type="checkbox" checked/>Tracking</label></div><p id="status"></p><details><summary>How to read this estimate</summary><ul id="warnings"></ul></details></div>
<aside><h3>Estimated events</h3><p>Each event needs an observed approach to the ball-top zone. Select a moment to check it. Dashed teal shoes show image-motion evidence; amber shoes show the closer pose view.</p><div id="events" class="event-list"></div>
<details><summary>Your corrections</summary><p>Separate from the automatic result. Starts as a copy, not a verified count. Export to keep your edits.</p><p id="review-count"></p><button id="add">Add tap at current frame</button><button id="save">Export corrections</button><label>Import corrections<input id="import" type="file" accept="application/json"/></label><div id="review" class="event-list"></div></details></aside></div></section><section id="export-fallback" hidden><label for="export-json">Export JSON — copy this if your browser does not save the download</label><textarea id="export-json" readonly rows="6"></textarea></section><footer>Local processing · No accuracy score</footer></main>`;
const video = $<HTMLVideoElement>("video");
const player = new AnnotatedPlayer(
  video,
  $<HTMLCanvasElement>("overlay"),
  $("status"),
);
let result: Result | null = null,
  review: Review | null = null,
  busy = false;
function error(e: unknown) {
  $("error").textContent = e instanceof Error ? e.message : String(e);
  $("error").hidden = false;
}
async function request(url: string, options?: RequestInit) {
  const r = await fetch(url, options);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${r.status})`);
  }
  return r.json();
}
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  $("export-fallback").hidden = false;
  $<HTMLTextAreaElement>("export-json").value = JSON.stringify(value, null, 2);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
function renderReview() {
  if (!review) return;
  $("review-count").textContent =
    `${review.events.filter((e) => e.label === "touch").length} taps in your editable copy`;
  $("review").replaceChildren();
  for (const e of [...review.events].sort((a, b) => a.time - b.time)) {
    const row = document.createElement("div");
    const seek = document.createElement("button");
    seek.textContent = `${e.time.toFixed(2)}s · ${e.label}`;
    seek.onclick = () => player.seek(e.time);
    const remove = document.createElement("button");
    remove.textContent = "Remove";
    remove.setAttribute(
      "aria-label",
      `Remove correction at ${e.time.toFixed(2)} seconds`,
    );
    remove.onclick = () => {
      review!.events = review!.events.filter((x) => x.id !== e.id);
      renderReview();
    };
    row.append(seek, remove);
    $("review").append(row);
  }
}
function show(data: Result & { drill?: string }, id: string) {
  if (data.drill !== "toe_taps")
    throw new Error(
      "This is not a toe-tap result. Open it in its original drill.",
    );
  result = data;
  review = seedReview(data);
  player.load(data, `/api/jobs/${id}/video`);
  $("result").hidden = false;
  const reviewCount = data.events.filter((e) => e.status === "review").length;
  $("total").textContent =
    `${data.estimated_count} estimated taps · ${reviewCount} review candidate${reviewCount === 1 ? "" : "s"}`;
  $("events").replaceChildren();
  for (const e of data.events) {
    const button = document.createElement("button");
    button.textContent = `${e.time.toFixed(2)}s · ${e.body_part?.replaceAll("_", " ") ?? "foot identity unclear"} · ${e.status === "counted" ? "estimated tap" : "review timing after tracking gap"}`;
    button.onclick = () => player.seek(Math.max(0, e.time - 0.3));
    $("events").append(button);
  }
  if (!data.events.length)
    $("events").textContent =
      "No supported cycles found. This does not mean no taps occurred. Use replay and corrections.";
  $("warnings").replaceChildren();
  for (const w of data.warnings) {
    const li = document.createElement("li");
    li.textContent = w;
    $("warnings").append(li);
  }
  renderReview();
  history.replaceState(null, "", `?job=${encodeURIComponent(id)}`);
}
function setBusy(value: boolean) {
  busy = value;
  $("progress").hidden = !value;
  document
    .querySelectorAll<
      HTMLInputElement | HTMLButtonElement
    >("#upload input,#upload button")
    .forEach((e) => (e.disabled = value));
}
async function follow(id: string) {
  for (;;) {
    const s = await request(`/api/jobs/${id}`);
    $("stage").textContent =
      `${s.stage.replaceAll("_", " ")} · ${s.frames} / ${s.total || "?"} frames`;
    const bar = $<HTMLProgressElement>("bar");
    if (s.total) {
      bar.max = s.total;
      bar.value = s.frames;
    } else bar.removeAttribute("value");
    if (s.stage === "error") throw new Error(s.error);
    if (s.stage === "complete") {
      show(await request(`/api/jobs/${id}/result`), id);
      return;
    }
    await new Promise((r) => setTimeout(r, 700));
  }
}
$("upload").onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  const file = $<HTMLInputElement>("file").files?.[0];
  if (!file) return;
  if (file.size > 250 * 1024 * 1024) {
    error(new Error("Video exceeds 250 MB. Trim it first."));
    return;
  }
  setBusy(true);
  $("stage").textContent = "Uploading video locally…";
  $<HTMLProgressElement>("bar").removeAttribute("value");
  $("error").hidden = true;
  video.pause();
  try {
    const body = new FormData();
    body.append("file", file);
    body.append("drill", "toe_taps");
    const job = await request("/api/jobs", { method: "POST", body });
    $("result").hidden = true;
    await follow(job.id);
  } catch (e) {
    error(e);
  } finally {
    setBusy(false);
  }
};
$("refresh-video").onclick = () => player.refreshVideo();
$("previous").onclick = () => player.step(-1);
$("next").onclick = () => player.step(1);
$<HTMLSelectElement>("speed").onchange = (e) =>
  (video.playbackRate = Number((e.target as HTMLSelectElement).value));
$<HTMLInputElement>("tracking").onchange = (e) =>
  (player.enabled = (e.target as HTMLInputElement).checked);
$("export").onclick = () =>
  result && download(result, "toe-taps-analysis.json");
$("save").onclick = () =>
  review && download(review, "toe-taps-corrections.json");
$("add").onclick = () => {
  if (!review || !result) return;
  review.events.push({
    id: crypto.randomUUID(),
    time: Math.min(video.currentTime, result.video.duration),
    label: "touch",
    note: "Manually added toe tap",
  });
  renderReview();
};
$<HTMLInputElement>("import").onchange = async (e) => {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (!f || !result) return;
  try {
    review = parseReview(await f.text(), result);
    renderReview();
  } catch (e) {
    error(e);
  }
};
const job = new URLSearchParams(location.search).get("job");
if (job) {
  setBusy(true);
  follow(job)
    .catch(error)
    .finally(() => setBusy(false));
}
