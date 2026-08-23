# Supervision layering — the one insight that makes or breaks a Hermes-native orchestrator

## The inverted diagram (what NOT to build)
A common first design puts the orchestrator ABOVE Hermes and claims it "monitors
and restarts Hermes":

```
  Jarvis (supervisor)
     -> Supervisor
        -> Hermes (worker)
```
On a Hermes-desktop-app setup this is backwards. Hermes is what keeps the cron
engine alive. If Hermes closes, the cron stops, and nothing *inside* it can revive
it. The watchdog chain "Jarvis restarts Hermes" can never fire.

## The correct chain
```
  Windows (Task Scheduler / startup)  ->  launches Hermes or runs a cycle on boot
  Hermes (cron engine)                ->  runs the orchestrator every 30m
  Orchestrator (Jarvis)               ->  spawns/monitors workers, persists to SQLite
```
The orchestrator is a *guest* of Hermes. The only thing that can bring Hermes (and
therefore the orchestrator) back after a crash/reboot is an OS-level trigger that
does not depend on Hermes.

## Why this matters on a constrained box
Adding a fleet of heartbeat daemons (one per worker, plus a supervisor daemon) to
"fix" supervision would consume the very RAM the guard is trying to protect on a
6 GB machine. The RAM-safe answer is:
- ONE cron job (the orchestrator brain) — already inside Hermes.
- ONE external watchdog (Task Scheduler, 10 min) — cheap, survives Hermes death.
- TWO Task Scheduler tasks (JarvisBoot onlogon, JarvisWatchdog 10m).

No extra always-on processes.

## The dispatch boundary (delegate_task is a TOOL, not an API)
`delegate_task` is an agent tool available to the cron run, not a Python function
you can import. So the durable core must NOT call it. Instead:

1. `run_cycle()` returns a `CycleReport` containing a `Dispatch` (the worker brief:
   sub_goal + verification + context + toolsets).
2. The Hermes cron agent reads that brief from the CLI output and calls
   `delegate_task(goal=sub_goal, context="Verification: ...\n"+context, toolsets=...)`.
3. When the worker finishes, the agent feeds the result back next tick as
   `<task_id>|done|summary`, which the core parses and verifies.

This keeps the core fully testable offline (no network, no tokens) while the
actual worker execution stays in the agent layer where delegate_task lives.

## Honest limits (cite these, don't over-promise)
No software guarantees "never stops". Realistic goal: automatic recovery from
EXPECTED failures + maximize uptime. Single points of failure the software alone
cannot overcome: permanent hardware failure, extended power loss, OS corruption,
long external outages, bugs needing code fixes. Design for recovery, not a fantasy
of uninterrupted operation.
