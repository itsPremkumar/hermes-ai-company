# 🤖 All Bots — Full Details (34)

> Live rebuild data: `configs/FLEET.json` · Per-bot kits: `bots/<name>/` · Personas: `souls/`

## Quick table

| Bot | Role | Model |
|---|---|---|
| [`architect`](#architect) | Architect (legacy) | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`backend`](#backend) | Backend Engineer | `poolside/laguna-s-2.1:free` |
| [`business-dev`](#business-dev) | Business Development | `z-ai/glm-5.2:free` |
| [`ceo`](#ceo) | Chief Executive | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`chief-of-staff`](#chief-of-staff) | Chief of Staff | `(inherit)` |
| [`coo`](#coo) | Chief Operating Officer | `(inherit)` |
| [`cto`](#cto) | Chief Technology Officer | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`data-engineer`](#data-engineer) | Data Engineer | `poolside/laguna-s-2.1:free` |
| [`devops`](#devops) | DevOps (legacy) | `poolside/laguna-s-2.1:free` |
| [`devops-engineer`](#devops-engineer) | DevOps Engineer | `poolside/laguna-s-2.1:free` |
| [`engineering-manager`](#engineering-manager) | Engineering Manager | `z-ai/glm-5.2:free` |
| [`frontend`](#frontend) | Frontend Engineer | `poolside/laguna-s-2.1:free` |
| [`fullstack-dev`](#fullstack-dev) | Fullstack Developer | `poolside/laguna-s-2.1:free` |
| [`hr-recruiter`](#hr-recruiter) | HR Recruiter | `nvidia/nemotron-nano-9b-v2:free` |
| [`it-support`](#it-support) | IT Support | `nvidia/nemotron-nano-9b-v2:free` |
| [`junior-dev`](#junior-dev) | Junior Developer | `(inherit)` |
| [`product-manager`](#product-manager) | Product Manager | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`product-owner`](#product-owner) | Product Owner | `(inherit)` |
| [`project-manager`](#project-manager) | Project Manager | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`qa-engineer`](#qa-engineer) | QA Engineer | `poolside/laguna-s-2.1:free` |
| [`qa-lead`](#qa-lead) | QA Lead — QUALITY GATE | `poolside/laguna-s-2.1:free` |
| [`research-analyst`](#research-analyst) | Research Analyst | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`scrum-master`](#scrum-master) | Scrum Master | `(inherit)` |
| [`security-engineer`](#security-engineer) | Security Engineer | `poolside/laguna-s-2.1:free` |
| [`senior-backend`](#senior-backend) | Senior Backend Engineer | `poolside/laguna-s-2.1:free` |
| [`senior-frontend`](#senior-frontend) | Senior Frontend Engineer | `poolside/laguna-s-2.1:free` |
| [`solution-architect`](#solution-architect) | Solution Architect | `nvidia/nemotron-3-super-120b-a12b:free` |
| [`tech-lead`](#tech-lead) | Tech Lead | `poolside/laguna-s-2.1:free` |
| [`technical-writer`](#technical-writer) | Technical Writer | `z-ai/glm-5.2:free` |
| [`tester`](#tester) | Tester | `poolside/laguna-s-2.1:free` |
| [`ui-ux-designer`](#ui-ux-designer) | UI/UX Designer | `z-ai/glm-5.2:free` |
| [`vp-delivery`](#vp-delivery) | VP Delivery | `(inherit)` |
| [`vp-engineering`](#vp-engineering) | VP Engineering | `(inherit)` |
| [`vp-sales`](#vp-sales) | VP Sales | `z-ai/glm-5.2:free` |

---


## EXECUTIVE team

### `ceo` — Chief Executive

Sets company priorities, runs morning briefings & weekly reviews, owns escalations. Delegates by @mention; never executes directly.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `memory`, `session_search`, `cronjob`, `clarify`, `todo`, `skills`
- **Skills (38):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `weekly-review-planning`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/ceo/`](../bots/ceo/) · **Run:** `hermes -p ceo chat`

---

### `cto` — Chief Technology Officer

Owns technical strategy, architecture decisions, tool/model vetting (with security-engineer), and delivery standards.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `session_search`, `memory`, `skills`, `todo`
- **Skills (38):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `oss-project-vetting`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/cto/`](../bots/cto/) · **Run:** `hermes -p cto chat`

---

### `coo` — Chief Operating Officer

Cross-team operational coordination; advises on process; no execution tools by design.

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/coo/`](../bots/coo/) · **Run:** `hermes -p coo chat`

---

### `chief-of-staff` — Chief of Staff

Runs the kanban pipeline: creates/decomposes task cards, routes work via the routing map, owns COMPANY_WORK_SOP compliance.

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/chief-of-staff/`](../bots/chief-of-staff/) · **Run:** `hermes -p chief-of-staff chat`

---

### `product-manager` — Product Manager

Turns goals into specs; light market research; feeds Delivery room with requirements.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `web`, `memory`, `todo`, `clarify`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/product-manager/`](../bots/product-manager/) · **Run:** `hermes -p product-manager chat`

---

### `product-owner` — Product Owner

Backlog ownership & acceptance criteria advice (advisory role).

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/product-owner/`](../bots/product-owner/) · **Run:** `hermes -p product-owner chat`

---

### `project-manager` — Project Manager

Timeline & dependency tracking across cards; status reporting to ceo.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/project-manager/`](../bots/project-manager/) · **Run:** `hermes -p project-manager chat`

---


## RESEARCH & DATA team

### `research-analyst` — Research Analyst

PRIMARY live-data collector: internet search, X/Twitter listening, market/competitor scans. Born 2026-08-22.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `web`, `x_search`, `session_search`, `memory`, `skills`, `clarify`, `todo`
- **Skills (0):** —
- **Folder:** [`bots/research-analyst/`](../bots/research-analyst/) · **Run:** `hermes -p research-analyst chat`

---

### `data-engineer` — Data Engineer

Crunches collected data into datasets/reports; code_execution pipelines.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `code_execution`, `file`, `terminal`, `web`, `memory`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/data-engineer/`](../bots/data-engineer/) · **Run:** `hermes -p data-engineer chat`

---


## DELIVERY team

### `tech-lead` — Tech Lead

Reviews diffs, assigns implementation tasks, enforces standards; runs codebase-inspection; final synthesis in swarms.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `terminal`, `file`, `skills`, `todo`, `session_search`
- **Skills (39):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `codebase-inspection`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `github-issue-to-pr`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/tech-lead/`](../bots/tech-lead/) · **Run:** `hermes -p tech-lead chat`

---

### `backend` — Backend Engineer

Server-side implementation in isolated worktrees; carries github-issue-to-pr SOP.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `terminal`, `file`, `code_execution`, `skills`, `todo`
- **Skills (38):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `github-issue-to-pr`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/backend/`](../bots/backend/) · **Run:** `hermes -p backend chat`

---

### `senior-backend` — Senior Backend Engineer

Reserve depth for complex server work (hidden roster candidate).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/senior-backend/`](../bots/senior-backend/) · **Run:** `hermes -p senior-backend chat`

---

### `frontend` — Frontend Engineer

UI implementation; image_gen for mockups.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `file`, `image_gen`, `skills`, `todo`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/frontend/`](../bots/frontend/) · **Run:** `hermes -p frontend chat`

---

### `senior-frontend` — Senior Frontend Engineer

Reserve depth for complex UI work (hidden roster candidate).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/senior-frontend/`](../bots/senior-frontend/) · **Run:** `hermes -p senior-frontend chat`

---

### `fullstack-dev` — Fullstack Developer

PRIMARY production-line worker — built research-radar end-to-end; worktree builds, issue→PR.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `terminal`, `file`, `code_execution`, `skills`, `todo`
- **Skills (38):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `github-issue-to-pr`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/fullstack-dev/`](../bots/fullstack-dev/) · **Run:** `hermes -p fullstack-dev chat`

---

### `junior-dev` — Junior Developer

Shadow/learning tasks only; minimal tools.

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/junior-dev/`](../bots/junior-dev/) · **Run:** `hermes -p junior-dev chat`

---

### `qa-lead` — QA Lead — QUALITY GATE

FINAL GATE: project suite + qa_harness.py must exit 0; never accepts self-reports; codebase-inspection enabled.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `terminal`, `file`, `code_execution`, `vision`, `skills`
- **Skills (38):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `codebase-inspection`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/qa-lead/`](../bots/qa-lead/) · **Run:** `hermes -p qa-lead chat`

---

### `qa-engineer` — QA Engineer

Test authoring support (hidden roster candidate).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/qa-engineer/`](../bots/qa-engineer/) · **Run:** `hermes -p qa-engineer chat`

---

### `tester` — Tester

Manual/exploratory test checklists (hidden roster candidate).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (14):** `apple`, `autonomous-ai-agents`, `creative`, `devops`, `email`, `github`, `media`, `mlops`, `note-taking`, `productivity`, `research`, `smart-home`, `social-media`, `software-development`
- **Folder:** [`bots/tester/`](../bots/tester/) · **Run:** `hermes -p tester chat`

---

### `devops` — DevOps (legacy)

Older profile; superseded by devops-engineer (hide candidate).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/devops/`](../bots/devops/) · **Run:** `hermes -p devops chat`

---

### `devops-engineer` — DevOps Engineer

Deploys via Vercel MCP, CI pipelines, cron-owned cleanup routines.

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free`
- **Tools:** `terminal`, `file`, `cronjob`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/devops-engineer/`](../bots/devops-engineer/) · **Run:** `hermes -p devops-engineer chat`

---

### `security-engineer` — Security Engineer

Secret scans, dependency audits, oss-project-vetting; signs off merges (SECURITY-APPROVED).

- **Model pin:** `poolside/laguna-s-2.1:free`
- **Fallbacks:** —
- **Tools:** `terminal`, `file`, `code_execution`, `session_search`, `skills`
- **Skills (39):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `oss-project-vetting`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/security-engineer/`](../bots/security-engineer/) · **Run:** `hermes -p security-engineer chat`

---


## GROWTH team

### `business-dev` — Business Development

Lead-gen research, repo growth, competitor price monitoring, content-site marketing.

- **Model pin:** `z-ai/glm-5.2:free`
- **Fallbacks:** —
- **Tools:** `web`, `memory`, `skills`, `tts`
- **Skills (40):** `agent-native-distribution`, `apple`, `automated-content-site`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `github-repo-growth`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `product-price-monitor`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/business-dev/`](../bots/business-dev/) · **Run:** `hermes -p business-dev chat`

---

### `vp-sales` — VP Sales

Outreach research, pricing intel (x_search), voice summaries (tts).

- **Model pin:** `z-ai/glm-5.2:free`
- **Fallbacks:** —
- **Tools:** `web`, `x_search`, `memory`, `tts`
- **Skills (39):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `github-repo-growth`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `product-price-monitor`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/vp-sales/`](../bots/vp-sales/) · **Run:** `hermes -p vp-sales chat`

---

### `technical-writer` — Technical Writer

Docs/READMEs/blogs; content-site marketing channel.

- **Model pin:** `z-ai/glm-5.2:free`
- **Fallbacks:** —
- **Tools:** `file`, `web`, `image_gen`, `skills`
- **Skills (38):** `agent-native-distribution`, `apple`, `automated-content-site`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/technical-writer/`](../bots/technical-writer/) · **Run:** `hermes -p technical-writer chat`

---

### `hr-recruiter` — HR Recruiter

Job descriptions, screening criteria, job-hunting market research.

- **Model pin:** `nvidia/nemotron-nano-9b-v2:free`
- **Fallbacks:** —
- **Tools:** `web`, `file`, `clarify`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/hr-recruiter/`](../bots/hr-recruiter/) · **Run:** `hermes -p hr-recruiter chat`

---


## SPECIAL OPS team

### `ui-ux-designer` — UI/UX Designer

Mockups (image_gen) + design review (vision).

- **Model pin:** `z-ai/glm-5.2:free`
- **Fallbacks:** —
- **Tools:** `image_gen`, `vision`, `file`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/ui-ux-designer/`](../bots/ui-ux-designer/) · **Run:** `hermes -p ui-ux-designer chat`

---

### `it-support` — IT Support

ONLY bot with computer_use — machine health, GUI fixes.

- **Model pin:** `nvidia/nemotron-nano-9b-v2:free`
- **Fallbacks:** —
- **Tools:** `terminal`, `computer_use`, `file`, `skills`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/it-support/`](../bots/it-support/) · **Run:** `hermes -p it-support chat`

---


## COORDINATION team

### `scrum-master` — Scrum Master

Ceremony facilitation advice (advisory role).

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/scrum-master/`](../bots/scrum-master/) · **Run:** `hermes -p scrum-master chat`

---

### `vp-delivery` — VP Delivery

Delivery risk oversight (advisory role).

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/vp-delivery/`](../bots/vp-delivery/) · **Run:** `hermes -p vp-delivery chat`

---

### `vp-engineering` — VP Engineering

Engineering org oversight (advisory role).

- **Model pin:** `(inherit)`
- **Fallbacks:** —
- **Tools:** minimal
- **Skills (0):** —
- **Folder:** [`bots/vp-engineering/`](../bots/vp-engineering/) · **Run:** `hermes -p vp-engineering chat`

---

### `engineering-manager` — Engineering Manager

People/process management advice (advisory role).

- **Model pin:** `z-ai/glm-5.2:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/engineering-manager/`](../bots/engineering-manager/) · **Run:** `hermes -p engineering-manager chat`

---

### `architect` — Architect (legacy)

Superseded by solution-architect/cto (hide candidate).

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/architect/`](../bots/architect/) · **Run:** `hermes -p architect chat`

---

### `solution-architect` — Solution Architect

System design blueprints for complex cards.

- **Model pin:** `nvidia/nemotron-3-super-120b-a12b:free`
- **Fallbacks:** —
- **Tools:** `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web`
- **Skills (37):** `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao`
- **Folder:** [`bots/solution-architect/`](../bots/solution-architect/) · **Run:** `hermes -p solution-architect chat`

---
