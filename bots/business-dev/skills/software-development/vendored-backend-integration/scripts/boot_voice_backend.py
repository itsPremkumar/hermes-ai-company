#!/usr/bin/env python3
"""Re-runnable boot/health/leak probe for a vendored FastAPI backend.

Usage:
  python scripts/boot_voice_backend.py \
      --pkg speech --src C:/one/Automated-Video-Generator/src \
      --port 17497 --cache C:/one/Automated-Video-Generator/workspace/cache/voicebox
(--venv defaults to <skill>/../venv/Scripts/python.exe — the in-repo venv;
 pass --venv explicitly only to test an external interpreter.)

Asserts: /health -> 200, DB written to --cache (NOT to <src>/<pkg>/../data),
and that nothing leaks into the repo's src/data. Prints LEAK/OK lines so a
CI step can grep for them.
"""
import argparse
import glob
import os
import subprocess
import sys
import time
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default="speech")
    ap.add_argument("--src", required=True)
    ap.add_argument("--venv", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "venv", "Scripts", "python.exe"))
    ap.add_argument("--port", type=int, default=17497)
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()

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
    for _ in range(40):
        time.sleep(1)
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                print("HEALTH:", r.status)
                up = True
                break
        except Exception:
            pass
    print("SERVER UP:", up)

    repo_data = os.path.join(a.src, "data")  # should NOT exist
    leak = bool(glob.glob(os.path.join(repo_data, "*.db")))
    cached = bool(glob.glob(os.path.join(data_dir, "*.db")))
    print("DB in cache:", cached)
    print("LEAK src/data:", leak)

    proc.terminate()
    try:
        proc.communicate(timeout=5)
    except Exception:
        proc.kill()

    if up and cached and not leak:
        print("RESULT: OK")
        sys.exit(0)
    print("RESULT: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
