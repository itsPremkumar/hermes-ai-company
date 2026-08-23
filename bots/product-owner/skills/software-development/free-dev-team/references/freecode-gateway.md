# freecode — zero-cost OSS MCP coding gateway (the working unlock)

When Ruflo's `claude-code` exec group is BLOCKED (binary shell-out to paid
Claude Code; OpenCode `serve` is a stub; group is DORMANT in v3.32.7), the
different-perspective fix is: **don't inject into Ruflo — build a standalone
free MCP coding server and register it directly in Hermes.**

## Why this works
- Ruflo spawns `claude mcp serve` and expects Claude-Code-style tools
  (Write/Read/Edit/Bash/Glob/Grep). Those tools are just file/bash primitives.
- A tiny stdio MCP server can implement the SAME tool surface backed by LOCAL
  execution + an optional free local model (Ollama). No Anthropic key, no
  network, $0.
- Register it as its own Hermes MCP server: `hermes mcp add freecode
  --command bash --args bin/freecode-stdio.sh`. The agent calls free coding
  tools directly — parallel to Ruflo (coordination/memory) and HY3-free
  delegate_task subagents.

## freecode-mcp.py (core shape)
- `from mcp.server import Server`; `from mcp.server.stdio import stdio_server`.
- Register tools with `@APP.list_tools()` / `@APP.call_tool()`.
- `async def main(): async with stdio_server() as (r, w): await APP.run(r, w, APP.create_initialization_options())`.
- Tools: `Write{path,content}`, `Read{path}`, `Edit{path,old_string,new_string}`,
  `Bash{command,cwd?}`, `Glob{pattern,path?}`, `Grep{pattern,path,glob?}`.
  Use stdlib only (os, subprocess, glob, re) — no deps.
- Optional: route a "Think"/"AskUser" step to Ollama if `OLLAMA_MODEL` set.

## CRITICAL mcp SDK gotchas (cost real debug cycles)
- `Server` has NO `run_stdio_async()` method in this SDK version — use
  `async with stdio_server() as (r, w): await APP.run(r, w, opts)`.
- `stdio_server()` takes NO server arg (passing `APP` as stdin ->
  `'async for' requires __aiter__, got Server`).
- Import `asyncio` at top — don't rely on `__import__` in `__main__`.

## Verification recipe (the ONLY reliable method for a long-running stdio server)
- The server keeps stdin open until EOF; drive it with a real pipe:
  ```bash
  printf '%s\n%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize",...}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"Write","arguments":{"path":"C:/tmp/x.txt","content":"hi"}}}' \
    | timeout 10 env -u PYTHONPATH "$PY" bin/freecode-mcp.py >/dev/null 2>&1
  # then verify the file with PYTHON (os.path.exists), NOT bash [ -f ]
  ```
- DO NOT verify via `subprocess.Popen([...,], stdin=PIPE, stdout=PIPE)` then
  `terminate()`: the pipe-buffer deadlocks (server blocks writing its response
  because parent never reads) and `proc.terminate()` kills it mid-write.
  `stdout=DEVNULL` + `Popen` still raced in practice. Likewise `subprocess.run(
  [...,], input="...")` closes stdin immediately after writing — the server may
  not have read the 2nd JSON line before EOF, so the `tools/call` is never
  processed (file not written, no error). The terminal-pipe method
  above is the authoritative proof.
- Path gotcha: Python on MSYS resolves `C:/tmp/x.txt` -> `C:\tmp\x.txt`, but
  bash `[ -f "C:/tmp/x.txt" ]` FAILS (wrong path format for the shell). Always
  assert file existence via `python -c "import os; print(os.path.exists(p))"`
  with a forward-slash path, never bash `[ -f ]`.

## Ruflo claude-code group is DORMANT (sharper than "stub")
- Set `MCP_GROUP_CLAUDE_CODE=true`, prepend `bin/shim/claude` (-> freecode) to
  PATH, start `ruflo mcp start`. The group shows as enabled but:
  - `tools/list` does NOT advertise the claude tools (0 found).
  - A blind call `claude__Write` -> "Tool not found"; shim log shows 0 spawns.
- Conclusion: Ruflo v3.32.7 will not spawn `claude` via this group config.
  Don't burn time forcing it — use the standalone `freecode` server instead.

## Status
- freecode registered in Hermes as `freecode` MCP server: CONNECTED, 6 tools.
- Proven real effect: `Write` tool wrote a file to `C:\tmp` (verified via
  Python `open()`). Not a claim.
- Ruflo exec still blocked; agent now has a free local coding backend directly.
