---
name: claude-code-openrouter
description: >-
  Connect Claude Code CLI to OpenRouter free models (tencent/hy3:free, $0) —
  the correct cookbook env vars, pitfalls, wrapper/shim patterns, and MCP
  verification steps. No Anthropic key, no credit balance needed.
---

# Claude Code + OpenRouter (Free Models)

Connect Claude Code CLI (`claude` binary) to OpenRouter's free models at
**zero cost**. The official OpenRouter cookbook works, but **three env-var
pitfalls** cause most failures — documented below.

## The Three Pitfalls (root cause of 90% of failures)

| # | Wrong | Right | Why |
|---|-------|-------|-----|
| 1 | `ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1` | `https://openrouter.ai/api` | The `/v1` path breaks OpenRouter's routing for Claude Code |
| 2 | `ANTHROPIC_API_KEY=<key>` | `ANTHROPIC_AUTH_TOKEN=<key>` | Claude Code reads `ANTHROPIC_AUTH_TOKEN`, NOT `ANTHROPIC_API_KEY` |
| 3 | `ANTHROPIC_API_KEY` unset or missing | **Explicitly empty**: `ANTHROPIC_API_KEY=""` | A non-empty value conflicts with `AUTH_TOKEN` and causes model-not-found errors |

## Quick Start (one-shot test)

```bash
OPENROUTER_KEY="sk-or-..."
ANTHROPIC_BASE_URL="https://openrouter.ai/api" \
  ANTHROPIC_AUTH_TOKEN="$OPENROUTER_KEY" \
  ANTHROPIC_API_KEY="" \
  claude --model tencent/hy3:free -p "reply with: FREE"
```

Expected output: `FREE`

## Verified working models (all $0 on OpenRouter)

- `tencent/hy3:free` — primary target, proven working
- Other OpenRouter free models may work if Claude Code's allowlist accepts their slug

## Wrapper Pattern (for Ruflo / persistent use)

Create a shim that sets the correct env before calling the real `claude` binary.
This lets tools like Ruflo (which spawn `claude mcp serve`) pick up the free
model automatically.

```bash
#!/usr/bin/env bash
# claude-free.sh — routes `claude mcp serve` through OpenRouter free model
set -u
KEY=$(grep -ioE "sk-or-[A-Za-z0-9_-]{20,}" "${APPDATA}/../Local/hermes/.env" | head -1)
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$KEY"
export ANTHROPIC_API_KEY=""
REAL="/path/to/real/claude/binary"
exec "$REAL" --model tencent/hy3:free mcp serve "$@"
```

To intercept Ruflo's spawn: put a `claude` shim on PATH _before_ the real binary.
The shim calls claude-free.sh above. Ruflo's `initBackends()` spawns
`claude mcp serve` — with the shim it gets the free model.

## MCP Server Verification

Verify `claude mcp serve` works on the free model:

```bash
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
| CLAUDE_MODEL=tencent/hy3:free ANTHROPIC_BASE_URL=... ANTHROPIC_AUTH_TOKEN=... ANTHROPIC_API_KEY="" \
  claude --model tencent/hy3:free mcp serve
```

Expected: `serverInfo: {"name":"claude/tengu","version":"2.1.183"}` with
~32 tools including `Write`, `Read`, `Edit`, `Bash`, `Glob`, `Grep`,
`Agent`, `WebFetch`.

## Key Facts

- Claude Code v2.1.183 works with this config (tested on Windows/MSYS)
- `tencent/hy3:free` is **free** (pricing = 0/0 on OpenRouter)
- The MCP surface is identical to the paid Anthropic version (32 tools)
- `claude mcp serve` fully functional — enables Ruflo's `claude-code` group
- Claude Code's model allowlist **does** accept `tencent/hy3:free` with
  the correct env (the earlier "model not found" error was from wrong env,
  model slug is fine)

## Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| "model not found / may not exist" | `ANTHROPIC_BASE_URL` has `/v1` suffix, or `ANTHROPIC_API_KEY` set instead of `AUTH_TOKEN` | Use correct env (see chart above) |
| "402 — need more credits" | Using a paid model (e.g. claude-haiku-4.5) on free-tier OpenRouter | Switch to `tencent/hy3:free` |
| Infinite loop (shim calls itself) | Wrapper calls `claude` but shim replaces it on PATH | Use absolute path to real claude binary in the wrapper |
| Empty output / hang | Startup timing; the server processes on stdin close | Pipe JSON-RPC over stdin; `timeout` after 20-25s |
