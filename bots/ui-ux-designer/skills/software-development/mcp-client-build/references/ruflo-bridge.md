# Ruflo MCP stdio bridge — working recipe

How to build a Python MCP client that drives a REAL Ruflo server (launched via the
dev-team-stack wrapper) and mirrors external memory records into Ruflo namespaces.

## 1. The wrapper

`/c/Users/PREM KUMAR/dev-team-stack/bin/ruflo-mcp-stdio.sh` runs `ruflo mcp start` and
pipes stdout through `grep -v '^\[...T|INFO|Starting in stdio'` so the leading startup
log line is stripped and a strict MCP client can complete the JSON-RPC handshake.

## 2. Connection

```python
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession

params = StdioServerParameters(command="bash", args=["/c/Users/PREM KUMAR/dev-team-stack/bin/ruflo-mcp-stdio.sh"])
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # call_tool(...)
```

NOTE: do NOT set `PYTHONPATH`/`env` here — Ruflo manages its own node runtime. This is the
opposite of the in-process SAMM pattern, where you must inject PYTHONPATH so the child can
`import samm`.

## 3. Tool signatures (from `list_tools` on the live server)

- `memory_store(key: str, value: Any, namespace: str="default", tags: [...], ttl: number, upsert: bool=False)`
  returns `{"success": true, "key": ..., "namespace": ..., "stored": true, "hasEmbedding": true, "embeddingDimensions": 384, ...}`
- `memory_search(query: str, namespace: str="default", limit: number=10, threshold: number=0.3, smart: bool=False)`
  returns `{"query": ..., "results": [{"key":..., "namespace":..., "value":..., "similarity": 0.xx}], "total": N, ...}`

Store a record:
```python
await session.call_tool("memory_store", {
    "key": record.id,
    "value": {"content": record.content, "type": record.type.value,
              "agent": record.agent_id, "ts": record.timestamp},
    "namespace": ns,
    "upsert": True,
})
```

## 4. THE pitfall — `value` comes back as a JSON STRING

`memory_store` accepts a dict `value` and reports success. But `memory_search` returns
that dict double-encoded as a JSON string in many cases:

```
HITS=[{"key":"ee7c...","namespace":"dbg_...","value":"{\"content\":\"The deployment
pipeline must run migrations befo...","similarity":0.687}]
```

So `hit["value"]["content"]` raises `TypeError: string indices must be integers`.
Normalize every returned `value`:

```python
for hit in hits:
    val = hit.get("value")
    if isinstance(val, str):
        try: hit["value"] = json.loads(val)
        except (json.JSONDecodeError, TypeError): pass
```

## 5. Test hygiene

Ruflo memory is persistent and shared, so use a unique namespace per test:

```python
import time, uuid
ns = f"test_{uuid.uuid4().hex}_{int(time.time()*1000)}"
```

Run the real suite with no mocks:
`env -u PYTHONPATH /c/Users/PREM\ KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/ -q`
