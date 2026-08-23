#!/usr/bin/env python
"""External liveness watchdog for a Hermes-native orchestrator.

Runs via Windows Task Scheduler (INDEPENDENT of Hermes), so it survives Hermes
dying. It detects whether a cycle ran recently and exits:
    0 = healthy
    2 = stale (alert the operator)
It does NOT relaunch Hermes (cannot reliably start a GUI app from session 0);
detecting the gap and reporting it IS the recovery action. Reopening Hermes /
re-running the cron is the human-or-scheduler step.

Register:
  schtasks /create /tn "JarvisWatchdog" /tr "python <dir>\watchdog.py --db <dir>\jarvis_state.db --max-age-min 40" /sc minute /mo 10 /f
"""
import os
import sys
import time
import argparse


def check_stale(db_path: str, max_age_min: int) -> tuple:
    log_path = os.path.join(os.path.dirname(os.path.abspath(db_path)), "jarvis.log")
    if not os.path.exists(log_path):
        return True, "no event log (orchestrator may never have run)"
    try:
        from jarvis.core.logging import last_cycle_ts
        last = last_cycle_ts(log_path)
    except Exception:
        last = 0.0
    if last <= 0:
        return True, "no cycle event recorded yet"
    age = time.time() - last
    if age > max_age_min * 60:
        return True, f"last cycle {age / 60:.1f}m ago (> {max_age_min}m)"
    return False, f"healthy; last cycle {age / 60:.1f}m ago"


def main():
    p = argparse.ArgumentParser(description="External orchestrator liveness watchdog")
    p.add_argument("--db", default="jarvis_state.db")
    p.add_argument("--max-age-min", type=int, default=40)
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()
    stale, msg = check_stale(a.db, a.max_age_min)
    if not a.quiet:
        print(f"[{'STALE' if stale else 'OK'}] {msg}")
    return 2 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
