# 06 — Scripts

Canonical location: `%HERMES_HOME%\hermes\scripts\` (cron refers to this folder).
Copies in `C:\one\hermes-ai-company\scripts\` are for version control / reading.

## company_watchdog.py — the alarm system
- **Fires:** every 30 min (no_agent cron `company-watchdog`)
- **Checks:** gateway process alive (command-line match, not stale state file) ·
  Telegram platform state · free RAM < 500 MB · per-cron last_status errors ·
  kanban zombie workers (running rows whose PID is dead)
- **Output discipline:** SILENT when healthy; prints alarms → delivered to origin chat
- **Side effect:** always regenerates `%HERMES_HOME%\hermes\ops-dashboard.html`
  (auto-refresh page: gateway / telegram / RAM / cron fleet / kanban line rows)

## kanban_dispatch.sh (v2) — the production line
- **Fires:** every 60 min (no_agent cron `kanban-production-line`)
- **Logic:** if any card running → exit silently. Else promote ONE blocked → ready
  (--force, audit reason) → `hermes kanban dispatch --max 1 --json`.
  Prints only on failure.
- **Why v2 exists:** gateway embedded dispatcher + Windows no-cap = instant fan-out
  (twice). dispatch_in_gateway:false + this script = exactly one worker.

## qa_harness.py — the generic quality gate
- **Usage:** `python qa_harness.py <project_dir>` → exit 0 PASS / 1 FAIL
- **Checks:** py_compile all .py · pytest if tests exist · every `self-test`
  subcommand · hardcoded-secret regex scan · README/SKILL presence
- **Dual-tested** against a clean dir and a poisoned dir before deployment
- qa-lead's SOUL.md makes running it MANDATORY before anything ships

## model_health.py — model-vanish guard
- **Fires:** manually or attach to watchdog later
- **Checks:** all pinned models still present in OpenRouter catalog (GET only, $0)
- **Silent** when healthy; names vanished models + re-pin action when not

## Where things live

| Thing | Path |
|---|---|
| Profiles (bots) | `%HERMES_HOME%\hermes\profiles\<bot>\` |
| Gateway cron store | <gateway-profile> profile via `hermes cron ...` CLI |
| Kanban board DB | `%HERMES_HOME%\hermes\kanban\boards\it-company-ops\kanban.db` |
| Ops dashboard | `%HERMES_HOME%\hermes\ops-dashboard.html` |
| This repo copy | `C:\one\hermes-ai-company\` |
