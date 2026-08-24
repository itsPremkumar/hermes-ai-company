# 21 — Skills Hub Utilization Plan

Browse online: **[Skills Hub](https://hermes-agent.nousresearch.com/docs/skills)** — https://hermes-agent.nousresearch.com/docs/skills

The Skills Hub indexes **90,000+ skills across 14 registries** (official,
skills-sh, clawhub, github, lobehub, nvidia, openai, anthropic, huggingface,
voltagent, gstack, minimax, browse-sh, well-known). This plan governs how our
company finds, vets, assigns, and maintains skills per bot per scenario.

## Current state (audited 2026-08-23)
- 13 company scripts + proof system live; skills assigned ad-hoc so far
- fullstack-dev carries 485 skill files (inherited); other bots carry 3–6
- Security scanner auto-blocks dangerous community skills (verified working)

## The pipeline (already live — see docs/12)
```
search (--json) → trust filter (official > clawhub > skills.sh)
→ scanner-gated install → copy to bots/<bot>/skills/ → deploy to
profile → verify via `hermes -p <bot> skills list` → record in docs/12 → commit
```

## Per-bot skill scenarios & targets

| Bot | Scenarios that need hub skills | Wave-2 search queries | Target count |
|---|---|---|---|
| ceo | decision frameworks, OKR templates | "strategy", "okr" | ≤6 total |
| cto | architecture review checklists | "architecture", "tech-radar" | ≤5 |
| product-manager | PRD templates, roadmapping | "prd", "roadmap" | ≤5 |
| tech-lead | code-review guides | "code-review", "refactoring" | ≤4 |
| backend / fullstack-dev | API design, DB migrations, testing patterns | "api-design", "sql", "pytest" | keep lean; rely on lessons |
| qa-lead | test heuristics, coverage tools | "test-heuristics", "coverage" | ≤5 |
| devops-engineer | docker, CI templates, monitoring | "docker-compose", "github-actions" | ≤5 |
| research-analyst | citation formats, fact-check flows | "citations", "fact-check" | ≤4 |
| security-engineer | OWASP checks, dependency audit | "owasp", "dependency-audit" | ≤5 |
| agent-architect | agent design patterns | "agent-patterns", "multi-agent" | ≤4 |
| agent-builder | LangGraph/LangChain recipes | "langgraph", "rag" | ≤6 |
| mcp-specialist | MCP server templates | "mcp-server" | ≤5 |
| prompt-engineer | eval harnesses, few-shot libraries | "prompt-eval" | ≤4 |

Rules: max 3 new hub skills per bot per wave · official source first ·
scanner BLOCKED = skip forever · every install recorded in docs/12.

## Wave-2 execution plan (next session, ~1 hr)
1. Run the searches above with `--source official` first; fall back to clawhub.
2. Install top pick per bot into its profile; verify with `hermes -p <bot> skills list`.
3. Sync SKILLS.txt manifests in bots/<bot>/ kits.
4. Commit + push (fleet-sync Action will validate).

## Ongoing governance
- Monthly: re-run model_health-style sweep for newly-broken community skills.
- Any bot that fails a build twice for a missing capability gets a targeted
  Skills Hub search queued as a wave task.
- Dangerous-verdict skills are never forced; document the block in docs/12.
