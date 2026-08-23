# 19 — Supervisor Rotation & Lessons Memory (IMPLEMENTED)

Adapted from NVIDIA AVO's two core long-horizon mechanisms. Live 2026-08-23.

## P0 — Supervisor Rotation (`kanban_dispatch.py`)
Every dispatcher tick scans blocked cards with `consecutive_failures >= 2`:
- **Rotation 1**: model_override → next in fallback chain (laguna:free ↔ NVIDIA NIM)
- **Rotation 2+**: injects approach-change hint into card body
- **After 3 rotations**: `SUPERVISOR_PARKED` event, needs human attention

Self-test: rotated a synthetic card (laguna→NIM, event logged) AND 3 real
stuck cards on its first tick.

## P1 — Cross-Build Lessons (`company_lessons.py`)
```
python company_lessons.py record <card> <done|failed> "+worked;-failed;..."
python company_lessons.py read [n]
python company_lessons.py stats
```
Ledger: `profiles/agent-builder/memories/lessons.jsonl`
agent-builder SOUL has MANDATORY rule to read it before any build.

## Script ownership (org chart, NOT bunny)
| Scripts | Owner |
|---|---|
| kanban_dispatch, watchdog, model_health, adaptive_intake | devops-engineer |
| adaptive_mode | ceo |
| company_lessons + lessons.jsonl | agent-builder |
| proof_checklist, qa_harness, proof_* | qa-lead |
| scan_secrets | security-engineer |

Gateway cron reads central `%HERMES_HOME%/scripts/` (runtime mirror);
master copies live in owner profiles. bunny holds nothing.

## Verification (2026-08-23)
- P0 synthetic rotation test: fired, model rotated, event logged ✅
- P1 ledger seeded + agent-builder confirms rule visible in context ✅
- Live tick with real builds running: silent success, RAM stable ✅
