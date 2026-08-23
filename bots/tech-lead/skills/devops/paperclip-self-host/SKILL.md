---
name: paperclip-self-host
description: Run Paperclip (paperclipai/paperclip) with the Hermes Agent adapter on a Windows dev machine NATIVELY (no Docker) — install the pnpm monorepo, build, create the Postgres DB, and start the server via tsx. Documents the Windows/MSYS/pnpm pitfalls that otherwise silently stall the install or crash startup with confusing errors.
---

# Paperclip self-hosting (Windows, native, with Hermes)

Paperclip (`paperclipai/paperclip`, MIT, ~73k stars) is an open-source orchestration
platform for teams of AI agents — "if OpenClaw is an employee, Paperclip is the company."
This skill covers running it on a Windows dev box **without Docker**, with the Hermes
Agent adapter wired in so you can hire a Hermes "employee" (CTO/engineer).

## Key fact: Hermes is already bundled — do NOT hand-wire it

Paperclip's `main` branch **ships** the Hermes adapter:
- `packages/adapters/hermes` (local CLI) and `packages/adapters/hermes-gateway` (HTTP/SSE)
- `server/src/adapters/registry.ts` imports `createHermesLocalServerAdapter()` and
  `createHermesGatewayServerAdapter()` from `@paperclipai/hermes-paperclip-adapter`.

The upstream source is `NousResearch/hermes-paperclip-adapter` (published as
`@paperclipai/hermes-paperclip-adapter`, v0.3.x). A normal Paperclip install already
gives you the `hermes_local` and `hermes_gateway` adapter types. You do **not** manually
wire the adapter. Cloning the NousResearch repo builds standalone (`npm install && npm run build`
→ `dist/`) but is only needed if you want to patch the adapter itself.

- `hermes_local`: Paperclip shells out to the `hermes` CLI as a child process each heartbeat.
  Requires `hermes` on PATH for the user running Paperclip.
- `hermes_gateway`: Paperclip calls an already-running Hermes API server over HTTP/SSE
  (start Hermes with `API_SERVER_ENABLED=true API_SERVER_KEY=<secret> hermes gateway run --replace`).

## Environment (verified on the build host)

Node 22.x, pnpm 9.x (install via `npm install -g pnpm@9`; `corepack enable` failed on that
host), Python 3.11, git. Hermes Agent installed natively (Windows). PostgreSQL 17 present as
a Windows service on `:5432` — **embedded Postgres will NOT run under an admin Windows account**
(see Pitfalls), so use the external one.

## Procedure

1. **Clone + install**
   ```
   git clone https://github.com/paperclipai/paperclip && cd paperclip
   pnpm install --ignore-scripts --config.node-linker=hoisted
   ```
   (The `--ignore-scripts` + `hoisted` flags avoid the MSYS link stall — see Pitfalls.)

2. **Build**
   ```
   pnpm build
   ```
   Runs `tsc` across all workspace packages; expect **0 errors**. The default `server` build
   script is `tsc && mkdir -p dist/onboarding-assets dist/built-ins && cp -R src/onboarding-assets/. dist/onboarding-assets/ && cp -R src/built-ins/. dist/built-ins/`.
   If tsc passed but those two dirs are missing under `server/dist/`, create them:
   `mkdir -p server/dist/onboarding-assets server/dist/built-ins && cp -R server/src/onboarding-assets/. server/dist/onboarding-assets/ && cp -R server/src/built-ins/. server/dist/built-ins/`.

3. **Create the Postgres role + database** (see `scripts/setup-pg-db.bat` and
   `references/windows-pnpm-pitfalls.md`). Then set:
   ```
   DATABASE_URL=postgres://<role>:<pw>@localhost:5432/<db>
   ```

4. **Start the server via `tsx`** — NOT `node dist/index.js` (see Pitfall). Use the launcher
   bat (`templates/run-server.bat`) invoked as:
   ```
   cmd.exe /c "C:/abs/path/run-server.bat"
   ```
   Do NOT invoke node/tsx with absolute Windows paths through the git-bash shell (MSYS path
   mangling — Pitfall). Inside the bat, native `C:\` paths are correct, and the
   `../node_modules/.bin/tsx` shim works.

5. **Bootstrap the instance + company + agent.** The UI path is documented below, but
   **every step is also a REST call** — see `references/paperclip-api-bootstrap.md` for the
   full scriptable flow (sign-up → `POST /api/bootstrap/claim` with an `Origin` header →
   `POST /api/companies` → `POST /api/companies/:id/agents` → heartbeat invoke). Gotchas
   captured there: mutation endpoints need `Origin: http://localhost:3100` (else
   "trusted browser origin" error); `role` is a **lowercase** enum (`cto` not `CTO`);
   `PATCH /api/issues/:id` is root-mounted (not under `/companies/:id`); the task-bridge key
   (`POST /api/agents/:id/keys` with `scope.kind=task_bridge`) is **required for autonomous
   execution** — without it Hermes boots and waits for a task ID instead of pulling the issue.

   Browser path: `GET /api/health` → `{"status":"ok"}`; open `http://localhost:3100` →
   create owner account (first run) → create Company → add agent with `adapterType=hermes_local`.

6. **Post-setup agent management.** After bootstrap, agents need manual post-setup:
   `references/paperclip-agent-management.md` covers re-authentication after server restart,
   enabling heartbeat (disabled by default), creating the task-bridge key with its required
   `projectId` field, resetting stale agent sessions after config changes, and the valid
   `hermes_local` provider list. Without these steps the agent stays idle or fails with
   confusing errors.

## OpenRouter API key: env passthrough to the adapter

Paperclip passes `OPENROUTER_API_KEY` to the Hermes adapter via the
`ADAPTER_ENV_PASSTHROUGH` mechanism in `server/src/services/plugin-loader.ts`:

```typescript
const ADAPTER_ENV_PASSTHROUGH = [
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "GOOGLE_API_KEY",
  "GEMINI_API_KEY",
  "OPENROUTER_API_KEY",
];
```

These keys are injected into the worker env when the Hermes adapter runs. To make
them available:

- **Persistent (survives reboots):** `setx OPENROUTER_API_KEY "sk-or-v1-..."` in
  a terminal (takes effect in new shells only).
- **Per-launcher:** add `set OPENROUTER_API_KEY=sk-or-v1-...` to the
  `run-server.bat` before the `tsx` line.
- **Current shell (bash):** `export OPENROUTER_API_KEY="sk-or-v1-..."` before
  starting the server.

If a free OpenRouter model (`tencent/hy3:free`, etc.) previously returned empty
responses on the shared pool, adding a personal key gives it a dedicated rate
limit and it starts returning real content. The key is read by the
`@paperclipai/hermes-paperclip-adapter` → Hermes CLI → OpenRouter SDK chain.

## Reviving a downed server (root causes + recovery recipe)

A server that was running earlier but now returns `connection refused` on `:3100` is a recurring
failure mode on this host. Two root causes dominate:

### Root cause A — Task Scheduler battery/idle policy killed it
The `PaperclipServer` (and `PaperclipWatchdog`) scheduled tasks are registered with
`DisallowStartIfOnBatteries=true` and `StopIfGoingOnBatteries=true`. If the laptop later ran on
battery, the server process is terminated and NOT restarted (the boot trigger already fired).
**Debug:** `schtasks /query /tn "\PaperclipServer" /xml` → look for those two lines. **Fix:** just
restart it — `schtasks /run /tn "\PaperclipServer"`, or launch `run-server.bat` manually. Don't
edit the task unless you want it to survive battery.

### Root cause B — DB password was redacted, so a restarted server can't connect
`run-server.bat` is committed with `DATABASE_URL=postgres://paperclip:***@localhost:5432/paperclip`
— the real password was stripped by a "no secrets" git commit + secret scanner. The server boots
only while a valid password is in memory at the one good boot; after a restart it dies at DB
connect. Postgres uses `scram-sha-256` for TCP (`host` lines in `pg_hba.conf`), so you must recover
the `paperclip` role password. **Recovery recipe (admin on the box):**
```bat
REM 1. Temporarily relax pg_hba host lines to trust (NOT the local line — Windows has no unix socket)
REM    edit C:\Program Files\PostgreSQL\17\data\pg_hba.conf : change
REM      host  all  all  127.0.0.1/32  scram-sha-256  ->  trust
REM      host  all  all  ::1/128        scram-sha-256  ->  trust
REM    then reload:  psql -U postgres -h 127.0.0.1 -c "SELECT pg_reload_conf();"
REM 2. Reset the role password
psql -U postgres -h 127.0.0.1 -c "ALTER ROLE paperclip WITH PASSWORD 'paperclip_dev_pw_2026';"
REM 3. Restore scram-sha-256 on the host lines, reload again
REM    (server-side connect now uses the known password; app-side requests re-auth via cookie)
```
Then launch with the recovered password (below) — do NOT edit `run-server.bat` (preserve the
user's redacted file); inject `DATABASE_URL` into the launch environment instead. Remember to back
up `pg_hba.conf` before editing and restore it exactly (security: leave the DB on `scram-sha-256`).

### Sourcing the LLM key (OPENROUTER_API_KEY is not in env/registry)
The server needs `OPENROUTER_API_KEY` for the `hermes_local` agent. It is NOT in the shell env,
not in the Windows registry (machine/user), and `run-server.bat` only references `%OPENROUTER_API_KEY%`.
**Find it** in the Hermes home `.env`:
```bash
grep -E '^OPENROUTER_API_KEY=' "/c/Users/PREM KUMAR/AppData/Local/hermes/.env" | head -1 | cut -d= -f2-
```
(The Paperclip agent's model is `tencent/hy3:free` via openrouter, so this key funds it.)

### Launching the server from git-bash WITHOUT MSYS path doubling
Calling `node "C:\one\..."` (backslash) through bash rewrites the path to `C:\c\one\...` →
`Cannot find module`. **Forward-slash Windows paths do NOT get doubled.** Launch via `cmd.exe /c`
with forward-slash absolute paths:
```bash
OR_KEY="$(grep -E '^OPENROUTER_API_KEY=' "/c/Users/PREM KUMAR/AppData/Local/hermes/.env" | head -1 | cut -d= -f2-)"
cmd.exe /c "set OPENROUTER_API_KEY=$OR_KEY&& cd /d C:\one\paperclip-company\paperclip\server&& set PORT=3100&& set HOST=0.0.0.0&& set SERVE_UI=true&& set BETTER_AUTH_SECRET=paperclip-dev-secret-change-me&& set PAPERCLIP_DEPLOYMENT_MODE=authenticated&& set PAPERCLIP_DEPLOYMENT_EXPOSURE=private&& set PAPERCLIP_PUBLIC_URL=http://localhost:3100&& set PAPERCLIP_HOME=C:\one\paperclip-company\data\paperclip&& set PAPERCLIP_MIGRATION_AUTO_APPLY=true&& set DATABASE_URL=postgres://paperclip:paperclip_dev_pw_2026@localhost:5432/paperclip&& set NODE_OPTIONS=--max-old-space-size=8192&& set PATH=C:\Users\PREM KUMAR\AppData\Local\Programs\Python\Python312;%PATH%&& node C:/one/paperclip-company/paperclip/node_modules/tsx/dist/cli.mjs C:/one/paperclip-company/paperclip/server/src/index.ts >> C:\one\paperclip-company\tsx-out.log 2>&1"
```
You can also reuse `run-server.bat` unchanged by exporting `OPENROUTER_API_KEY` and `DATABASE_URL`
into the environment first, then `cmd.exe /c "C:\one\paperclip-company\run-server.bat"`.
**Verify:** `curl -s localhost:3100/api/health` → `{"status":"ok",...}`.

### Before you relaunch: is a healthy server already listening? (avoid duplicate on :3101)

**Do NOT blindly relaunch on a crash/watch-pattern alert without first checking whether a
healthy instance is already up.** Two verified traps (2026-07-15 session):

- **A watch-pattern match on the startup `echo` line is a FALSE POSITIVE.** The launcher's
  `echo "launching Paperclip ... on :3100"` fires the watcher *before* `exec tsx` runs — the
  process can (and did) then exit `127` a split-second later (backslash-path mangling: `C:\\one\\...`
  in a bash launcher collapses to `C:onepaperclip...` → `exec: ...tsx: not found`). Matching the
  echo is NOT proof the server booted. Always confirm with `process poll` (check `exit_code`) and a
  real health probe, not the log line.
- **If :3100 is already taken, Paperclip silently falls back to :3101** and logs
  `Server 3101 (requested 3100)`. A relaunch fired on a stale alert then leaves TWO live servers
  (original on :3100 + duplicate on :3101), doubling Node RAM on a box that often has <400 MB free.
  **Before relaunching, check:**
  ```bash
  netstat -ano 2>/dev/null | grep -E ':310[01]\b' | grep LISTENING
  curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 5 http://localhost:3100/api/health
  ```
  If :3100 already returns `HTTP 200`, the server is fine — do nothing. If you already spawned a
  duplicate on :3101, kill it (`process kill` on the session you started, or `taskkill /F /PID <pid> /T`
  using the netstat PID) and keep the original.
- **The `.bin/tsx` shim ALSO mangles POSIX `/c/one/...` paths** (rewrites them to `C:\c\one\...` →
  `Cannot find module`), not just backslash paths — so "the .bin/tsx shim works" only holds inside a
  `.bat` with native `C:\` paths. From git-bash, the reliable launch is `node` directly against tsx's
  real CLI with a **forward-slash Windows** path (survives MSYS intact):
  ```bash
  cd /c/one/paperclip-company/paperclip/server
  # ...export PORT/HOST/DATABASE_URL/PAPERCLIP_*/NODE_OPTIONS...
  exec node "C:/one/paperclip-company/paperclip/node_modules/tsx/dist/cli.mjs" src/index.ts
  ```

### Re-authenticating (cookie) after restart
External-Postgres sessions normally survive restart (see `paperclip-local-company`), but if the
cookie file is stale/empty, re-sign-in: `POST /api/auth/sign-in/email` with
`{"email":"prem@local.dev","password":"LocalDevPass123!"}`, then write a proper Netscape cookie file
(domain must be `localhost`, NOT `#HttpOnly_localhost`). `curl -b /c/one/.../cj.txt` from git-bash
fails with `failed to open cookie file` (MSYS rewrites the path) — use a relative `-b cj.txt` run
from the company dir, or pass the token via a `Cookie:` header. The heartbeat-invoke endpoint also
requires `Origin: http://localhost:3100`.

## 24/7 Operation (Hermes cron watchdog)

To keep Paperclip running 24/7 without a dedicated terminal, set up a no_agent
Hermes cron job that polls the health endpoint and restarts the server if it goes
down. This survives terminal closes, reboots (if Hermes Desktop is running), and
transient crashes.

### Setup

1. Place `templates/watchdog.sh` into `~/.hermes/scripts/watchdog.sh`.
2. Customize `PAPERCLIP_HEALTH_URL` and `PAPERCLIP_SERVER_BAT` at the top of
   the script, or rely on defaults.
3. Create the cron job (set `no_agent=true` so no LLM token is burned per tick):
   ```bash
   # From Hermes CLI or via cronjob tool:
   cronjob(action='create',
     name='paperclip-watchdog',
     schedule='5m',
     script='watchdog.sh',
     no_agent=true)
   ```

The cron job runs every 5 minutes, does a single `curl` check, and only
restarts when the server is unresponsive. No tokens consumed, no LLM overhead.

### Windows-native alternative (more robust on a dev box)

If Hermes Desktop is not guaranteed to be running, use **Windows Task Scheduler**
instead — `scripts/watchdog.py` is a stdlib-only, zero-LLM watchdog that does the
same health-check + auto-restart + idle-nudge, plus it re-authenticates each
cycle (so the session never expires) and writes `company-status.json` /
`company-report.md`. Register it with two `schtasks /Create` calls (every 5 min
**and** `/SC ONSTART`) and a `PaperclipServer` `/SC ONSTART` task with
`/DELAY 0001:00`. Full recipe + auth/run-output gotchas in
`references/continuous-operation.md`. Prefer this when you want the company to
survive a reboot without a logged-in Hermes session.

### What the watchdog covers

- **Server crash recovery:** if Paperclip exits for any reason, it's back
  within 5 minutes.
- **Agent heartbeat continuity:** Paperclip's own agent loop runs on a timer;
  as long as the server is up, agents self-dispatch on their heartbeat.
- **Zero maintenance:** the cron output is saved locally; errors surface
  through Hermes cron list.

### Autonomous agent execution checklist

For an agent to work hands-off:
1. **Heartbeat enabled** — `PATCH /api/agents/:id` with
   `runtimeConfig: { heartbeat: { enabled: true } }`.
2. **Task-bridge key exists** — `POST /api/agents/:id/keys` with
   `{ scope: { kind: "task_bridge", projectId: "<COMPANY_ID>" } }`.
3. **An issue is assigned** to the agent (`PATCH /api/issues/:id` with
   `assigneeAgentId`).
4. **Server stays up** — covered by the watchdog above.

### Known agent behavior limits

**The agent autonomy gap.** A Hermes agent with a task-bridge key can:
- Complete an assigned issue ✅
- Create child / follow-on issues ✅
- Upload artifacts and post comments ✅
- Set its own issue to `done` ✅

What it **cannot** do autonomously:
- **Self-assign child issues it creates** ❌ — child issues are always left
  with `assigneeAgentId: null`, stalling the pipeline until a bridge mechanism
  fills the gap.
- **Set issue status via board-mutation endpoints from a non-browser origin**
  (needs `Origin: http://localhost:3100` + valid session cookie).
- **Interact with `ask_user_questions` / `request_confirmation`** — the
  interaction endpoint has strict schema requirements that the agent's POST
  attempts often violate (4xx).

**Bridging the autonomy gap.** To keep the company developing without manual
stepping between issues:

1. **Cron-based auto-assigner** — create a Hermes cron job (every 15m) that
   queries unassigned `todo` issues and PATCHes them to the agent. The agent's
   heartbeat then picks them up on the next cycle.
2. **Parent-issue pattern** — attach "after completing this, create child issues
   AND leave them `in_progress` assigned to yourself" in the AC. The agent
   follows this some of the time, but unreliably — the cron fallback is the
   safety net.
3. **Manual batch** — PATCH all child issues to the agent in one call, then
   trigger `heartbeat/invoke`. The agent works through them sequentially.

**PATCH persistence quirk for model/provider.** `PATCH /api/agents/:id` values
for `adapterConfig.model` and `adapterConfig.provider` are silently overwritten
by `normalizeMediatedAdapterConfigForPersistence` in the server route handler.
The stored config always reflects what was set at agent creation. Workarounds:
- Create a new agent with the desired config if you must change it.
- Accept the creation-time config if it works — the PATCH failure is cosmetic.
- Alternatively, modify the normalize function in the server source and restart.

### Building a full autonomous company (C-suite pattern, verified end-to-end)

Beyond one agent, you can stand up a complete org. Verified working layout for a
zero-cost company (all `hermes_local`, model `tencent/hy3:free` via OpenRouter, heartbeat on):

| Agent | role enum | Mandate |
|-------|-----------|---------|
| Hermes CEO | `ceo` | Strategy, roadmap, cross-agent coordination |
| Hermes CTO | `cto` | Product engineering, infra |
| Hermes CMO | `cmo` | Brand, GTM, pricing, outreach |
| Hermes COO | `devops` | Delivery ops, SLAs, client workflows |
| Hermes CFO | `cfo` | Unit economics, burn=$0 guard, revenue ledger |
| Hermes Head of Product | `pm` | Roadmap specs, feedback loop |
| Hermes QA | `qa` | Test plans, release gates |

Steps that actually worked (one session):
1. Create each agent via `POST /api/companies/:id/agents` with `runtimeConfig.heartbeat.enabled:true`
   and the `adapterConfig` block above. Do them ONE AT A TIME — batching 5 in one shell
   loop hit transient errors; the loop also scrambled the `agentId`→epic mapping (bash
   associative-array ordering), so assign epics from an authoritative `identifier→id` map
   written to a JSON file, not inline shell vars.
2. Create a **project** (`POST /api/companies/:id/projects`) for the product build.
3. Create **epic issues** (`POST .../issues` with `projectId`, `assignedAgentId`, AND
   `status:"todo"` together — see assignment gotchas in `references/paperclip-api-bootstrap.md`).
4. Two-step activate each epic: PATCH `assigneeAgentId`+`status:"todo"`, then PATCH
   `status:"in_progress"` (in_progress requires an assignee or it 422s).
5. Each agent self-dispatches its epic via heartbeat. Agents produce **artifact work-products**
   (Paperclip attachments) — retrieve them: `GET /api/issues/:id/work-products` → each item's
   `metadata.attachmentId` → `GET /api/attachments/<id>/content`. Download these to local files
   so the human has deliverables (see `scripts/fetch_assets.py` pattern in `references/continuous-operation.md`).

**Detecting "is the agent running" without a runs-list endpoint.** This build's
`/api/agents/:id/heartbeat-runs?page=1&limit=3` route returns 404 (not exposed). Use the
agent's own `status` field instead: `status=="running"` means a heartbeat is active; combine
with `lastHeartbeatAt` to decide whether to nudge. The watchdog nudge guard: nudge only when
`status != "running"` AND `(now - lastHeartbeatAt) > IDLE_NUDGE_SECS` AND pending work exists.
This prevents the double-nudge problem (manual invoke while auto-heartbeat is on cancels runs).

See `references/continuous-operation.md` for the Task Scheduler recipe, Set-Cookie auth
gotcha, artifact retrieval, and the revenue-asset pattern.

## Cron-tick decision checklist (exact order of operations for scheduled checks)

When executing a periodic check (every 5–30 min) to advance the company pipeline,
run these steps in order. This is the cron-friendly concise sequence; for full
diagnostics (stale runs, timeout analysis, zombie server) see the sections below.

1. **Fetch all issues** — `GET /api/companies/:companyId/issues`. This is the
   authoritative live source. Ignore stale local JSON snapshots.

2. **Audit done issues** — For each issue with `status: "done"`:
   - Read its completion note (run log's last ~10 lines) for stated next steps.
   - Check for existing child issues (same `parentId`).
   - If agent mentioned unfinished follow-up work but no child issue tracks it →
     `POST` a new child issue with `assigneeAgentId` + `status: "todo"` so the
     server auto-triggers a heartbeat on creation.
   - If follow-up is already captured and in_progress/done → skip.

3. **Adopt orphan todo/backlog issues** — For each issue with `status: "todo"`
   or `"backlog"` AND `assigneeAgentId: null`:
   - Assign to the appropriate agent via `PATCH /api/issues/:id` with
     `assigneeAgentId` + `status: "todo"`. The heartbeat system auto-advances
     to `in_progress` on the next tick — no second PATCH needed.

4. **Check agent liveness** — `GET /api/agents/:agentId`:
   - If `status: "running"` AND issues assigned to it have `activeRun` objects
     with recent `startedAt` → agent is actively working; **skip heartbeat**.
   - If `status: "idle"` AND pending work exists → invoke heartbeat
     (`POST /api/agents/:id/heartbeat/invoke` with `Origin: http://localhost:3100`).
   - If `status: "running"` but NO issue has an active run and the run-log
     directory has no new files in the last hour → the agent has a stale
     "running" marker. Cancel the ghost run, reset session, re-trigger.

5. **Cross-check run logs for genuine execution** — `ls -lt` the agent's
   run-log directory. If the most recent `.ndjson` has a modification timestamp
   within the last heartbeat interval and >3 lines of output, the agent is
   genuinely executing work regardless of API status.

6. **Report** — Summarize what was done, what was already running, and what
   needs human attention (founder-gated steps: npm publish, domain registration,
   LinkedIn account creation, Gumroad publish — none an agent can do).

## Operations monitoring — issue lifecycle tracking & agent progress

Beyond basic agent liveness (`status` + `lastHeartbeatAt`), you need to track whether
agents are actually making progress on assigned work. This section covers inspecting
issue state transitions, reading run logs to confirm real work, and auditing done
issues for required follow-up.

### Why API-based liveness is not enough

`agent.status == "running"` only means a heartbeat process is active — it does NOT
mean the agent is making progress. An agent can be "running" while its run is
rate-limited, timed out, or stuck producing no output. Use the file-system run logs
and issue lifecycle data to determine actual work.

### Run log analysis (real-time, file-system approach)

The `stdoutExcerpt` returned by `GET /api/heartbeat-runs/<id>` stays `""` until the
run exits. For real-time progress, read the raw `.ndjson` log files:

```
RUN_LOGS = <PAPERCLIP_HOME>/data/paperclip/instances/default/data/run-logs/<COMPANY_ID>/<AGENT_ID>/
```

Each `.ndjson` file is a run's streaming output — **one JSON object per line** with keys
`ts` (ISO timestamp), `stream` (`stdout`/`stderr`), and `chunk` (the text payload).
`tail`/`head` on the raw file show JSON, not clean prose. To extract readable lines:
```bash
python -c "import sys,json; [print(json.loads(l).get('chunk','').rstrip()) for l in sys.stdin if l.strip()]" < <run_id>.ndjson
```
Some runs end with `"Exit code: 0"` / `"timed out: true"` inside the `chunk`; others
end with agent-init lines like `[hermes] Session: ...`. Check them with:
- `ls -lt $RUN_LOGS | head -5` — most recent runs first
- parse `head -3 <run_id>.ndjson` — init lines name the workspace/issue the run targets
- parse `tail -5 <run_id>.ndjson` — last activity (exit code, timeout, or agent init)
- `wc -l <run_id>.ndjson` — more lines = more work done; a 4-line file with just init + timeout
  means the agent produced nothing useful (PRE-7 pattern)

### Issue lifecycle states

| State | Meaning for operations |
|-------|----------------------|
| `todo` | Assigned but never started. Heartbeat auto-advances to in_progress on next cycle. |
| `in_progress` | Has (or had) an active run. Check the run log to confirm actual work was done. |
| `in_review` | Agent completed work, awaiting review. May or may not have a current run. |
| `done` | Completion timestamp tells recency. Check if follow-up child issues exist. |
| `blocked` | Run failed/timed out without auto-retry. Needs triage. PRE-7 hit this: video production timed out with zero output → status set to `blocked`. |
| `backlog` | Not yet assigned. Will NOT auto-advance until moved to `todo`. |

Key auto-advancement behaviors (observed in production):
- **Auto-`in_progress`**: Issues with `status: "todo"` and an assignee get
  auto-advanced to `in_progress` on the next heartbeat cycle. PRE-34 transitioned
  from `todo` to `in_progress` between two API polls without manual PATCH.
- **Auto-respawn after timeout**: When a run times out at 1800s (the default
  `timeoutSec`), a new run is automatically created for the same issue.
  Run e978e29a timed out → run bc5e04ff spawned for the same issue (PRE-34).
  One timeout is not permanent failure; repeated timeouts suggest the task needs
  smaller decomposition or a longer timeout.
- **No auto-spawn for `done`**: The agent creates child issues but leaves them
  unassigned (see "Bridging the autonomy gap" above). Done issues require a
  manual audit (see below).

### Done-issue follow-up audit

1. `GET /api/companies/:id/issues` → filter `status == "done"`
2. For each done issue:
   - Read the completion note (last ~10 lines of the issue's most recent run log)
     for stated next steps
   - Check if child issues exist via `parentId` linking back
   - If follow-up exists AND is assigned/in_progress → no action needed
   - If follow-up exists but is unassigned → assign via cron bridge or manual PATCH
   - If follow-up is mentioned but NOT tracked as an issue → create a child issue
3. Example from this session: PRE-12 (monetization site) noted "register domain,
   LinkedIn page" as next steps. Checked PRE-5 (showcase repo) — already captured
   LinkedIn scope. No new child needed.

### Cron-based auto-assigner for unassigned todos

The autonomy gap (child issues left unassigned) can be bridged with a Hermes cron
job (every 5-15 minutes) that queries unassigned `todo` issues and PATCHes them
to the appropriate agent. Without this, each completed issue creates orphans that
stall the pipeline.

Full operational patterns and session-specific observations in
`references/operations-monitoring.md`.

## Omniroute install (DEFAULT linker, NOT hoisted — hoisted misses pre-built dist/)

**CRITICAL: do NOT use `--config.node-linker=hoisted` for omniroot.** The
hoisted linker skips extraction of the pre-built `dist/server.js` (tarball
entries under `dist/` are pruned), producing a package that can only boot to
`✖ Server not found at: ...dist/server.js`. Use the default isolated linker so
the published bundle files land in the right place.

Omniroute (`omniroute` npm package v3.8.46, by diegosouzapw) is a free AI
gateway with 160+ providers, auto-fallback, and an OpenAI-compatible endpoint.
Install it into a throwaway project:

```bash
mkdir omniroute && cd omniroute
echo '{"name":"omniroute-local","private":true,"dependencies":{"omniroute":"*"}}' > package.json
pnpm install --ignore-scripts
```

The `--ignore-scripts` flag avoids the postinstall step that stalls on MSYS
(paperclip-style) and saves time. The pre-built bundle including
`dist/server.js` is extracted correctly with the default linker.

On a slow network, add a `.npmrc`:
```
fetch-retries=20
fetch-retry-factor=2
fetch-retry-mintimeout=1000
fetch-retry-maxtimeout=60000
fetch-timeout=120000
network-concurrency=4
```

Start via:
```bat
node node_modules\\omniroute\\bin\\omniroute.mjs
```
(port 20128 by default, configurable via `PORT` or `OMNIROUTE_PORT` env vars.)

### Hoisted-linker startup fix (Windows — only if you used the wrong linker)

If you used `--config.node-linker=hoisted` for omniroute (the wrong linker —
see above), two issues appear:

1. **`package.json` missing from the package root** — hoisted linker strips
   it. Create a stub: `{"name":"omniroute","version":"3.8.46"}`
2. **`dist/server.js` missing** — the entire pre-built bundle was never
   extracted. The only fix is to reinstall with the default linker
   (`pnpm install --ignore-scripts`, no hoisted flag).

## Set env vars permanently (Windows)

For env vars that must survive reboots (API keys, etc.), use `setx`:
```cmd
setx OPENROUTER_API_KEY "sk-or-v1-..."
```
This writes to the user-level registry — new terminal shells pick it up, but the
current shell doesn't. Combine with `export` in bash or `set` in a `.bat` for the
current session.

Paperclip's `run-server.bat` or Omniroute's `start-omniroute.bat` are the right
places to set per-launcher env vars (add `set VAR=value` before the node command).

## Hiring a Hermes agent (adapterConfig)

```json
{
  "name": "Hermes Engineer",
  "adapterType": "hermes_local",
  "role": "cto",
  "adapterConfig": {
    "model": "tencent/hy3:free",
    "provider": "openrouter",
    "maxIterations": 50,
    "timeoutSec": 1800,
    "persistSession": false,
    "enabledToolsets": ["terminal","file","web"]
  }
}
```
Gotchas (full detail in `references/hermes-free-model-config.md` and
`references/paperclip-agent-management.md`):
- **Provider prefix is NOT repeated in `model`**: `provider:"openrouter"` + `model:"openrouter/tencent/hy3:free"` → HTTP 400. Use `model:"tencent/hy3:free"`. Same for `nous`.
- **`persistSession` must be `false`** for scheduled agent work. `true` resumes a stale
  session and Hermes prints "provide the task" instead of executing the issue.
- **`role` is a fixed lowercase enum** — invalid values are rejected with `invalid_enum_value`.
  Valid: `ceo|cto|cmo|cfo|security|engineer|designer|pm|qa|devops|researcher|general`.
  There is **no `coo` and no `product`** — map them: COO → `devops` (ops/delivery fits),
  Head of Product → `pm`. An invalid role returns a `None` agent (creation looks like it
  failed) — re-create with a valid enum value.
- **Free models are rate-limited / capability-limited.** OpenRouter's shared free pool 429s
  the large models and the small ones that return content are too weak to follow the
  execution contract. For reliable autonomy use a dedicated free key (Groq/Cerebras/NVIDIA NIM)
  or a fallback gateway (OmniRoute). A working free alternative is `deepseek-v4-flash-free`
  via OpenCode Zen (`provider: "auto"`). Debug via `GET /api/heartbeat-runs/<RUN_ID>` → `stdoutExcerpt`.
- **`git` is not a valid Hermes toolset** (it's part of terminal/file) — invalid entries just warn.
- **Autonomous execution needs a task-bridge key** (`POST /api/agents/:id/keys`,
  `scope.kind=task_bridge` with `projectId` = company ID). Without it the agent
  never self-dispatches the issue. The `projectId` field is **required**.
- **Heartbeat is disabled by default** on new agents. Enable it via
  `PATCH /api/agents/:id` with `runtimeConfig: { heartbeat: { enabled: true } }`.
- **`opencode` is NOT a valid `hermes_local` provider.** Valid providers are:
  `auto`, `openrouter`, `nous`, `openai-codex`, `copilot`, `copilot-acp`,
  `anthropic`, `huggingface`, `zai`, `kimi-coding`, `minimax`, `minimax-cn`,
  `kilocode`. Use `"auto"` to let Hermes use its own config.yaml.

## Pitfalls (Windows / MSYS / pnpm)

Full failure modes + exact commands in `references/windows-pnpm-pitfalls.md`. Summary:

- **Auth is endpoint-class dependent, not blanket.** Company-scoped *data* reads
  accept the Netscape cookie file as-is: `curl -b /path/cj.txt GET /api/companies/:id/issues`
  returns `200`. But **agent-control endpoints** (`GET /api/agents/:id`,
  `POST .../heartbeat/invoke`, and any `PATCH /api/agents/...`) reject `-b cj.txt`
  with `401 Unauthorized` — same server, different auth gate. Fix for those: extract the
  `session_token` value (7th tab field on the `localhost` line of `cj.txt`) and pass it
  as a literal `Cookie:` header **plus** `Origin: http://localhost:3100`. Exact working
  commands + observed HTTP codes are in `references/paperclip-api-auth.md`. TL;DR:
  `-b cj.txt` for issue/company reads; `-H "Cookie: <token>" -H "Origin: http://localhost:3100"`
  for anything under `/api/agents/...`. (Mutating *issue* endpoints also need `Origin`.)
- **Agent status running plus currentRunId null equals idle after a server crash.** A crashed
  server leaves the agent flagged running with a 6h-stale heartbeat but no active run. Treat that
  as idle (pending work exists) and invoke heartbeat — the new run transitions to running and
  produces a fresh run-log. Do NOT trust status running alone as proof it is working.
- **Job/cron briefs assert STALE issue state — re-fetch before mutating.** A scheduled
  task brief may claim all 4 issues are in_progress while the live API shows in_review / blocked / done.
  Never PATCH status/assignee to match the brief. Always GET the issues first, read each target's true
  status plus assigneeAgentId, and act on actual state. If a brief's premise is wrong, report the
  divergence and proceed from real state (no destructive changes). This session the brief said all 4
  PRE issues were in_progress; live state was PRE-5/6 in_review, PRE-7 blocked (blocker PRE-74 =
  user-login-gated video publish), PRE-8 done (with child PRE-11 in_progress already tracking
  follow-up). Outcome: nothing to re-assign, no new children needed, only a heartbeat nudge.

- **pnpm install stalls during linking on git-bash** — Symptom: 1248 packages resolved/reused,
  `added 0` frozen for minutes, no `.modules.yaml`. Fix: `pnpm install --ignore-scripts
  --config.node-linker=hoisted`.
- **MSYS path mangling** — passing `C:\one\...` to `node` through bash becomes `C:\c\one\...`
  (extra `c`) → MODULE_NOT_FOUND. Fix: run everything via `cmd.exe /c "C:/path/bat.bat"`;
  inside bats use native `C:\` paths. The `.bin/tsx` shim works; direct
  `node node_modules/.pnpm/tsx@.../cli.mjs` fails.
- **`node dist/index.js` crashes** with `ERR_MODULE_NOT_FOUND` for `packages/db/src/client.js`
  because workspace `exports` point at `./src/index.ts`. Fix: run `tsx src/index.ts`.
- **Embedded PostgreSQL refuses a Windows admin account** ("Execution of PostgreSQL by a user
  with administrative permissions is not permitted"). Fix: external Postgres via `DATABASE_URL`.
- **Creating the PG role/db without the postgres password** — pg_hba is `scram-sha-256`. On
  Windows psql uses TCP `host`, so change the `host 127.0.0.1/32 scram-sha-256` line to `trust`
  (NOT the `local` line — no Unix socket on Windows), `net stop/start` the service, create with
  `psql -U postgres -h 127.0.0.1 -w`, then restore pg_hba. Use `ping -n 4 127.0.0.1 >nul`
  instead of `timeout /t` (MSYS intercepts `timeout`).

- **Server down = battery policy or redacted DB password.** If `:3100` is refused, check first:
  (a) `schtasks` — `PaperclipServer` has `StopIfGoingOnBatteries`/`DisallowStartIfOnBatteries`, so a
  battery stint kills it; just restart. (b) the DB password in `run-server.bat` is `***` (secret-scanned)
  — a fresh boot can't connect; recover the `paperclip` role password via temp-trust pg_hba (see
  "Reviving a downed server" above). Postgres is `scram-sha-256` over TCP on Windows — edit the
  `host` lines, not the `local` line, and restore them after.
- **OpenRouter key is NOT in env/registry** — grep it from `%LOCALAPPDATA%\hermes\.env`
  (`OPENROUTER_API_KEY=`) before launching the server; the agent's free model needs it to execute.
- **MSYS doubles backslash `C:\` to `C:\c\` for node/tsx** → `Cannot find module`. Use forward-slash
  `C:/one/...` absolute paths (they survive intact) and launch via `cmd.exe /c`. Applies to direct
  `node` calls as well as the `.bin/tsx` shim.
- **`curl -b /abs/path/cj.txt` → "failed to open cookie file"** under git-bash (MSYS path rewrite).
  Use a relative `-b cj.txt` from the company dir, or the `Cookie:` header approach.

## Verification checklist

- `GET /api/health` → `{"status":"ok","deploymentMode":"authenticated"}`.
- Server log: `Server listening on 0.0.0.0:3100` and `Migrations applied` / `applied`.
- `/api/adapters` returns `{"error":"Board access required"}` until you log in — expected, not a failure.
- After login, the agent-creation form lists `hermes_local` (and `hermes_gateway`).

## References / templates / scripts

- `references/paperclip-api-auth.md` — exact working auth incantations: `-b cj.txt` for company/issue reads vs `Cookie:` header + `Origin` for `/api/agents/...`; token extraction; heartbeat-invoke returns 202; which routes 404/401/403.
- `references/windows-pnpm-pitfalls.md` — full Windows/pnpm/MSYS failure modes + exact commands.
- `references/paperclip-api-bootstrap.md` — scriptable first-run: sign-up, claim, company, agent, issue, heartbeat, task-bridge key, and the non-obvious route paths/headers.
- `references/paperclip-agent-management.md` — post-setup operations: re-authentication after restart, enabling heartbeat, task-bridge key gotchas, valid providers list, model resolution chain, reading run output, troubleshooting.
- `references/hermes-free-model-config.md` — Hermes model/provider gotchas for hermes_local agents (prefix doubling, persistSession trap, free-model rate limits, OmniRoute install wall, config.yaml sandbox block).
- `references/continuous-operation.md` — keep-alive beyond install: Task Scheduler recipe for watchdog+server, Set-Cookie auth gotcha, reading run output / why stdoutExcerpt is empty until exit, task-bridge `projectId` requirement, artifact work-products retrieval, CTO+CMO revenue pattern.
- `references/omniroute-windows-startup.md` — Windows-specific Omniroute polyfill fix (Node.js 22 .ts import), serve subcommand requirement, hoisted linker recovery, first-run 500 diagnostic.
- `scripts/verify-openrouter-model.sh` — probe a free OpenRouter model for tool-call support before wiring it into an agent (exit 0 = usable for autonomy).
- `scripts/watchdog.py` — Windows-native, zero-LLM watchdog: re-auth, health check, auto-restart server, nudge idle worker agent; pair with Task Scheduler (see `references/continuous-operation.md`).
- `scripts/setup-pg-db.bat` — idempotent: temporarily trusts local PG, creates role+db, restores secure pg_hba.
- `templates/run-server.bat` — parameterized server launcher (sets env, runs tsx, logs to file).
- `templates/watchdog.sh` — no_agent Hermes cron script for 24/7 uptime (pings health endpoint, restarts on failure).

## Reality check

This automates the *work* of a company; it does not generate revenue by itself. You still need
a product people pay for and an API budget. Treat it as a self-running engineering/marketing
team you own and steer.
