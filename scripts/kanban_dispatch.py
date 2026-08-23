#!/usr/bin/env python3
"""Kanban single-flow dispatcher v3 (pure python - WSL-free for gateway cron).
Releases ONE blocked card per tick only when nothing is running. Silent unless failing."""
import json, os, sqlite3, subprocess, sys

HERMES = os.path.join(os.environ.get("LOCALAPPDATA",""), "hermes")
DB = os.path.join(HERMES, "kanban", "boards", "it-company-ops", "kanban.db")

def q(sql):
    c = sqlite3.connect(DB, timeout=15)
    r = c.execute(sql).fetchall(); c.close(); return r

try:
    running = q("select count(*) from tasks where status='running'")[0][0]
    if running >= 1:
        sys.exit(0)                       # a build is in flight - stay quiet
    ready = q("select count(*) from tasks where status='ready'")[0][0]
    if ready == 0:
        nxt = q("select id from tasks where status='blocked' order by priority desc, created_at asc limit 1")
        if not nxt:
            sys.exit(0)                   # queue empty
        tid = nxt[0][0]
        subprocess.run(["hermes","kanban","promote",tid,"hourly line: single-card release","--force"],
                       capture_output=True, text=True, timeout=120)
    out = subprocess.run(["hermes","kanban","dispatch","--max","1","--json"],
                         capture_output=True, text=True, timeout=300)
    txt = out.stdout or ""
    if out.returncode != 0:
        print("KANBAN DISPATCH FAILED:", (out.stderr or "")[-200:])
    elif '"error"' in txt or "spawn_failed" in txt:
        for line in txt.splitlines():
            if '"error"' in line or "spawn_failed" in line: print(line.strip()[:160])
except Exception as e:
    print(f"DISPATCHER ERROR: {e}")
sys.exit(0)
