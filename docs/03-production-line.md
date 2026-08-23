# 03 — Production Line (Kanban)

## Board
`it-company-ops` (SQLite WAL) at
`%HERMES_HOME%\hermes\kanban\boards\it-company-ops\kanban.db`

## Card states and who may set them

```
blocked ──(kanban_dispatch.sh v2, ONE per tick)──▶ ready ──(dispatcher spawn)──▶ running
   ▲                                    │                             │
   │        failure / gave_up           │                             │ success + QA PASS
   │◀───────────────────────────────────┘                             ▼
   │                                                              done
   └────────────── QA FAIL (request-changes) ◀── review ◀──────────┘
```

**THE LAWS** (each earned the hard way — see 07):

1. **Cards LIVE in `blocked`.** The gateway's embedded dispatcher auto-spawns every
   `ready`/`todo` card it sees and **ignores config caps on Windows**. Only `blocked`
   is untouched by it.
2. **One worker maximum, ever.** Each bot process ≈ 400–600 MB on this 6 GB box.
3. **`kanban_dispatch.sh` is the ONLY release valve.**
   - if any card is `running` → do nothing (silent exit)
   - else promote exactly ONE blocked → ready → dispatch --max 1
4. **Gateway embedded dispatcher must stay OFF:**
   `profiles/<gateway-profile>/config.yaml → kanban: dispatch_in_gateway: false`
   (needs gateway restart after change)
5. **Killed workers leave stale claims.** Dispatcher silently skips rows with a
   `claim_lock`. After killing workers: clear `claim_lock/claim_expires` for affected rows.
6. **max_turns=200 for builder bots** (fullstack-dev, backend, frontend, qa-lead,
   tech-lead, junior-dev). 60 was proven too small for full project builds.

## Verified flow of 2026-08-22 (the reference run)

| Attempt | Outcome | Lesson |
|---|---|---|
| #10/#30 | crashed (my kill during fan-out emergency) | expected |
| #50 | gave_up at turn 60/60 | budget raised to 200 |
| #51 | **completed in 829 s** — built research-radar, self-QA 23/23, security-reviewed, pushed + PR merged to <github-account>/research-radar | full pipeline works |

Independent verification (fresh clone + qa_harness.py): COMPILE 13 ✔ · PYTEST 23 ✔ ·
SECRETS clean ✔ · DOCS ✔ → VERDICT PASS.

## Adding work

```bash
hermes kanban create "Build: <name>" --assignee fullstack-dev \
  --body "Free-stack agentic project. Build in worktree ..., push to <github-account>/<name>"
# card lands in triage/todo; move to blocked so it queues safely:
hermes kanban block <task_id> "queued for production line"
```

The hourly cron (`kanban-production-line`) will pick it up automatically.
