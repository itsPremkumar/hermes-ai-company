# Stale-DOING recovery (tasks wedged in `doing`)

## Symptom
`jarvis.cli tasks` shows one or more rows stuck in `doing` for a very long time, and
the loop emits `ESCALATION: N cycles with no progress` forever even though the goal's
other work is idle. Dashboard may show `Spawn? NO` (if the resource guard also trips).

## Root cause
A worker was dispatched (`status -> doing`, `attempts += 1`) but never filed a
`<task_id>|done|summary>` report back. The task sits in `doing` indefinitely. The
planner dedups open sub-goals against `(OPEN|DOING)` text, so the wedged `doing` task:
- blocks re-dispatch of that sub_goal (dedup sees it "in flight"), AND
- blocks the sub_goal from ever reaching DONE -> the stuck-counter never resets ->
  permanent escalation.

This is DIFFERENT from `escalation_orphaned_reports.md`, which is about worker REPORTS
filed under STALE task IDs. Here there is no report at all — just a silent `doing`.

## Fix (shipped in repo, commit 98e01ca)
`jarvis/core/cycle.py::_recover_stale_doing()` runs every cycle (step 1b, before the
resource gate). Any task still `doing` with `updated_at` older than
`Defaults.stale_doing_minutes` (90 min) is reset to `open`. That releases the dedup, so
the next tick re-decomposes and re-dispatches it. The recovery is logged:
`event=recover, status=stale_doing_reset`.

## How to verify the fix is live (after a cycle)
```
PYTHONPATH="C:/Users/PREM KUMAR/prems-jarvis-hermes" python -m jarvis.cli --db "<db>" log | grep recover
```
and `jarvis.cli tasks` should show the previously-wedged task flipped `doing -> open`
(or already re-dispatched back to `doing` with a fresh `updated_at`).

## Quick local repro (proves the mechanism without waiting 90 min)
Inject `Defaults().stale_doing_minutes = 0` and run one `run_cycle`; every `doing` task
older than `now` is recovered immediately.
