import layout from "./dribbling-layout.html?raw";
import "./dribbling.css";
import { AnnotatedPlayer } from "./player";
import type { Setup, DribbleResult } from "./dribbling-types";
import { SessionStory } from "./session-story";
import "./session-story.css";
const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
document.querySelector("#app")!.innerHTML = layout;
const preview = $<HTMLVideoElement>("preview"),
  video = $<HTMLVideoElement>("video");
const canvas = $<HTMLCanvasElement>("setup-canvas");
const player = new AnnotatedPlayer(video, $("overlay"), $("tracking-status"));
const story = new SessionStory(video, (time) => {
  player.seek(time);
});
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
  $("upload-panel").hidden = false;
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
  const [timing, ...description] = content.split(" · ");
  const title = document.createElement("span");
  title.className = "event-time";
  title.textContent = timing;
  const detail = document.createElement("span");
  detail.className = "event-description";
  detail.textContent = description.join(" · ");
  b.append(title, detail);
  b.className = cls;
  b.onclick = () => {
    story.selectAt(time);
    document
      .querySelectorAll(".event-list button.selected")
      .forEach((el) => el.classList.remove("selected"));
    b.classList.add("selected");
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
  story.load(data);
  player.load(data, `/api/jobs/${id}/video`);
  $("results").hidden = false;
  $("upload-panel").hidden = true;
  $("turns-tab-count").textContent = String(d.turns.length);
  $("pace-tab-count").textContent = String(d.trips.length);
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
  $("turn-timeline").replaceChildren();
  for (const t of d.turns) {
    const inferred = t.evidence === "inferred_edge_return";
    const interval = t.time_interval;
    const marker = document.createElement("button");
    marker.className = `${inferred ? "inferred" : "visible"} ${t.side}`;
    marker.dataset.turnId = t.id;
    marker.style.left = `${Math.min(99, Math.max(1, ((interval ? (interval.start + interval.end) / 2 : t.time) / data.video.duration) * 100))}%`;
    if (interval)
      marker.style.width = `${((interval.end - interval.start) / data.video.duration) * 100}%`;
    marker.setAttribute(
      "aria-label",
      `${t.side} turn at ${t.time.toFixed(2)} seconds${inferred ? ", inferred" : ""}`,
    );
    marker.title = marker.getAttribute("aria-label")!;
    marker.onclick = () => {
      activateTab("turns");
      const index = d.turns.indexOf(t);
      const item = $("turns").children[index] as HTMLButtonElement;
      item.click();
      item.scrollIntoView({ block: "nearest" });
      $("turn-timeline")
        .querySelectorAll("button")
        .forEach((el) => el.setAttribute("aria-pressed", "false"));
      marker.setAttribute("aria-pressed", "true");
    };
    $("turn-timeline").append(marker);
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
      ? `${slow.length === 1 ? "One section was" : `${slow.length} sections were`} slower than your usual pace. Replay ${slow[0].start.toFixed(1)}–${slow[0].end.toFixed(1)}s and check whether the change was intentional.`
      : "No clear pace dips in the sections we could compare.",
    d.setup.require_markers
      ? d.turns.some((t) => t.marker_status !== "not_assessed")
        ? short.length
          ? `The ball turned before the marker ${short.length} time(s). Take a look if reaching it was your goal.`
          : `None of the assessed turns was clearly short. Close calls and off-camera turns still need your own judgment.`
        : "The view wasn’t clear enough to judge marker reach. You can still review the turns."
      : "Marker reach was not your selected goal, so it was not assessed.",
  ];
  if (!d.trips.some((t) => t.relative_speed !== null))
    feedback[0] =
      "A few more clear sections will help us compare your pace. Keep your full route in view next time.";
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
    "new-upload",
    "apply-positions",
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
$<HTMLInputElement>("evidence").onchange = () => {
  player.enabled = $<HTMLInputElement>("evidence").checked;
  $("guides").hidden = !player.enabled;
};
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

$("new-upload").onclick = () => {
  if (!busy) $<HTMLInputElement>("file").click();
};
function activateTab(tab: "turns" | "pace") {
  for (const name of ["turns", "pace"]) {
    const selected = tab === name;
    $(name + "-panel").hidden = !selected;
    $(name + "-tab").setAttribute("aria-selected", String(selected));
    $(name + "-tab").tabIndex = selected ? 0 : -1;
  }
}
for (const name of ["turns", "pace"] as const) {
  $(name + "-tab").onclick = () => activateTab(name);
  $(name + "-tab").onkeydown = (e) => {
    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      const next =
        e.key === "Home"
          ? "turns"
          : e.key === "End"
            ? "pace"
            : name === "turns"
              ? "pace"
              : "turns";
      activateTab(next);
      $(next + "-tab").focus();
    }
  };
}

$("apply-positions").onclick = () => {
  const ids = [
    "area-left",
    "area-top",
    "area-right",
    "area-bottom",
    "marker-left",
    "marker-right",
  ];
  const raw = ids.map((id) => $<HTMLInputElement>(id).value);
  const values = raw.map((v) => Number(v) / 100);
  const [left, top, right, bottom, ml, mr] = values;
  if (
    raw.some((v) => v.trim() === "") ||
    values.some((v) => !Number.isFinite(v) || v < 0 || v > 1) ||
    right - left < 0.1 ||
    bottom - top < 0.1 ||
    ml < left ||
    mr > right ||
    mr - ml < 0.1
  ) {
    showError(
      "Use 0–100%, with an area and marker spacing of at least 10%. Markers must be inside the area.",
    );
    return;
  }
  setup.roi = [left, top, right, bottom];
  setup.markers = [ml, mr];
  stopSelection();
  drawGuides(canvas, setup);
  $("error").hidden = true;
  $("setup-status").textContent = "Area and marker positions applied.";
};
