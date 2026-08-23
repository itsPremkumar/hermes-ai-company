# 07 — Lessons Learned (every one paid for with a real incident)

## 1. The 20-worker fan-out (twice, same day)
**What happened:** promoting cards on Windows spawned ALL of them at once; RAM fell to
~0 MB free; manual taskkill rescue.
**Root cause (in source):** gateway runs an embedded kanban dispatcher
(`gateway/kanban_watchers.py`). Its memory-derived concurrency cap reads `/proc`
(**Linux-only**) — on Windows it fails OPEN = unlimited workers. Config caps
`max_in_progress` were set but the embedded dispatcher's auto-promotion ignored them.
**Laws:** `dispatch_in_gateway: false`; cards live in `blocked`; ONE release valve.

## 2. The zombie gateway state file
`gateway_state.json` said "running" with a PID that had been dead since Aug 18 while the
REAL gateway ran under another PID.
**Law:** never trust state files for liveness — match actual process command lines.

## 3. Two cron stores, only one alive
Desktop app keeps its own `cron/jobs.json`; it STALLS when the app closes (jobs sat
overdue). The CLI/gateway store kept ticking 24/7 but was empty.
**Law:** real jobs → `hermes cron create` (gateway store). Desktop store parked.

## 4. The config-drift execution guard
Any agent job without explicit provider+model is BLOCKED the moment the global model
config changes (`RuntimeError: ... config drifted`). This silently killed jobs twice.
**Law:** pin every job at creation. Unpinned + error status = drift victim.

## 5. Free tiers vanish without notice
OpenRouter retired the `:free` variants of tencent/hy3, meituan/longcat-2.0,
stepfun/step-3.7-flash — 3 of our 4 pins — caught within hours by model_health.py.
**Law:** never single-pin the fleet; run the catalog guard.

## 6. Stale claims freeze queues silently
After killing worker PIDs, rows kept `claim_lock=laptop:<deadpid>`; the dispatcher's
SQL filters `claim_lock IS NULL`, so those cards were skipped with zero output.
**Law:** after any kill, clear claim_lock/claim_expires on affected rows.

## 7. Iteration budget kills full builds
60 turns was enough to start a project and die mid-way ("Iteration budget exhausted").
200 turns completed an entire product in ~14 min of work time.
**Law:** builder profiles carry max_turns: 200.

## 8. Empty .env = silent useless bot
research-analyst was created via CLI without copying credentials: web tools present but
zero API keys → would have failed on first real call.
**Law:** after `profile create`, copy the main `.env` into the new profile.

## 9. Subagent self-reports are not facts
The pilot claimed "23/23 tests pass, merged to GitHub." True — but proven only by
cloning the repo fresh and re-running tests independently.
**Law:** verification = independent reproduction, never reading logs.

## 10. RAM is the company's scarcest asset
~800 MB–1.4 GB free typical. One extra Chrome tab can starve a build.
**Law:** heavy tools (browser/computer_use/delegation/media) scoped to single bots;
one worker; watchdog alarm at <500 MB.
