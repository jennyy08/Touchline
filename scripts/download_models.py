"""Explicit one-time download. Analysis never downloads weights implicitly."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import urllib.request
import ssl
import shutil
import zipfile
import certifi

p = argparse.ArgumentParser()
p.add_argument("--include-small", action="store_true", help="Compatibility flag: yolo11s is now always included")
a = p.parse_args()
root = Path(__file__).resolve().parents[1] / "models"
root.mkdir(exist_ok=True)
context = ssl.create_default_context(cafile=certifi.where())
manifest = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {}


def fetch(url, target):
    print(f"Downloading {target.name} from {url}", flush=True)
    partial = target.with_suffix(".partial")
    try:
        with urllib.request.urlopen(url, context=context) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


for name in ["yolo11n.pt", "yolo11n-pose.pt", "yolo11s.pt"]:
    url = f"https://github.com/ultralytics/assets/releases/download/v8.3.0/{name}"
    target = root / name
    if not target.exists():
        fetch(url, target)
    manifest[name] = {"url": url, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "license": "AGPL-3.0"}

# Heel/toe landmarks: official MMPose RTMPose-x Halpe-26 ONNX export (zip contains end2end.onnx).
FEET = "rtmpose-x-halpe26.onnx"
FEET_URL = ("https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/"
            "rtmpose-x_simcc-body7_pt-body7-halpe26_700e-384x288-7fb6e239_20230606.zip")
FEET_ZIP_SHA256 = "0c33d9ba030e7011686e6a7f48fd85df383378216f2f5765ae389c1828685e68"
target = root / FEET
if not target.exists():
    archive = root / "rtmpose-x-halpe26.zip"
    fetch(FEET_URL, archive)
    try:
        data = archive.read_bytes()
        if hashlib.sha256(data).hexdigest() != FEET_ZIP_SHA256:
            raise SystemExit(f"Unexpected SHA-256 for {FEET_URL}; refusing to install it.")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            member = next(n for n in z.namelist() if n.endswith("end2end.onnx"))
            target.write_bytes(z.read(member))
    finally:
        archive.unlink(missing_ok=True)
manifest[FEET] = {"url": FEET_URL, "zip_sha256": FEET_ZIP_SHA256,
                  "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "license": "Apache-2.0 (MMPose release; trained on public pose datasets with their own terms)"}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Models ready. See models/manifest.json for sources and SHA-256 hashes.")
