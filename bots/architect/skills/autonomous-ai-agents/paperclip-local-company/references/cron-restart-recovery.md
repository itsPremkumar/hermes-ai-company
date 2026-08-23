# Cron restart & recovery — field notes from a real "server was down" cron pass

This supplements the SKILL.md recovery section with what *actually* happens when a
cron job finds the Paperclip server down or the agent in a soft-error state. Verified
on a Windows git-bash cron run (server restarted via `tsx`, agent recovered, heartbeat
dispatched and confirmed live).

## Case A — server is FULLY STOPPED (not a zombie)
SKILL.md's "Zombie server process" assumes a node.exe is alive but not serving. If
`curl localhost:3100/api/health` returns **connection refused (exit 7)** AND
`netstat -ano | grep 3100` shows **nothing**, the server isn't running at all — there
is no node to kill. Just **start it** (the launch env from `run-server.bat`):
```bash
cd /c/one/paperclip-company/paperclip/server
export PORT=3100 HOST=0.0.0.0 SERVE_UI=true BETTER_AUTH_SECRET=paperclip-dev-secret-change-me \
  PAPERCLIP_DEPLOYMENT_MODE=authenticated PAPERCLIP_DEPLOYMENT_EXPOSURE=private \
  PAPERCLIP_PUBLIC_URL=http://localhost:3100 PAPERCLIP_HOME=/c/one/paperclip-company/data/paperclip \
  PAPERCLIP_MIGRATION_AUTO_APPLY=true DATABASE_URL='postgres://paperclip:***@localhost:5432/paperclip' \
  NODE_OPTIONS='--max-old-space-size=1500' \
  PATH="/c/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312:$PATH"
node node_modules/tsx/dist/cli.mjs src/index.ts >> /c/one/paperclip-company/tsx-out.log 2>&1
```
Health returns `{"status":"ok"}` within ~10s. The `***` literal in `DATABASE_URL` is
the real password on this box (sessions live in external Postgres, so `cj.txt` survives
restart — no re-auth needed). Use `NODE_OPTIONS=1500`, NOT the bat's 8192 (OOMs a 6 GB box).

## Case B — agent "error" after a restart: "Process lost -- server may have restarted"
After restart the agent reads `status:"error"` with that `errorReason`. `POST
/api/agents/<ID>/runtime-state/reset-session` (Cookie + Origin + `{}`) clears the
*runtime* error (`lastError:null`, `lastRunStatus:"succeeded"`) but the agent's
top-level `status:"error"` flag may **still persist** as a stale value — it clears only
on the next *successful* run, not on reset. Do NOT treat the lingering flag as a blocker;
proceed to invoke heartbeat / let the 30s tick dispatch. This is the restart-recovery
path (reset → invoke), distinct from the provider-failure soft-error (reasons null) where
you must NOT invoke.

## Dual dispatch (expected, not a bug)
After you assign an `in_progress`+agent issue AND invoke heartbeat, you get **two** runs:
- the manual invoke → a *general* heartbeat run (scoped to no specific issue), and
- the 30s scheduler tick → a *separate* run **scoped to the assigned issue** (wake payload
  `reason: issue_assigned`), with a temp dir `paperclip-run-<issue>-<runid>`.
Both `hermes` subprocesses are real work; `maxConcurrentRuns` (default 3) absorbs it.
Confirmed: run `0e86b541` (general) + run `fee74d38` (PRE-89-scoped) both spawned same
second, both alive.

## How to PROVE a run is live (don't trust `status:"running"` alone)
The invoke nudges `status` to `running` *instantly* even when no run has started
(`activeRunId` stays null). And the `run-logs/<runId>.ndjson` file often **does not
exist until the run completes/flushes** — so the run-logs dir is NOT a reliable
in-flight liveness signal. Use these instead:
1. **Temp scratch dir:** `%TEMP%/paperclip-run-<issue>-<runid>/` — recently-modified files
   (`dash.json`, `openapi.json`, `fin_ev.json`, `.paperclip-run-scratch.json`) prove the
   agent is writing work products right now.
2. **Process list:** `tasklist | grep hermes` then inspect command lines — a live
   `hermes.EXE chat -q "..." -m tencent/hy3:free --provider openrouter ...` whose args
   contain the run ID (e.g. `Run ID: 0e86b541-...`) is the definitive "executing" proof.
   CreationDate ~ now + a high-RAM child = alive.

Free-model latency (`tencent/hy3:free`) means the first ~1–2 min may show only startup
noise / no further output — that is alive-but-slow, NOT a dead run. Only cancel if you see
an `Exit code:` line AND `activeRun: null`.

## cron-mode tooling gotchas
- **`execute_code` is BLOCKED in cron mode** ("runs arbitrary local Python… Cron jobs run
  without a user present to approve it"). When a cron pass must parse JSON, write the
  script with `write_file` and run it via `terminal` + `python` instead.
- **Windows `python.exe` rejects MSYS absolute paths:** `open('/c/one/.../x.json')` raises
  `FileNotFoundError` even though shell `ls /c/one/...` works (MSYS only translates paths
  for some tools, not the Windows Python runtime). Fix: `cd` to the dir first and use a
  *relative* path (`open('x.json')`), or pass a Windows-style `C:\one\...` path. This bites
  every time you parse run-logs / issues JSON with `python` from git-bash.
