# Verification Patterns for Free-Model Routing

## Subagent Result Reliability

Subagent "completed" banners are unreliable. Always verify on disk
independently before committing. Specific failure modes observed:

1. **Delegation owner exit** — subagent results lost, repo state unchanged,
   "completed" banner still fires. Detected by checking `git diff HEAD`
   and `git log --oneline -1` — if the intended changes aren't committed
   or in the working tree, the banner lied.

2. **Hallucinated content** — subagent may pad its summary with irrelevant
   or false information (e.g., a cookbook quote that doesn't apply to
   the user's config). Cross-check against actual test output.

**Action:** After each delegation batch:
- `git status --short` to see what actually changed
- Run the full test suite yourself (don't trust the subagent's reported count)
- Spot-check key features (new methods, new CLI subcommands, new endpoints)

## Path Format Mismatch (MSYS/Windows)

When verifying file operations in ad-hoc scripts, MSYS bash paths and
Python paths resolve differently:

| Environment | `/tmp/foo.txt` resolves to | `C:/tmp/foo.txt` resolves to |
|-------------|---------------------------|------------------------------|
| MSYS bash   | MSYS temp dir             | `C:\tmp\foo.txt`             |
| Python (Windows native) | `C:\tmp\foo.txt` (if C:\tmp exists) | `C:\tmp\foo.txt` |

**Rule:** Use Python's own `os.path.exists()` for verification, not
bash `[ -f ]`. Or use a single path format that both agree on:
e.g., `C:/tmp/...` in Python's `open()` call works because Python
accepts forward slashes on Windows.

## MCP Server Verification (stdio)

The proven method for verifying a stdio MCP server responds correctly:

```bash
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
| timeout 25 bash /path/to/wrapper mcp serve 2>/dev/null > /tmp/out.txt
# Then parse /tmp/out.txt with Python, check serverInfo.name and tools
```

Do NOT use `subprocess.Popen(stdout=PIPE)` for long-running servers —
the pipe buffer deadlocks. Use `> file` redirect + read file after
timeout kills the process.

## "Connection closed" Errors

When an MCP client reports "Connection closed" but the server works
standalone (tested via raw JSON-RPC pipe), check:

1. Is the server binary a Win32 app? Node.js scripts need to be wrapped
   in `bash -c` or a `.sh` launcher, not spawned directly.
2. Is stdout piped through a filter? `grep --line-buffered` is required
   for real-time output; block-buffered grep causes the client to time out.
3. Does the server require stdin to stay open? Stdio MCP servers read
   one request per line and respond; closing stdin kills the server before
   the response is written. Use a persistent connection (Hermes MCP add)
   or a background process with kept-open stdin.
