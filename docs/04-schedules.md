# 04 — Schedules (all in the ALWAYS-ON gateway store)

Created via `hermes cron create ...` (<gateway-profile> profile). Inspect: `hermes cron list`.
The desktop app's private store (`%HERMES_HOME%\hermes\cron\jobs.json`) is PARKED —
it stalls when the app closes; do not put real jobs there.

## Active jobs (verified 2026-08-22 19:46 IST)

| Name | Schedule | Type | Purpose |
|---|---|---|---|
| company-watchdog | every 30m | no_agent script | gateway/RAM/Telegram/cron/kanban-zombie checks; silent when healthy; regenerates ops-dashboard.html |
| kanban-production-line | every 60m | no_agent script | releases ONE build card per tick |
| <github-account>: build next project | every 2880m | agent + skill | next CLI product for <github-account> account; workdir C:\one |
| sproutern-weekly-growth-report | Mon 09:00 | agent → origin chat | growth analysis of sproutern.dpdns.org |
| sproutern-reddit-question-radar | daily 04:00 | agent → origin chat | community radar |
| sproutern-freshness-radar | monthly (1st) 07:00 | agent → origin chat | stale-content audit |
| avo-lab-evolution-tick | every 30m | agent + skill, continuity | AVO Labs heartbeat (separate lab) |
| avo-lab-watchdog | every 120m | no_agent script | AVO stall watchdog |

## Pins (mandatory)

Every agent job pins provider+model explicitly:
`--provider openrouter --model nvidia/nemotron-3-super-120b-a12b:free`
(radars use nemotron-nano-9b-v2:free).
Unpinned jobs get killed by the config-drift guard the moment the global model changes.

## Changing a job

```bash
hermes cron list                 # get id
hermes cron edit <id> --schedule "every 45m" --provider openrouter --model <model>
hermes cron run <id>             # fire once now
```

## Watchdog alert path

company_watchdog prints ONLY on failure → stdout is delivered to the **origin chat**
(this desktop conversation). RAM < 500 MB, gateway dead, Telegram down, cron errors,
kanban zombie workers = the five alarms.
