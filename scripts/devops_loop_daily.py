#!/usr/bin/env python3
"""
devops_loop_daily.py — entrypoint for the Hermes cron job 'devops-loop-daily'.

The real engine is C:/one/_devops_loop/loop.py (see C:/one/_devops_loop/README.md).
This thin wrapper exists because the Hermes `no_agent` cron runner executes
`.sh` scripts via /bin/bash, which is NOT present in the cron sandbox (only the
interactive terminal has bash). `.py` scripts run under the Hermes venv Python,
which is available in the cron worker — so we use that.

SAFETY: runs loop.py in --dry mode (verify + plan only; no git commits/pushes/
docker). It still produces daily_<date>.md + backlog.json. Drop --dry AFTER
reviewing the first report and accepting the blast radius (auto-push to remotes).
"""
import datetime
import glob
import os
import subprocess
import sys

LOOP = r"C:/one/_devops_loop/loop.py"
ROOT = r"C:/one"
LOOP_DIR = r"C:/one/_devops_loop"


def main():
    if not os.path.exists(LOOP):
        print(f"ERROR: DevOps engine not found at {LOOP}", file=sys.stderr)
        return 2
    # Run with the same Python the cron worker uses (Hermes venv).
    cmd = [sys.executable, LOOP, "--root", ROOT, "--dry"]
    try:
        rc = subprocess.call(cmd)
    except Exception as e:  # genuine crash -> real error
        print(f"ERROR: DevOps engine crashed: {e}", file=sys.stderr)
        return 1

    # loop.py exits 1 when repos FAIL (by design) — that is NOT a scheduler
    # failure; the real pass/fail data lives in daily_<date>.md. Report success
    # if the run produced a report, else a genuine failure.
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    report = os.path.join(LOOP_DIR, f"daily_{today}.md")
    if os.path.exists(report) or glob.glob(os.path.join(LOOP_DIR, "daily_*.md")):
        print(f"OK: DevOps loop completed (engine exit={rc}); report at {report}")
        return 0
    print("ERROR: DevOps loop finished but no daily report was written", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
