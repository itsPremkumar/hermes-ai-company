#!/usr/bin/env python3
"""
reactivate_goals.py — flip every Hermes standing goal to `active`.

Use case: user pastes "/goal show" / "turn all my goals on" into a non-session
channel (coding-agent, cron, gateway). The goals live in $HERMES_HOME/state.db
under state_meta key `goal:<session_id>`. Flipping status to active makes them
run the next time Hermes opens in that session; to run them *now* autonomously,
also launch delegate_task background workers with the full goal spec.

Safe: goes through hermes_cli.goals (load_goal/save_goal) so serialization
invariants are preserved — never hand-edits the JSON.

Usage:
    HERMES_HOME=/path/to/hermes python reactivate_goals.py
    python reactivate_goals.py --hermes-home C:\Users\PREM KUMAR\AppData\Local\hermes
    python reactivate_goals.py --only 20260713_185031_d600ab 20260628_203254_a7d08b

Requires the hermes-agent repo on PYTHONPATH (the dir containing hermes_cli/).
"""
import argparse
import json
import os
import sqlite3
import sys

# Add the hermes-agent checkout to the path if invoked from elsewhere.
_HERE = os.path.dirname(os.path.abspath(__file__))
# skill layout: <skills>/<category>/<name>/scripts/reactivate_goals.py
# repo layout:   <hermes-agent>/hermes_cli/goals.py  -> go up 5 dirs.
for _candidate in (
    os.path.join(_HERE, "..", "..", "..", "..", ".."),  # hermes-agent root
    os.environ.get("HERMES_AGENT_ROOT", ""),
):
    _candidate = os.path.abspath(_candidate)
    if os.path.isdir(os.path.join(_candidate, "hermes_cli")):
        sys.path.insert(0, _candidate)
        break


def main() -> int:
    ap = argparse.ArgumentParser(description="Reactivate Hermes /goal rows.")
    ap.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME"),
                    help="Profile HERMES_HOME (defaults to $HERMES_HOME).")
    ap.add_argument("--only", nargs="*", default=None,
                    help="Restrict to these session ids (suffix of goal:<sid>).")
    args = ap.parse_args()

    home = args.hermes_home
    if not home:
        try:
            from hermes_constants import get_hermes_home
            home = str(get_hermes_home())
        except Exception:
            home = os.path.expanduser("~/.hermes")
    os.environ["HERMES_HOME"] = home

    try:
        from hermes_cli.goals import load_goal, save_goal
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: cannot import hermes_cli.goals: {exc}", file=sys.stderr)
        return 2

    # Read the DB directly only to enumerate rows cheaply (no live session needed).
    db_path = os.path.join(home, "state.db")
    if not os.path.exists(db_path):
        print(f"ERROR: no state.db at {db_path}", file=sys.stderr)
        return 2
    con = sqlite3.connect(db_path)
    keys = [r[0] for r in con.execute(
        "SELECT key FROM state_meta WHERE key LIKE 'goal:%'")]
    con.close()

    only = set(args.only or [])
    changed = 0
    for key in keys:
        sid = key.split(":", 1)[1]
        if only and sid not in only:
            continue
        st = load_goal(sid)
        if st is None:
            print(f"[{sid}] NO ROW / unparseable")
            continue
        old = st.status
        st.status = "active"
        st.turns_used = 0
        st.paused_reason = None
        st.last_verdict = None
        st.last_reason = None
        for a in ("waiting_on_pid", "waiting_on_session", "waiting_reason", "waiting_since"):
            setattr(st, a, None)
        st.waiting_until = 0.0
        save_goal(sid, st)
        print(f"[{sid}] {old!r} -> {st.status!r} (turns reset to 0)")
        changed += 1

    print(f"DONE — {changed} goal row(s) reactivated under {home}")
    print("NOTE: status=active makes each goal run when its live Hermes session "
          "opens. To run autonomously NOW, dispatch delegate_task background "
          "workers with the goal's full spec + verification checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
