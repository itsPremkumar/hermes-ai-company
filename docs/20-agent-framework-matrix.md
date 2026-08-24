# 20 — Bot × Advanced Agent Framework Matrix

Which advanced agentic framework/pattern each bot uses, per scenario.
Hermes Bot Mode is the HOST; these are the design patterns our bots apply.

## Framework legend (2026 landscape)
| Pattern | Origin | Our usage |
|---|---|---|
| Graph workflow | LangGraph | state machines with cycles + human-in-loop |
| Role-based crew | CrewAI | specialist teams w/ defined roles |
| Handoff/orchestrator | OpenAI Agents SDK | CEO routes work to specialists |
| Deep-agent loop | DeepAgents | plan tool + filesystem + sub-agents for long builds |
| Code-as-action | Smolagents/HF | small free models act by writing Python |
| Class-as-agent | NOOA (NVIDIA) | agent = one testable Python class |
| Evolutionary variation | AVO (NVIDIA) | supervisor rotation + earned completion (LIVE) |
| MCP tools | Anthropic | universal tool servers |

## Per-bot assignment

### ceo — Orchestrator pattern (OpenAI Agents SDK style)
- Scenario: ANY incoming work request
- Uses: kanban + delegation toolsets; classifies → routes → tracks via card IDs
- Framework mapping: handoffs. CEO = triage agent; specialists = sub-agents.

### agent-architect — Graph-workflow designer (LangGraph style)
- Scenario: new agentic project specs
- Outputs: mermaid state graphs, node specs, typed handoff payloads,
  stop conditions — LangGraph-implementable designs ≤6 nodes

### agent-builder — Deep-agent loop (DeepAgents/LangGraph)
- Scenario: implementing designed systems
- Uses: goal-mode cards (= AVO-style iterate-until-judge-done), filesystem +
  terminal tools, lessons.jsonl memory across builds

### mcp-specialist — MCP-native tooling
- Scenario: any tool-integration need
- Builds MCP servers so EVERY bot gains new tools without code changes

### prompt-engineer — Code-as-action advocate (Smolagents style)
- Scenario: free-tier model performance problems
- Designs prompts that emit executable actions instead of prose

### research-analyst — Tool-augmented retrieval
- Scenario: market/tech research
- web + x_search + memory; cited reports

### qa-lead / security-engineer — Gate keepers (earned completion, AVO-derived)
- Scenario: every build's final phase
- proof_checklist vetoes: files/tests/secrets/repo-live proofs REQUIRED

### devops-engineer — Ops automation
- Scenario: CI/deploy/monitoring
- owns dispatcher v4 (supervisor rotation), watchdog, schedules

## Scenario → pipeline map
| Scenario | Flow |
|---|---|
| "Build app X" | ceo→card→fullstack-dev(goal)→qa-lead proofs→ship |
| "Research topic" | ceo→research-analyst→cited report card |
| "Design agent system" | cto→agent-architect spec→agent-builder impl→qa |
| "Add company tool" | mcp-specialist builds MCP server→all bots gain it |
| "Stalled build" | devops-engineer supervisor rotates model/approach |
