---
name: persistent-orchestrator
description: >
  Build a persistent, 24/7 goal-decomposition orchestrator that runs INSIDE Hermes
  (the desktop app) as a cron-driven "CEO" agent. Use when the user wants an always-on
  "Jarvis" / "agent OS" / "continuous goal loop" that checks a goal, decomposes the
  remaining gap into sub-goals, spawns throwaway worker agents via delegate_task,
  verifies their output, and loops forever — without exhausting a low-RAM box.
  Covers the durable SQLite state engine, the cron+SQLite+delegate_task pattern,
  verification gates, resource guards, and the CRITICAL supervision layering
  (Hermes is the host; the OS Task Scheduler is the real recovery point). Load for
  any "build me an autonomous agent / orchestrator / agent OS / continuous goal
  loop / make it run forever" request.
---

# Persistent Orchestrator (Hermes-native)

## When to use
- User wants a 24/7 autonomous system, "agent OS", "Jarvis", or "continuous goal loop".
- System must survive crashes/reboots and must NOT OOM a constrained machine.
- Workers should be spawned and torn down — NOT one giant agent doing everything.

## Architecture (proven on a 6 GB Windows box)
```
Durable core  (pure Python + sqlite3, ZERO 3rd-party deps):
  State     -> goal + tasks in jarvis_state.db  (survives reboot/crash)
  Planner   -> evaluate goal + decompose gap     (LLM-overridable; deterministic default)
  Dispatcher-> OPEN task -> worker brief          (caps concurrency)
  Verifier  -> file-exists / HTTP-200 / marker gate (stops spin-on-lies)
  Monitor   -> RAM/CPU guard (blocks spawn when starved)
  Cycle     -> run_cycle(): one deterministic tick
Scheduling:
  Hermes cron job -> `python -m cli run` every 30m   (the orchestrator "brain")
Worker execution:
  cron agent reads DISPATCH brief -> delegate_task(sub_goal, context=verification, toolsets)
Reboot survival (OUTSIDE Hermes):
  Windows Task Scheduler: JarvisBoot (onlogon) + JarvisWatchdog (every 10m)
```

## KEY INSIGHT — supervision layering (do NOT invert this)
Hermes (desktop app) is the HOST. The orchestrator is a cron GUEST inside it.
Therefore: **the orchestrator CANNOT restart Hermes.** A "Jarvis restarts Hermes"
watchdog chain is architecturally backwards and will never work. The recovery chain
must terminate at the OS:
```
  Windows Task Scheduler  ->  launches Hermes / runs a cycle on boot
  Hermes (cron engine)    ->  runs orchestrator every N min
  Orchestrator            ->  spawns/monitors workers, persists to SQLite
```
The external watchdog (run by Task Scheduler, independent of Hermes) is the ONLY
liveness check that survives Hermes dying. It detects a stale cycle and alerts;
it does NOT relaunch a GUI app from session 0. See references/supervision_layering.md.

## Build steps
1. Core in stdlib only (sqlite3) so it runs on a starved box with zero install.
2. State persists to SQLite; everything durable lives there, not in worker memory.
3. `run_cycle()` is pure Python + deterministic; tests run OFFLINE (no network/tokens).
   Inject `Monitor(min_free_ram_mb=0, max_cpu_percent=100)` in tests so they don't
   depend on live RAM.
4. Worker spawning uses the Hermes `delegate_task` TOOL — there is no Python SDK for
   it. The core emits a Dispatch brief; the cron agent reads it and calls
   delegate_task. Keep the spawn boundary explicit (see reference).
5. Verification gate: a task is DONE only when its check passes. Reject unverified
   "done" (requeue up to max_attempts, then FAILED).
6. Guardrails: max_open_tasks (3 on 6 GB RAM), RAM<400 MB / CPU>85% blocks spawn,
   dedupe in-flight sub-goals, escalate to operator after N idle cycles (don't burn
   tokens forever).
7. Logging: one JSON line per event to jarvis.log; rotate at ~2 MB (disk-full guard).
8. Reboot: register two `schtasks` entries (JarvisBoot onlogon, JarvisWatchdog 10m).

## Pitfalls (hit and fixed this session)
- **`State.get_task()` returns a FRESH object each call.** Mutate the ref you hold,
  then `update_task(same_ref)`. Re-fetching + mutating a second object silently loses
  the change (test fails unexpectedly).
- **`pytest` is NOT in the Hermes venv by default.** Run `python -m pip install pytest`
  into the venv first, or pytest reports "collected 0 items".
- **`C:\\one` is a junction to `C:\\c\\one` on this box.** write_file may warn the
  resolved path is `C:\\c\\one\\...`; the files are real there. Explorer may show
  `C:\\one\\...` as empty — open `C:\\c\\one\\...` instead. Run pytest from the real path.
- **Don't build the 27-row "Agent OS" failure table as theater.** Each row is real
  ONLY if a component + integration exists. Build the subset that has a backing
  component (logging, watchdog, reboot task, dedupe, caps). The rest is a wishlist.
- **Stress-test on the LIVE box, not assumptions.** The RAM guard WILL block dispatch
  when free RAM < 400 MB (observed ~316 MB) — that is correct behavior, not a bug.
  Verify the dispatch path with a permissive Monitor in a script.

## delegate_task WAVE DISCIPLINE (critical on a 6 GB box)
When you fan out many worker agents with `delegate_task` (e.g. a "make this project
world-class" swarm of 7-11 agents), these rules prevent the whole batch dying:
- **Hard cap = `max_concurrent_children` (3 on this box).** A batch with >3 tasks is
  rejected. Dispatch in WAVES of 3, not one giant batch.
- **Cascade, don't inject.** Launch Wave 1 (3 agents). When the async batch-complete
  notification arrives, launch Wave 2 into the freed slots. Do NOT launch a new agent
  mid-batch while a prior wave is still "running"/interrupted — injecting into an
  occupied slot caused a branch-switch that contaminated another agent's worktree
  (one agent found itself on the wrong branch and its deliverable conflicted).
- **Subagents are INVISIBLE in the Hermes desktop UI.** They do NOT appear as terminal
  tabs or chat panels; they surface only as a consolidated result message when the
  batch finishes. If the user says "I see no subagents," verify liveness via
  `git branch -a` / `git log` / `git worktree list` — a real agent leaves branches +
  commits (e.g. `ci/github-actions` with a real commit = proof of life). Don't poll;
  the batch-complete callback is the signal.
- **Free RAM before a heavy wave.** Kill the GPU Voicebox backend and Chrome first —
  agents running `npm run typecheck`/`test:unit` on a 6 GB box with <1 GB free get
  OOM-killed/interrupted. Empty slots are useless if the box can't run the work.
- **Salvage interrupted agents.** If a batch returns `status=interrupted`, the agents'
  partial work often survives as untracked files / dangling branches / stashes. Before
  re-dispatching, `git stash` the valuable partial artifacts, `git checkout main &&
  git reset --hard && git clean -fd` to a known-good tree, then recover the stash. Do
  NOT let dangling untracked files (e.g. stray `convert.ts` duplicates, `_conc*.txt`
  scratch dumps) rot the tree. Then re-dispatch the unfinished task as a SMALLER,
  single-agent job (not a parallel batch) so it actually finishes.
- **Prefer direct completion over agents for already-written artifacts.** If an agent
  produced finished files (docs, new ops) but got interrupted before committing, commit
  them YOURSELF (they're done) and only delegate the genuinely-unfinished work (e.g.
  the remaining failing tests). This halves agent load and RAM pressure.

## Verify before claiming done (the user demands real verification)
- pytest green (offline) + a `selftest` subcommand (offline structural checks).
- End-to-end CLI: init -> run (dispatches) -> report done (verification PASS -> DONE).
- Cron job created AND `cronjob action=run` returns execution_success.
- Both Task Scheduler tasks show Status: Ready.
- Push to GitHub (real remote, real commit hash) — not just "created locally".

## Support files
- references/supervision_layering.md — why Hermes=host + the dispatch-boundary pattern.
- scripts/watchdog_template.py — external liveness check (exit 2 = stale/alert).
