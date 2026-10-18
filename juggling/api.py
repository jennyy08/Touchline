"""Local single-job HTTP adapter. Analysis itself does not know about HTTP."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import atexit
import shutil
import logging
import tempfile
import threading
import uuid
from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .pipeline import analyze
from .config import Config
from .dribbling import DrillSetup

ROOT = Path(__file__).resolve().parents[1]
JOB_ROOT = Path(tempfile.mkdtemp(prefix="juggle-lab-"))
app = FastAPI(title="Touchline · local juggling lab")
executor = ThreadPoolExecutor(max_workers=1)
lock = threading.Lock()
jobs = {}
busy = False
MAX_BYTES = 250 * 1024 * 1024


def cleanup(folder=JOB_ROOT):
    executor.shutdown(wait=True)
    shutil.rmtree(folder, ignore_errors=True)


atexit.register(cleanup)


def run_job(job_id, source, drill_setup=None):
    global busy
    def progress(**state):
        with lock:
            jobs[job_id].update(state)
    try:
        options = {"drill_setup": drill_setup} if drill_setup is not None else {}
        analyze(source, JOB_ROOT / job_id, ROOT / "models", progress=progress, **options)
        progress(stage="complete")
    except Exception as exc:
        logging.exception("Analysis failed")
        progress(stage="error", error=str(exc) if isinstance(exc, ValueError) else
                 "Analysis failed unexpectedly. Check the server terminal for details; try a shorter MP4.")
    finally:
        with lock:
            busy = False


def claim_analysis():
    global busy
    with lock:
        if busy:
            return False
        busy = True
        return True


def release_analysis():
    global busy
    with lock:
        busy = False


@app.post("/api/jobs", status_code=202)
async def create_job(file: UploadFile = File(...), drill: str = Form("juggling"), setup: str = Form("{}")):
    global busy
    if drill not in ("juggling", "side_to_side"):
        await file.close()
        raise HTTPException(422, "Unknown drill.")
    drill_setup = None
    if drill == "side_to_side":
        try:
            drill_setup = DrillSetup.model_validate_json(setup)
        except ValueError as exc:
            await file.close()
            raise HTTPException(422, f"Invalid practice setup: {exc}")
    if not claim_analysis():
        raise HTTPException(409, "An upload or live session is already running. Wait for it to finish.")
    job_id = uuid.uuid4().hex
    folder = JOB_ROOT / job_id
    folder.mkdir()
    source = folder / "source.video"
    size = 0
    try:
        with source.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Video exceeds 250 MB. Trim or compress it and retry.")
                target.write(chunk)
        if not size:
            raise HTTPException(400, "The uploaded file is empty.")
        with lock:
            jobs[job_id] = {"id": job_id, "name": file.filename or "Video", "stage": "queued", "frames": 0, "total": 0}
        executor.submit(run_job, job_id, source, drill_setup)
    except BaseException:
        source.unlink(missing_ok=True)
        with lock:
            busy = False
        raise
    finally:
        await file.close()
    return {"id": job_id}


def get_job(job_id):
    with lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found. Jobs are temporary; upload again after a server restart.")
        return dict(job)


@app.get("/api/jobs/{job_id}")
def status(job_id: str):
    return get_job(job_id)


@app.get("/api/jobs/{job_id}/result")
def result(job_id: str):
    if get_job(job_id)["stage"] != "complete":
        raise HTTPException(409, "The analysis is not complete.")
    return json.loads((JOB_ROOT / job_id / "result.json").read_text())


@app.get("/api/jobs/{job_id}/video")
def video(job_id: str):
    if get_job(job_id)["stage"] != "complete":
        raise HTTPException(409, "Playback is available after analysis completes.")
    return FileResponse(JOB_ROOT / job_id / "playback.mp4", media_type="video/mp4")


@app.get("/api/health")
def health():
    return {"ok": True, "models_ready": all((ROOT / "models" / name).exists()
             for name in (Config().detector, Config().pose_model))}


from .live_api import make_router
app.include_router(make_router(claim_analysis, release_analysis, executor, ROOT / "models"))


if (ROOT / "frontend/dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "frontend/dist", html=True), name="frontend")
