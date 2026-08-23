# Budget semantics (Paperclip company spend ceiling)

Verified 2026-07-15 against live server build `canary/v2026.714.0-canary.16`
(`paperclipai/paperclip`, local checkout at `/c/one/paperclip-company/paperclip`).

## What `budgetMonthlyCents` controls
It is the **monthly spend ceiling** that gates agent operations (LLM inference).
- Mutation endpoint: `PATCH /api/companies/:companyId/budgets`, body `{ "budgetMonthlyCents": N }`.
- Handler (`server/src/routes/costs.ts:334`) calls `companies.update({budgetMonthlyCents})`
  then `budgets.upsertPolicy(companyId, { scopeType:"company", amount:N, windowKind:"calendar_month_utc" })`.
- On company create (`server/src/routes/companies.ts:399`): `if (company.budgetMonthlyCents > 0)`
  the policy is upserted. **At `$0`, NO policy is written.**

## Consequence
`$0` budget = no spend policy = agents have **no ceiling to run inference under** =
**automation cannot execute**. This is a hard brake, NOT a cost-saving mode. "Set budget
to zero" and "start automation" are mutually exclusive in Paperclip's model.

## Verified recipe (this session)
```bash
TOKEN=$(grep 'paperclip-default.session_token' cj.txt | awk '{print $NF}')
curl -s -X PATCH -H "Cookie: paperclip-default.session_token=$TOKEN" \
  -H "Origin: http://localhost:3100" -H "Content-Type: application/json" \
  -d '{"budgetMonthlyCents":0}' \
  "http://localhost:3100/api/companies/<CID>/budgets"
# -> 200 + company JSON; re-GET /api/companies/<CID> to confirm budgetMonthlyCents:0
```
Mutation needs `Cookie` + `Origin` + JSON body. Re-GET to confirm it persisted (§6
post-change discipline).

## Session outcome (user chose literal $0 + automation)
- Budget PATCH → 200, `budgetMonthlyCents:0` confirmed.
- CEO `POST /heartbeat/invoke` → 202 `running`, run `9b4e7010…` created.
- Run stayed `running` with no usage/result/error; 4/7 agents in `error` (root cause
  `tencent/hy3:free` timeouts); revenue blocked on human gates. **$0 earned** — as predicted.
- Lesson: execute literally when the user accepts the no-earn outcome, but report the honest
  result; don't imply money was made.
