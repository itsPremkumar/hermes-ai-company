# 02 — Fleet Roster (verified 2026-08-22)

All bots are Hermes profiles at `%HERMES_HOME%\hermes\profiles\<name>\`.
Toolsets live in `platform_toolsets.cli` of each profile's `config.yaml`.
Models pinned in `model:` block; fallback chain in `fallback_providers:`.

## Executive Team
| Bot | Model pin | Tools | Extra skills |
|---|---|---|---|
| ceo | nemotron-3-super:free | memory, session_search, cronjob, clarify, todo, skills | weekly-review-planning, free-dev-team |
| cto | glm-5.2:free | session_search, memory, skills, todo | oss-project-vetting, free-dev-team |
| product-manager | nemotron-3-super:free | web, memory, todo, clarify, skills | — |

## Research & Data Team
| Bot | Tools | Notes |
|---|---|---|
| research-analyst *(born 08-22)* | web, x_search, session_search, memory, skills, clarify, todo | the live-data collector |
| data-engineer | code_execution, file, terminal, web, memory, skills | crunches what research collects |
| business-dev | web, memory, skills, tts | lead-gen + market scans; repo-growth, price-monitor, content-site |

## Delivery Team (all have NVIDIA-NIM first fallback)
| Bot | Tools | Extra skills |
|---|---|---|
| tech-lead | terminal, file, skills, todo, session_search | github-issue-to-pr, codebase-inspection |
| backend | terminal, file, code_execution, skills, todo | github-issue-to-pr |
| fullstack-dev | terminal, file, code_execution, skills, todo | github-issue-to-pr |
| frontend | file, image_gen, skills, todo | — |
| qa-lead | terminal, file, code_execution, vision, skills | codebase-inspection · **quality-gate SOUL order** |
| devops-engineer | terminal, file, cronjob, skills | Vercel MCP deploys |
| junior-dev | (minimal) | reserved for shadow tasks |

## Growth Team
| Bot | Tools | Extra skills |
|---|---|---|
| technical-writer | file, web, image_gen, skills | automated-content-site |
| vp-sales | web, x_search, memory, tts | repo-growth, price-monitor |
| hr-recruiter | web, file, clarify, skills | job-hunting |

## Special Ops
| Bot | Tools | Notes |
|---|---|---|
| ui-ux-designer | image_gen, vision, file, skills | mockups on demand |
| it-support | terminal, computer_use, file, skills | ONLY bot with desktop control |
| security-engineer | terminal, file, code_execution, session_search, skills | secret-scans, audits |

## Coordination roles (deliberately tool-less)
coo · chief-of-staff · scrum-master · product-owner · vp-delivery · vp-engineering —
they think and advise; they cannot execute anything.

## Planned group rooms [HUMAN STEP]
Exec (ceo·cto·product-manager) · Delivery (tech-lead·backend·qa-lead) ·
Growth (business-dev·vp-sales·technical-writer)

## Duplicate profiles to HIDE in roster UI [HUMAN STEP]
devops, qa-engineer, tester, architect, solution-architect, senior-backend,
senior-frontend, engineering-manager, vp-delivery, vp-engineering, product-owner,
scrum-master, data-engineer, frontend-or-ui-ux (pick one to keep visible)
