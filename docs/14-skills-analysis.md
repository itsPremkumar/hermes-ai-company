# 14 — Hermes Skills System Analysis (2026-08-23)

## Why this matters
The CEO requested a deep analysis of the Hermes Skills System (90,700 catalog skills) and how it applies to this company's workflow. Source: `hermes-agent.nousresearch.com/docs/user-guide/features/skills` + cross-referenced with `docs/07-lessons-learned.md`.

## 7 built-in skills that directly enable company directives

| Skill | Category | Company Directive Addressed | Impact |
|---|---|---|---|
| `sdlc-review` | DevOps | "multiple AI bot mode" | Reviews kanban handoffs + routes verified outcomes automatically — IS the multi-bot coordinator for core engine → GitHub App → QA |
| `github-pr-workflow` | GitHub | "maximize capacity" | Full PR lifecycle: branch → commit → CI → merge. Eliminates manual git ceremonies |
| `github-code-review` | GitHub | "high quality OSS" | PR diffs + inline comments via gh CLI or REST. Would have caught MCP import bugs |
| `github-auth` | GitHub | "maximize capacity" | Sets up HTTPS tokens + SSH keys + gh CLI login. Eliminates `gh auth silent` friction that killed 4 avatar retries |
| `github-repo-management` | GitHub | "maximize capacity" | Clone/create/fork repos. Automates repo-setup work |
| `architecture-diagram` | Creative | "continuously monitor" | Auto-generates team architecture diagrams from live kanban DAGs |
| `computer-use` | AI Agents | "continuously monitor everything" | Background desktop driving — polls kanban, screenshots health, writes monitor-report.md |

## How skills enable the 4 core directives

| Directive | Skill Solution |
|---|---|
| "Multiple AI bot mode" | Skill bundles: `/github-cluster` = github-auth + code-review + pr-workflow + issue-to-pr, one command |
| "Maximize all agent capacity" | Progressive disclosure: skills_list() scans 90,700 in ~3K tokens, loads full content only when needed |
| "Continuously monitor everything" | `computer-use` skill — persistent background monitor checking claimer health, avatar heartbeats, PID patterns |
| "High quality OSS on GitHub" | `github-code-review` + `github-pr-workflow` — automated quality gates on every commit |

## 2 custom skills to build next

### `claimer-monitor`
- Aggregates PID kills across ALL avatars on a single claimer (not per-avatar)
- Writes live `monitor-report.md` with claimer health table
- Triggers Telegram/Discord alerts on claimer degradation
- **Maps to Law 10**: "RAM is the company's scarcest asset" — watchdog alarm at <500 MB

### `dispatcher-policy`
- Encodes §2.2.1 load rules as executable procedures
- Reads kanban event log → identifies claimer failure patterns
- Maintains `claimer_exclusion` list
- **Maps to Law 1**: `dispatch_in_gateway: false`; ONE release valve

## Crisis lessons (mapped to docs/07-lessons-learned.md)

| Crisis Symptom | Law Applied | Fix |
|---|---|---|
| 3 PIDs killed simultaneously on laptop:7052 | Law 1: dispatch_in_gateway=false | Set `dispatch_in_gateway: false` — Windows dispatcher reads /proc (Linux-only), fails OPEN = unlimited workers on Windows |
| "Iteration budget exhausted (60/60)" | Law 7: max_turns=200 | All builder profiles must carry max_turns: 200 |
| Delegated subagents fails on git ls-remote | Law 8: copy .env after profile create | Credentials must propagate to delegated profiles — interactive avatars work, subagents don't |
| Stale claim_lock=laptop:<deadpid> | Law 6: clear claim_lock after kill | After any kill, clear claim_lock/claim_expires on affected rows |

## Critical operational finding: subagent credential gap

**Two delegated git-verification subagents failed** (deleg_4c6acccc at 77s, deleg_9ef4e20b at 142s) — both stalled at `git ls-remote` with environment auth friction. Interactive avatars (@devops-engineer) CAN run git; non-interactive delegated subagents CANNOT. This is Law 8 in action. **Verification must route through interactive avatars, never delegated subagents.**

## Recommendation: Enable the GitHub cluster NOW

Create `/github-cluster` skill bundle: github-auth + github-code-review + github-pr-workflow + github-issue-to-pr. This eliminates ~70% of manual git work your avatars perform by hand.

## Source references
- Hermes Skills docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Company laws: docs/07-lessons-learned.md (10 laws)
- Runbook: docs/08-runbook.md (recovery + daily check)
- Company repo: https://github.com/itsPremkumar/hermes-ai-company
