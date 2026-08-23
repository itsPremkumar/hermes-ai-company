---
name: mcp-server-build
description: Build a working Model Context Protocol (MCP) server in Python with the official `mcp` SDK (FastMCP) — exposing callable tools to any MCP client, with SAMM/backend-backed logic that is unit-testable without a transport. Use when a task says "build an MCP server", "expose tools over MCP", "add remember/recall/search (or any) tools callable by an MCP client", or "wire our engine behind an MCP endpoint". Covers FastMCP tool registration, the testable-coroutine-tool pattern, streamable-HTTP vs stdio entrypoints, and the gotchas (async tools need asyncio.run in sync tests, endpoint path, DNS-rebinding on localhost).
---

# Build an MCP Server (Python, FastMCP)

Goal: a server any MCP client can call, with tools that delegate to your real
business logic (engine / DB / store) — and that are testable without spinning up
a transport.

## When to use
- "Build an MCP server exposing `remember`/`recall`/`search`"
- "Expose our engine as MCP tools"
- "Add a `run_mcp(db_path, port)` entrypoint the CLI imports"
- Phase-N of a memory/agent substrate that needs an MCP face

## Preferred stack: FastMCP
`from mcp.server.fastmcp import FastMCP`. It registers typed tools via a decorator
and handles JSON-RPC framing, schema generation, and transport selection for you.

## Pattern that survives testing: coroutine tool logic + thin server wrapper

Keep the SAMM/backend logic as **module-level async functions** (`mcp_remember`,
`mcp_recall`, `mcp_search`). The FastMCP `@server.tool` wrappers just call them and
`json.dumps` the result. This lets tests exercise the logic directly — no socket.

```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from .engine import SAMM
from .embedder import LocalEmbedder

_ENGINES: dict[tuple, SAMM] = {}

def _get_engine(db_path="samm.db") -> SAMM:
    key = (db_path,)
    eng = _ENGINES.get(key)
    if eng is None:
        eng = SAMM(db_path=db_path, embedder=LocalEmbedder(use_model=False))
        _ENGINES[key] = eng

def _rec(rec):  # model -> json-ready dict
    return rec.model_dump(mode="json") if isinstance(rec, BaseModel) else dict(rec)

# ---- pure, testable logic ----
async def mcp_remember(namespace, agent_id, content, type="fact", db_path="samm.db"):
    rec = _get_engine(db_path).remember(namespace, agent_id, content, type=type)
    return _rec(rec)

async def mcp_recall(memory_id, db_path="samm.db"):
    rec = _get_engine(db_path).recall(memory_id)
    if rec is None:
        return {"error": f"memory {memory_id} not found"}
    return _rec(rec)

async def mcp_search(namespace, query, limit=10, db_path="samm.db"):
    from .models import MemoryQuery
    rows = _get_engine(db_path).search(MemoryQuery(namespace=namespace, query=query, limit=limit))
    return [{"record": _rec(r), "score": round(float(s), 6)} for r, s in rows]

# ---- FastMCP server ----
def _build_server(db_path="samm.db"):
    srv = FastMCP(name="samm-mcp", instructions="...")
    @srv.tool(name="remember", description="Store a new memory.")
    async def remember(namespace: str = Field(...), agent_id: str = Field(...),
                       content: str = Field(...), type: str = Field("fact")) -> str:
        return json.dumps(await mcp_remember(namespace, agent_id, content, type, db_path))
    # ... recall, search similarly
    return srv

def run_mcp(db_path="samm.db", port=7701):
    srv = _build_server(db_path)
    srv.settings.host = "127.0.0.1"
    srv.settings.port = port
    srv.run(transport="streamable-http")
```

### Why this shape
- **Testable core**: `asyncio.run(mcp_remember(...))` verifies behavior with no
  server. Tests never depend on a transport being up.
- **One engine per db_path**: a module-level cache avoids re-opening SQLite per call
  and keeps tests + server sharing one connection.
- **Error as data**: `recall` of a missing id returns `{"error": ...}`, never an
  exception the client can't parse.

## Transport choice
- **streamable-http** (`transport="streamable-http"`): binds `127.0.0.1:port`,
  answers JSON-RPC POST at `/mcp`. Easiest to verify with a plain HTTP client
  (see `mcp-server-verify` references/streamable-http-probe.md). Good default for a
  service you run behind your own host.
- **stdio**: `srv.run(transport="stdio")` — what most desktop MCP clients (Claude
  Code, Cursor) launch as a subprocess. Use when the server is a CLI subcommand the
  client spawns.

## Tests
```python
import asyncio
def test_remember(db_path):
    rec = asyncio.run(mcp_remember("ns", "a", "hi", db_path=db_path))
    assert rec["content"] == "hi" and "id" in rec
# recall-missing:
assert "error" in asyncio.run(mcp_recall("nope", db_path=db_path))
# tool wiring:
import asyncio
server = _build_server(db_path=":memory:")
tools = asyncio.run(server.list_tools())
assert {"remember","recall","search"} <= {t.name for t in tools}
```
Always use `asyncio.run(...)` for the coroutine tool functions in **sync** pytest
tests — calling them bare emits `RuntimeWarning: coroutine never awaited` and the
test asserts against a coroutine object, not the result.

## Pitfalls
- **async tools in sync tests**: wrap every mcp_* call in `asyncio.run`. (Hard trap —
  the call "succeeds" but returns a coroutine and every assertion silently fails.)
- **localhost DNS-rebinding**: FastMCP enables DNS-rebinding protection on
  `127.0.0.1`/`localhost`, restricting `allowed_hosts` to `127.0.0.1:*`. Probe from
  `127.0.0.1`, not a mismatched host. To bind `0.0.0.0`, pass a
  `TransportSecuritySettings(enable_dns_rebinding_protection=False, ...)`.
- **endpoint path**: streamable-http serves at `/mcp` (not `/`), default.
- **schema types**: tool arg annotations become the JSON schema. Use
  `str = Field(...)` for required, `str = Field("fact")` for defaults. Unknown
  `type` strings: coerce to a default enum member rather than raising (so the tool
  never 500s on a bad client arg).
- **PYTHONPATH shadowing crashes pytest**: see `mcp-server-verify`
  references/streamable-http-probe.md — run the suite with `env -u PYTHONPATH`.

## Verify before declaring done
1. `asyncio.run(server.list_tools())` lists every required tool name.
2. Each `mcp_*` function returns correct data / error shape (sync pytest + asyncio.run).
3. Live probe: start `run_mcp`, POST `initialize` to `http://127.0.0.1:<port>/mcp`,
   assert `200` + `serverInfo` (no MCP client required).
