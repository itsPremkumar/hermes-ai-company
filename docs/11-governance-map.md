# 11 — Governance Map & Gap Register

Where every governing document lives, and which known gaps remain.

## Document hierarchy (who wins on conflict)

```
docs/09-sops.md            ← Constitution (highest)
docs/sop-workflows/
  COMPANY_WORK_SOP.md      ← work lifecycle: ready→assigned→claimed→in_progress
                             →review→approved→completed→archived; ACK rule;
                             routing map; board = single source of truth
  PARALLEL_WORKFLOW_SOP.md ← worktree isolation, branch/PR discipline,
                             §8 MANDATORY Security Merge Gate
                             (SECURITY-APPROVED / SECURITY-BLOCKED)
souls/*/                   ← per-bot persona + standing orders
docs/07-lessons-learned.md ← the 10 laws from real incidents
DEPLOY.md                  ← rebuild procedure for fresh machines
```

## Full asset inventory

| Tier | Location | Contents |
|---|---|---|
| 1 Constitution | `docs/09-sops.md` | §1–§6 all standing laws |
| 2 Workflow SOPs | `docs/sop-workflows/` | work lifecycle, ACK rule, security merge gate |
| 3 Roadmap | `docs/10-product-roadmap.md` | the 20-product build plan |
| 4 Executable skills | `skills-hub-company/` | kanban-orchestrator, kanban-worker, sdlc-review, fleet-cicd-verification, hermes-ops-dashboard |
| 5 Bot personas | `souls/` (34) | one per org profile |
| 6 Configs | `configs/` (29 + FLEET.json) | sanitized rebuild data |
| 7 Scripts | `scripts/` (7) | watchdog, dispatcher, QA, model guard, devops loop |
| 8 Specs | `specs/` (17) | chief-of-staff task templates & artifacts |
| 9 Snapshots | `snapshots/` | audit, cron list, board CSV |

## Known gaps (honest register — fix, don't hide)

| # | Gap | Status |
|---|---|---|
| G1 | Some early projects were dispatched via direct bot chat, NOT through the kanban board → no ACK trail, no review/security gates on that work. **Rule going forward: every task enters through the board.** | process debt acknowledged |
| G2 | Group rooms not yet created [HUMAN STEP] | pending owner |
| G3 | Roster duplicates not hidden yet [HUMAN STEP] | pending owner |
| G4 | `hermes update` pending (must close app first) [HUMAN STEP] | pending owner |
| G5 | No phone escalation channel until Telegram linked [HUMAN STEP] | pending owner |
