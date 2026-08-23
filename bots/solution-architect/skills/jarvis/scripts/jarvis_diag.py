#!/usr/bin/env python3
r"""Jarvis escalation triage - instant diagnosis of 'ESCALATION with no dispatch'.

Run with the jarvis package importable (PYTHONPATH points at the canonical repo):
    PYTHONPATH="C:/Users/PREM KUMAR/prems-jarvis-hermes" python <skill_dir>/scripts/jarvis_diag.py <jarvis_state.db>

Prints per task: status / priority / attempts:max_attempts / toolsets / verification,
and the result of Dispatcher.ready_task() - the single call that decides whether the
cycle will dispatch. If ready_task() is None while open/doing tasks exist, the cause is
almost always exhausted attempts (Cause 3): a task dispatched max_attempts times that
still failed its verification gate (e.g. landing page built but never deployed, so the
"deployed URL returns HTTP 200" check can't pass). See references/escalation_triage.md
for the full decision tree and the correct OPERATOR-side fix (do NOT just reset attempts).

API NOTE (verified against the live jarvis package): Dispatcher takes ONE positional
arg (the State instance), NOT (state, defaults). Keep this module docstring RAW
(r"""...""") and use forward-slash or quoted paths - a C:\Users\... path inside a plain
(non-raw) string raises unicodeescape at import time.
"""
import sys
from jarvis.core.state import State, TaskStatus
from jarvis.core.dispatcher import Dispatcher


def _safe(fn, default="n/a"):
    try:
        return fn()
    except Exception:
        return default


def main():
    if len(sys.argv) < 2:
        print("usage: jarvis_diag.py <path-to-jarvis_state.db>")
        return 2
    db_path = sys.argv[1]
    s = State(db_path)
    print(f"DB: {db_path}")

    # Best-effort cycle / stuck counters (accessor names vary by version).
    cycle = _safe(lambda: s.get_cycle())
    stuck = _safe(lambda: s._get_meta("stuck"))
    print(f"cycle={cycle}  stuck={stuck}")

    print("-" * 78)
    blocked = False
    for t in s.list_tasks():
        note = ""
        if t.status == TaskStatus.OPEN and t.attempts >= t.max_attempts:
            note = "  <== EXHAUSTED (open but attempts>=max: never dispatched)"
            blocked = True
        elif t.status == TaskStatus.DOING:
            note = "  <== WEDGED DOING (recover resets after stale_doing_minutes)"
            blocked = True
        print(
            f"{t.id} | {t.status.name:6} | prio={int(t.priority)} | "
            f"att={t.attempts}/{t.max_attempts} | tools={t.toolsets}"
        )
        print(f"         sub : {t.sub_goal}")
        print(f"         ver : {t.verification}{note}")
    print("-" * 78)

    disp = Dispatcher(s)  # ONE arg: the State
    try:
        rt = disp.ready_task()
        print(f"ready_task() -> {rt.id if rt else None}")
    except Exception as e:
        print(f"ready_task() RAISED {type(e).__name__}: {e}")
        rt = None

    if blocked and rt is None:
        print("DIAGNOSIS: open/doing tasks exist but ready_task() is None -> ESCALATION deadlock.")
        print("  Cause 3 (exhausted attempts) is most likely. See references/escalation_triage.md")
        print("  for the correct fix. Do NOT just reset attempts/max_attempts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
