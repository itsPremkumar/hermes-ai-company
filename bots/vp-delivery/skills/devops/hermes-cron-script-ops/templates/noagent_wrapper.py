#!/usr/bin/env python3
"""
noagent_wrapper.py — KNOWN-GOOD template for a Hermes `no_agent` cron script.

Why this shape (see skill 'hermes-cron-script-ops'):
  * The cron sandbox has NO /bin/bash, so the entrypoint MUST be .py and is
    executed via the Hermes venv Python (sys.executable inherits the venv).
  * ANY non-zero exit is flagged "error" by the scheduler, even when the job
    ran fine. So we return 0 when the run COMPLETED and wrote its artifact,
    reserving 1/2 for genuine crashes.
  * Keep it read-only (--dry) by default; flip to live only after review.

Replace ENGINE_PATH / ARTIFACT_PATH / ENGINE_ARGS for your real engine.
"""
import datetime
import glob
import os
import subprocess
import sys

ENGINE_PATH = r"C:/path/to/your/engine.py"      # the real work script
ARTIFACT_DIR = r"C:/path/to/output_dir"           # where the report lands
ENGINE_ARGS = ["--root", r"C:/", "--dry"]         # pass-through args


def main():
    if not os.path.exists(ENGINE_PATH):
        print(f"ERROR: engine not found at {ENGINE_PATH}", file=sys.stderr)
        return 2
    try:
        rc = subprocess.call([sys.executable, ENGINE_PATH, *ENGINE_ARGS])
    except Exception as e:  # genuine crash -> real error
        print(f"ERROR: engine crashed: {e}", file=sys.stderr)
        return 1

    # Success = the run completed and produced an output artifact. The
    # engine's own pass/fail (e.g. rc==1 when items fail) is NOT a scheduler
    # failure; that data lives in the artifact, not the exit code.
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    report = os.path.join(ARTIFACT_DIR, f"daily_{today}.md")
    if os.path.exists(report) or glob.glob(os.path.join(ARTIFACT_DIR, "daily_*.md")):
        print(f"OK: engine completed (exit={rc}); report at {report}")
        return 0
    print("ERROR: engine finished but no report was written", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
