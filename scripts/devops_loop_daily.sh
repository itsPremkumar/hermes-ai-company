#!/usr/bin/env bash
# devops_loop_daily.sh — wrapper for the closed-loop DevOps verification system.
# Real engine: <workspace-root>/_devops_loop/loop.py  (see <workspace-root>/_devops_loop/README.md)
#
# The Hermes cron job 'devops-loop-daily' (0 9 * * *) invokes THIS script.
# It was previously missing -> job errored every run.
#
# SAFETY: wired to --dry (verify + plan only; no git commits/pushes/docker).
# This makes the job RUN (produces daily_<date>.md + backlog.json) without
# side effects. To enable real auto-remediation + push, drop the --dry flag
# AFTER reviewing the first report and confirming the blast radius is acceptable.
set -u
PY="$HOME/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
LOOP="<workspace-root>/_devops_loop/loop.py"
[ -x "$PY" ] || PY="python"
# Outer bound: never let this cron wedge the fleet on the low-RAM host.
# 540s < the 600s per-command timeout inside loop.py; script exits 124 if it trips.
timeout 540 "$PY" "$LOOP" --root C:/one --dry
