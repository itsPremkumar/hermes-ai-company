# Paperclip Company API — verified curl recipes

Environment from the active session (Prem Autonomous Co):
- Server: `http://localhost:3100`
- companyId: `3056c999-62ba-4321-ae69-799a61286bad`
- agentId (Hermes Engineer): `9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f`
- cookie file: `cj.txt` (Netscape format, `paperclip-default.session_token`)

## Cookie extraction (send raw as a header — do NOT decode, and do NOT use curl -b)

On this git-bash/Windows host `curl -b cj.txt` fails to open the MSYS-path Netscape jar
(`WARNING: failed to open cookie file`), so no cookie is sent and the server returns `401`.
Extract the token with `grep`/`awk` and send it RAW (still `%3D`-encoded) as an explicit header —
the server accepts the encoded value and returns `200`. Decoding is a fallback, not the default.

```bash
# raw token — Netscape jar's data line is line 2; token is field 7 (TAB-separated)
TOKEN=$(sed -n '2p' cj.txt | awk -F'\t' '{print $7}')
# Verified: server accepts this URL-encoded value (%3D intact) and returns 200.
# Fallback if needed: grep session_token cj.txt | awk '{print $NF}'
```

## GET (no Origin needed)
```bash
curl -s -H "Cookie: paperclip-default.session_token=$TOKEN" \
  "http://localhost:3100/api/companies/3056c999-62ba-4321-ae69-799a61286bad/issues" \
  -o pc_issues.json
# 200 + JSON array. A 401 here means the cookie file wasn't read / token blank — verify
# grep session_token cj.txt returns a value; do NOT blind-retry.
```

## PATCH — assign / activate an issue
```bash
curl -s -X PATCH \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Content-Type: application/json" \
  -d '{"assigneeAgentId":"9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f","status":"in_progress"}' \
  "http://localhost:3100/api/issues/{issueId}"
# 200 + updated issue. issueId is the UUID `id`, not the `identifier` (PRE-82).
# A status->in_progress PATCH auto-spawns an execution run for the agent.
```

## MUTATIONS — MUST include Origin header
```
# Invoke a heartbeat to revive an idle/error agent:
curl -s -i -X POST \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "http://localhost:3100/api/agents/9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f/heartbeat/invoke"
# 202 + run object {status:"queued"}  on success
# 403 {"error":"Board mutation requires trusted browser origin"}  if Origin missing
```

## Reading agent state
```
curl -s -H "Cookie: paperclip-default.session_token=$TOKEN" \
  "http://localhost:3100/api/agents/9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f"
# look at: status, lastHeartbeatAt, errorReason, runtimeConfig.heartbeat
```

## Parsing issues (python, NOT python3 on this host)
```
python - <<'PY'
import json
data=json.load(open('pc_issues.json'))
print(len(data), "issues")
for i in data:
    if i['identifier'] in ('PRE-5','PRE-6','PRE-7','PRE-8'):
        print(i['identifier'], i['status'], i['assigneeAgentId'], i['title'][:40])
# children of an issue:
kids=[i for i in data if i['parentId']=='515aaf11-a33e-48e4-b1d3-313fb77055b5']
PY
```

## Run-log verification (no API for run history)
```
RLDIR="data/paperclip/instances/default/data/run-logs/3056c999-62ba-4321-ae69-799a61286bad/9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f"
ls -t "$RLDIR" | head -1          # newest run
tail -n 3 "$RLDIR/<runId>.ndjson" # confirm live
```

## Notes
- `GET /api/agents/{id}/runs` and `.../companies/{id}/agents/{id}/runs` both returned
  "API route not found" — there is NO stable run-history API; rely on the run-log NDJSON files.
- `GET /api/heartbeat-runs/{runId}` (per-run) **DOES exist** — returns HTTP 200 with the run record (`status`, `startedAt`, `finishedAt`, `error`). Verified this session; poll it to confirm a freshly-invoked heartbeat entered `running`. (The run-log NDJSON keyed by run `id` remains a valid alternative.)
- The agent record's `status` field normally returns **`idle`** (resting state between heartbeats),
  OR `error` if the last run exited non-zero. It does NOT reliably flip to `running` while a
  heartbeat runs — trust the run-log file, not `status`, to confirm execution.
- **HTTP 200 with body `{"error":"Unauthorized"}` is a failure** (stale/unaccepted cookie). A
  successful GET returns a large JSON array, never that 24-byte error object. Always inspect the body.
