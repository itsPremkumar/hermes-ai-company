---
name: paperclip-local-company
description: Stand up a local autonomous "agent company" — Paperclip (the orchestrator) + Hermes Agent employees (via the hermes_local adapter) — on Windows via the Hermes terminal. Covers the verified pnpm/tsx build, the embedded-Postgres-vs-admin trap, and how the Hermes adapter is already bundled in Paperclip main (so you do NOT hand-wire it). Use when the user wants to "run a Paperclip company", "hire a Hermes agent in Paperclip", "build the agent-company stack", or references paperclipai/paperclip + NousResearch/hermes-paperclip-adapter.
---

# Paperclip + Hermes local "agent company"

Paperclip (`paperclipai/paperclip`) is an open-source orchestration platform for running teams of
AI agents as a "company": companies, org chart, goals, budgets, tickets, heartbeats. Hermes Agent
(`NousResearch/hermes-agent`) is a 30+ tool agent. The **hermes_local** adapter lets Paperclip shell
out to the `hermes` CLI as a managed employee.

## Mental model (how the pieces connect)
```
Paperclip (company/orchestrator, Node server + React UI)
   └─ on each heartbeat, calls the hermes_local adapter's execute()
        └─ runs:  hermes chat -q "<task>"   (Hermes uses its 30+ tools)
   └─ results + cost flow back; sessions persist across heartbeats
```
"OpenClaw is an employee, Paperclip is the company." Any agent that can receive a heartbeat can be
hired. Paperclip also supports Claude, Codex, Cursor, Gemini, Grok, OpenCode, Pi, and HTTP adapters.

## KEY FACT — the Hermes adapter is ALREADY bundled
Paperclip's `main` branch **ships** the Hermes adapter:
- `packages/adapters/hermes` + `packages/adapters/hermes-gateway` in the monorepo
- `server/src/adapters/registry.ts` imports `createHermesLocalServerAdapter` / `createHermesGatewayServerAdapter`
  from `@paperclipai/hermes-paperclip-adapter`
- The standalone `NousResearch/hermes-paperclip-adapter` repo is the **upstream source** (published as
  `@paperclipai/hermes-paperclip-adapter`). A normal `pnpm install` of Paperclip already gives you
  `hermes_local` + `hermes_gateway` adapters. **Do NOT hand-patch the registries** — just add a
  `hermes_local` agent after first run.

Two adapter modes:
- `hermes_local` — Paperclip starts `hermes chat` as a child process (same trusted host). Needs `hermes` on PATH.
- `hermes_gateway` — Paperclip calls an already-running Hermes API server over HTTP/SSE.
  Start Hermes gateway first: `API_SERVER_ENABLED=true API_SERVER_KEY=<secret> hermes gateway run --replace --accept-hooks`

## Prerequisites (this machine had all of these)
- Node 22+, pnpm (install via `npm i -g pnpm@9` if missing; corepack is flaky here)
- Hermes Agent installed (`hermes` on PATH). Windows native install:
  `iex (irm https://hermes-agent.nousresearch.com/install.ps1)`
- At least one LLM key for Hermes (in `~/.hermes/.env`, or via Nous Portal).
- **Model auto-detect trap**: leaving the agent `model` blank defaults to `"auto"`,
  which passes `-m auto` — Hermes then auto-detects a model instead of using its
  configured default. Always set `model` explicitly.

## Verified Windows build + run (native, no Docker needed)
Docker path exists (docker-compose.yml in repo) but the **Docker daemon is often OFF** on this host —
prefer the native run below. Paperclip uses embedded Postgres by default, but embedded Postgres
**refuses to run under a Windows admin account** (see Pitfalls). Use an external Postgres via
`DATABASE_URL` (a full PostgreSQL is frequently already installed as a Windows service on :5432 — point
Paperclip at it).

Step-by-step:
1. Clone: `git clone https://github.com/paperclipai/paperclip` (depth 1 is fine).
2. Install deps. The default pnpm linker **stalls on the MSYS git-bash shell** during linking — use
   hoisted linker (see Pitfalls). From the repo root:
   `pnpm install --ignore-scripts --config.node-linker=hoisted`
3. Build all workspace packages: `pnpm build` (tsc passes with 0 errors on a clean tree).
4. Start the server with **tsx on the source** (NOT `node dist/index.js` — see Pitfalls):
   `../node_modules/.bin/tsx src/index.ts`  (run from `server/`)
   Pass env (see env block / templates/run-server.bat). With `DATABASE_URL` set to your external
   Postgres, it migrates and listens on PORT (default 3100).
5. Open `http://localhost:3100` → create owner account → create company → add agent `hermes_local`.
   Or script it via the REST API (see references/quickstart.md).

## Server env (set before launch)
```
PORT=3100
HOST=0.0.0.0
SERVE_UI=true
BETTER_AUTH_SECRET=<any-string, dev-only>
PAPERCLIP_DEPLOYMENT_MODE=authenticated      # first run creates an owner account
PAPERCLIP_DEPLOYMENT_EXPOSURE=private
PAPERCLIP_PUBLIC_URL=http://localhost:3100
PAPERCLIP_HOME=<writable dir>
PAPERCLIP_MIGRATION_AUTO_APPLY=true
DATABASE_URL=postgres://<user>:<pass>@localhost:5432/paperclip   # REQUIRED on Windows admin accounts
```

## Creating a Hermes employee (agent payload)
```json
POST /api/companies/:companyId/agents
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
    "enabledToolsets": ["terminal","file","web"],
    "checkpoints": false,
    "quiet": true
  }
}
```

### Post-creation steps (agent won't work without these)
1. **Enable heartbeat** — new agents boot with heartbeat **disabled**:
   ```bash
   PATCH /api/agents/<AGENT_ID>
   {"runtimeConfig": {"heartbeat": {"enabled": true, "maxConcurrentRuns": 3}}}
   ```
2. **Create task-bridge key** — required for autonomous issue execution:
   ```bash
   POST /api/agents/<AGENT_ID>/keys
   {"scope": {"kind": "task_bridge", "projectId": "<COMPANY_ID>"}, "name": "bridge"}
   ```
   The `projectId` field is mandatory. Returns a `pcp_...` token auto-injected as
   `PAPERCLIP_BRIDGE_API_KEY` into the Hermes subprocess.
3. **Reset session** after any config change:
   ```bash
   POST /api/agents/<AGENT_ID>/runtime-state/reset-session
   {}  # empty body is required
   ```

### Model & provider notes
- Valid `hermes_local` providers: `auto`, `openrouter`, `nous`, `openai-codex`,
  `copilot`, `copilot-acp`, `anthropic`, `huggingface`, `zai`, `kimi-coding`,
  `minimax`, `minimax-cn`, `kilocode`. **`opencode` is NOT valid.**
- Empty model → defaults to `"auto"` → passed as `-m auto` (Hermes ignores its
  configured default and auto-detects). Always set model explicitly.
- Known working free models: `tencent/hy3:free` (via openrouter, needs
  `OPENROUTER_API_KEY` in server env), `deepseek-v4-flash-free` (via auto,
  needs `OPENCODE_ZEN_API_KEY` in `~/.hermes/.env`).

## Continuous autonomous operation (the lifecycle after setup)

Once the Hermes agent is hired and the heartbeat is enabled, the company runs itself — but
with specific handoff patterns the founder/board must understand.

### Issue lifecycle
1. **Create an issue** (via UI or API) with a clear description.
2. If you set `assigneeAgentId` on creation, Paperclip **immediately starts a heartbeat
   run** for that agent — no wait for the next tick. If you leave assignee blank, the
   issue sits in `todo` until assigned.
3. **Agent picks it up** on the next available heartbeat. It reads the issue, creates
   Python scripts, executes work (terminal commands, file edits, API calls to Paperclip).
4. **Agent produces deliverables** — artifacts uploaded as issue attachments, work products
   created, issue status updated.
5. **Agent creates child issues** for follow-up work (e.g., PRE-3 → PRE-5 through PRE-8).
6. **Agent sets issue to `done` or `in_review`** and exits cleanly.

### Critical pattern: agent does NOT self-assign, but the SERVER auto-triggers
The Hermes CTO agent creates child issues but **never assigns itself to them** — it leaves
them as `todo` with no assignee, expecting the board/founder to confirm. This is an agent
behavior, NOT a server limitation.

**However**, if YOU (the cron/founder) create an issue via API with `assigneeAgentId` set,
Paperclip **immediately auto-starts a heartbeat run** for it. The server respects
`maxConcurrentRuns` (default 3) — if the agent is at capacity, new runs queue until a slot
opens.

To keep the pipeline moving:
- **Via cron:** set up a 15-minute cron job that assigns unassigned `todo` issues to the
  agent AND creates follow-up child issues for `done` items (see "Cron job for continuous
  development" below).
- **Via API:** when creating child issues for completed work, set `assigneeAgentId` to
  the agent's UUID and Paperclip auto-starts execution.
- **Manually:** after each completed cycle, assign new issues via UI or API.

### Heartbeat reliability
Each agent run starts a `hermes chat` subprocess. The model response time determines run
duration (~3–4 min for a full issue cycle). If the subprocess is lost (killed/crashes), the
run stays in "running" state in Paperclip. **Fix:**
```bash
# Extract cookie value (curl -b cj.txt fails on git-bash — MSYS path issue)
TOKEN=$(grep 'paperclip-default.session_token' /c/one/paperclip-company/cj.txt | awk '{print $NF}')

# Cancel the stale run (needs Cookie + Origin + Referer)
curl -s -X POST "http://localhost:3100/api/heartbeat-runs/<RUN_ID>/cancel" \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Referer: http://localhost:3100/"

# Reset session and re-trigger
curl -s -X POST "http://localhost:3100/api/agents/<AGENT_ID>/runtime-state/reset-session" \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Content-Type: application/json" -d '{}'

curl -s -X POST "http://localhost:3100/api/agents/<AGENT_ID>/heartbeat/invoke" \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Referer: http://localhost:3100/"
```
**Heartbeat invoke header note:** the `/heartbeat/invoke` endpoint checks for a trusted
browser origin and returns `"Board mutation requires trusted browser origin"` without
browser-emulating headers. You need `Cookie` + `Origin` + `Referer` (or
`X-Requested-By: paperclip` instead of `Referer`). The 3-header set (Cookie + Origin +
Referer) is the simplest reliable combination. Using `-b cj.txt` alone fails on git-bash
because MSYS path rewriting interferes with curl's `-b` flag — always prefer the cookie-header
approach shown above.

### Diagnosing a stuck heartbeat (before cancelling)
Before cancelling a stale run, check whether the agent actually produced output or just
went silent. Each run's stdout/stderr is persisted as a per-run ndjson log:

```bash
# Find the most recent run logs by modification time
ls -lt /c/one/paperclip-company/data/paperclip/instances/default/data/run-logs/<COMPANY_ID>/<AGENT_ID>/*.ndjson

# Check the last 20 lines — was the agent making progress?
tail -20 <latest-run>.ndjson

# Each line: {"ts":"...","stream":"stdout|stderr","chunk":"...","seq":N}
# Key signals the agent is still alive:
#   - Recent timestamps (within the last few minutes)
#   - Tool call output (code changes, API responses, file diffs)
#   - `[hermes]` lifecycle messages
# Key signals the agent stalled:
#   - Last timestamp hours ago with no new lines added
#   - `RateLimitError [HTTP 429]` or similar API errors
#   - `[hermes] Exit code: 0` or `[hermes] Exit code: 1` — process exited cleanly but Paperclip didn't notice
```

If the run log shows a clean exit code (`Exit code: 0`), the agent finished the work but
Paperclip didn't update the run status — cancel + reset + retrigger. If it shows rate-limit
errors or a last-output timestamp hours ago, the subprocess died and needs the same fix.

**Corrective/handoff run silently dying (PRE-7 pattern).** When a prior run times out or
exits, the system may auto-create a *corrective* or *handoff* run (`correctiveRunId` in the
issue's `successfulRunHandoff` points to the new run). These corrective runs sometimes die
before producing any meaningful output. Diagnostic:

- The new run's `.ndjson` log has only 3–4 startup lines (workspace fallback warning,
  `Warning: could not read agent instructions file`, `Starting Hermes Agent`,
  `Resuming session: ...`) — nothing more, even after several minutes.
- The log file is ~700–800 bytes (startup noise only).
- The API may briefly show `activeRun: { status: "running" }` but later reflect
  `activeRun: null` as the server cleans up the ghost.
- The agent's own endpoint (`GET /api/agents/:id`) shows `status: "idle"` because the
  dead run was never formally cancelled.

**Fix:** invoke a fresh heartbeat (see the `heartbeat/invoke` call above). No need to cancel
the dead run — it was never truly alive. The fresh invoke creates a new run that picks up the
issue from scratch. Use the cookie-header approach (not `-b cj.txt`) to sidestep the MSYS
path issue on git-bash. **NOTE: `POST /api/agents/<ID>/runtime-state/reset-session`
is board-gated (assertBoard) — with the company cookie in `cj.txt` it returns 400/401 and
does NOT clear state for the operator. Don't rely on it; the heartbeat-invoke path works
without a board token.**

### Zombie server process (Node alive, port not serving)
Paperclip's Node process can appear in the process list while the HTTP server is not serving
requests. This happens when the process hangs internally without fully terminating:
- `ps -W | grep node` shows node.exe alive with a PID
- `curl -s --max-time 5 http://localhost:3100/api/health` returns connection refused (exit code 7)
- `netstat -ano | grep 3100` returns nothing — port is unbound
- The process is a zombie: occupies memory and a PID slot but does no work

**Detection:** Always test the health endpoint, not just the process list. A running Node
process with a health endpoint that doesn't respond IS a zombie.

**Recovery sequence when the server is a zombie:**
1. Kill the stale Node process by PID: `kill -9 <PID>` (git-bash) or `taskkill /F /PID <PID>` (cmd)
2. Verify port is free: `netstat -ano | grep 3100` returns nothing, curl still fails
3. Start the server (run-server.bat or tsx command)
4. Wait for health endpoint to return `{"status":"ok"}`
5. Reset the agent's runtime session (stale after crash):
   `POST /api/agents/<ID>/runtime-state/reset-session`
   **NOTE: board-gated** — with the company cookie in `cj.txt` it returns 400/401,
   so the operator can't run it. Prefer the heartbeat-invoke path (works with the
   company cookie) to re-dispatch; if the agent is in `error`, first swap its model
   off `tencent/hy3:free` (see the soft-error pitfall above) then invoke.
6. Invoke heartbeat: `POST /api/agents/<ID>/heartbeat/invoke`
7. Verify dispatch: check run-logs directory for new `.ndjson` files within 60 seconds

**Cron-safe approach:** Before any agent-state operations, probe `/api/health`. If it fails
but the process is alive, recover the server first — don't attempt heartbeat operations on
a zombie instance.

### Heartbeat invoke queue vs. scheduler tick
Calling `POST /api/agents/<ID>/heartbeat/invoke` returns a run with status `"queued"`. However,
the agent's 30-second heartbeat tick scheduler is independent — it dispatches runs for the
highest-priority issues automatically. When `maxConcurrentRuns` (default 3) is saturated, the
queued invoke stays `queued` until a slot opens, while the tick continues dispatching new runs.

**Immediate agent status transition.** Calling `/heartbeat/invoke` changes the agent's `status`
from `"idle"` to `"running"` instantly, even though no actual run has started yet
(`activeRunId` remains `null`). This `"running"` status means "nudged / has accepted work" —
the agent is in a transitional state between idle and executing. Do NOT treat `status: "running"`
as proof that a run is actively executing; cross-reference with `activeRunId` and the
run-logs directory.

**Don't rely on the queued run status to determine if the agent is working.**
Instead, check the run-logs directory for new files:
```bash
ls -lt /c/one/paperclip-company/data/paperclip/instances/default/data/run-logs/<COMPANY_ID>/<AGENT_ID>/*.ndjson | head -5
```
If new log files appear with recent modification timestamps, the scheduler is healthy and
the agent is being dispatched. The queued invoke is a safety-net trigger, not the primary
dispatch mechanism.

**Practical implication for cron jobs:** After invoking heartbeat, don't poll the run status
endpoint — check for new run-log files instead. If new logs appear within 60 seconds, the
scheduler is working and the agent is active. The agent's `status` field will already be
`"running"` from the invoke nudge, so use `lastHeartbeatAt` + run-log presence (not just
`status`) to determine whether the agent is truly executing work.

**Pro tip:** run logs use UUID filenames (not issue IDs). Cross-reference by checking the
`PAPERCLIP_TASK_ID` or `issueId` in the context snapshot within the log's first JSON line
to identify which issue a run was serving.

### Board mutations need Cookie + Origin (and sometimes Referer/X-Requested-By) headers
PATCH/DELETE endpoints on issues and agents require `Origin: http://localhost:3100` AND a valid
session cookie — otherwise you get `"Board mutation requires trusted browser origin"`. Always
pass the cookie via the `Cookie` header (not `-b`, which fails on git-bash):
```bash
TOKEN=$(grep 'paperclip-default.session_token' /c/one/paperclip-company/cj.txt | awk '{print $NF}')
curl -s -X PATCH "http://localhost:3100/api/issues/<ID>" \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Content-Type: application/json" \
  -H "X-Requested-By: paperclip" \
  -d '{"status":"done"}'
```
**Important:** `Origin` alone may still return 403 in some setups. Always include
`X-Requested-By: paperclip` (or `Referer: http://localhost:3100/`) alongside `Origin` for
reliable mutations. This was verified: `Origin` alone → 403, adding `X-Requested-By: paperclip`
→ 200.

### Session cookie survival depends on database engine
With **external PostgreSQL** (`DATABASE_URL` set, the recommended setup for Windows admin
accounts), Better Auth sessions are stored in the database and **survive server restarts**.
The same cookie works before and after restart — no re-authentication needed. Verified:
server stopped at 07:37, restarted at 07:54, same cookie accepted immediately.

With **embedded Postgres** (no `DATABASE_URL`, default), the ephemeral DB is created fresh on
each server start, so session data is lost. Re-authentication is required:
```bash
TOKEN=$(grep 'paperclip-default.session_token' /c/one/paperclip-company/cj.txt | awk '{print $NF}')
curl -s -X POST "http://localhost:3100/api/auth/sign-in/email" \
  -H "Content-Type: application/json" \
  -d '{"email":"prem@local.dev","password":"LocalDevPass123!"}' \
  -H "Cookie: paperclip-default.session_token=$TOKEN" -H "Origin: http://localhost:3100"
```
(Use `-c cj.txt` on the first sign-in to save the cookie to the file, then extract the token
for subsequent requests with the `grep | awk` pattern.)

### PATCH adapterConfig normalization trap
When you PATCH an agent's `adapterConfig` WITHOUT `replaceAdapterConfig: true`, the
`normalizeMediatedAdapterConfigForPersistence` function MAY overwrite `model`/`provider`
with values detected from the Hermes config. **Nuance (verified 2026-07-15):** this
session PATCHed all 7 agents from `tencent/hy3:free` -> `anthropic/claude-3.5-haiku`
via the company cookie (`PATCH /api/agents/:id` with `{"adapterConfig":{"model":...,"provider":"openrouter"}}`)
and a follow-up `GET /api/agents/:id` CONFIRMED the new model PERSISTED. So the
normalization did NOT clobber it here. If you ever see the response show your value
but a re-GET shows the OLD model, the merge fired — fix by passing
`replaceAdapterConfig: true` in the PATCH body to bypass the merge logic. The model-swap
recovery in `references/soft-error-hy3.md` (paperclip-company-ops skill) relies on the
plain PATCH persisting, which it did.

## Cron job for continuous development

Set up a periodic cron job that monitors the issue pipeline and advances work so the
founder doesn't need to assign issues manually:

```bash
hermes cron create --name "company-revenue-pulse" --schedule "every 15m" \
  --prompt "Check the Paperclip company and advance revenue work.
- Fetch issues via GET /api/companies/{companyId}/issues
- For 'done' issues, create follow-up child issues if appropriate
- For unassigned 'todo'/'backlog' issues, assign to the agent and set in_progress.
- If agent is idle and work exists, invoke heartbeat: POST /api/agents/{id}/heartbeat/invoke" \
  --enabled-toolsets terminal,file,web
```

The long-running agent heartbeat loop (30s) processes issues one at a time, while the
15-minute cron handles pipeline management (assigning, creating follow-ups, triggering).

The full operational checklist for each cron execution — stale-run detection, session
reset, follow-up creation, timeout unblocking, and dispatch verification — is documented
in `references/cron-pipeline-workflow.md`. Load this file before writing or modifying
the cron prompt. The "Data Processing Mechanics for Cron Jobs" section in that file details the
JSON pipe-breakage workaround (multi-line descriptions), PATCH 400 diagnosis, and run-log summary
scanning for next-step recommendations — essential implementation patterns for cron execution.

## Maintaining the knowledge base (GitHub as single source of truth)

The company is built locally at `/c/one/paperclip-company`, but a local-only company drifts and is
fragile. Establish GitHub as the canonical store and treat every document/prompt/tool as versioned
knowledge. Full verified commands + pitfalls: `references/github-knowledge-base.md`.

### Triggering principle
"If it isn't committed, it isn't done." Push the real, running company (products, income engine,
finance ledger, `hermes-paperclip-adapter` source, COMPANY_PLAN, status snapshot) — not just a
constitution doc. Create two repos: `Hermes-Full-Autonomous-Company` (the OS) and
`Hermes-Prompt-Library` (versioned prompts).

### Prompt-consolidation discipline (this is a class of work, not a one-off)
Users will hand you several overlapping "master prompt / constitution" drafts. Do NOT push them all
as-is. Instead:
1. **Adopt the draft whose structure matches the REAL stack** as the spine. Here that was
   `hermes-master-operating-prompt.md` (Paperclip + OpenClaw + budget caps + human-in-the-loop).
2. **Drop fictional-stack assumptions.** Drafts routinely list tools you do NOT run (n8n, Mem0,
   CrewAI, AutoGen, standalone "OmniRouter", OpenHands). The actual stack is Paperclip + Hermes +
   OpenClaw + `hermes-paperclip-adapter` + OmniRoute→OpenRouter + Automated-Video-Generator.
3. **Consolidate into ONE versioned constitution** (`CONSTITUTION.md` = master operating prompt v2.0).
   Archive superseded drafts in `prompts/archive/` — never delete (they ARE the version history).
4. **Never build on unverified "leaked system prompts"** (e.g. "Claude Fable 5"). Prefer
   officially-published guidance.
5. **Embed the low-RAM memory-discipline rule** explicitly (this box runs at ~70–150 MB free):
   close tools after use, exclude `node_modules` from pushes, clean up staging dirs.

### Governance contract to preserve (Section 0 of the constitution)
Money has a human in the loop (budget caps + approval gates), no binding commitments without
sign-off, no deceptive claims, compliance is mandatory, self-improvement = better skills/docs not
unsupervised self-editing of the charter. Any change to Section 0 is a human-reviewed decision.

### THIS-USER auto-push rule (load-bearing — corrected by the user more than once)
The user stated explicitly and repeatedly: **push ALL code automatically to his `itspremkumar`
GitHub account via git CLI — never ask for approval and never ask for a token.** Git uses
**cached Windows Credential Manager creds** for `itspremkumar`, so just run `git init/add/commit/push`
and it authenticates silently. If a "Select an account" modal appears, that is a BUG (a stale
`x-access-token` identity in GCM) — FIX it per `git-credential-manager-windows`, do NOT ask the
user. `gh` CLI is not installed; use git CLI + `curl` with the cached token for any GitHub API call.
Treat every push as going to `itspremkumar/*`.

### OS-spec implementation pattern (reviewer/architecture-suggestion → repo artifacts)
When the user (or a reviewer) hands a list of architecture improvements for the company, do NOT
paste them into the constitution as prose. Implement them as **concrete, auditable repo artifacts**
— this is the "repository = operating system" principle: the constitution defines agent *behavior*;
the repo defines the *system*. Verified recipe (the v2.0 → v3.0 bump):
1. For each suggestion, create a real file: `docs/<subsystem>.md` (spec),
   `knowledge-base/<x>.md` (state/metrics), `agents/registry.md` (agent interface),
   `tools/repo-index.md` (catalog).
2. Wire the *behavioral* ones into `autonomy-loop.py` (the 24/7 cron brain) — e.g. a **confidence
   gate** (≥75 proceed+validate, 50–74 consult second model, <50 escalate to human) and a **benchmark
   logger** that appends a row to `knowledge-base/benchmarks.md` every tick (RAM, success/failure
   rate, revenue, automation coverage).
3. Add a `CONSTITUTION.md` Section 17 table mapping each subsystem → its real file, so the spec is auditable. Bump the version (v2.0→v3.0).
4. Reject "invent a new service" suggestions (n8n/Mem0/CrewAI event-bus) — map the subsystem onto
   what ACTUALLY runs (Paperclip + cron + GitHub + Hermes memory). Don't bloat a low-RAM box.
5. Run an ad-hoc verifier (`hermes-verify-*.py`) against the changed loop; fix any bug it finds;
   then commit + push (auto, per the THIS-USER rule above).

## PITFALLS (all hit and solved this session)
- **pnpm install "hangs" on MSYS/git-bash**: node_modules size freezes, no `@paperclipai` symlinks
  appear, yet network is active. Cause: the default `isolated` linker does slow/hung hardlink+symlink
  resolution under MSYS. **Fix: `pnpm install --ignore-scripts --config.node-linker=hoisted`.** Hoisted
  links in seconds. (The `--ignore-scripts` skips the harmless `link-plugin-dev-sdk` postinstall; you
  then `pnpm build` explicitly.)
- **`node dist/index.js` fails** with `ERR_MODULE_NOT_FOUND` (e.g. can't find
  `packages/db/src/client.js`). Cause: workspace packages declare `exports: { ".": "./src/index.ts" }`
  — they resolve to **source .ts**, not built `dist`. **Fix: run via tsx** —
  `../node_modules/.bin/tsx src/index.ts` from `server/`. tsx loads `.ts` exports fine.
- **⚠️ Launch-command backslash mangling (THE most common first-launch failure on git-bash).** The
  repo's `run-server.bat` uses Windows backslash paths (`C:\one\paperclip-company\...`).
  Under git-bash those backslashes get mangled INTO the command itself, producing a
  confusing-not-found error that looks like a missing file, NOT a path issue:
  ```text
  bash: exec: C:onepaperclipcompanypaperclipnode_modulesbintsx: not found
  ```
  (note: `C:\one\...` → `C:onepaperclip...` — the slashes vanished, not escaped).
  **Fix:** launch from a git-bash shell using **forward-slash MSYS paths** for EVERYTHING —
  the `cd`, the env `PAPERCLIP_HOME`, and the tsx/node binary:
  ```bash
  cd /c/one/paperclip-company/paperclip/server
  export PAPERCLIP_HOME=/c/one/paperclip-company/data/paperclip   # FORWARD slashes
  node node_modules/tsx/dist/cli.mjs src/index.ts                # NOT C:\one\...
  ```
  The `run-server.bat` is fine when double-clicked from a real `cmd.exe`, but for Hermes/git-bash
  launches always translate to forward slashes.
- **⚠️ Do NOT `exec` the launch command inside a `terminal(background=true)` shell.** `exec`
  detaches and the process silently dies (you'll see `bash: no job control in this shell` then the
  port never binds). **Fix:** just run `node ...` directly as the background command (no `exec`, no `nohup`/`setsid`
  wrappers — the tool tracks the child PID itself).
- **⚠️ `run-server.bat` RAM cap OOMs a 6 GB box — override it.** The bat sets
  `set NODE_OPTIONS=--max-old-space-size=8192` (8 GB). On this host (~6 GB, often 70–150 MB free)
  that makes the server allocate 8 GB and the box freezes / the process is killed. **Fix:** when launching from
  git-bash, export a RAM-safe cap instead:
  ```bash
  export NODE_OPTIONS="--max-old-space-size=1500"   # NOT 8192
  ```
  Verified: with 1500 the server boots cleanly and holds at ~330 MB free; with 8192 it OOMs.
  (Same low-RAM discipline as the OpenClaw gateway — see `openclaw-setup` Pitfall 2.)
- **Do NOT call tsx by its absolute `.pnpm` path.** The MSYS shell rewrites `C:\one\...` → `C:\c\one\...`
  and node then reports `Cannot find module 'C:\c\one\...'`. Use the **relative shim**
  `../node_modules/.bin/tsx` (works) or a `.bat` that uses the native `C:\one\...` `.bin\tsx` path.
- **Embedded Postgres refuses admin accounts on Windows**: error
  *"Execution of PostgreSQL by a user with administrative permissions is not permitted."* Cause: the
  interactive user is an admin. **Fix: set `DATABASE_URL` to an external PostgreSQL.** A full PostgreSQL
  17 is often already installed as a Windows service on :5432 (runs under a service account, not the
  admin user) — just `createdb paperclip` (or let Paperclip migrate) and point `DATABASE_URL` at it.
- **Adapter already bundled** — don't edit `server/src/adapters/registry.ts` or `ui/src/adapters/*`.
  Adding a `hermes_local` agent via UI/API is all that's needed.
- **Docker daemon off** — skip compose; use the native tsx run above.
- **Heartbeat disabled by default** — agent stays "idle" and never executes work.
  Must set `runtimeConfig.heartbeat.enabled: true` explicitly after creation.
- **Empty model → `-m auto`** — blank model field defaults to `"auto"` which passes
  `-m auto`. Hermes with `-m auto` ignores its configured `config.yaml` default and
  auto-selects a model (often falls back to OpenRouter free pool → 429 rate limits).
  Always set model explicitly.
- **Task-bridge key needs `projectId`** — `scope.kind: "task_bridge"` without
  `scope.projectId` returns `"task_bridge keys require at least one project or parent
  issue boundary"`. Pass the company UUID as `projectId`.
- **`opencode` is not a valid `hermes_local` provider** — the adapter's
  `VALID_PROVIDERS` list (from `constants.ts`) does not include it. Setting it causes
  fallthrough to model-prefix inference or `"auto"`. Valid providers: `auto`, `openrouter`,
  `nous`, `openai-codex`, `copilot`, `copilot-acp`, `anthropic`, `huggingface`, `zai`,
  `kimi-coding`, `minimax`, `minimax-cn`, `kilocode`.
- **Session cookie expires on server restart** — Better Auth invalidates sessions.
  Re-login via `POST /api/auth/sign-in/email` after each restart. Use
  `-H "Origin: http://localhost:3100"` for mutation endpoints.
- **PATCH adapterConfig normalization overwrites model/provider** — the
  `normalizeMediatedAdapterConfigForPersistence` function reads Hermes config and
  overwrites `model` and `provider`. PATCH response may show your values but they
  are not persisted. Set values in Hermes `config.yaml` directly, or pass
  `replaceAdapterConfig: true` in the PATCH body.
- **Agent does NOT self-assign child issues** — the CTO agent creates follow-up
  issues but leaves them unassigned. Founder must assign them manually or via cron.
- **Board mutations need `Origin: http://localhost:3100`** — PATCH/DELETE on issues
  and agents return `"Board mutation requires trusted browser origin"` without it.
  Always pass the cookie via the `Cookie` header (not `-b`, which fails on git-bash)
  plus `Origin` and `Referer` or `X-Requested-By` headers.
- **Heartbeat runs can get stuck** — if the Hermes subprocess is killed/crashes,
  Paperclip keeps the run in "running" state. Cancel the stale run and reset the
  agent session before re-triggering.
- **Done issue auto-dispatches a fresh run (PRE-18 pattern)** — an issue marked
  `status: done` can still receive a new heartbeat run if Paperclip's scheduler
  dispatches it after the issue was already completed. The run's `startedAt`
  timestamp is *after* the issue's `completedAt`. The agent loads the issue,
  sees it's done, and exits immediately — producing a run log with only 2–3
  lines (startup warnings + "Starting Hermes Agent") and no tool output. This
  run occupies a `maxConcurrentRuns` slot indefinitely until cancelled.
  **Diagnostic:** issue has `activeRun` with `status:running` AND the run log
  is ~700–800 bytes (only startup messages). **Fix:** cancel the stale run
  and reset the agent session.
- **Zombie server process (Node alive, port not serving)** — the Paperclip Node
  process can appear in the process list but the HTTP server is not actually bound
  to port 3100. `ps -W | grep node` shows it alive but `curl localhost:3100/api/health`
  returns connection refused (exit code 7). The process is hung internally — a zombie.
  **Fix:** kill the stale Node PID (`kill -9 <PID>`), verify the port is free
  (`netstat -ano | grep 3100` returns nothing), restart the server, then reset agent
  runtime session and re-trigger heartbeat. Always test the health endpoint before
  acting on agent state — process-list presence alone is misleading.
- **AGENTS.md instructions file missing** — the heartbeat run log starts with
  `Warning: could not read agent instructions file "C:\\...\\AGENTS.md": ENOENT`.
  The agent runs without company-specific context, producing generic output that
  does not reference the company playbook, budget caps, or operating principles.
  **Fix:** create the instructions directory and a `templates/AGENTS.md`-style
  instructions file at the expected path:
  `<PAPERCLIP_HOME>/instances/default/companies/<CID>/agents/<AGENT_ID>/instructions/AGENTS.md`.
  Load the `templates/AGENTS.md` template from this skill, fill placeholders,
  and write it. After creating the file, reset the agent session:
  `POST /api/agents/<ID>/runtime-state/reset-session`.
- **Agent "soft error" state (status: error, "Process lost -- server may have restarted")** —
  after repeated run failures the agent status sticks at `"error"` with that errorReason.
  On THIS company the recurring root cause is the **default `tencent/hy3:free` model**
  (OpenRouter free tier drops connections / 429s). The fix is a **model swap, NOT a reset-session**:
  `PATCH /api/agents/:id` with `{"adapterConfig":{"model":"anthropic/claude-3.5-haiku","provider":"openrouter"}}`
  (Cookie + Origin + JSON body; the company cookie is sufficient — NOT board-only).
  After the swap the agent STILL shows `error` until it completes ONE successful run —
  so **invoke a heartbeat** (`POST /api/agents/:id/heartbeat/invoke`, `202` queued);
  on the next `succeeded` run the flag clears and status flips to `idle`. Verified 2026-07-15:
  all 4 error agents recovered this way.
  **CRITICAL correction:** `POST /api/agents/:id/runtime-state/reset-session` is guarded by
  `assertBoard(req)` — with the **company** cookie in `cj.txt` it returns **400/401** and does
  NOT clear the flag. Do NOT rely on it to fix soft errors as the operator. The model-swap
  + heartbeat-success path needs no board token.
  **Nuance vs the old "don't invoke heartbeats on soft-error agents" rule:** that is correct ONLY
  *before* the root cause is fixed (invoking an unfixed `hy3:free` agent just re-fails and feeds
  the loop). *After* you swap to a reliable model, invoking the heartbeat is exactly what clears
  the flag. So: **fix model → THEN invoke.** Full recipe in `references/soft-error-hy3.md`
  (in the paperclip-company-ops skill). See `references/agent-run-patterns.md` for diagnosis.
- **Heartbeat invoke can stay "queued" indefinitely** — calling
  `POST /api/agents/<ID>/heartbeat/invoke` returns a `queued` run, but if the
  scheduler's 30-second tick is already at `maxConcurrentRuns` capacity, the
  queue does not drain until a slot opens. The agent may still be working via the
  tick scheduler. Verify agent activity by checking the run-logs directory for
  new `.ndjson` files, not by polling the queued run's status endpoint.
- **Heartbeat invoke COALESCES with an in-flight run (no duplicate spawned)** — calling `POST /api/agents/<ID>/heartbeat/invoke` while a run is ALREADY active (agent `status` was `running`, the run started minutes earlier and still has `finishedAt: null`) does NOT create a new run. It returns the **existing** run object — same `id` and same `startedAt` as the in-flight run, `status: "running"`. A cron job must not assume each invoke kicks off fresh work: if the returned runId matches the agent's currently-known active run, the invoke simply **coalesced** with the run already underway (it merged into the existing cycle, it did NOT fail). Only when the agent is **idle** does the invoke queue a genuinely NEW run (distinct runId, `status: "queued"` → `running`). Practical implication: after invoking, cross-check the returned runId against the run-logs dir — a brand-new `.ndjson` file means a fresh run; the same/recently-touched file means the invoke coalesced. Don't double-count a coalesced invoke as new progress, and don't mistake it for a failed invoke either. (Verified this session: an invoke fired while a 03:23 run was still finishing returned that same `8d6aca26` run; a later invoke after the agent went idle queued a new `3d76bf39` run.) This is distinct from the scheduler's independent 30-second tick — the manual invoke is a safety-net nudge that merges with any run already in flight.
- **MSYS rewrites `-b /c/...` paths for curl** — in git-bash, `curl -b /c/one/.../cj.txt`
  fails with `failed to open cookie file` because MSYS rewrites `/c/` but curl's `-b`
  flag doesn't go through the same path expansion as file arguments. **Fix options** (try
  in order of reliability):
  1. Use the native Windows path with quotes: `--cookie C:/one/paperclip-company/cj.txt`
  2. Keep cookie files in the current directory and use the relative `-b cj.txt`.
  3. **Fallback (always works):** pass the raw cookie value via the `Cookie` header, which
     bypasses both MSYS path rewriting and Netscape cookie-file format issues:
     ```bash
     TOKEN=$(grep 'paperclip-default.session_token' /c/one/paperclip-company/cj.txt | awk '{print $NF}')
     curl -s -H "Cookie: paperclip-default.session_token=$TOKEN" "http://localhost:3100/api/..."
     ```
     The token is the last whitespace-delimited field on the cookie-file line. This approach
     works for both GET reads and POST mutations (pair with `Origin` header for writes) and
     sidesteps all filesystem-path and cookie-format pitfalls at once.
- **Windows `python.exe` rejects MSYS absolute paths** — when you run the Windows Python
  interpreter from git-bash, `open('/c/one/.../file.json')` raises `FileNotFoundError` even
  though shell `ls /c/one/...` works (MSYS only translates paths for some tools, not the
  Windows Python runtime). **Fix:** `cd` to the dir first and use a *relative* path
  (`open('file.json')`), or pass a Windows-style `C:\\one\\...\\file.json` path. This bites
  every time you parse run-logs / issues JSON with `python` instead of `execute_code` — and
  note **`execute_code` is BLOCKED in cron mode** ("runs arbitrary local Python… Cron jobs
  run without a user present to approve it"), so a cron pass must write the script with
  `write_file` and run it via `terminal` + `python`.
- **Cookie file domain format matters** — `curl -b file.txt` parses Netscape cookie files.
  If the domain line has `HttpOnly_localhost` (written by some auth flows), curl skips it
  because the domain `HttpOnly_localhost` doesn't match the request to `localhost`. **Fix:**
  the domain in the cookie file must be just `localhost` (no prefix). The `watchdog-cj.txt`
  has the correct format (`localhost`); `cj.txt` from a fresh sign-in may have the wrong
  format (`#HttpOnly_localhost`). Regenerate with `-c` flag, or edit the file to remove
  `#HttpOnly_` from the domain.
- **Issue creation auto-starts heartbeat runs** — POST a new issue with `assigneeAgentId`
  set, and Paperclip IMMEDIATELY fans out a heartbeat run. No 30s wait. This is distinct
  from the "agent doesn't self-assign" behavior: the AGENT doesn't assign, but the SYSTEM
  auto-triggers when you set assignee on creation. At `maxConcurrentRuns` capacity (default 3),
  new issues queue. Monitor active runs via the `activeRun` field in issue responses.
- **Issue creation needs Origin + Content-Type headers** — even though GET reads work with
  just the cookie, POSTing a new issue requires BOTH headers:
  ```bash
  TOKEN=$(grep 'paperclip-default.session_token' /c/one/paperclip-company/cj.txt | awk '{print $NF}')
  curl -s -H "Cookie: paperclip-default.session_token=$TOKEN" -H "Origin: http://localhost:3100" \
    -H "Content-Type: application/json" \
    -X POST -d '{"title":"...","assigneeAgentId":"<AGENT_ID>"}' \
    http://localhost:3100/api/companies/<CID>/issues
  ```
  Without `Origin`, you get `Board mutation requires trusted browser origin`.
- **`POST /api/issues` is 404 — create issues via the COMPANY-scoped route** — the bare
  `/api/issues` endpoint does not exist (returns 404). Create issues at
  `POST /api/companies/<CID>/issues` (parentId, assigneeAgentId, status, priority all in the
  body). Reading a single issue works at `GET /api/issues/<ISSUE_ID>` and PATCH/mutations go
  to `/api/issues/<ID>` — but creation MUST be company-scoped. (Verified this session:
  `POST /api/issues` → 404; same payload to `POST /api/companies/<CID>/issues` → 201.)
- **Stale cookie jar returns 401 — re-auth, don't trust the file** — both `cj.txt` and
  `watchdog-cj.txt` can go stale (this session: the supplied `cj.txt` returned 401 and even
  `watchdog-cj.txt` had aged out). The API uses Better-Auth session cookies, NOT the agent
  Bearer API key, for browser-style REST calls. On 401, re-authenticate with
  `POST /api/auth/sign-in/email` (`prem@local.dev` / `LocalDevPass123!`, constants in
  `watchdog.py`) and overwrite the jar with `-c`. Full self-healing cron pattern in
  `references/cron-auth-recovery.md`. Don't waste a pass on a dead cookie.
- **Local JSON snapshots go stale** — `iss.json`, `company-status.json`, and other files
  written to the repo by previous agent runs are snapshots from when they were generated,
  not live state. This session found `company-status.json` was ~19 hours stale (generated
  2026-07-12T14:51Z vs actual-time 2026-07-13T03:35Z). The API at
  `GET /api/companies/<CID>/issues` is the authoritative live source. Always prefer the
  API over local JSON files for current issue status. Use local files only for historical
  comparison or when the server is down.

- **Cron follow-up creation must be idempotent — check existing children first** — when a cron pass finds a `done` issue and decides to spawn follow-up work, FIRST filter the issues list by `parentId == <done issue id>` and confirm no child already covers the same scope in a live/terminal state (`in_progress` / `in_review` / `done`). This session: PRE-8 (`done`, direct outreach) already had child PRE-11 (`in_progress`, *"Monitor job board outreach responses"*) actively running — spawning a second "monitor outreach" child would have been a duplicate run. If a covering child already exists, skip creation and let it ride. (Inverse of the "agent does NOT self-assign" pitfall: here the agent DID create the follow-up, so the cron must avoid doubling it.)
- **Free-model first-token latency looks like a stuck run — don't cancel it** — after `POST /heartbeat/invoke`, the new run's `.ndjson` can sit at exactly 783 bytes (the 3 startup lines: workspace-fallback warning, `Loaded agent instructions`, `Starting Hermes Agent`) for 1–2 minutes with no further output. This is the `tencent/hy3:free` model's high first-token latency, NOT a dead run. A genuinely dead run shows the same 3 lines PLUS a subsequent `Exit code:` line and an `activeRun` that later reads `null` (the "corrective run silently dying" pattern). **Do NOT** cancel + re-trigger on the basis of a small log during the first ~2 min — cross-check `lastHeartbeatAt` and wait; the log grows once the model emits. Distinguish clearly: *silent + no Exit code + within 2 min = alive, just slow*; *silent + has Exit code + activeRun null = dead, re-trigger*.

## Updating an existing Paperclip install (bump canary/stable)

Your live company runs from a git checkout at `/c/one/paperclip-company/paperclip`, started via the
`PaperclipServer` scheduled task (or `run-server.bat`) with `../node_modules/.bin/tsx src/index.ts`
(run from `server/`). To bump versions in place:

1. **Back up state FIRST** — `cp -r /c/one/paperclip-company/data /c/one/paperclip-company/data-backup-<ts>`.
   Company data lives at `PAPERCLIP_HOME=C:\one\paperclip-company\data\paperclip` (external Postgres,
   so sessions survive restart — but back up before a rebuild anyway).
2. **Stop the running server** — find the `tsx src/index.ts` node.exe via
   `wmic process where "name='node.exe'" get ProcessId,CommandLine | grep tsx` → `taskkill /PID <pid> /F`.
   Verify with `curl /api/health` → non-200.
3. **Fetch + checkout target** — `git fetch --tags origin` then `git checkout -f <tag>`
   (e.g. `canary/v2026.714.0-canary.16`, or stable `v2026.707.0`).
4. **Reinstall** — `pnpm install --ignore-scripts --config.node-linker=hoisted`
   (hoisted avoids the MSYS hardlink hang; `--ignore-scripts` skips the harmless postinstall).
5. **Build** — `pnpm build` (tsc across the workspace).
6. **Restart** — launch `../node_modules/.bin/tsx src/index.ts` as `terminal(background=true)`
   (NOT `nohup`/`setsid` — rejected by the tool; NOT `exec` — detaches and dies). Set
   `export NODE_OPTIONS="--max-old-space-size=1500"` (NOT 8192 — OOMs the 6 GB box).
7. **Verify** — poll `GET /api/health` until `200`; confirm company + agents intact via API.

### Update pitfalls (hit + solved 2026-07-15)
- **Stale `.git/index.lock`** — a prior crashed git process leaves `.git/index.lock`; `git checkout`
  fails with "may have crashed... remove the file manually". **Fix:** `rm -f .git/index.lock` then retry.
- **Latest *stable* ≠ newest build.** `releases/latest` API only returns stable tags (e.g. `v2026.707.0`);
  newer **canary** tags (e.g. `canary/v2026.714.0-canary.16`) exist on `master` but are NOT "releases".
  A local checkout can already be a canary *newer* than the latest stable. Check `git tag -l` + commit
  dates (`git log -1 --format=%ci`) before assuming an update is needed. Don't equate "latest release"
  with "newest build" — and don't claim a canary tag "doesn't exist" just because it's absent from the
  releases API; check local `git tag -l` too.
- **`pnpm build` fails on optional `google-sheets-mcp-server`** (missing `googleapis`). The package is
  optional (Google Sheets MCP you likely don't need) but its failure aborts the recursive build.
  **Fix:** `cd packages/google-sheets-mcp-server && npm install googleapis --no-save --ignore-scripts
  --legacy-peer-deps`, then rebuild that package. The core `server` package builds fine regardless;
  `server/dist` presence (esp. `dist/index.js`) is the real success signal, not a clean full-build exit.
- **Windows build-script quirk:** the `server` package's build script runs `mkdir -p` / `cp -R` (Unix
  syntax) which FAILS under Windows cmd ("The syntax of the command is incorrect"). `tsc` itself passes.
  **Fix:** run `tsc` directly in `server/`, then manually `mkdir -p dist/onboarding-assets
  dist/built-ins` + `cp -R src/onboarding-assets/. dist/onboarding-assets/` + `cp -R src/built-ins/.
  dist/built-ins/`. `dist/index.js` will then exist and the server runs.
- **Don't trust `wmic OS Get FreePhysicalMemory` here** — it returned empty on this host. The low-RAM box
  is why you use the hoisted linker + bounded `timeout` on every heavy command; proceed without a RAM read.

## Reality check to set with the user
Paperclip automates the *work* of a company; it does not generate revenue by itself. You still need a
product people pay for and an API budget. Treat it as a self-running engineering/marketing team you own
and steer. Agents won't run until a model key is present for Hermes.

## References & templates
- `references/soft-error-hy3.md` — canonical soft-error fix (in the paperclip-company-ops skill): `tencent/hy3:free` root cause, model-swap PATCH recipe, `/reset-session` is board-only, fix-model-then-invoke sequence.
- `references/cron-restart-recovery.md` — What really happens when a cron finds the server down / agent in `Process lost` error: fully-stopped vs zombie, the stale top-level `status:error` flag after `reset-session`, dual dispatch (manual invoke + scheduler), and how to *prove* a run is live via the `%TEMP%/paperclip-run-*` scratch dir + `hermes.exe` command lines (the `run-logs/<runId>.ndjson` often isn't written until completion). Load before running the pipeline cron job or deciding whether to invoke a heartbeat.
- `references/agent-run-patterns.md` — Run lifecycle states, failure mode diagnosis (connection error vs timeout vs success), recovery action loop detection, agent status values ("error" with null errorReason = soft error), when to invoke heartbeat vs not, run-log-to-issue cross-referencing, and the "done issue still dispatched" pattern. Load when diagnosing agent non-responsiveness or deciding whether to intervene in a recovery loop.
- `references/cron-pipeline-workflow.md` — Cron job operational checklist: stale-run detection, session reset, follow-up creation for done items, timeout unblocking, dispatch verification, AND data-processing mechanics (JSON pipe-breakage workaround, PATCH 400 diagnosis, run-log summary scanning for next-step recommendations, run-ID cross-referencing). Load before writing or modifying the cron prompt for the revenue pulse job.
- `references/blocked-issue-recovery.md` — Recovery-action decoder: how `activeRecoveryAction.kind` (`stranded_assigned_issue` vs `missing_disposition`) dictates cron intervention on `blocked` issues, plus the partial-deliverable blocker subtype. Load when a cron pass finds a `blocked` issue and must decide whether to reset+heartbeat or leave it alone.
- `references/cron-auth-recovery.md` — Self-healing cron auth: detect stale `cj.txt` (401), re-authenticate via `sign-in/email`, overwrite the jar, and the idempotent probe-atop-of-pass pattern. Load BEFORE every automated pipeline cron run.
- `references/issue-automation-workflow.md` — Programmatic issue automation API: exact curl commands for creating issues, assigning to agents (triggering autonomous execution), batch-sprint launches, and troubleshooting. Shows how to bypass the "agent doesn't self-assign" limitation. Verified on a 7-agent Paperclip instance. Load before automating Paperclip work pipelines.
- `references/windows-build-pitfalls.md` — deeper repro recipes for each pitfall above.
- `references/quickstart.md` — copy-paste command sequence + REST seed script.
- `references/continuous-development-loop.md` — keeping the agent company running: issue lifecycle, cron setup for pipeline management, revenue model sequencing (PRE-3 → PRE-5–PRE-8 pattern), founder handoff gates, cookie expiry recovery, board mutation Origin header.
- `references/github-knowledge-base.md` — pushing the local company to GitHub as single source of truth: repo creation via cached creds, curated copy (exclude node_modules), `master` default branch, write_file native-path bug, prompt-consolidation + reality-match rules.
- `references/verify-agent-comparison-claims.md` — when a user pastes an AI-generated "Hermes vs Paperclip vs OpenClaw" comparison, verify star/version/date claims against the live GitHub API (two docs this session fabricated numbers) before trusting them.
- `templates/run-server.bat` — known-good Windows launcher (native paths, tsx shim, env block).
- `templates/AGENTS.md` — Standard agent instructions template with mission, priorities, active issues, work rules, and retry discipline. Fill in the placeholders ({AGENT_NAME}, {COMPANY_NAME}, {MISSION}, etc.) and write to `<PAPERCLIP_HOME>/instances/default/companies/<CID>/agents/<AGENT_ID>/instructions/AGENTS.md`. Load before creating or updating agent instructions for a company.
