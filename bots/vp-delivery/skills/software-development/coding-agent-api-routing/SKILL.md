---
name: coding-agent-api-routing
description: "Route coding agents (Claude Code, Codex) through alternative API providers (OpenRouter, Ollama, LiteLLM) to use free or low-cost models."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [claude-code, openrouter, api-routing, free-models, coding-agents, mcp, antropic-compatible]
    related_skills: [mcp-server-verification, mcp-server-build, systematic-debugging]
---

# Coding Agent API Routing

Route coding agent CLIs (Claude Code, Codex, etc.) through alternative API providers to use free or low-cost models without the native key.

## When to Use

- You have a coding agent CLI that requires a paid API key (e.g., Anthropic for Claude Code)
- You want to use a free model (e.g., `tencent/hy3:free` on OpenRouter) through that CLI
- The agent sends requests in Anthropic/OpenAI API format and accepts a configurable base URL
- You need headless/MCP-server mode for automated use

## Claude Code + OpenRouter (proven)

### The Correct Config (3 vars — subtle: wrong names cost hours)

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"   # NOTE: NOT /v1 suffix
export ANTHROPIC_AUTH_TOKEN="sk-or-..."                  # Claude Code reads THIS, not ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=""                              # Must be EXPLICITLY empty (conflict)
```

**Common mistakes that cause "model not found":**
- Using `https://openrouter.ai/api/v1` — the `/v1` suffix breaks routing
- Setting `ANTHROPIC_API_KEY` instead of `ANTHROPIC_AUTH_TOKEN` — Claude Code ignores ANTHROPIC_API_KEY for auth
- Leaving `ANTHROPIC_API_KEY` unset (not explicitly empty) — causes auth conflicts
- Not clearing cached Anthropic login (`claude /logout`) — cached credentials shadow env vars

### Finding a Working Model Slug

1. Query OpenRouter's model list for available models:
```bash
curl -s https://openrouter.ai/api/v1/models -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  | python -c "import sys,json; ms=json.load(sys.stdin)['data']; [print(m['id'], '| pricing:', m['pricing']) for m in ms if m['id'].startswith('anthropic') or 'free' in m['id'].lower()]"
```

2. Filter by pricing — genuinely free models have `prompt: 0, completion: 0`

3. Claude Code accepts model slugs pass-through (it doesn't validate them against an Anthropic allowlist when routing via custom base URL). Any slug OpenRouter serves works, including:
   - `tencent/hy3:free` (proven working, $0)
   - Other OpenRouter `*:free` models

### Testing the Connection

```bash
claude --model tencent/hy3:free -p "reply with the single word: CONNECTED"
# Expected: "CONNECTED" (exit 0)
```

### Interpret Error Responses

| Error | Meaning | Fix |
|-------|---------|-----|
| `model may not exist or you may not have access` | Claude Code rejected the slug before sending to API | Try a different slug; verify slug exists on OpenRouter |
| `API Error: 402 This request requires more credits` | Base URL + AUTH_TOKEN is correct, but model costs credits (or Claude Code requested too many tokens) | Switch to a free model (`*:free`) or add credits |
| `Claude X was retired on ...` | Model slug is deprecated | Query OpenRouter for current slug |
| `The model X is deprecated and will reach EOL` | Same — find current slug | Same |

## Headless / MCP Server Mode

Ruflo and other agent frameworks spawn `claude mcp serve` to use Claude Code's tools (Write/Read/Edit/Bash/Glob/Grep/Agent/etc.) over stdio MCP.

To run this headlessly on a free model, the `claude` binary must resolve with the correct env vars. Two approaches:

### Option A: Environment Wrapper (shim)

Create a shim on PATH that sets env vars before calling real Claude Code:

```bash
#!/usr/bin/env bash
KEY=$(grep -ioE "sk-or-[A-Za-z0-9_-]{20,}" "${APPDATA}/../Local/hermes/.env" 2>/dev/null | head -1)
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$KEY"
export ANTHROPIC_API_KEY=""
REAL="/path/to/real/claude"
exec "$REAL" --model tencent/hy3:free mcp serve "$@"
```

### Option B: Direct MCP Registration

Register in Hermes:
```bash
hermes mcp add claude-free --command bash --args /path/to/claude-free.sh
```

### Verify MCP Server

```bash
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
| timeout 25 bash /path/to/wrapper mcp serve 2>/dev/null
# Expected: initialize returns serverInfo.name="claude/tengu"
# tools/list returns 32+ tools (Write, Read, Edit, Bash, etc.)
```

## Other Providers

The same approach works with any Anthropic-compatible endpoint:
- **LiteLLM** — proxy that translates OpenAI/Anthropic requests to any provider
- **Ollama** — local models via `http://localhost:11434/v1` (OpenAI-compatible, needs additional translation layer for Anthropic format)
- **OpenAI** — set `ANTHROPIC_BASE_URL` to an OpenAI-compatible endpoint and use OpenAI model slugs (may need `--model gpt-*`)

## Limitations

- Claude Code's `-p` (single prompt) mode may prompt for file-write permission in interactive mode — use `mcp serve` for headless automated use
- Free models are slower and less capable than paid Anthropic models — use for development/testing, not production
- Some OpenRouter free models have rate limits or may be retired
- The `claude mcp serve` headless mode works for automated tool execution but does not stream back thinking/logs

## Reference Files

- `references/verification-patterns.md` — MSYS/Windows path handling, subagent result verification, MCP server testing patterns
