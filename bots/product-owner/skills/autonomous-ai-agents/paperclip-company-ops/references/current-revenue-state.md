# Standing revenue blocker — Prem Autonomous Co (company 3056c999)

Captured 2026-07-14 after the agent completed run `cf6ed067` working **PRE-86 (Revenue
dashboard M4)**. The agent's own disposition (verbatim finding): *"the constraint is not
burn/capital — it's the founder live-publish gates ... Until those are crossed, M4 actuals
will track M1–M3 (targets escalate, booked revenue stays $0)."*

## The structural bottleneck
Booked revenue = **$0** and will remain $0 until the **founder crosses the live-publish gates**
(these require authenticated *human* accounts — the agent is barred by the authorization boundary):

| Gate | Issue |
|------|-------|
| Gumroad publish | PRE-52 |
| GitHub Sponsors | PRE-57 |
| Medium | PRE-54 |
| Fiverr gigs | PRE-58 |

## Remaining revenue work is ALL human-gated (as of 2026-07-14)
- **PRE-5** (showcase repo / LinkedIn) — `in_review` → founder review/approve
- **PRE-6** (agent-labor service + pricing tiers) — `in_review` → founder review/approve
- **PRE-7** (produce & publish 3 sample videos) — `blocked` → child **PRE-74** needs founder YouTube/TikTok login
- **PRE-8** (direct outreach on free job boards) — `done`; follow-up chain already live:
  - **PRE-11** (monitor job-board responses) — `blocked` (founder must log in + read replies)
  - **PRE-81** (execute free-board outreach) — `blocked` (founder login gate)
  - **PRE-79** (founder to report job-board replies) — `in_progress`, **founder-owned** (no agent assignee)

## What an ops / cron run SHOULD do
1. Snapshot issues + agent status. **Re-snapshot immediately before any mutation** — the board
   is volatile (agent self-mutates on its own heartbeat ticks).
2. Confirm PRE-8's follow-up chain (PRE-11 / PRE-81 / PRE-79) exists → no new child needed.
3. If the agent is `idle` AND there is outstanding (human-gated) work, invoke a heartbeat
   (§4). It will re-scan and re-confirm the human gates — that is expected, not a failure.
4. **Report the publish-gate blocker to the founder as the #1 action item.** Do NOT thrash
   trying to "advance revenue" the agent cannot cross. The lever is human, not agent.

## Heartbeat run this session (worked example)
- Invoked `POST /api/agents/9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f/heartbeat/invoke` with
  `Origin: http://localhost:3100` + `Cookie` header → `202`, run `9b7aba97-9628-49b8-97b5-52f1f5c94d7d`
  queued; agent `status` flipped `idle`→`running`. (First attempt without `Origin` → `403
  "Board mutation requires trusted browser origin"` — re-add the header.)
- Poll status with `GET /api/heartbeat-runs/{runId}` (NOT `/api/runs/{runId}` — that 404s).

## Continuity — dashboard series now current through M6 (added 2026-07-14, later run)
- **PRE-87 (Revenue dashboard M5)** completed this session (run `ba693e30`); its acceptance criteria
  required an M6 handoff note, and no M6 issue existed → **PRE-90 (Revenue dashboard M6)** was created as a
  child of PRE-87 (`parentId = 365372c8…`), `status:"in_progress"`, assigned to the Hermes Engineer, then
  dispatched via a single heartbeat (`POST /heartbeat/invoke` → run `c9728594…`, agent flipped `idle`→`running`,
  verified by re-GET of PRE-90 + run-log file). The monthly M1→M5→M6 series is now unbroken.
- Reminder for the next ops/cron pass: once PRE-90 is `done`, the next gap to fill is **M7** (child of PRE-90),
  per the same recurring-cadence rule. Until the founder crosses the live-publish gates (PRE-52/57/54/58), every
  M-dashboard will still report ~$0 actuals — report that as the founder's #1 action item, don't thrash.
