# Deployment Guide — Use This Company Anywhere

This folder is self-contained. Anyone can rebuild the company on any machine
(Windows/macOS/Linux) with a free Hermes Agent install.

## Prerequisites
1. [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed (`hermes` on PATH)
2. One **free** OpenRouter account + API key (https://openrouter.ai — `:free` models need no card)
3. Optional: NVIDIA NIM API key (build.nvidia.com — free credits) for the fallback chain

## Placeholders used in this repo
| Placeholder | Meaning |
|---|---|
| `<user>` | your OS username |
| `<github-org>` | your single GitHub account for ALL company operations |
| `<github-account>` | same account (product repos live here) |
| `<gateway-profile>` | the Hermes profile that runs your gateway (default install: `default`) |
| `%HERMES_HOME%` | your Hermes data dir (`%LOCALAPPDATA%\hermes` on Windows, `~/.hermes` elsewhere) |
| `<owner-email>` | your email |

## Rebuild steps (30–60 min)

### 1. Create bot profiles
For every entry in `configs/FLEET.json`, create a profile and apply its config:
```bash
hermes profile create <bot> --no-skills --description "<role from docs/02>"
cp configs/<bot>.config.yaml %HERMES_HOME%/profiles/<bot>/config.yaml
cp souls/<team>/<bot>.md %HERMES_HOME%/profiles/<bot>/SOUL.md
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/<bot>/.env        # MANDATORY
```
(On Windows use `%HERMES_HOME%\...`; adjust to your shell.)

### 2. Install company scripts
```bash
cp scripts/* %HERMES_HOME%/scripts/
```

### 3. Start the always-on gateway
```bash
hermes gateway run            # or: hermes gateway install --start-now --start-on-login
hermes cron create "every 30m" --name company-watchdog --no-agent \
  --script company_watchdog.py --deliver local
hermes cron create "every 60m" --name kanban-production-line --no-agent \
  --script kanban_dispatch.sh --deliver local
```
Add the remaining jobs from `docs/04-schedules.md`.

### 4. Arm safety switches (CRITICAL — read docs/07 first)
In `<gateway-profile>/config.yaml`:
```yaml
kanban:
  max_in_progress: 1
  max_in_progress_per_profile: 1
  dispatch_in_gateway: false   # Windows has NO auto memory cap otherwise!
```

### 5. Set up the board & queue work
```bash
hermes kanban init
hermes kanban create "Build: my-first-tool" --assignee fullstack-dev --body "<spec>"
hermes kanban block <task_id> "queued"
bash scripts/kanban_dispatch.sh     # releases ONE card; hourly cron continues it
```

### 6. Verify
- `hermes cron list` shows all jobs with future next-run times
- `hermes -p qa-lead skills list` shows codebase-inspection
- Watch one build: `hermes kanban tail <task_id>`
- Ship gate: `python scripts/qa_harness.py <built-project-dir>` must PASS

## Rules reminder
Read `docs/09-sops.md` before operating. The five laws in `docs/07-lessons-learned.md`
were learned through real outages — do not skip them.
