#!/usr/bin/env python3
"""Pending-task intake for the production line.
File format (%LOCALAPPDATA%/hermes/pending-task.txt):
  line1: assignee profile
  rest:  task text (title + body)
adaptive_mode.py decides goal vs plain automatically."""
import os, subprocess, sys

HERMES = os.path.join(os.environ.get("LOCALAPPDATA",""), "hermes")
TF = os.path.join(HERMES, "pending-task.txt")
AM = os.path.join(HERMES, "scripts", "adaptive_mode.py")

if not os.path.isfile(TF):
    sys.exit(0)
lines = open(TF, encoding="utf-8").read().splitlines()
if len(lines) < 2:
    sys.exit(0)
assignee, text = lines[0].strip(), " ".join(lines[1:]).strip()
r = subprocess.run(["python", AM, "create", assignee, "--", text],
                   capture_output=True, text=True, timeout=120)
ok = "Created" in (r.stdout or "")
if ok:
    os.rename(TF, TF + ".done")
sys.exit(0)
