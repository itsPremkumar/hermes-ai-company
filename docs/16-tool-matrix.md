# 16 — Per-Agent Tool Assignment Matrix (exact, from live configs)

Source of truth: each bot's `config.yaml` (`toolsets:` + `platform_toolsets.cli:`).
Snapshot date: 2026-08-23. All models: primary `poolside/laguna-s-2.1:free`
(OpenRouter) with NVIDIA NIM fallback unless noted.

## Toolset legend
| Tool | What it gives the bot |
|---|---|
| `terminal` | Run shell commands |
| `file` | Read/write files |
| `code_execution` | Execute Python/code snippets in sandbox |
| `web` | Web search + page fetch |
| `x_search` | X/Twitter search |
| `memory` | Persistent memory across sessions |
| `session_search` | Search past conversation sessions |
| `skills` | Load and use installed skills |
| `todo` | Manage a task checklist |
| `clarify` | Ask the user clarifying questions |
| `cronjob` | Create/manage scheduled jobs |
| `kanban` | Create/update kanban cards (work assignment) |
| `delegation` | Spawn sub-agents for parallel work |

## Executive & management

### ceo — Chief Executive (max_turns 60)
- **toolsets**: memory, session_search, cronjob, clarify, todo, skills, **kanban**, **delegation**
- **cli_tools**: bfl, clarify, cronjob, delegation, kanban, memory, session_search, skills, todo
- **NO terminal / NO code_execution** (least-privilege: delegates, never executes)
- Special duty: single entry point for work assignment (see its SOUL protocol)

### cto — Technology Officer (60)
- toolsets: hermes-cli, session_search, memory, skills, todo
- cli_tools: session_search, memory, skills, todo
- No execution tools — reviews and advises only

### product-manager (60)
- toolsets: hermes-cli, web, memory, todo, clarify, skills
- cli_tools: web, memory, todo, clarify, skills

## Engineering

### tech-lead (200)
- cli_tools: terminal, file, skills, todo, session_search
- Reviews diffs; can run read-only commands

### backend / fullstack-dev (200)
- cli_tools: terminal, file, code_execution, skills, todo
- Full build stack for implementation

### qa-lead (200)
- cli_tools: terminal, file, code_execution, vision, skills, todo
- Runs test suites; vision for screenshot verification

### devops-engineer (200)
- cli_tools: terminal, file, cronjob, skills (+web via plugin)
- Owns deploy/monitoring schedules

### security-engineer (200)
- cli_tools: terminal, file, code_execution, session_search, skills
- Runs audits, secret scans

## Agentic-AI specialists

### agent-architect (200)
- cli_tools: clarify, file, memory, pixel-office, session_search, skills, todo, web
- Designs systems; no terminal by design

### agent-builder (200)
- cli_tools: terminal, file, code_execution, pixel-office, skills, todo
- Implements agent projects

### mcp-specialist (200)
- cli_tools: terminal, file, code_execution, pixel-office, skills, todo, web
- Builds/tests MCP servers

### prompt-engineer (200)
- cli_tools: file, memory, pixel-office, skills, todo
- code_execution REMOVED (least-privilege pass 2026-08-23)

## Research

### research-analyst (60)
- cli_tools: clarify, memory, session_search, skills, todo, web, x_search
- Web + X search; no execution tools

## Fallback chain (all bots)
1. nvidia / llama-3.3-nemotron-super-49b-v1
2. openrouter / poolside/laguna-s-2.1:free
3. openrouter / z-ai/glm-5.2:free (being phased out — tier unstable)

## Enforcement
- Config-level: `platform_toolsets.cli` is the allow-list.
- Runtime check: ask bot to run a nonce'd echo command — real output proves
  terminal access (models may falsely claim capability).
- See docs/15-tool-access-policy.md for the policy rationale.
