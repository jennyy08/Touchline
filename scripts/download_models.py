"""Explicit one-time download. Analysis never downloads weights implicitly."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
import ssl
import shutil
import certifi

p = argparse.ArgumentParser()
p.add_argument("--include-small", action="store_true", help="Compatibility flag: yolo11s is now always included")
a = p.parse_args()
root = Path(__file__).resolve().parents[1] / "models"
root.mkdir(exist_ok=True)
names = ["yolo11n.pt", "yolo11n-pose.pt", "yolo11s.pt"]
manifest = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {}
for name in names:
    url = f"https://github.com/ultralytics/assets/releases/download/v8.3.0/{name}"
    target = root / name
    if not target.exists():
        print(f"Downloading {name} from {url}", flush=True)
        partial = target.with_suffix(".partial")
        try:
            with urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where())) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    manifest[name] = {"url": url, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "license": "AGPL-3.0"}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Models ready. See models/manifest.json for sources and SHA-256 hashes.")
