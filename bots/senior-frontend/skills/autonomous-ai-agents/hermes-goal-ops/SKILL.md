---
name: hermes-goal-ops
description: >-
  Operate Hermes's persistent `/goal` subsystem: inspect, reactivate, and
  drive standing goals. Use when the user sends a goal command outside a live
  Hermes session (e.g. "/goal show" into a coding-agent channel), asks to
  "turn all my goals on / active", "make my goals run continuously", or wants
  a goal loop to actually execute without manually opening each session.
  Covers the DB storage layout, the safe reactivation pattern that preserves
  serialization invariants, and — most importantly — the per-session loop
  limitation that makes `delegate_task` background workers the only way to
  run goals autonomously outside a live session.
---

# Hermes Goal Ops (`/goal` state manipulation + autonomous execution)

Hermes has a persistent, cross-turn `/goal` subsystem (a Ralph-style loop:
after each turn a judge model checks if the goal is done; if not, Hermes keeps
working until done / paused / cleared / turn budget exhausted). This skill is
about operating that subsystem from the agent side — reading and mutating
stored goals, and getting them to actually *run* when no interactive session
is bound to them.

## Where goals live

- Store: `$HERMES_HOME/state.db` (SQLite). On Windows that is typically
  `C:\Users\<user>\AppData\Local\hermes\state.db`. `HERMES_HOME` is the
  profile-aware path (`hermes_constants.get_hermes_home()`).
- Table: `state_meta(key TEXT, value TEXT)`.
- Row key: `goal:<session_id>` (e.g. `goal:20260713_185031_d600ab`).
- `value` is `GoalState.to_json()` — a JSON blob with at least:
  `goal, status, turns_used, max_turns, created_at, last_turn_at,
  last_verdict, last_reason, paused_reason, subgoals[], waiting_on_pid,
  waiting_on_session, waiting_until, waiting_reason, waiting_since, contract{}`.
- Status enum: `active | paused | done | cleared`. `GoalManager.has_goal()`
  is true only for `active` + `paused` (not `done`/`cleared`).

## Inspect without a live session

Read the DB directly to see every goal and its state:

```python
import sqlite3, json
db = sqlite3.connect(r"C:\Users\PREM KUMAR\AppData\Local\hermes\state.db")
for k, v in db.execute("SELECT key,value FROM state_meta WHERE key LIKE 'goal:%'"):
    d = json.loads(v)
    print(d["status"], d.get("turns_used"), "/", d.get("max_turns"), d["goal"][:80])
```

A session can have multiple goals across history; the *active* one for a
session is the row whose key matches that session's id.

## Reactivate goals safely (preserve invariants)

Do NOT hand-edit the JSON. The `hermes_cli.goals` module is the source of
truth for serialization and is cheap to import. Set `HERMES_HOME` first so it
binds to the right profile:

```python
import sys; sys.path.insert(0, "/path/to/hermes-agent")
import os; os.environ["HERMES_HOME"] = r"C:\Users\PREM KUMAR\AppData\Local\hermes"
from hermes_cli.goals import load_goal, save_goal

for sid in ["<session_id_1>", "<session_id_2>", ...]:
    st = load_goal(sid)
    if st is None: continue
    st.status = "active"
    st.turns_used = 0            # reset exhausted budgets
    st.paused_reason = None
    st.last_verdict = None
    st.last_reason = None
    for a in ("waiting_on_pid", "waiting_on_session", "waiting_reason", "waiting_since"):
        setattr(st, a, None)
    st.waiting_until = 0.0
    save_goal(sid, st)
```

To flip a single goal: `mgr.resume()` (clears pause + resets turns) or
`mgr.set(goal_text)` (fresh active goal). The `GoalManager` is constructed as
`GoalManager(session_id=sid, default_max_turns=int)`.

## CRITICAL: the goal loop is per-session

This is the part that surprises people. Flipping `status='active'` in the DB
does **not** start a loop by itself. The loop driver,
`HermesCLI._maybe_continue_goal_after_turn()` in `cli.py`, only fires **inside
a live Hermes session bound to that `session_id`** — it's called from the
post-turn hook. There is no native "one session runs every goal at once" mode.

Consequences for "turn all goals on and keep working on them":

1. **Reactivate in the DB** (above) → goals are now `active` and will run the
   moment you open Hermes in each goal's own session.
2. **To run them autonomously right now** (no human opening sessions), you
   must dispatch worker agents that execute the goal spec directly:
   `delegate_task(goal=<full goal text + verification checklist>,
   background=true, toolsets=["web","terminal","file","delegation"])`.
   The worker is NOT the Hermes goal loop — it's an agent you gave the full
   acceptance criteria, so paste the entire spec (all phases + the
   VERIFICATION checklist), not just the headline.

So the honest answer to "make all goals continuously working" is: reactivate
them in the DB (so live sessions drive them) AND/OR launch `delegate_task`
background workers for the ones you want executing immediately.

## Gotchas

- `state.goal` is free text. If a goal was set by pasting a `git diff`, the
  stored text is a raw diff/patch hunk (starts with
  `a/... → b/...` + `@@ ... @@`), not clean prose. Read the *whole* value
  before handing it to a worker — don't assume it's a sentence.
- `contract` shape: `outcome / verification / constraints / boundaries /
  stop_when`. Goals can carry an explicit completion contract; when running a
  goal via `delegate_task`, include any contract + the judge's VERIFICATION
  block as the worker's acceptance checklist so it knows when to stop.
- A `paused` goal with `paused_reason='turn budget exhausted (N/N)'` means the
  loop ran out of turns, not that it finished. Resetting `turns_used=0` on
  reactivation is what lets it run again.
- Context compression rotates `session_id` to a fresh child; `load_goal` is a
  flat lookup, so an active goal "dies" at the compaction boundary unless
  migrated. Don't be surprised if an old `goal:<sid>` row is for a dead
  session — check `state_meta` for the current session id if a goal seems
  missing live.
- Memory/secret hygiene: only touch `goal:<session_id>` rows. Don't read or
  modify `auth.json`, `.env`, or other credential rows.

## Companion files

- `scripts/reactivate_goals.py` — re-runnable script that flips every
  `goal:%` row to `active` (resets budgets + clears wait barriers) under a
  given `HERMES_HOME`. Run it before launching background workers.
- `references/goal-state-schema.md` — full `GoalState` field reference and the
  judge/contract fields, for when you need to read or set a specific field.
