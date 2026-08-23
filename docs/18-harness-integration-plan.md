# 18 — Earned-Completion Integration ✅ IMPLEMENTED & SELF-TESTED

Adapted from `hermes-harness-plugins`: **completion is EARNED via executable
proofs, never self-declared.** Live since 2026-08-23.

## New scripts (all in `scripts/`, deployed to gateway profile)
| Script | Role |
|---|---|
| `proof_checklist.py` | gen/run/verify per-card proof checklists (exit 0/6/7) |
| `scan_secrets.py` | secret-pattern scanner used as a proof |
| `proof_files_exist.py` | workspace has real content |
| `proof_readme_license.py` | README + LICENSE present |
| `proof_goal_documented.py` | goal.json with non-trivial criteria |
| `proof_repo_live.py` | GitHub repo returns HTTP 200 + non-empty |
| `kanban_dispatch.py` v4 | veto sweep on every tick |

## The 6 standard proofs per build card
1. files-exist (>4 files, >200B outside .git)
2. readme-license present
3. no-secrets (pattern scan)
4. qa-harness PASS (compile+pytest+secrets+docs, per-project-root pytest isolation)
5. goal-criteria-documented (goal.json from card body)
6. repo-live (GitHub API 200) — only when a slug exists

## Veto flow (dispatcher v4)
Every tick: any running card whose worker self-declares `{"status":"complete"}`
gets its checklist verified. Fail → result CLEARED + `COMPLETION_VETOED` event
logged → worker keeps going. Pass → completion accepted.

## Self-test evidence (2026-08-23)
| Test | Expected | Got |
|---|---|---|
| mcp-toolforge (real shipped project) | all proofs pass | ✅ 6/6 EARNED |
| synthetic empty-workspace card claiming done | VETO exit 6 | ✅ vetoed, 6 failing listed |
| end-to-end dispatcher: fake done + empty ws | result cleared + event | ✅ VETOED |
| end-to-end dispatcher: real passing proofs | accepted, no veto | ✅ kept |

## Bugs found & fixed while building this
- qa_harness pytest ran under bare python (no pytest) → now uses hermes venv python
- root-level pytest collected nested example projects → per-project-root isolation,
  top-level run excludes nested roots
- worker pip-installed its own package into the SHARED hermes venv contaminating
  other builds' imports → contaminated copy uninstalled; lesson: builders must
  use their worktree venvs only

## Success criterion — MET
A card with an empty workspace can NEVER reach status='done'.


## CORRECTION (2026-08-23): company scripts live in COMPANY profiles, not bunny

bunny = owner's personal session profile — NOT part of the company hierarchy.
Script ownership now follows the org chart:

| Script(s) | Owner profile | Role |
|---|---|---|
| kanban_dispatch.py, company_watchdog.py, model_health.py, adaptive_intake.py | **devops-engineer** | ops infrastructure |
| adaptive_mode.py | **ceo** | work classification/assignment |
| company_lessons.py + agent-builder/memories/lessons.jsonl | **agent-builder** | cross-build memory |
| proof_checklist.py, qa_harness.py, proof_*.py | **qa-lead** | quality gate |
| scan_secrets.py | **security-engineer** | security proofs |

Runtime note: gateway cron reads from central `%HERMES_HOME%/scripts/` by
filename only — that directory is a runtime mirror; master copies live in the
owner bot's `scripts/` dir. bunny holds no company scripts.
