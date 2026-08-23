# 15 — Tool Access Policy (Least Privilege)

Every bot gets ONLY the tools its role requires. Audited 2026-08-23.

## Access matrix

| Bot | terminal | code_execution | file | web | memory | kanban | delegation | notes |
|---|---|---|---|---|---|---|---|---|
| ceo | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | delegates; never runs shell |
| cto | ❌ | ❌ | ❌ | ❌ | ✅ | — | — | review/design only |
| product-manager | ❌ | ❌ | ❌ | ✅ | ✅ | — | — | research + specs |
| tech-lead | ✅ | ❌ | ✅ | — | — | — | — | reviews diffs |
| backend / fullstack-dev | ✅ | ✅ | ✅ | — | — | — | — | builders |
| qa-lead | ✅ | ✅ | ✅ | — | — | — | — | runs tests (+vision) |
| devops-engineer | ✅ | ❌ | ✅ | — | — | — | — | deploy/monitor + cronjob |
| security-engineer | ✅ | ✅ | ✅ | — | ✅ | — | — | audits |
| research-analyst | ❌ | ❌ | ❌ | ✅ | ✅ | — | — | web+x_search only |
| agent-architect | ❌ | ❌ | ✅ | ✅ | ✅ | — | — | designs, never executes |
| agent-builder | ✅ | ✅ | ✅ | — | — | — | — | implements designs |
| mcp-specialist | ✅ | ✅ | ✅ | ✅ | — | — | — | builds/tests servers |
| prompt-engineer | ❌ | ❌* | ✅ | — | ✅ | — | — | *code_execution stripped |

## Rules
1. **Managers don't execute.** ceo/cto/PM/architect have no shell.
2. **Builders get full local stack** (terminal+file+code) but no delegation.
3. **Only ceo delegates** (kanban + delegation toolsets).
4. Runtime verification beats config: after any change, ask the bot to run a
   nonce'd echo command; real execution output proves terminal access.
5. `pixel-office` removed from ceo (bundled-skill tool surface).
