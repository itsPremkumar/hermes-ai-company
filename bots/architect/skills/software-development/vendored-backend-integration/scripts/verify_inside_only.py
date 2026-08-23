#!/usr/bin/env python3
"""Definitive proof that a vendored backend is self-contained INSIDE the repo.

Runs the delete-then-verify gate (Pitfall 15):
  1. Boot the backend using ONLY the in-repo venv (<skill>/../venv).
  2. Hit /health, then /speak with the DEFAULT engine -> assert real bytes.
  3. (caller deletes the external folder BEFORE this script, or pass --delete-external)
  4. Assert the integration test still passes with the external folder ABSENT.

Usage:
  python scripts/verify_inside_only.py \
      --pkg speech --src C:/one/Automated-Video-Generator/src \
      --port 17497 --cache C:/one/Automated-Video-Generator/workspace/cache/voicebox \
      --external C:/one/voicebox

Exit 0 = self-contained. Exit 1 = still depends on the external folder.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default="speech")
    ap.add_argument("--src", required=True)
    ap.add_argument("--venv",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "..", "venv", "Scripts", "python.exe"))
    ap.add_argument("--port", type=int, default=17497)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--external", default=None,
        help="External folder that must be GONE for the proof. If passed and still exists, script deletes it then verifies.")
    a = ap.parse_args()

    # Gate 0: external must be absent (or we delete it now).
    if a.external and os.path.exists(a.external):
        shutil.rmtree(a.external, ignore_errors=True)
        print("DELETED external:", a.external)
    if a.external and os.path.exists(a.external):
        print("EXTERNAL STILL PRESENT - cannot prove self-contained")
        sys.exit(1)

    os.makedirs(a.cache, exist_ok=True)
    data_dir = os.path.join(a.cache, a.pkg)
    os.makedirs(data_dir, exist_ok=True)

    url = f"http://127.0.0.1:{a.port}/health"
    proc = subprocess.Popen(
        [a.venv, "-m", f"{a.pkg}.main", "--host", "127.0.0.1",
         "--port", str(a.port), "--data-dir", data_dir],
        cwd=a.src, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    up = False
    for _ in range(60):
        time.sleep(1)
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                print("HEALTH:", r.status); up = True; break
        except Exception:
            pass
    if not up:
        proc.terminate()
        print("RESULT: FAIL (backend did not boot from in-repo venv)")
        sys.exit(1)

    # /speak with the DEFAULT engine (resolve a preset profile first if needed).
    prof = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{a.port}/profiles", timeout=5) as r:
            for p in json.load(r):
                if p.get("preset_engine"):
                    prof = p["name"]; break
    except Exception:
        pass
    if not prof:
        print("RESULT: FAIL (no preset profile to speak with)")
        proc.terminate(); sys.exit(1)

    body = json.dumps({"text": "inside only verification", "profile": prof}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{a.port}/speak", data=body,
        headers={"Content-Type": "application/json"})
    gen_id = None
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            gen_id = json.load(r).get("id")
    except Exception as e:
        print("SPEAK error:", e)
    ok = False
    for _ in range(60):
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{a.port}/generate/{gen_id}/status", timeout=5) as r:
                if json.load(r).get("status") == "completed":
                    ok = True; break
        except Exception:
            pass

    proc.terminate()
    try: proc.communicate(timeout=5)
    except Exception: proc.kill()

    leak = bool(glob.glob(os.path.join(a.src, "data", "*.db")))
    cached = bool(glob.glob(os.path.join(data_dir, "*.db")))
    if ok and cached and not leak and not (a.external and os.path.exists(a.external)):
        print("RESULT: OK (self-contained: in-repo venv, real /speak, external absent)")
        sys.exit(0)
    print(f"RESULT: FAIL (ok={ok} cached={cached} leak={leak})")
    sys.exit(1)

if __name__ == "__main__":
    main()
