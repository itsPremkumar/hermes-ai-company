# Ruflo reality — VERIFIED evidence (updated 2026-07-19)

This file captures what Ruflo actually does in this $0 stack, with reproduction-grade
detail. It replaces the earlier "MCP server is flaky / unusable" note — the MCP connection
to Hermes NOW WORKS via a stdio wrapper. Keep it honest: Ruflo still cannot *execute* agents
for free, but its MCP tool surface (memory, swarm, agents) is now callable from Hermes.

## 1. Ruflo CANNOT self-execute agent work on a free model (unchanged)
- `ruflo swarm coordinate`, `ruflo agent spawn`, `ruflo hive-mind init/spawn` create topology
  and QUEUE tasks but do NOT run agent code.
- `hive-mind status` → "No workers in hive"; queued tasks stay "pending dispatch".
- Only documented execution path is `hive-mind spawn --claude` = **Claude Code** (paid
  Anthropic, EXCLUDED by mandate).
- **Claude Code + OpenRouter-free proxy FAILED** (do not retry): Claude Code validates the
  model slug against Anthropic's list and rejects `tencent/hy3:free`; Anthropic-named models
  via the OpenRouter proxy return retired/access errors and aren't free anyway.
- Real executor in this stack = **`delegate_task` subagents on `tencent/hy3:free`** (Hermes =
  Queen/orchestrator/verifier). That IS the "multiple agents" team — just not Ruflo-powered.

## 2. Ruflo MCP server ↔ Hermes — WORKING (the fix)
Ruflo's stdio MCP server is a real, full MCP server (returns `initialize` + `tools/list` with
327 tools: `memory_store`, `memory_search`, `swarm_init`, `agent_spawn`, `metaharness_*`,
`federation_bbs_*`, `business_pod_*`, `agenticow_*`, etc.). The problem was the *handshake*
with Hermes's Python MCP client, not the server.

### Root cause
Ruflo prints a startup log line to **stdout** before the JSON-RPC stream:
```
[2026-07-19T02:26:50.029Z] INFO [claude-flow-mcp] (mcp-...) Starting in stdio mode
```
Hermes's `mcp` SDK client reads stdout line-by-line; the stray non-JSON line desyncs the
stream → `✗ Failed to connect: Connection closed`.

### Failed attempts (don't retry)
- `npx ruflo@latest mcp start` (the gist's command) — `npx -y ruflo@latest` **hangs on
  download** (npm/network). Use the LOCALLY INSTALLED `ruflo` binary (v3.32.7).
- `ruflo mcp start -t http -p <port>` — prints "Running, 27 tools enabled, PID ..." but the
  HTTP listener **never binds** on this Windows/MSYS host. `/health` and `/rpc` return empty.
  (Ruflo's launcher runs unix-isms like `ps -o` that fail under MSYS — symptom of broken
  Windows support.) Use **stdio**, not HTTP.
- `ruflo mcp start | grep -vE '...INFO...'` (no `--line-buffered`) — the pipe is
  **block-buffered**, so ruflo's JSON response sits in grep's buffer and Hermes times out:
  `MCP call timed out after 40.2s`.

### Working recipe (verified end-to-end)
**Wrapper** `bin/ruflo-mcp-stdio.sh`:
```bash
#!/usr/bin/env bash
# Strip ruflo's stdout [INFO] log line so Hermes's MCP client completes the handshake.
# --line-buffered is REQUIRED (plain grep buffers -> 40s timeout).
set -o pipefail
ruflo mcp start "$@" 2>/dev/null | grep --line-buffered -vE '^\[[0-9]{4}-[0-9]{2}-[0-9]{2}T|INFO|Starting in stdio' || true
```
**Register + enable in Hermes:**
```bash
hermes mcp remove ruflo            # if a broken entry exists
hermes mcp add ruflo --command bash --args "bin/ruflo-mcp-stdio.sh" --connect-timeout 60
# (prompts "Save config anyway? [y/N]" on first connect failure — answer y; config persists)
hermes mcp test ruflo              # -> ✓ Connected (890ms), ✓ Tools discovered: 327
hermes tools enable "ruflo:*"      # -> ✓ Enabled
```
Config is saved in `~/.hermes/config.yaml` (persists across sessions).

**End-to-end proof (real tool call, not just discovery):**
```python
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
async def main():
    p = StdioServerParameters(command='bash', args=['bin/ruflo-mcp-stdio.sh'])
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            a = await s.call_tool('memory_store', {'key':'x','value':'works','namespace':'default'})
            b = await s.call_tool('memory_search', {'query':'works','namespace':'default'})
            print('store:', a.content[0].text[:60], '| search hit:', 'x' in b.content[0].text)
asyncio.run(main())
# -> store: {"success": true, ...} | search hit: True
```

### What you can now do through the MCP connection
- `memory_store` / `memory_search` / `memory_list` — persistent shared KV+vector store
- `swarm_init` / `swarm_status` / `swarm_health` — coordination topology
- 327 Ruflo tools total in Hermes's toolset, callable from this agent
- `agent_spawn` / `agent_list` — NOTE: `agent_execute` needs `ANTHROPIC_API_KEY` (Claude Code);
  excluded, so agents don't actually RUN. Ruflo = coordinator/memory/MCP provider only.

### Ruflo memory API contract (learned building SAMM↔Ruflo bridge, 2026-07-19)
When wrapping Ruflo memory in your own client class, these shapes are verified:
- **`memory_store` args:** `{"key": str, "value": <any JSON>, "namespace": str, "upsert": bool}`
  → returns `{"success": true, "key": ..., "namespace": ..., ...}`.
- **`memory_search` args:** `{"query": str, "namespace": str, "limit": int}`
  → returns `{"results": [{"key":..., "value": <dict OR truncated JSON-string>, "similarity": float}], "total": int, "searchTime": str, "backend": "HNSW + sql.js"}`.
- **TRAP — `value` in `memory_search` is server-side TRUNCATED to a preview string**
  (e.g. `'{"content":"The deployment pipeline must run migrations befo...'`). So:
  - `json.loads(value)` raises `JSONDecodeError` (unterminated) → catch it.
  - Normalize with a `_coerce_dict(s)`: try `json.loads`, then `ast.literal_eval`
    (handles single-quote Python-repr strings), else return the raw `str`.
  - Tests must NOT assert exact-`value["content"]` equality on search results — assert by
    **key presence** + that the value (dict or string prefix) contains the original content.
- **`swarm_init` args:** `{"topology": "hierarchical", "maxAgents": int, "strategy": "specialized"}`
  → returns `{"success": true, "swarmId": "swarm-<ts>-<id>", ...}`. Real, usable.
- Keep the client KISS: `mcp.client.stdio` `stdio_client` + `ClientSession`, one
  `initialize()` per call (Ruflo's stdio server is spawned per subprocess; no long-lived session needed).

## 3. OpenRouter free-slug corrections (unchanged, still valid)
- `meta-llama/llama-3.2-1b-instruct:free` is WRONG (404). Use `meta-llama/llama-3.2-1b-instruct`.
- The HY3 free model the user wants is **`tencent/hy3:free`** (pricing 0/0, returns `OK`).
- Verify any slug with a direct `curl POST https://openrouter.ai/api/v1/chat/completions`
  before trusting Ruflo's config.
- Key pitfall: a masked/empty `OPENROUTER_API_KEY` in `.env` is NOT a usable key. Check
  `echo ${#KEY}` > 20 chars and run a real curl completion before claiming "configured".
