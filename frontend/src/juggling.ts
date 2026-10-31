import layout from "./layout.html?raw";
import "./style.css";
import { AnnotatedPlayer } from "./player";
import {
  countSplit,
  isHeard,
  parseReview,
  seedReview,
  stopsOf,
} from "./review";
import { labels, type Result, type Review } from "./types";

const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
document.querySelector("#app")!.innerHTML = layout;
let result: Result | null = null,
  review: Review | null = null;
const player = new AnnotatedPlayer(
  $("video"),
  $("overlay"),
  $("tracking-status"),
);
const video = $<HTMLVideoElement>("video");
const error = (message: string) => {
  $("error").textContent = message;
  $("error").hidden = false;
};
const clearError = () => {
  $("error").hidden = true;
};
const text = (tag: string, value: string, cls = "") => {
  const e = document.createElement(tag);
  e.textContent = value;
  e.className = cls;
  return e;
};
function download(name: string, value: unknown) {
  const serialized = JSON.stringify(value, null, 2);
  $("export-title").textContent = name;
  $<HTMLTextAreaElement>("export-text").value = serialized;
  $("export-status").textContent = "";
  $("save-json").onclick = () => {
    const url = URL.createObjectURL(
      new Blob([serialized], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    $("export-status").textContent =
      "Download requested. If no file appears, use Copy JSON.";
  };
  $("copy-json").onclick = async () => {
    try {
      await navigator.clipboard.writeText(serialized);
      $("export-status").textContent = "JSON copied.";
    } catch {
      $<HTMLTextAreaElement>("export-text").select();
      $("export-status").textContent =
        "Press Ctrl+C or ⌘C to copy the selected JSON.";
    }
  };
  $<HTMLDialogElement>("export-dialog").showModal();
}

function save() {
  if (!review) return;
  try {
    localStorage.setItem(
      `touchline:${review.video_sha256}`,
      JSON.stringify(review),
    );
    $("save-status").textContent = "Saved in this browser";
  } catch {
    $("save-status").textContent = "Export to save your review";
  }
}
function reviewCount() {
  $("review-count").textContent = String(
    review?.events.filter((e) => e.label === "touch").length ?? 0,
  );
}
function renderReview() {
  if (!review || !result) return;
  const host = $("review-events");
  host.replaceChildren();
  reviewCount();
  $("uncertain-intervals").replaceChildren();
  for (const interval of review.uncertain_intervals ?? []) {
    const b = document.createElement("button");
    b.className = "interval-note";
    b.textContent = `Uncertain ${interval.start.toFixed(2)}–${interval.end.toFixed(2)}s · ${interval.note}`;
    b.onclick = () => player.seek(interval.start);
    $("uncertain-intervals").append(b);
  }
  for (const event of [...review.events].sort((a, b) => a.time - b.time)) {
    const row = document.createElement("div");
    row.className = "review-row";
    const seek = document.createElement("button");
    seek.textContent = "▶";
    seek.title = "Seek to contact";
    seek.onclick = () => player.seek(Math.max(0, event.time - 0.35));
    const time = document.createElement("input");
    time.type = "number";
    time.min = "0";
    time.max = String(result.video.duration);
    time.step = "0.001";
    time.value = event.time.toFixed(3);
    time.setAttribute("aria-label", "Contact time in seconds");
    time.onchange = () => {
      const n = Number(time.value);
      if (
        !time.value ||
        !Number.isFinite(n) ||
        n < 0 ||
        n > result!.video.duration
      ) {
        time.value = event.time.toFixed(3);
        error("Enter a contact time inside this video.");
        return;
      }
      event.time = n;
      save();
    };
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Contact label");
    for (const label of labels) {
      const option = document.createElement("option");
      option.value = label;
      option.textContent = label;
      select.append(option);
    }
    select.value = event.label;
    select.onchange = () => {
      event.label = select.value as typeof event.label;
      reviewCount();
      save();
    };
    const remove = document.createElement("button");
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Remove review event");
    remove.onclick = () => {
      review!.events = review!.events.filter((e) => e.id !== event.id);
      save();
      renderReview();
    };
    const note = document.createElement("input");
    note.value = event.note;
    note.placeholder = "Optional note";
    note.setAttribute("aria-label", "Review note");
    note.className = "event-note";
    note.onchange = () => {
      event.note = note.value;
      save();
    };
    row.append(seek, time, select, remove, note);
    host.append(row);
  }
  if (!review.events.length)
    host.append(
      text(
        "p",
        "No review events yet. Pause at a contact and choose “At playhead”.",
        "muted",
      ),
    );
}
function showResult(data: Result, id: string) {
  result = data;
  sessionStorage.setItem("touchline:job", id);
  history.replaceState(null, "", `?job=${encodeURIComponent(id)}`);
  player.load(data, `/api/jobs/${id}/video`);
  $("workspace").hidden = false;
  $("empty").hidden = true;
  $("count").textContent = String(data.estimated_count);
  const split = countSplit(data);
  $("count-split").textContent = split.heard
    ? `${split.seen} seen + ${split.heard} heard (ball out of view)`
    : "";
  $("runtime").textContent =
    `${data.video.frames} frames · ${data.runtime_seconds.toFixed(1)}s processing`;
  $("candidate-count").textContent =
    `${data.events.filter((e) => e.status === "review").length} contacts need review · ${data.tracking_gaps.length} tracking gaps`;
  $("warnings").replaceChildren(...data.warnings.map((w) => text("li", w)));
  $("event-total").textContent = `${data.events.length} candidates`;
  $("events").replaceChildren();
  $("timeline").replaceChildren();
  for (const gap of data.tracking_gaps) {
    const span = document.createElement("span");
    span.className = "gap";
    span.style.left = `${(gap.start / data.video.duration) * 100}%`;
    span.style.width = `${Math.max(0.25, ((gap.end - gap.start) / data.video.duration) * 100)}%`;
    span.title = `Missing observations ${gap.start.toFixed(2)}–${gap.end.toFixed(2)}s`;
    $("timeline").append(span);
  }
  // Stops (ball held still, e.g. a catch) are shown for context and never counted.
  const stops = stopsOf(data);
  for (const stop of stops) {
    const span = document.createElement("button");
    span.className = "stop-span";
    span.style.left = `${(stop.start / data.video.duration) * 100}%`;
    span.style.width = `${Math.max(0.5, ((stop.end - stop.start) / data.video.duration) * 100)}%`;
    span.title = `Juggling stopped ${stop.start.toFixed(2)}–${stop.end.toFixed(2)}s`;
    span.setAttribute("aria-label", span.title);
    span.onclick = () => player.seek(Math.max(0, stop.start - 0.35));
    $("timeline").append(span);
  }
  const stopRow = (stop: (typeof stops)[number]) => {
    const button = document.createElement("button");
    button.className = "event stop";
    button.append(
      text("span", "■", "event-number"),
      text("strong", `${stop.start.toFixed(3)}s`),
      text(
        "span",
        `ball held still ${(stop.end - stop.start).toFixed(1)}s`,
        "event-reason",
      ),
      text("span", "STOPPED", "event-badge"),
    );
    button.onclick = () => player.seek(Math.max(0, stop.start - 0.35));
    return button;
  };
  let pendingStops = [...stops].sort((a, b) => a.start - b.start);
  data.events.forEach((e, index) => {
    while (pendingStops.length && pendingStops[0].start < e.time)
      $("events").append(stopRow(pendingStops.shift()!));
    const heard = isHeard(e);
    const button = document.createElement("button");
    button.className = `event ${e.status}${heard ? " heard" : ""}`;
    button.append(
      text("span", String(index + 1).padStart(2, "0"), "event-number"),
      text("strong", `${e.time.toFixed(3)}s`),
      text("span", e.reason.replaceAll("_", " "), "event-reason"),
      text(
        "span",
        heard ? "HEARD" : e.status === "counted" ? "ESTIMATED" : "REVIEW",
        "event-badge",
      ),
    );
    button.onclick = () => player.seek(e.time - 0.35);
    $("events").append(button);
    const marker = document.createElement("button");
    marker.className = `marker ${e.status}${heard ? " heard" : ""}`;
    marker.style.left = `${(e.time / data.video.duration) * 100}%`;
    marker.title = `${e.time.toFixed(3)}s · ${e.reason.replaceAll("_", " ")}`;
    marker.setAttribute("aria-label", marker.title);
    marker.onclick = button.onclick;
    $("timeline").append(marker);
  });
  for (const stop of pendingStops) $("events").append(stopRow(stop));
  if (!data.events.length)
    $("events").append(
      text(
        "p",
        "No supported contact candidates. Review the replay and add events manually.",
        "muted",
      ),
    );
  review = seedReview(data);
  try {
    const saved = localStorage.getItem(`touchline:${data.video.sha256}`);
    if (saved) review = parseReview(saved, data);
  } catch {
    error("Saved review could not be loaded. The automatic result is intact.");
  }
  renderReview();
}
async function request(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = (await response.json()).detail ?? message;
    } catch {}
    throw new Error(String(message));
  }
  return response.json();
}
$("choose").onclick = () => $<HTMLInputElement>("upload").click();
$<HTMLInputElement>("upload").onchange = async () => {
  const file = $<HTMLInputElement>("upload").files?.[0];
  if (!file) return;
  clearError();
  if (file.size > 250 * 1024 * 1024) {
    error("Video exceeds 250 MB. Trim or compress it first.");
    return;
  }
  $("filename").textContent = file.name;
  $("workspace").hidden = true;
  $<HTMLButtonElement>("choose").disabled = true;
  $("progress-panel").hidden = false;
  $("progress-label").textContent = "Uploading locally…";
  $<HTMLProgressElement>("progress").removeAttribute("value");
  try {
    const body = new FormData();
    body.append("file", file);
    const { id } = await request("/api/jobs", { method: "POST", body });
    sessionStorage.setItem("touchline:job", id);
    await followJob(id);
  } catch (e) {
    error(e instanceof Error ? e.message : String(e));
  } finally {
    $<HTMLButtonElement>("choose").disabled = false;
    $("progress-panel").hidden = true;
    $<HTMLInputElement>("upload").value = "";
  }
};
async function followJob(id: string) {
  for (;;) {
    const state = await request(`/api/jobs/${id}`);
    $("progress-label").textContent =
      (
        {
          queued: "Waiting to start",
          loading_models: "Loading local models",
          analyzing: "Tracking ball & body",
          counting: "Finding contact events",
        } as Record<string, string>
      )[state.stage] ?? state.stage;
    $("progress-detail").textContent = state.frames
      ? `${state.frames}${state.total ? ` / ${state.total}` : ""} frames`
      : "";
    const bar = $<HTMLProgressElement>("progress");
    if (state.total)
      bar.value = Math.min(99, (state.frames / state.total) * 100);
    else bar.removeAttribute("value");
    if (state.stage === "error") throw new Error(state.error);
    if (state.stage === "complete") {
      showResult(await request(`/api/jobs/${id}/result`), id);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
}
$("previous").onclick = () => player.step(-1);
$("next").onclick = () => player.step(1);
$<HTMLSelectElement>("speed").onchange = () => {
  video.playbackRate = Number($<HTMLSelectElement>("speed").value);
};
$<HTMLInputElement>("show-overlay").onchange = () => {
  player.enabled = $<HTMLInputElement>("show-overlay").checked;
};
$("add-event").onclick = () => {
  if (!review || !result) return;
  review.events.push({
    id: crypto.randomUUID(),
    time: Math.min(video.currentTime, result.video.duration),
    label: "touch",
    note: "",
  });
  renderReview();
  save();
};
$("export-review").onclick = () =>
  review && download("touchline-review.json", review);
$("download-result").onclick = () =>
  result && download("touchline-analysis.json", result);
$("import-review").onclick = () => $<HTMLInputElement>("review-file").click();
$<HTMLInputElement>("review-file").onchange = async () => {
  const input = $<HTMLInputElement>("review-file"),
    file = input.files?.[0];
  if (!file || !result) return;
  try {
    review = parseReview(await file.text(), result);
    renderReview();
    save();
    clearError();
  } catch (e) {
    error(e instanceof Error ? e.message : String(e));
  }
  input.value = "";
};
// A local job URL lets a completed analysis reopen without re-uploading.
const previous =
  new URLSearchParams(location.search).get("job") ??
  sessionStorage.getItem("touchline:job");
if (previous) {
  $("progress-panel").hidden = false;
  $<HTMLButtonElement>("choose").disabled = true;
  followJob(previous)
    .catch((e) => {
      sessionStorage.removeItem("touchline:job");
      error(e.message);
    })
    .finally(() => {
      $("progress-panel").hidden = true;
      $<HTMLButtonElement>("choose").disabled = false;
    });
}
