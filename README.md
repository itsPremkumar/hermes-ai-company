# Hermes AI Company — Complete Architecture & Operations Manual

> **What this is:** A fully autonomous IT company running entirely inside Hermes Agent's
> Bot Mode on a single 6 GB RAM Windows laptop. Zero paid services. Zero third-party daemons.
> Built, tested, and verified on **2026-08-22**.

---

## 1. The Company in One Paragraph

25 named Hermes bots (each a real Hermes profile) form an IT company: an executive team that
plans, a delivery team that builds software in isolated git worktrees, a QA gate that refuses
unverified work, and growth/research teams that market and study the market. A Kanban
production line converts queued task cards into shipped GitHub repositories — one build at a
time, 24/7, governed by cron routines on an always-on gateway scheduler. Everything runs on
free-tier LLM inference (OpenRouter `:free` + NVIDIA NIM fallback chain). Cost: **$0/month**.

## 2. Document Map

| Doc | Contents |
|---|---|
| [`docs/01-architecture.md`](docs/01-architecture.md) | System layers, data flow diagram, design decisions |
| [`docs/02-fleet-roster.md`](docs/02-fleet-roster.md) | All 25+ bots: role, team, model pin, toolset, assigned skills |
| [`docs/03-production-line.md`](docs/03-production-line.md) | Kanban pipeline: states, laws, dispatcher logic |
| [`docs/04-schedules.md`](docs/04-schedules.md) | Every cron job: schedule, store, pin, purpose |
| [`docs/05-free-resource-stack.md`](docs/05-free-resource-stack.md) | Every $0 resource used + probes + honest limits |
| [`docs/06-scripts.md`](docs/06-scripts.md) | Each script: path, what it does, when it fires |
| [`docs/07-lessons-learned.md`](docs/07-lessons-learned.md) | Hard-won laws (fan-outs, zombie claims, dual stores…) |
| [`docs/08-runbook.md`](docs/08-runbook.md) | How to operate: daily check, recovery, adding a bot/card |
| [`docs/09-sops.md`](docs/09-sops.md) | Company Constitution: all SOPs & standing instructions |
| [`DEPLOY.md`](DEPLOY.md) | **Deploy anywhere:** placeholders + rebuild steps for a fresh machine |
| [`docs/10-product-roadmap.md`](docs/10-product-roadmap.md) | The 20-product build plan |
| [`docs/11-governance-map.md`](docs/11-governance-map.md) | Document hierarchy + honest gap register |
| [`docs/sop-workflows/`](docs/sop-workflows/) | Work lifecycle SOP (ACK rule, routing, review) + parallel/worktree SOP with security merge gate |
| [`skills-hub-company/`](skills-hub-company/) | 5 executable company skills (kanban orchestrator/worker, sdlc-review, fleet CI verify, ops dashboard) |
| [`souls/`](souls/) | All 37 bot SOUL.md personas, organized by team (+ index README) |
| [`configs/`](configs/) | Sanitized per-bot config snapshots + FLEET.json (machine-readable roster) |
| [`bundles/`](bundles/) | Skill bundles (/research-pack, /delivery-pack) |
| [`specs/`](specs/) | Chief-of-staff task specs & board attachments (17 items) |
| [`snapshots/audit-2026-08-22.md`](snapshots/audit-2026-08-22.md) | Point-in-time verification evidence |

## 3. Folder Layout

```
C:\one\hermes-ai-company\
├── README.md              ← you are here
├── docs\                  ← the 8 manuals above
├── souls\                 ← every bot's SOUL.md by team (executive/, delivery/, …)
├── scripts\               ← ALL company scripts (7)
├── configs\               ← sanitized per-bot config snapshots + FLEET.json
├── bundles\               ← skill bundles
├── specs\                 ← chief-of-staff task specs (17)
└── snapshots\             ← dated audit/verification records
```

## 4. Quick Facts

| Item | Value |
|---|---|
| Hermes version at build | v0.20.5 (2026.8.19) |
| Bots | 25 tooled (+10 minimal coordination roles) |
| Teams | Executive · Delivery · Growth · Research · Special-Ops |
| Production line | Kanban board `it-company-ops`, 1 worker max |
| Inference | OpenRouter `:free` ×3 models + NVIDIA NIM fallback |
| Schedulers | Gateway store (always-on) — desktop store parked |
| Watchdog | `company_watchdog.py` every 30 min, silent-when-healthy |
| Ops dashboard | `%HERMES_HOME%\hermes\ops-dashboard.html` |
| Proven output | 3 repos built→QA'd→pushed autonomously on day one |

## 5. Status Legend

Anything marked **[HUMAN STEP]** in these docs requires the owner's hands:
`hermes update` after closing the desktop app · hiding duplicate roster rows · creating the
three group rooms in the Bots tab · Telegram link for phone escalations.
