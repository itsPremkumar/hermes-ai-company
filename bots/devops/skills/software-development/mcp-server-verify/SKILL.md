---
name: mcp-server-verify
description: Verify an MCP (Model Context Protocol) server actually works over stdio — not just by reading code. Use when a user asks "does the MCP work", "check the MCP connection", or "audit the MCP server for errors". Covers the JSON-RPC handshake, tools/list, live tools/call, and the common safe-mode trap that makes write tools fail.
---

# MCP Server Verification (stdio)

Verifying an MCP server means **proving it speaks the protocol and executes tools** — not just
that the file parses. The reliable method is to launch it over stdio, send JSON-RPC frames, and
inspect the responses.

## When to use
- "check if the MCP connection works"
- "audit this MCP for errors / improvements"
- "does the MCP server run?"
- Debugging a client that "connects but does nothing"

## Steps
1. **Find the launch command.** Look at `package.json` scripts (e.g. `"mcp": "tsx src/mcp-server.ts"`)
   or the server file. Run via the project's TS runner: `npx tsx src/mcp-server.ts` (NOT
   `node node_modules/.bin/tsx` — that shim is not directly node-runnable).
2. **Send the protocol frames** in order, piped to stdin:
   - `initialize` (id 1) with `protocolVersion:"2024-11-05"`
   - `notifications/initialized` (no id)
   - `tools/list` (id 9), `resources/list` (id 10), `prompts/list` (id 11)
   - one or more `tools/call` (id 20+) with real args
3. **Parse responses** with python (one JSON object per line). Check:
   - `initialize` returns `result` with `serverInfo` + `capabilities`
   - `tools/list` returns `result.tools` (count + names)
   - `tools/call` returns `result.content` (read tools) or `isError:true` (write tools blocked)
4. **Test a write tool both ways**: run once without the flag (expect block) and once with
   `ALLOW_UNSAFE_MCP_TOOLS=1` (expect success). See pitfall below.
5. **Clean up**: if a write test mutated a tracked file, `git checkout -- <file>` to restore.

A re-runnable probe is in `scripts/probe_mcp.sh`.

## WINDOWS / MSYS SPECIFICS (Hermes on Windows — git-bash)

The stdio-pipe + python approach above silently fails in this environment. Two traps:

1. **`spawn('npx')` / `spawn('cmd')` ENOENT inside a Node child.** A Node `child_process.spawn('npx', [...])`
   raises `Error: spawn npx ENOENT` because the MSYS PATH translation isn't inherited by the
   grandchild. Fix: wrap with `cmd.exe` →
   `spawn('cmd.exe', ['/c', 'npx -y <pkg> ...'], { windowsHide: true })`.
2. **Heredocs collapse newlines.** Writing a probe via `cat > file <<'EOF'` and running it can
   flatten newlines (the shell re-emits the whole script on one line → `SyntaxError: Missing
   catch`). Prefer a Node probe that buffers stdout and splits on `\n` per frame.

### Reusable Node stdio probe (Windows-safe)
```js
const { spawn } = require('child_process');
// wrap npx in cmd.exe so MSYS PATH resolves it
const proc = spawn('cmd.exe', ['/c', 'npx -y <pkg> <subcommand> <arg>'], {
  cwd: 'C:/abs/path/to/project', stdio: ['pipe','pipe','pipe'], windowsHide: true,
});
let buf = '';
const send = (o) => proc.stdin.write(JSON.stringify(o) + '\n');
proc.stdout.on('data', (d) => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
    if (!line) continue;
    try {
      const m = JSON.parse(line);
      if (m.id === 1 && m.result) {                 // initialize done
        send({ jsonrpc:'2.0', id:2, method:'tools/list', params:{} });
        // or: send({ jsonrpc:'2.0', id:2, method:'tools/call', params:{ name:'worker_list', arguments:{} } });
      }
      if (m.id === 2 && m.result) {
        const tools = m.result.tools;
        console.log('TOOLS:', tools ? tools.length : JSON.stringify(m.result).slice(0,300));
      }
      if (m.error) console.log('ERROR:', JSON.stringify(m.error).slice(0,300));
    } catch (e) {}
  }
});
proc.stderr.on('data', (d) => { const s=d.toString(); if(/token|Config loaded|refreshed/i.test(s)) console.log('[auth]', s.trim()); });
send({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{name:'probe',version:'1.0'} } });
setTimeout(() => { console.log('DONE'); proc.kill(); process.exit(0); }, 15000);
```
Also: when *writing* a probe file with the `write_file` tool on this host, the path can get
doubled (`C:\c\one\...` instead of `C:\one\...`). Always `cat > /abs/path/file.cjs <<'EOF'`
via terminal, or verify the real path with `ls -la` after writing.

### Project-scoped .mcp.json (not global)
To register an MCP for one repo, write `.mcp.json` in the project root:
```json
{ "mcpServers": { "cloudflare": { "command": "npx", "args": ["-y", "@cloudflare/mcp-server-cloudflare@latest", "run", "<ACCOUNT_ID>"] } } }
```
The client (Claude Code / Cursor / etc.) picks it up automatically. `.mcp.json` is usually NOT
gitignored — it's safe to commit when it only carries a public account id, not a secret token.
See `references/cloudflare-mcp.md` for the Cloudflare-specific server and its auth model.

## PITFALL — Hermes client desyncs on a stdout [INFO] line (stdio)
When you wire a third-party MCP server into **Hermes** (`hermes mcp add <name> --command <bin> --args ...`
then `hermes mcp test`), the test can report **"Connection closed"** or hang ~40s even though the
server works fine from a raw `stdio_client` probe. Root cause: the server prints a startup log line
(e.g. `[INFO] Starting in stdio mode`, or a timestamped JSON-ish line) to **STDOUT** *before* the
JSON-RPC stream. Hermes's Python MCP client reads stdout line-by-line and desyncs on the
non-JSON line → closes. A naive `grep -v` pipe "fix" makes it worse: block-buffered grep holds
the JSON response until the pipe closes → 40s timeout.

**Fix — wrap the server in a script that strips the noise line with `--line-buffered`:**
```bash
#!/usr/bin/env bash
# bin/<name>-mcp-stdio.sh — let Hermes' client complete the handshake
set -o pipefail
<bin> mcp start "$@" 2>/dev/null | grep --line-buffered -vE '^\[[0-9]{4}-[0-9]{2}-[0-9]{2}T|INFO|Starting in stdio' || true
```
Then register the **wrapper**, not the raw binary:
```bash
hermes mcp add <name> --command bash --args "bin/<name>-mcp-stdio.sh"
hermes mcp test <name>      # -> ✓ Connected (NNNms), ✓ Tools discovered: NNN
hermes tools enable "<name>:*"
```
Verify independently (don't trust the "completed" banner): `hermes mcp test` must print
`✓ Connected` + a tool count, and a live `stdio_client` call to `tools/list` / a write tool must round-trip.
This trap is **Hermes-client-specific** — raw `mcp` SDK probes and Claude-Code-style hosts may tolerate the
stray line; Hermes's client does not. (Real case: ruflo `mcp start` stdout `[INFO]` line →
`bin/ruflo-mcp-stdio.sh` wrapper fixed it; `npx ruflo@latest` also hangs on download here, so use the
locally-installed binary, not the gist's `npx` form.)

## PITFALL — safe mode blocks all writes by default
Many MCP servers (including `itsPremkumar/Automated-Video-Generator`) declare the `mcp` runtime with
`safeMode: true`. Every **write/mutation** tool (`write_input_script`, `delete_*`, `upload_asset`,
`update_env_config`, `run_pipeline_command`, `delete_output`) throws `ForbiddenError: safe mode`
unless `ALLOW_UNSAFE_MCP_TOOLS=1` is set. **Read tools work fine.** A user will see "MCP connected
but every action fails" and think it's broken. Fix = document the flag (see `references/safe-mode.md`).
Always check the server's capability/safe-mode config before declaring write tools "broken".

## PITFALL — prettier vs eslint
CI "Lint & Format" jobs often run BOTH `npm run lint` (eslint, warnings-only = exit 0) AND
`npm run format:check` (prettier). A green eslint does NOT mean CI is green. If Lint&Format fails,
run `npm run format` (prettier --write) — it reformats many files but is whitespace-only safe.

## PITFALL — cannot read CI logs without a token
GitHub Actions log downloads require auth (`https://api.github.com/repos/.../actions/runs/<id>/logs`
returns JSON error for public repos unauthenticated). To diagnose a CI test failure you can't see:
reproduce locally with the exact CI command, and/or ask the user to paste the error or provide a
PAT with `actions:read`.

## Verification checklist
- [ ] initialize returns serverInfo
- [ ] tools/list count matches expectation (e.g. 23)
- [ ] resources/list + prompts/list return expected counts
- [ ] a read tool call returns real data
- [ ] a write tool call: blocked by default, works with ALLOW_UNSAFE_MCP_TOOLS=1
- [ ] working tree clean after test (no stray mutations)

## STREAMABLE HTTP transport (FastMCP / Python servers)

Many Python MCP servers (built on `mcp.server.fastmcp.FastMCP`) serve over **streamable
HTTP** instead of stdio — `server.run(transport="streamable-http")` binds `127.0.0.1:port`
and answers JSON-RPC POSTs at `http://127.0.0.1:<port>/mcp`. This is often simpler to verify
than stdio because you can hit it with a plain HTTP client — no pipe framing.

### Steps
1. Start the server (background), e.g. `python -m pkg.cli mcp --port 7799 --db /tmp/x.db`.
   Confirm it does NOT exit (it's a long-lived server). If it exits immediately, read its
   stderr — a crash at import is the usual cause.
2. POST an `initialize` frame and read the SSE-wrapped response:
```
import urllib.request, json
req = urllib.request.Request(
    "http://127.0.0.1:7799/mcp",
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
        "params":{"protocolVersion":"2024-11-05","capabilities":{},
                  "clientInfo":{"name":"probe","version":"0"}}).encode(),
    headers={"Content-Type":"application/json",
             "Accept":"application/json, text/event-stream"})
r = urllib.request.urlopen(req, timeout=5)
body = r.read().decode()
# body is "event: message\r\n\r\ndata: {<jsonrpc result>}\r\n"
assert r.status == 200
assert '"serverInfo"' in body        # or parse the `data:` line as JSON
```
   The `/mcp` endpoint returns `text/event-stream`: each event is `event: message` then
   `data: <json>` on the next line. Parse the `data:` line to get the JSON-RPC result.
3. To list tools, send `notifications/initialized` then a `tools/list` POST (same endpoint).
   FastMCP exposes `server.list_tools()` too — call it directly in-process for an even faster
   unit-level check (see `references/streamable-http-probe.md`).

### Pitfall — DNS-rebinding protection on localhost
FastMCP auto-enables DNS-rebinding protection when `host in ("127.0.0.1","localhost","::1")`,
restricting `allowed_hosts` to `127.0.0.1:*`. Probe from `127.0.0.1` (NOT `0.0.0.0`/`localhost`
mismatch). If you must bind `0.0.0.0`, pass a `TransportSecuritySettings` with
`enable_dns_rebinding_protection=False` or matching `allowed_hosts`.

### Pitfall — pytest collection crash from a shadowing PYTHONPATH
When running the server's own test-suite under a Python interpreter, a **foreign `PYTHONPATH`**
(e.g. the agent host's own venv) can shadow the project's packages and crash pytest at
*collection* time with `ModuleNotFoundError: pydantic_core._pydantic_core` (triggered by an
auto-loaded `langsmith` pytest11 plugin from the wrong venv). Symptom: `-p no:langsmith`
does NOT help — the entrypoint plugin loads before `-p` flags are applied. Fix: run with a
clean PYTHONPATH — `env -u PYTHONPATH python -m pytest tests/ -q`. General rule: if pytest
dies at config/collection with an import error from a venv you don't recognize, check
`sys.path` for foreign site-packages and unset the offending `PYTHONPATH` first.

See `references/streamable-http-probe.md` for a copy-ready probe + the PYTHONPATH-unset recipe.
