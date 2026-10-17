import layout from "./live-layout.html?raw";
import "./style.css";
import "./live.css";
import { framePacket, FrameFlight } from "./live-protocol";

document.querySelector("#app")!.innerHTML = layout;
const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const video = el<HTMLVideoElement>("camera");
const overlay = el<HTMLCanvasElement>("live-overlay");
const toggle = el<HTMLInputElement>("live-show-overlay");
const start = el<HTMLButtonElement>("live-start");
const stop = el<HTMLButtonElement>("live-stop");
const capture = document.createElement("canvas");
const flight = new FrameFlight();
let stream: MediaStream | null = null;
let socket: WebSocket | null = null;
let active = false, stopping = false, generation = 0;
let origin = 0, sentAt = 0, lastReply = 0, timer = 0;
let lastFrameTime = -1;
let watchdog = 0;
try { toggle.checked = localStorage.getItem("touchline:live-overlay") !== "false"; } catch {}
function view() {
  overlay.hidden = !toggle.checked || !active;
  video.hidden = toggle.checked && active;
  el("view-label").textContent = toggle.checked && active ? "Last analyzed frame" : "Live preview";
}
toggle.onchange = () => {
  try { localStorage.setItem("touchline:live-overlay", String(toggle.checked)); } catch {}
  view();
};
function fail(message: string) {
  el("live-error").textContent = message;
  el("live-error").hidden = false;
}
function cleanup() {
  ++generation; // Invalidate permission promises and replies from the old session.
  active = false;
  clearTimeout(timer); clearTimeout(watchdog);
  stream?.getTracks().forEach(t => t.stop());
  stream = null; video.srcObject = null;
  flight.complete();
  start.disabled = false; stop.disabled = true;
  el("live-state").textContent = stopping ? "Session ended" : "Ready to restart";
  el("camera-placeholder").hidden = false;
  view();
}
function sendStop() {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({type: "stop"}));
    watchdog = window.setTimeout(() => { socket?.close(); cleanup(); fail("Stopping timed out. Start a new session."); }, 10000);
  }
}
async function captureFrame(token: number) {
  if (!active || stopping || token !== generation || !socket || socket.readyState !== WebSocket.OPEN) return;
  if (video.readyState < 2 || video.currentTime === lastFrameTime) {
    timer = window.setTimeout(() => void captureFrame(token), 15); return;
  }
  if (!flight.begin()) return;
  try {
    const scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
    capture.width = Math.round(video.videoWidth * scale);
    capture.height = Math.round(video.videoHeight * scale);
    capture.getContext("2d")!.drawImage(video, 0, 0, capture.width, capture.height);
    lastFrameTime = video.currentTime;
    sentAt = performance.now();
    const blob = await new Promise<Blob>((resolve, reject) => capture.toBlob(b => b ? resolve(b) : reject(new Error("Camera frame could not be encoded.")), "image/jpeg", .85));
    const packet = framePacket((sentAt - origin) / 1000, await blob.arrayBuffer());
    if (token !== generation || socket?.readyState !== WebSocket.OPEN) { flight.complete(); return; }
    socket.send(packet);
    watchdog = window.setTimeout(() => { fail("Analysis timed out. Check the server and restart."); socket?.close(); cleanup(); }, 15000);
  } catch (error) { fail(String(error)); socket?.close(); cleanup(); }
}
type Contact = {time: number; status: string; reason: string};
function events(rows: Contact[]) {
  const list = el("live-events");
  if (rows.length && !list.querySelector("li[data-event]")) list.replaceChildren();
  for (const e of rows) {
    const item = document.createElement("li");
    item.dataset.event = "true";
    item.className = e.status === "counted" ? "live-counted" : "live-review";
    item.textContent = `${e.time.toFixed(2)}s · ${e.status === "counted" ? "Estimated touch" : "Needs review"} · ${e.reason.replaceAll("_", " ")}`;
    list.prepend(item);
    while (list.children.length > 8) list.lastElementChild?.remove();
  }
}
function draw(sample: {status: string; box: number[] | null; pose: Record<string, number[]>}) {
  overlay.width = capture.width; overlay.height = capture.height;
  const ctx = overlay.getContext("2d")!;
  ctx.drawImage(capture, 0, 0);
  ctx.lineWidth = 2;
  ctx.strokeStyle = sample.status === "observed" ? "#a7f35b" : "#ffc567";
  ctx.setLineDash(sample.status === "predicted" ? [6, 5] : []);
  if (sample.box) { const [x,y,x2,y2] = sample.box; ctx.strokeRect(x,y,x2-x,y2-y); }
  ctx.setLineDash([]); ctx.fillStyle = "#73dfe0";
  for (const [name, [x,y]] of Object.entries(sample.pose)) {
    if (name.includes("wrist")) continue;
    ctx.beginPath(); ctx.arc(x,y,3,0,2*Math.PI); ctx.fill();
  }
}
start.onclick = async () => {
  const token = ++generation;
  socket = null;
  start.disabled = true; stop.disabled = false; stopping = false;
  el("live-error").hidden = true;
  el("live-count").textContent = "0";
  el("live-events").replaceChildren();
  el("live-state").textContent = "Requesting camera permission…";
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access needs localhost in a supported browser.");
    const acquired = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},frameRate:{ideal:30,max:30}},audio:false});
    if (token !== generation || stopping) { acquired.getTracks().forEach(t=>t.stop()); return; }
    stream = acquired; video.srcObject = stream; await video.play();
    if (token !== generation || stopping) return;
    el("camera-placeholder").hidden = true;
    el("live-state").textContent = "Loading local models…";
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/live`);
    socket = ws;
    watchdog = window.setTimeout(() => { fail("Models took too long to load. Check the server."); ws.close(); cleanup(); }, 60000);
    ws.onopen = () => ws.send(JSON.stringify({type:"start",feet:"off"}));
    ws.onmessage = (message) => {
      if (token !== generation) return;
      const reply = JSON.parse(message.data);
      if (reply.type === "ready") {
        clearTimeout(watchdog); active = true; origin = performance.now(); lastReply = 0; lastFrameTime = -1;
        view();
        if (stopping) sendStop(); else void captureFrame(token);
      } else if (reply.type === "frame") {
        clearTimeout(watchdog); flight.complete();
        const now = performance.now();
        const fps = lastReply ? 1000 / (now-lastReply) : 0; lastReply = now;
        el("live-count").textContent = String(reply.count);
        el("live-state").textContent = reply.sample.status === "lost" ? "Tracking lost · hidden touches may be missed" : reply.sample.status === "predicted" ? "Ball predicted · waiting for observation" : reply.floor_y === null ? "Finding floor · contacts may need review" : "Ball observed";
        el("live-metrics").textContent = `${fps.toFixed(1)} processed fps · ${Math.round(now-sentAt)} ms round trip`;
        draw(reply.sample); events(reply.new_events);
        if (stopping) sendStop();
        else timer = window.setTimeout(() => void captureFrame(token), Math.max(0, 1000/30-(now-sentAt)));
      } else if (reply.type === "stopped") {
        el("live-count").textContent = String(reply.count); events(reply.new_events);
        el("live-state").textContent = "Session ended"; cleanup();
      } else if (reply.type === "error") { fail(reply.message); ws.close(); cleanup(); }
    };
    ws.onerror = () => { if (token === generation) fail("Could not connect to local analysis. Check that the server is running."); };
    ws.onclose = () => { if (token === generation) { if (!stopping && active) fail("Connection closed. Start a new session."); cleanup(); } };
  } catch (error) { if (token===generation) { fail(error instanceof Error ? error.message : String(error)); cleanup(); } }
};
stop.onclick = () => {
  stopping = true; stop.disabled = true; clearTimeout(timer);
  el("live-state").textContent = "Finishing the last contact…";
  stream?.getTracks().forEach(t=>t.stop());
  if (!socket || socket.readyState !== WebSocket.OPEN) { ++generation; socket?.close(); cleanup(); }
  else if (active && !flight.busy) sendStop();
};
window.addEventListener("pagehide", () => { ++generation; socket?.close(); cleanup(); });
