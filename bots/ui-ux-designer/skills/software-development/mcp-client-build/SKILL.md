---
name: mcp-client-build
description: Build a programmatic MCP client in Python (mcp SDK ClientSession + stdio_client / streamablehttp_client) that talks to a running MCP server and calls its tools — and the real gotchas (launching a stdio vs HTTP server, parsing JSON tool results, async context management). Use when a task says "add an MCP client", "connect to an MCP server", "remember/recall/search (or any) tools callable from Python", or "wrap our MCP server in a client class". Pair with mcp-server-build (authoring) and mcp-server-verification (proving connectivity).
---

# MCP Client Build (Python)

## When to use
- "add a SAMM/agent MCP client module", "connect to a running MCP server from Python"
- expose `remember/recall/search` (or any server tools) as a clean Python API
- write tests that drive a real MCP server WITHOUT mocking the tool calls

## The SDK import map (version-fragile — verify, don't guess)
The `mcp` SDK does NOT re-export everything from `mcp.client`. Submodules:
- `from mcp.client.session import ClientSession`
- `from mcp.client.stdio import stdio_client, StdioServerParameters`
- `from mcp.client.streamable_http import streamablehttp_client`  (for HTTP servers)

`from mcp.client import ClientSession, StdioServerParameters` FAILS (AttributeError) —
`ClientSession` lives in `mcp.client.session`, not `mcp.client`. Always import from the
submodule. Check actual paths with `python -c "import mcp.client as c; print([m for m in dir(c)])"`.

## Pattern: in-process stdio client (REAL, no mocks)
Best for tests + local use. The client spawns the MCP server as a subprocess and speaks
MCP over the child's stdin/stdout. This is a genuine client↔server round-trip.

```python
import os
import json
from contextlib import AsyncExitStack
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SammClient:
    def __init__(self, db_path="samm.db", python_exe=None):
        self.db_path = db_path
        self._python_exe = python_exe or sys.executable
        self._session = None
        self._stack = None

    async def connect(self):
        if self._session is not None:
            return self
        env = dict(os.environ)
        env["PYTHONPATH"] = _PKG_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        # Launch a REAL stdio MCP server, NOT a streamable-HTTP one.
        launch = ("import sys; "
                  "from samm.mcp_server import _build_server; "
                  "srv=_build_server(db_path=sys.argv[1]); "
                  "srv.run(transport='stdio')")
        params = StdioServerParameters(
            command=self._python_exe,
            args=["-c", launch, self.db_path],
            env=env,
        )
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def close(self):
        stack, self._stack = self._stack, None
        self._session = None
        if stack is not None:
            await stack.aclose()

    async def __aenter__(self): return await self.connect()
    async def __aexit__(self, *a): await self.close()

    async def _call(self, name, args):
        result = await self._session.call_tool(name, args)
        return _parse(result)

    async def remember(self, ns, agent_id, content, type="fact"):
        return await self._call("remember",
            {"namespace": ns, "agent_id": agent_id, "content": content, "type": type})

    async def recall(self, memory_id):
        return await self._call("recall", {"memory_id": memory_id})

    async def search(self, ns, query, limit=10):
        return await self._call("search",
            {"namespace": ns, "query": query, "limit": limit})

def _parse(result):
    """Extract + JSON-decode the text payload from a CallToolResult."""
    for block in getattr(result, "content", []):
        if getattr(block, "type", None) == "text":
            try: return json.loads(block.text)
            except (json.JSONDecodeError, TypeError): return {"raw": block.text}
    return {}
```

## CRITICAL pitfall: `cli mcp` often starts a STREAMABLE-HTTP server, not stdio
A common mistake: spawn `python -m yourpkg.cli mcp` to feed the stdio client. If the
CLI's `mcp` subcommand calls `FastMCP(...).run(transport="streamable-http")`, the child
binds a TCP port and BLOCKS — the stdio client never gets JSON-RPC on stdout, so
`call_tool` hangs/raises `McpError`. Symptom in subprocess stderr:
`ERROR bind on address ('127.0.0.1', 7701): only one usage of each socket address`.

FIX: launch the server with `transport='stdio'` explicitly (inline `-c` script, or a
dedicated stdio entrypoint), so it reads requests from stdin and writes responses to stdout.
Stdio transport needs NO port — drop the `--port` arg from the client launcher.

## Pitfalls + gotchas
- **Context stack ownership.** `stdio_client` + `ClientSession` MUST share one
  `AsyncExitStack` (or `async with`) so the subprocess + pipes close together. Closing
  the session while leaving the child alive leaks a process and can raise
  `RuntimeError: Attempted to exit cancel scope in a different task`.
- **Tool results are JSON strings.** FastMCP tool funcs that `return json.dumps(...)` put
  the JSON in a `text` content block. Decode `result.content[0].text` yourself (see `_parse`).
  If a tool returns a dict directly, the block text is already JSON — same parse works.
- **Async in sync tests.** Tests can drive the client with `asyncio.run(client.connect())`
  inside a plain `def test_*(...)` — no `pytest-asyncio` mode config needed. This mirrors
  the repo's existing `asyncio.run(...)` test style and avoids mode mismatches.
- **PYTHONPATH for the child.** Set `env["PYTHONPATH"]` to the package root so the spawned
  server can `import samm` regardless of the test's cwd. Pass a fresh `env` copy, not `os.environ`.
- **Use a temp DB per test** (e.g. `tempfile.mkstemp(suffix=".db")`, remove first) so runs are
  hermetic. Clean it up in fixture teardown.

## Verification (proof it works)
Run real round-trips, never trust `initialize` alone:
```
async with SammClient(db_path=tmp) as c:
    rec = await c.remember("ns", "a", "The sky is blue.")
    assert rec["content"] == "The sky is blue." and rec["id"]
    assert (await c.recall(rec["id"]))["id"] == rec["id"]
    hits = await c.search("ns", "sky")
    assert rec["id"] in [h["record"]["id"] for h in hits]
```
Confirm with the project's runner, e.g.
`env -u PYTHONPATH python -m pytest tests/ -q` → count passed, 0 failed.

## Variant: launch a THIRD-PARTY server via a wrapper shell script (e.g. Ruflo)
When the MCP server is not your own package (you can't inject `transport='stdio'`), drive
it through the wrapper script that starts it. The child is still a stdio MCP server; you
just point `StdioServerParameters` at `bash` + the wrapper path instead of `python -c`.

```python
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession

class RufloBridge:
    def __init__(self, wrapper="/path/to/ruflo-mcp-stdio.sh"):
        self._wrapper = wrapper

    async def search_similar(self, query, namespace="samm", limit=5):
        params = StdioServerParameters(command="bash", args=[self._wrapper])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "memory_search",
                    {"query": query, "namespace": namespace, "limit": limit},
                )
        payload = _parse(result)
        hits = payload.get("results", []) if isinstance(payload, dict) else []
        # SEE PITFALL BELOW: Ruflo returns stored object `value` as a JSON STRING.
        for hit in hits:
            val = hit.get("value")
            if isinstance(val, str):
                try: hit["value"] = json.loads(val)
                except (json.JSONDecodeError, TypeError): pass
        return hits
```

Key points that differ from the in-process pattern:
- `command="bash"`, `args=[wrapper]` — the wrapper must exec the real server so MCP JSON-RPC
  flows on stdout. (The SAMM `ruflo-mcp-stdio.sh` wraps `ruflo mcp start` and strips the
  leading `[INFO]`/date log lines that would desync a strict MCP handshake.)
- Do NOT set `PYTHONPATH`/`env` — the server manages its own node/ruflo runtime.
- Per-call `async with` is fine for low-volumebridging; for high throughput, hold one
  session on an `AsyncExitStack` like the in-process example.

### CRITICAL pitfall — Ruflo returns stored object `value` as a JSON STRING
Ruflo's `memory_store(key, value=<object>, namespace, upsert=True)` accepts a dict value
and reports success, but `memory_search` returns that value **double-encoded as a JSON
string**, not a dict:
```json
{"key":"abc","namespace":"ns","value":"{\"content\":\"...\"}","similarity":0.66}
```
If your test does `hit["value"]["content"]` it raises `TypeError: string indices must be
integers`. Normalize every returned `value` with `json.loads` (guarded, since Ruflo may
occasionally return a plain dict for trivial values). Confirmed against Ruflo's real
`memory_store`/`memory_search` tools — see `references/ruflo-bridge.md`.

### Unique-namespace hygiene for tests
Ruflo state is persistent/shared across runs, so generate a unique namespace per test to
avoid collisions with stale data from prior runs:
```python
import time, uuid
ns = f"test_{uuid.uuid4().hex}_{int(time.time()*1000)}"
```
This lets the same suite run repeatedly without `rec.id in keys` assertions picking up
ghost entries from earlier runs.

## Support files
- `templates/stdio-client-template.py` — copy-ready, drop-in `SammClient` (stdio transport, JSON result parsing). Replace the `samm` package refs with your server's import.
- `references/ruflo-bridge.md` — working Ruflo MCP-stdio bridge recipe + the JSON-string `value` transcript, for the third-party-wrapper variant above.
