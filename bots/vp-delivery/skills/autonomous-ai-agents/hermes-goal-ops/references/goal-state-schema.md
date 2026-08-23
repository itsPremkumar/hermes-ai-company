# GoalState schema reference (`hermes_cli/goals.py`)

Stored as `state_meta` row `goal:<session_id>` in `$HERMES_HOME/state.db`,
value = `GoalState.to_json()` (a JSON string).

## Top-level fields

| field            | type    | meaning |
|------------------|---------|---------|
| `goal`           | str     | Free-text objective. May be a raw git-diff hunk if set by pasting a diff (starts `a/... → b/...` + `@@ ... @@`). Read the whole value. |
| `status`         | str     | `active` \| `paused` \| `done` \| `cleared`. `GoalManager.has_goal()` is true only for `active`+`paused`. |
| `turns_used`     | int     | Loop iterations consumed. Reaching `max_turns` pauses the goal with `paused_reason='turn budget exhausted (N/N)'`. |
| `max_turns`      | int     | Turn budget. Default from config `goals.max_turns` (fallback 20); per-goal override via `agent.goal_max_turns` or `/goal draft` config. |
| `created_at`     | float   | epoch seconds |
| `last_turn_at`   | float   | epoch seconds of last loop turn (0.0 if never run) |
| `last_verdict`   | str\|null | judge verdict: `continue` \| `done` \| null |
| `last_reason`    | str\|null | judge's reasoning text |
| `paused_reason`  | str\|null | why paused (e.g. user-paused, budget exhausted) |
| `subgoals`       | list[str] | user-added criteria via `/subgoal` |
| `waiting_on_pid` | int\|null | wait barrier: park loop on a background PID until it exits |
| `waiting_on_session` | str\|null | wait barrier: park loop on another session |
| `waiting_until`  | float   | epoch seconds; park loop until this time |
| `waiting_reason` | str\|null | human-readable wait reason |
| `waiting_since`  | float   | epoch seconds when the barrier was set |
| `contract`       | dict    | completion contract (see below) |

## `contract` sub-object

| field         | meaning |
|---------------|---------|
| `outcome`     | what "done" looks like (evidence-based, not a vibe) |
| `verification`| how the judge checks completion |
| `constraints` | hard limits / must-nots |
| `boundaries`  | scope edges |
| `stop_when`   | explicit termination condition |

When a goal carries a contract, the judge checks completion against it. If you
run the goal via a `delegate_task` worker, paste the contract + any
`VERIFICATION` block as the worker's acceptance checklist so it knows when to
stop (the worker is NOT the Hermes judge loop).

## Mutation API (use these, not raw JSON)

```python
from hermes_cli.goals import GoalManager, load_goal, save_goal, clear_goal
mgr = GoalManager(session_id=sid, default_max_turns=int)
mgr.set(goal_text, contract=...)   # new active goal
mgr.resume()                       # paused -> active, resets turns_used
mgr.pause(reason="user-paused")    # active -> paused
mgr.mark_done(reason)              # -> done
mgr.clear()                        # -> cleared, unbinds _state
load_goal(sid) / save_goal(sid, state)   # direct DB get/put
clear_goal(sid)                    # mark cleared (preserved for audit)
```

## Loop driver (why DB flip alone doesn't run it)

`HermesCLI._maybe_continue_goal_after_turn()` (in `cli.py`) is the loop driver.
It is only invoked from the live-session post-turn hook, bound to that
session's `session_id`. There is no built-in "run all goals at once" mode. To
execute a goal autonomously without opening its session, dispatch a
`delegate_task(goal=<full spec + verification>, background=true)` worker.
