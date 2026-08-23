# Paperclip API auth — exact working incantations

Observed on the running instance (Windows native, server on `:3100`). The auth
model is **endpoint-class dependent**, which trips up every first cron-tick.

## 1. Company / issue data reads — use the cookie FILE
Works as-is (no `Origin`, no raw header):
```
curl -s -b /c/one/paperclip-company/cj.txt \
  "http://localhost:3100/api/companies/<COMPANY_ID>/issues"
```
Returns `200` + full JSON. Also works for other company-scoped GETs.

## 2. Agent-control endpoints — raw Cookie header + Origin
`-b cj.txt` returns `401 Unauthorized` here (even for a plain GET). Use:
```
TOK="paperclip-default.session_token=<value from cj.txt, 7th tab field on the localhost line>"
curl -s -H "Origin: http://localhost:3100" \
     -H "Cookie: $TOK" \
     "http://localhost:3100/api/agents/<AGENT_ID>"
# -> 200, full agent object (status, lastHeartbeatAt, runtimeConfig.heartbeat)
```

## 3. Invoke heartbeat
```
curl -s -H "Origin: http://localhost:3100" \
     -H "Cookie: $TOK" \
     -X POST "http://localhost:3100/api/agents/<AGENT_ID>/heartbeat/invoke"
# -> HTTP 202 Accepted  (queues a run; agent flips idle -> running)
```
Verify it actually ran: re-GET the agent (status becomes `running`) and check a
new `.ndjson` appears under
`<PAPERCLIP_HOME>/data/.../run-logs/<COMPANY_ID>/<AGENT_ID>/`.

## 4. Gotchas
- `GET /api/agents/:id/heartbeat-runs` → **404** (route not exposed). Use the
  agent `status` field + the run-log dir instead of a runs-list API.
- `GET /api/agents` (list, no id) → **401**. You must hit the per-agent URL.
- `Authorization: Bearer <token>` → **403**. Only the `Cookie:` header works.
- Token extraction: the Netscape cookie file's value is the 7th tab-separated
  field on the `localhost` line (after `TRUE`/`FALSE`/`/`/`FALSE`/`<expiry>`).
- Re-fetch issues (`GET .../issues`) is the authoritative live source — briefs
  assert stale state. Never PATCH to match a brief; act on real API state.
