# Ruflo exec unlock — VERIFIED recon (2026-07-19)

## What the source ACTUALLY says (read src/mcp-bridge/index.js)
- Ruflo 3.32.7 executes agents by **spawning the `claude` BINARY**, not by calling the Anthropic API directly:
  - line 96-99: `claude-code` group, `source: "claude"`
  - line 258: `command: "claude", args: ["mcp","serve"]`
  - line 136: `this.process = spawn(this.command, this.args, { stdio, env: {...process.env} })`
- It is a **binary shell-out**, NOT an Anthropic Messages API call.
- `claude-code` group is env-gated: `MCP_GROUP_CLAUDE_CODE === "true"`.

## CORRECTION to the old "LiteLLM proxy" theory
The previous free-dev-team text claimed Ruflo calls the Anthropic API *shape* and a
LiteLLM proxy unlocks free execution. **That is FALSE for v3.32.7.** Because it
shells the `claude` binary, the real unlock is an **OSS `claude`-compatible
binary on PATH** (user's instinct was right; LiteLLM-API theory was wrong).
ALWAYS read the exec source before claiming which proxy unlocks it.

## The free unlock attempt (OpenCode) — PARTIAL, documented honestly
1. shim `bin/claude-free.sh`: maps `claude mcp serve` -> `opencode serve`.
   Verified: `claude mcp serve` -> `opencode serve` (intercepted exec'd args).
2. PATH shim `bin/shim/claude` so Ruflo's `spawn("claude")` hits opencode.
3. Fixed OpenCode's broken install: `npm install` in `~/.cache/opencode`
   restored missing `@gitlab/opencode-gitlab-auth`.
4. **OpenCode CHAT works** on FREE model `opencode/hy3-free` (launched TUI, took prompts).
5. **BLOCKER (unresolved):** `opencode serve` (the MCP-server mode Ruflo needs)
   is a **STUB** in v1.1.35 — prints help, exits code 1, never binds a port.
   So Ruflo's claude-code group has no MCP server to connect to.

## Honest status
- Ruflo = coordinator + memory + MCP tool provider: WORKING (proven via stdio wrapper, 327 tools, memory round-trip).
- Ruflo autonomous exec via free model: BLOCKED (now by "OpenCode serve is a stub", NOT by "paid key").
- OpenCode as a SEPARATE free coding agent (chat): WORKING.

## To actually finish the unlock (not yet done)
- A) Find another OSS `claude`-compatible MCP server that actually serves.
- B) Use OpenCode as a Hermes `delegate_task` alternative (free coding agent) — separate win, does NOT unlock Ruflo exec.
- C) Wait/patch OpenCode `serve` upstream.

## Do NOT claim
- "Ruflo fully unlocked / executing on free models" — false until a working `claude` MCP server exists.
- "OpenCode is the Ruflo unlock" — only its chat works; its `serve` (MCP) is a stub.

## Repro recipe (re-verify any time)
```
# 1. confirm binary shell-out
grep -nE 'command: "claude"|spawn\(' /c/nvm4w/nodejs/node_modules/ruflo/src/mcp-bridge/index.js
# 2. fix + test opencode chat
cd ~/.cache/opencode && npm install
echo "write a python hello" | timeout 30 opencode -m opencode/hy3-free
# 3. test the serve stub (expect exit 1)
timeout 20 opencode serve --model opencode/hy3-free --port 8732 --print-logs
echo "exit was: $?"
```
