# Fleet Changelog

## 2026-08-23 — Lean rebuild v2
- Full wipe: 35 old profiles deleted; clean-slate restart.
- Lean core fleet rebuilt from blueprints: ceo, cto, product-manager, tech-lead,
  backend, fullstack-dev, qa-lead, devops-engineer, research-analyst, security-engineer.
- NEW agentic specialists added: agent-architect, agent-builder, mcp-specialist, prompt-engineer.
- CEO given kanban + delegation toolsets — single entry point for work assignment
  (Work Assignment Protocol in its SOUL).
- Models re-pinned: poolside/laguna-s-2.1:free primary (nemotron/glm :free tiers retired/unreliable),
  NVIDIA NIM fallback.
- Dispatcher v3 (pure Python) replaced bash version; gateway cron reads scripts from
  profiles/<gateway>/scripts/ (WSL-free).
- OUTPUT LAW added to all build cards after phantom-completion incident:
  files must exist in workspace + git commit must succeed or card = failed.
- mcp-toolforge shipped: github.com/<github-account>/mcp-toolforge (31 files, security audit included).
