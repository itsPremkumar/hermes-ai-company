# Claude Code + OpenRouter — free model cookbook

## The correct config (three things I got wrong before finding the cookbook)

Claude Code CAN route through OpenRouter to use free models. The OpenRouter
cookbook at https://openrouter.ai/docs/cookbook/coding-agents/claude-code
documents the correct env vars.

### Old wrong config (what I tried first, got "model not found"):
```
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1   ← WRONG: /v1 suffix
ANTHROPIC_API_KEY=sk-or-...                        ← WRONG: Claude Code reads AUTH_TOKEN, not API_KEY
# ANTHROPIC_API_KEY unset                          ← WRONG: must be EXPLICITLY empty
```

### Correct cookbook config (proven working):
```
ANTHROPIC_BASE_URL=https://openrouter.ai/api       ← NO /v1 suffix
ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY            ← this is the key Claude Code reads
ANTHROPIC_API_KEY=""                                 ← must be EXPLICITLY empty
```

### Additional steps
1. If previously logged into Claude Code with an Anthropic account,
   run `/logout` inside Claude Code to clear cached session.
2. The model slug must be one Claude Code's allowlist accepts AND OpenRouter
   serves. Free models work: `tencent/hy3:free` (pricing 0/0).

## Verified working commands

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="sk-or-..."   # real key
export ANTHROPIC_API_KEY=""
claude --model tencent/hy3:free -p "reply OK"
```

This returned "OK" in testing. The MCP server also works:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"...}' \
| ANTHROPIC_BASE_URL="https://openrouter.ai/api" \
  ANTHROPIC_AUTH_TOKEN="sk-or-..." \
  ANTHROPIC_API_KEY="" \
  claude --model tencent/hy3:free mcp serve
```
Returns valid initialize with `serverInfo: {name: "claude/tengu", version: "2.1.183"}`.
Tools/list returns 32 tools (Write, Read, Edit, Bash, Glob, Grep, Agent, WebFetch, etc.).

## Known limitation (July 2026)

On this Windows host, the Node.js HTTPS client can intermittently fail to reach
OpenRouter (`socket hang up`, timeout) even though curl works fine. This is an
environment-specific TLS/routing issue, not a config error. When it happens,
the `claude` command hangs for 60s then returns empty stdout. The fix/workaround
is unknown — retry later or use a different network. The config itself is correct.

## Related

- `freecode` — an alternative zero-cost MCP coding backend (Write/Read/Edit/Bash/Glob/Grep
  via local Python exec + optional Ollama) that doesn't depend on Node.js networking at all.
  See `references/freecode-gateway.md` in this skill.
