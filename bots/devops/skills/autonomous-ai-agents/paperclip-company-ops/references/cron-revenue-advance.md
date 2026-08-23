# Cron: advance Paperclip revenue work (headless)

Reusable procedure for a scheduled cron job that checks the Paperclip company and
advances revenue work without a human present. Derived from a 2026-07-15 run against
company `3056c999-…` / Hermes Engineer `9eed5712-…`.

## Endpoint routing (verified this build — differs from older skill text)
- **Companies**: `GET /api/companies/{companyId}/issues`, `POST /api/companies/{companyId}/issues`
- **Agents (BOTH prefixes work on this build)**: `GET /agents/{agentId}` and `GET /api/agents/{agentId}` BOTH return the full record (verified — `GET /api/agents/9eed5712-…` returned `status`, `lastHeartbeatAt`, `adapterConfig`); `GET /agents/{agentId}/runtime-state`; `POST /agents/{agentId}/heartbeat/invoke` (and `POST /api/agents/{agentId}/heartbeat/invoke`, which returned `202` this session). An earlier note that `/api/agents/...` returns 401/empty was WRONG for this build — use either form.
- **Heartbeat runs (under `/api`)**: `GET /api/companies/{companyId}/heartbeat-runs?limit=N`,
  `GET /api/heartbeat-runs/{runId}`
- **Single issue**: `GET /api/issues/{issueId}` — real owner is `assigneeAgentId` here
  (the issues LIST reports `assigneeId: null` for every issue; it's a denormalized stub).
- **Auth**: `curl -b /c/one/paperclip-company/cj.txt <url>` works when the Netscape jar domain
  line is plain `localhost`. Mutations need `Origin: http://localhost:3100` +
  `Content-Type: application/json` (else 403 "trusted browser origin").

## 6-step procedure
1. **Fetch issues**: `GET /api/companies/{cid}/issues` → save to file, parse with `python`.
   NEVER trust the list `assigneeId` (always null); use per-issue `assigneeAgentId`.
2. **Done issues → follow-up?** For each `done` issue, check a real, non-redundant next step
   exists (child with `parentId == issue.id`, or a known cadence successor). Create a child ONLY
   where a genuine gap exists. Do NOT spam follow-ups onto terminal `done` issues (one-off reviews,
   single publishes). This run: revenue dashboards M1–M6 already have M7 (PRE-91); PRE-8 already has
   PRE-81/82/11/79; no new children were warranted.
3. **Unassigned todo/backlog → assign**: for each `todo`/`backlog` with no `assigneeAgentId`,
   PATCH `/api/issues/{id}` (`Cookie`+`Origin`) → `assigneeAgentId: <HERMES>` + `status: in_progress`.
   Skip founder-only authorization-boundary tasks (job-board posting/reading, LinkedIn) — leave
   unassigned for the founder.
4. **Idle check**: read run-logs dir
   `data/paperclip/instances/default/data/run-logs/{cid}/{aid}/*.ndjson`. If the newest file shows a
   completed run and no run is `running`/`queued`, the agent is idle. Confirm via
   `GET /agents/{aid}` → `status:"idle"`, `lastHeartbeatAt`, `runtimeConfig.heartbeat.enabled`,
   `pausedAt` (null), `errorReason` (null).
5. **Heartbeat if idle + work exists**:
   ```bash
   TOKEN=$(grep 'paperclip-default.session_token' cj.txt | awk '{print $NF}')
   curl -s -X POST \
     -H "Cookie: paperclip-default.session_token=$TOKEN" \
     -H "Origin: http://localhost:3100" \
     -H "Content-Type: application/json" \
     -d '{}' \
     "http://localhost:3100/agents/{aid}/heartbeat/invoke"
   # 202 + run object { id, status:"queued" }
   ```
   The run-log `<runId>.ndjson` appears under the run-logs dir once the model cold-starts
   (can take minutes). Verify revival by **file presence** (ground truth), not the flapping
   `agent.status` field.
   **Read the run-log to confirm WHAT the run hit (real-time blocker check):** after the run
   starts, `tail` `<runId>.ndjson`. If it shows `[hermes] Exit code: 1` with
   `HTTP 402: ... can only afford N tokens`, the OpenRouter credit wall is STILL up — the
   invoke executed but could not advance work. Report that honestly (per §6f's 402 case); do
   NOT claim the heartbeat advanced revenue. This session a freshly-invoked run `e9620de2-…`
   reproduced the identical 402 within ~20 s, proving PRE-103 is a live billing wall, not
   stale history. A `202` on the invoke only means the run was *queued*; the run-log is the
   verdict on whether it did anything.
6. **Report**: issue states found, discrepancies vs the task brief, what you did (assignments,
   heartbeat run id), and the standing founder blocker.

## Gotchas (verified this session)
- **Task-brief premise can be WRONG**: brief claimed PRE-5/6/7/8 were all `in_progress`; live API
  showed PRE-5/PRE-6 `in_review`, PRE-7 `blocked`, PRE-8 `done`. Trust the API; report the
  discrepancy; do NOT force issues to match the brief.
- **`curl | python` empty body**: always `curl -s -o file.json <url>` then read `file.json`.
  Piping stdout into `python -c "json.load(stdin)"` intermittently returns empty →
  `JSONDecodeError: Expecting value`.
- **write_file vs terminal path split**: `write_file` resolves `/tmp/x` → `C:\tmp\x`, but the
  terminal's `/tmp` is MSYS temp (a *different* physical dir). Use an absolute `C:/Users/...` or
  workspace-relative path for any file both tools touch.
- **Server may drop after a heartbeat**: the single-process Node server can become unreachable
  (`curl` exit 7) while/after the run executes. Live API re-verification then fails — the on-disk
  run-log file remains as proof the run was accepted. Don't claim full verification when the server
  is down; state the blocker.

## Standing revenue blocker (this company, 2026-07-15)
Booked revenue is $0 and stays $0 until the founder crosses the live-publish gates:
Gumroad **PRE-52**, GitHub Sponsors **PRE-57**, Medium **PRE-54**, Fiverr **PRE-58**,
YouTube/TikTok **PRE-74**, and the job-board logins for **PRE-11/PRE-81/PRE-82**.
**PRE-5/PRE-6** (`in_review`) await founder review. Surface this as the #1 founder action item;
do not thrash on agent-side work the agent cannot cross.
