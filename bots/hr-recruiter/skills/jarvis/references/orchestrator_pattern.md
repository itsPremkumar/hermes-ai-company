# Jarvis orchestrator pattern -- expanded detail

## State machine (per task)
```
OPEN --dispatch--> DOING --worker report--> verify()
                                        |
                        pass ------------> DONE
                        fail & attempts<max --> OPEN   (requeue, retry)
                        fail & attempts>=max --> FAILED
                        blocked dependency --> BLOCKED
```
The verification gate is the only thing that moves a task to DONE. A worker
claiming "done" without passing the check is requeued, not trusted.

## Cycle (run_cycle) contract
Inputs: State, Planner, Dispatcher, Verifier, Monitor, Defaults, optional
reviewer_report.
Order of operations (each is a guard):
1. Goal set? else raise JarvisError.
2. Ingest reviewer_report (TASK_ID|STATUS|text) -> verify -> progress.
3. Goal accomplished? -> idle, return.
4. Resource guard (Monitor.can_spawn)? else idle, return.
5. Decompose: create <= max_new_per_cycle (1) sub-goals; DEDUPE vs OPEN/DOING.
   NOTE: creating a task is NOT progress -- do NOT reset the stuck counter here.
6. Dispatch <=1 worker if capacity (open_count < max_open_tasks=3). Dispatch =
   real progress -> reset stuck counter.
7. Else idle -> bump stuck counter; if >= stuck_cycles_before_escalation (12)
   -> escalate to operator instead of looping.

## Dispatch contract (what the Hermes agent gets)
```
task_id, sub_goal, goal_statement, verification, context, toolsets
```
The agent calls delegate_task(goal=sub_goal, context="Verification: <v>\n\n<ctx>",
toolsets=toolsets) and records task_id to feed the report back next tick.

## Why pure-Python core + agent-side dispatch
delegate_task is an agent tool, not importable. Splitting the decision engine
(pure stdlib, deterministic, testable offline) from the worker spawn (Hermes
cron agent) means:
- Tests run with zero network/tokens and are deterministic.
- The worker-spawn boundary is explicit and auditable.
- The core runs on a 6 GB / ~300 MB-free box without extra deps.

## Concurrency + resource policy (tuned for this box)
- max_open_tasks = 3 (RAM-bound; NOT queue-length-driven -- queue-driven spawning
  causes a death spiral where the orchestrator spends more tokens managing
  workers than workers spend working).
- min_free_ram_mb = 400, max_cpu_percent = 85 -- before any delegate_task call.
- idle sleep is cheap (no expensive reasoning when nothing to do).
