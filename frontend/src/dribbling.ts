import layout from "./dribbling-layout.html?raw";
import "./style.css";
import "./dribbling.css";
import { AnnotatedPlayer } from "./player";
import type { Result } from "./types";
interface Setup {
  roi: number[];
  markers: number[] | null;
  require_markers: boolean;
}
interface Turn {
  id: string;
  time: number;
  side: string;
  marker_status: string;
  evidence?: "visible_reversal" | "inferred_edge_return";
  time_interval?: { start: number; end: number };
}
interface Trip {
  id: string;
  start: number;
  end: number;
  direction: string;
  duration: number;
  speed: number;
  relative_speed: number | null;
  slower: boolean;
}
interface DribbleResult extends Result {
  drill: "side_to_side";
  dribbling: {
    setup: Setup;
    turns: Turn[];
    trips: Trip[];
    trip_basis: string;
    pace_gates: number[] | null;
    review_windows?: {
      start: number;
      end: number;
      side: string;
      reason: string;
    }[];
    notes: string[];
  };
}
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
document.querySelector("#app")!.innerHTML = layout;
const preview = $<HTMLVideoElement>("preview"),
  video = $<HTMLVideoElement>("video");
const canvas = $<HTMLCanvasElement>("setup-canvas");
const player = new AnnotatedPlayer(video, $("overlay"), $("tracking-status"));
let setup: Setup = { roi: [0, 0, 1, 1], markers: null, require_markers: false };
let selection: "area" | "markers" | null = null,
  clicks: number[][] = [];
let result: DribbleResult | null = null,
  objectUrl = "",
  busy = false;
const showError = (e: unknown) => {
  $("error").textContent = e instanceof Error ? e.message : String(e);
  $("error").hidden = false;
};
function drawGuides(c: HTMLCanvasElement, s: Setup) {
  const ctx = c.getContext("2d")!;
  ctx.clearRect(0, 0, c.width, c.height);
  const [x, y, r, b] = s.roi;
  ctx.strokeStyle = "#b8f96a";
  ctx.lineWidth = c.width / 300;
  ctx.strokeRect(
    x * c.width,
    y * c.height,
    (r - x) * c.width,
    (b - y) * c.height,
  );
  ctx.strokeStyle = "#ffbd66";
  ctx.setLineDash([c.width / 90, c.width / 150]);
  for (const m of s.markers ?? []) {
    ctx.beginPath();
    ctx.moveTo(m * c.width, y * c.height);
    ctx.lineTo(m * c.width, b * c.height);
    ctx.stroke();
  }
  ctx.setLineDash([]);
}
function stopSelection() {
  selection = null;
  clicks = [];
  canvas.classList.remove("selecting");
}
function startSelection(mode: "area" | "markers") {
  preview.pause();
  selection = mode;
  clicks = [];
  canvas.classList.add("selecting");
  $("setup-status").textContent =
    mode === "area"
      ? "Click two opposite corners of the usable practice area."
      : "Click the left marker, then the right marker.";
}
$("area").onclick = () => startSelection("area");
$("markers").onclick = () => startSelection("markers");
$("reset").onclick = () => {
  setup = { roi: [0, 0, 1, 1], markers: null, require_markers: false };
  $<HTMLInputElement>("require-markers").checked = false;
  stopSelection();
  drawGuides(canvas, setup);
  $("setup-status").textContent =
    "Full frame selected. Exclude mirrors before analysis.";
};
canvas.onclick = (e) => {
  if (!selection) return;
  const rect = canvas.getBoundingClientRect();
  clicks.push([
    (e.clientX - rect.left) / rect.width,
    (e.clientY - rect.top) / rect.height,
  ]);
  if (clicks.length < 2) {
    $("setup-status").textContent = "Now click the second point.";
    return;
  }
  const [a, b] = clicks;
  if (selection === "area") {
    const roi = [
      Math.min(a[0], b[0]),
      Math.min(a[1], b[1]),
      Math.max(a[0], b[0]),
      Math.max(a[1], b[1]),
    ];
    if (roi[2] - roi[0] < 0.1 || roi[3] - roi[1] < 0.1) {
      showError("Choose a larger practice area.");
      clicks = [];
      return;
    }
    setup.roi = roi;
    setup.markers = null;
    setup.require_markers = false;
    $<HTMLInputElement>("require-markers").checked = false;
  } else {
    const m = [Math.min(a[0], b[0]), Math.max(a[0], b[0])];
    if (m[0] < setup.roi[0] || m[1] > setup.roi[2] || m[1] - m[0] < 0.1) {
      showError("Place separated markers inside the green practice area.");
      clicks = [];
      return;
    }
    setup.markers = m;
  }
  stopSelection();
  drawGuides(canvas, setup);
  $("error").hidden = true;
  $("setup-status").textContent = setup.markers
    ? "Area and markers set. Enable the reach goal below if that was your intention."
    : "Practice area set. Optionally mark the paddles next.";
};
$<HTMLInputElement>("file").onchange = () => {
  if (busy) return;
  const f = $<HTMLInputElement>("file").files?.[0];
  if (!f) return;
  $("error").hidden = true;
  $("results").hidden = true;
  video.pause();
  if (f.size > 250 * 1024 * 1024) {
    showError("Video exceeds 250 MB. Trim or compress it first.");
    return;
  }
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(f);
  preview.src = objectUrl;
  $("filename").textContent = f.name;
  $("setup").hidden = false;
  setup = { roi: [0, 0, 1, 1], markers: null, require_markers: false };
  stopSelection();
  $<HTMLInputElement>("require-markers").checked = false;
  $("setup-status").textContent =
    "Full frame selected. Exclude any mirror before analysis.";
};
preview.onloadedmetadata = () => {
  canvas.width = preview.videoWidth;
  canvas.height = preview.videoHeight;
  drawGuides(canvas, setup);
};
preview.onerror = () =>
  showError(
    "This browser cannot preview the video. Convert it to H.264 MP4 to set the practice area.",
  );
async function request(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = (await response.json()).detail ?? message;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
function row(host: string, content: string, time: number, cls = "") {
  const b = document.createElement("button");
  b.textContent = content;
  b.className = cls;
  b.onclick = () => {
    player.seek(Math.max(0, time - 0.6));
    video.playbackRate = 0.5;
    $<HTMLSelectElement>("speed").value = "0.5";
    video.play().catch(showError);
  };
  $(host).append(b);
}
function show(data: DribbleResult, id: string) {
  if (data.drill !== "side_to_side")
    throw new Error(
      "This job is a juggling result. Open it on the juggling page.",
    );
  result = data;
  const d = data.dribbling;
  player.load(data, `/api/jobs/${id}/video`);
  $("results").hidden = false;
  const guides = $<HTMLCanvasElement>("guides");
  guides.width = data.video.width;
  guides.height = data.video.height;
  drawGuides(guides, d.setup);
  const ctx = guides.getContext("2d")!;
  ctx.strokeStyle = "#9ed4ff";
  ctx.lineWidth = guides.width / 400;
  for (const x of d.pace_gates ?? []) {
    ctx.beginPath();
    ctx.moveTo(x * guides.width, d.setup.roi[1] * guides.height);
    ctx.lineTo(x * guides.width, d.setup.roi[3] * guides.height);
    ctx.stroke();
  }
  $("turn-count").textContent = String(d.turns.length);
  const inferred = d.turns.filter(
    (t) => t.evidence === "inferred_edge_return",
  ).length;
  $("summary").textContent =
    `${d.turns.length - inferred} visible + ${inferred} inferred · ${d.trips.length} timed sections`;
  for (const id of ["turns", "trips", "gaps", "feedback", "notes"])
    $(id).replaceChildren();
  for (const t of d.turns) {
    const inferred = t.evidence === "inferred_edge_return";
    const interval = t.time_interval;
    const timing = interval
      ? `${interval.start.toFixed(2)}–${interval.end.toFixed(2)}s`
      : `${t.time.toFixed(2)}s`;
    row(
      "turns",
      inferred
        ? `${timing} · ${t.side} turn · inferred from edge return`
        : `${timing} · ${t.side} turn · ${t.marker_status.replaceAll("_", " ")}`,
      interval?.start ?? t.time,
      inferred ? "inferred" : t.marker_status,
    );
  }
  $("trip-basis").textContent =
    d.trip_basis === "inner_marker_section"
      ? "Pace sections measure the middle 70% between your markers (blue lines). This excludes the turn itself and is not a full repetition time."
      : "Trips run between consecutive visible turns.";
  for (const t of d.trips)
    row(
      "trips",
      `${t.start.toFixed(2)}–${t.end.toFixed(2)}s → ${t.direction} · ${t.duration.toFixed(2)}s · ${t.speed.toFixed(2)} area widths/s · ${t.relative_speed === null ? "not enough same-direction trips to compare" : `${Math.round(t.relative_speed * 100)}% of typical pace`}${t.slower ? " · SLOWER" : ""}`,
      t.start,
      t.slower ? "slower" : "",
    );
  for (const g of data.tracking_gaps)
    row("gaps", `${g.start.toFixed(2)}–${g.end.toFixed(2)}s`, g.start);
  const slow = d.trips.filter((t) => t.slower),
    short = d.turns.filter((t) => t.marker_status === "short");
  const feedback = [
    slow.length
      ? `${slow.length} section(s) were over 25% slower than your median in that direction. Replay them to check for pauses or intentional changes.`
      : "No substantially slower sections flagged among comparable sections.",
    d.setup.require_markers
      ? d.turns.some((t) => t.marker_status !== "not_assessed")
        ? `${short.length} of ${d.turns.filter((t) => t.marker_status !== "not_assessed").length} assessed turn(s) were clearly short of your markers. Review them against your intended route.`
        : "No visible turns could be assessed for marker reach. This is not a pass or a failure."
      : "Marker reach was not your selected goal, so it was not assessed.",
  ];
  if (!d.trips.some((t) => t.relative_speed !== null))
    feedback[0] =
      "Not enough complete sections to compare pace: at least 3 in the same direction are needed.";
  if (!d.turns.length)
    feedback.push(
      "No supported turns found. This does not mean you made no turns; inspect tracking and the selected area.",
    );
  for (const message of feedback) {
    const p = document.createElement("p");
    p.textContent = message;
    $("feedback").append(p);
  }
  for (const message of [...d.notes, ...data.warnings]) {
    const li = document.createElement("li");
    li.textContent = message;
    $("notes").append(li);
  }
  $("runtime").textContent =
    `${data.video.frames} frames · ${data.runtime_seconds.toFixed(1)}s processing`;
  history.replaceState(null, "", `?job=${encodeURIComponent(id)}`);
}
async function follow(id: string) {
  for (;;) {
    const s = await request(`/api/jobs/${id}`);
    $("progress-label").textContent =
      `${s.stage.replaceAll("_", " ")} · ${s.frames}${s.total ? ` / ${s.total}` : ""} frames`;
    const p = $<HTMLProgressElement>("progress");
    if (s.total) p.value = Math.min(99, (s.frames / s.total) * 100);
    else p.removeAttribute("value");
    if (s.stage === "error") throw new Error(s.error);
    if (s.stage === "complete") {
      show(await request(`/api/jobs/${id}/result`), id);
      return;
    }
    await new Promise((r) => setTimeout(r, 700));
  }
}
function setBusy(value: boolean) {
  busy = value;
  for (const id of [
    "file",
    "area",
    "markers",
    "reset",
    "analyze",
    "require-markers",
  ])
    $<HTMLButtonElement>(id).disabled = value;
  $("progress-panel").hidden = !value;
}
$("analyze").onclick = async () => {
  const file = $<HTMLInputElement>("file").files?.[0];
  if (!file || busy) return;
  setup.require_markers = $<HTMLInputElement>("require-markers").checked;
  if (setup.require_markers && !setup.markers) {
    showError("Set both marker positions first.");
    return;
  }
  if (!preview.videoWidth) {
    showError("Wait for the video preview to load.");
    return;
  }
  stopSelection();
  preview.pause();
  video.pause();
  $("error").hidden = true;
  setBusy(true);
  $("results").hidden = true;
  $("progress-label").textContent = "Uploading locally…";
  $<HTMLProgressElement>("progress").removeAttribute("value");
  try {
    const body = new FormData();
    body.append("file", file);
    body.append("drill", "side_to_side");
    body.append("setup", JSON.stringify(setup));
    const { id } = await request("/api/jobs", { method: "POST", body });
    history.replaceState(null, "", `?job=${encodeURIComponent(id)}`);
    await follow(id);
  } catch (e) {
    showError(e);
  } finally {
    setBusy(false);
  }
};
$("previous").onclick = () => player.step(-1);
$("next").onclick = () => player.step(1);
$<HTMLSelectElement>("speed").onchange = () =>
  (video.playbackRate = Number($<HTMLSelectElement>("speed").value));
$<HTMLInputElement>("evidence").onchange = () =>
  (player.enabled = $<HTMLInputElement>("evidence").checked);
$("export").onclick = () => {
  if (!result) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "touchline-side-to-side.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
};
const previous = new URLSearchParams(location.search).get("job");
if (previous) {
  setBusy(true);
  follow(previous)
    .catch(showError)
    .finally(() => setBusy(false));
}
