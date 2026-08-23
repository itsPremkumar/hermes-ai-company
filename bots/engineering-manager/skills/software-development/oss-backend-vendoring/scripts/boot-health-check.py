#!/usr/bin/env python3
"""
boot-health-check.py — verify a vendored Python backend package boots and serves,
without leaving any artifact inside the repo.

Run from OUTSIDE the repo (e.g. C:/tmp) so no _boot.py lands in the project tree.
Spawns `python -m <pkg>.main`, polls /health, reports the DB location and any
cwd-relative data-dir leak.

USAGE:
    python boot-health-check.py --pkg speech --proj "C:/one/Automated-Video-Generator" \
        --venv "C:/one/voicebox/.venv/Scripts/python.exe" --port 17499

Exit 0 = booted + /health 200 + no src/data leak. Non-zero = failed.
"""
import argparse, subprocess, sys, time, urllib.request, os, glob

parser = argparse.ArgumentParser()
parser.add_argument("--pkg", required=True, help="package name, e.g. speech")
parser.add_argument("--proj", required=True, help="project root (parent of src/)")
parser.add_argument("--venv", required=True, help="python interpreter with torch/etc")
parser.add_argument("--port", type=int, default=17499)
args = parser.parse_args()

src = os.path.join(args.proj, "src")
data_dir = os.path.join(args.proj, "workspace", "cache", args.pkg)
os.makedirs(data_dir, exist_ok=True)

proc = subprocess.Popen(
    [args.venv, "-m", f"{args.pkg}.main", "--host", "127.0.0.1",
     "--port", str(args.port), "--data-dir", data_dir],
    cwd=src, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

up, status = False, None
for _ in range(45):
    time.sleep(1)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/health", timeout=2) as r:
            status = r.status
            print("HEALTH:", status, r.read().decode()[:90])
            up = True
            break
    except Exception:
        pass

db_cache = glob.glob(os.path.join(data_dir, "*.db"))
db_leak = glob.glob(os.path.join(args.proj, "src", "data", "*.db"))
print("SERVER UP:", up)
print("DB in cache (good):", db_cache)
print("DB leak in src/data (BAD):", db_leak)

proc.terminate()
try:
    out, _ = proc.communicate(timeout=5)
    for line in out.splitlines()[-5:]:
        if line.strip():
            print("LOG:", line)
except Exception:
    proc.kill()

sys.exit(0 if (up and status == 200 and not db_leak) else 1)
