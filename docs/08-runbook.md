# 08 — Runbook (day-to-day operations)

## Morning check (2 minutes)
1. Open `%HERMES_HOME%\hermes\ops-dashboard.html` — all green?
2. `hermes kanban list` — anything in done? Anything stuck running > 30 min?
3. Watchdog silent = healthy. If it posted an alarm here, follow its ACTION line.

## Talk to the company
```bash
hermes -p ceo chat          # board meeting
hermes -p research-analyst chat   # live market data pull
@mention bots inside any chat     # handoffs
```

## Push work into the pipeline
```bash
hermes kanban create "Build: <name>" --assignee fullstack-dev --body "<spec>"
hermes kanban block <task_id> "queued"
# hourly cron picks it up; or force now:
bash %HERMES_HOME%/hermes/scripts/kanban_dispatch.sh
```

## Recovery recipes

| Symptom | Fix |
|---|---|
| Gateway down | `hermes gateway run` (background) or log off/on (Scheduled Task) |
| RAM < 500 MB | close Chrome first; `tasklist`, kill stray python workers |
| Cards stuck ready, nothing spawns | clear stale claims: `UPDATE tasks SET claim_lock=NULL, claim_expires=NULL WHERE status='ready'` then re-run dispatch script |
| Many workers spawned | taskkill worker PIDs from board DB → verify dispatch_in_gateway:false → restart gateway |
| Cron jobs all error with "config drifted" | `hermes cron edit <id> --provider openrouter --model <live-free-model>` |
| A pinned model vanished | run model_health.py, re-pin profiles/jobs to a listed survivor |

## Adding a new bot
```bash
hermes profile create <name> --no-skills --description "<role>"
cp %HERMES_HOME%/hermes/.env  %HERMES_HOME%/hermes/profiles/<name>/.env   # MANDATORY
# then edit config.yaml: model pin + platform_toolsets.cli + fallback_providers
# copy wanted skills into profiles/<name>/skills/
# write SOUL.md persona
```

## Adding a new routine
```bash
hermes cron create "every 60m" --name <job> --no-agent --script <file>.py --deliver local
# or agent job: add prompt + --provider openrouter --model <model> (ALWAYS pin)
```

## [HUMAN STEP] checklist (one-time)
- [ ] Close desktop app → `hermes update` (v0.20.5 → latest, incl. bot-mode fix)
- [ ] Bots tab: hide the 14 duplicate rows (list in docs/02)
- [ ] Bots tab: create Exec / Delivery / Growth group rooms (trios in docs/02)
- [ ] Optional: Telegram platform link for phone escalations
- [ ] Optional: `hermes gateway setup` for webhook event triggers
