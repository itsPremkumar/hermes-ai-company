# Soft-error recovery: `tencent/hy3:free` root cause + model-swap fix

Verified 2026-07-15 on the live `itsPremkumar` Paperclip company
(`Prem Autonomous Co`, localhost:3100, canary build). Class-level — will recur
whenever agents are hired on the default free OpenRouter model.

## Symptom
- Agent `status: error`, `errorReason: "Process lost -- server may have restarted"`.
- `GET /api/agents/:id` shows `adapterConfig.model: tencent/hy3:free`,
  `provider: openrouter`.
- This session ALL 4 error agents (QA, CFO, Head of Product, CEO) traced to this.

## Root cause
`hy3:free` is OpenRouter's free tier — it rate-limits / drops idle connections.
The `hermes_local` adapter shells out to `hermes chat`; when the model call
dies mid-session, Paperclip marks the run lost and the agent `error`. The error
flag is **sticky** (persists after the dead run is gone).

## Fix (working recipe — company cookie is sufficient)
1. Swap every `hy3:free` agent to a reliable model via PATCH:
```bash
TOKEN=$(grep 'paperclip-default.session_token' cj.txt | awk '{print $NF}')
for aid in <UUID1> <UUID2> <UUID3> <UUID4> <UUID5> <UUID6> <UUID7>; do
  curl -s -X PATCH \
    -H "Cookie: paperclip-default.session_token=$TOKEN" \
    -H "Origin: http://localhost:3100" \
    -H "Content-Type: application/json" \
    -d '{"adapterConfig":{"model":"anthropic/claude-3.5-haiku","provider":"openrouter"}}' \
    "http://localhost:3100/api/agents/$aid" -w " %{http_code}\n"
done
# each -> 200; GET /api/agents/:id now shows claude-3.5-haiku
```
Why this model: OpenRouter IS reachable here (verified `HTTP 200` to
`https://openrouter.ai/api/v1/models` with the `OPENROUTER_API_KEY` that lives in
Hermes's `~/.hermes/.env`). `anthropic/claude-3.5-haiku` is reliable + cheap.
The free `hy3:free` was the only culprit.

2. Clear the sticky error flag — invoke a heartbeat per agent; flag clears on the
   FIRST successful run:
```bash
curl -s -X POST \
  -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" \
  -H "Content-Type: application/json" \
  -d '{"reason":"model swapped off hy3:free; clearing soft-error"}' \
  "http://localhost:3100/api/agents/$aid/heartbeat/invoke"
# -> 202 {status:"queued"}
```
Then `GET /api/heartbeat-runs/:runId` -> `status: succeeded`, no `error`.
After that the agent is `idle` with `errorReason: none`. Verified: QA, CFO,
Head-of-Product all recovered this way.

## CORRECTION — `/reset-session` is board-only here
`POST /api/agents/:id/runtime-state/reset-session` is guarded by `assertBoard(req)`.
With the **company** session token in `cj.txt` it returns **400/401**. It does NOT
clear the soft-error flag for the operator. The model-swap + heartbeat-success path
above is the working recovery and needs no board token.

## Nuance vs "don't invoke heartbeats on soft-error agents"
The older rule (invoke only after fixing root cause) is correct ONLY *before* the
fix. Invoking a heartbeat on an **unfixed** `hy3:free` agent just re-fails and
feeds the loop. **After** you swap to a reliable model, invoking the heartbeat is
exactly what clears the flag. Sequence: **fix model -> THEN invoke.**

## Don't waste time on
- Re-running reset-session with the company cookie (board-gated, 400/401).
- Believing the agent is healthy just because `status` leaves `error` immediately
  after the swap — it stays `error` until the next run *succeeds*.
- Assuming a canary tag "doesn't exist" because it's absent from the releases API
  (canaries live on `master`, not `/releases/latest`) — unrelated to this fix but
  a parallel trap hit while updating the server this session.
