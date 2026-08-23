# Streamable-HTTP MCP probe + PYTHONPATH-unset recipe

## 1. Probe a FastMCP server over HTTP (no MCP client needed)

Start the server (background, long-lived — it must NOT exit):
```bash
cd /path/to/project
env -u PYTHONPATH python -m pkg.cli mcp --port 7799 --db /tmp/probe.db
# confirm it stays up; if it exits, read stderr for an import-time crash
```

Then probe `initialize` with a plain HTTP client:
```python
import urllib.request, json

def mcp_post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode()

# 1) initialize
status, body = mcp_post("http://127.0.0.1:7799/mcp", {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "probe", "version": "0"}},
})
assert status == 200
assert '"serverInfo"' in body          # SSE-wrapped: "event: message\r\ndata: {...}\r\n"

# 2) initialized notification (no id)
mcp_post("http://127.0.0.1:7799/mcp", {
    "jsonrpc": "2.0", "method": "notifications/initialized",
})

# 3) tools/list
status, body = mcp_post("http://127.0.0.1:7799/mcp", {
    "jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {},
})
# parse the `data:` line of the SSE body to get {"result": {"tools": [...]}}
```

## 2. In-process FastMCP tool-listing check (fastest, no socket)

```python
from pkg.mcp_server import _build_server
server = _build_server(db_path=":memory:")
tools = server.list_tools()            # coroutine in some SDK versions
# if async: import asyncio; tools = asyncio.run(server.list_tools())
names = {t.name for t in tools}
assert {"remember", "recall", "search"} <= names
```

## 3. PYTHONPATH shadowing — pytest collection crash

Symptom: `pytest tests/` dies at config/collection with
`ModuleNotFoundError: pydantic_core._pydantic_core` (raised from a `langsmith`
pytest11 auto-plugin). `-p no:langsmith` does NOT fix it — entrypoint plugins load
before `-p` flags are applied.

Cause: a foreign `PYTHONPATH` (e.g. the agent host's venv) shadows the target
interpreter's packages. Confirm with:
```bash
echo "$PYTHONPATH"
python -c "import sys; print([p for p in sys.path if 'venv' in p])"
```

Fix: run the suite with a clean PYTHONPATH:
```bash
env -u PYTHONPATH python -m pytest tests/ -q -p no:cacheprovider
```
(This is a shell-session artifact, NOT a project defect — capture the *fix*, not a
"this tool is broken" rule.)
