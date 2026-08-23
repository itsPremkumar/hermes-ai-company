# FastAPI / Starlette WebSocket testing with TestClient — full recipe

Reusable pattern for testing server-pushed WebSocket broadcasts (conflict streams,
live notifications, progress) via `fastapi.testclient.TestClient` under pytest.

## Why the naive test fails

`TestClient.websocket_connect(...)` services the ASGI app in an **anyio worker
thread with its own event loop**. The `starlette.websockets.WebSocket` object
binds to that loop. Driving the broadcast from the main test thread:

```python
import asyncio
asyncio.get_event_loop().run_until_complete(broadcast_conflict(d))  # RuntimeError: no loop
asyncio.run(broadcast_conflict(d))                                  # wrong loop owns the socket
```

`await ws.send_json(...)` then raises because the socket lives in TestClient's
loop, not the one you created. No public accessor reaches that loop — don't fight it.

## Fix: fire the broadcast inside the app's loop

Trigger it via an HTTP route that awaits your coroutine, so sender + receiver share
a loop:

```python
@app.post("/namespaces/{ns}/conflicts/notify", dependencies=[Depends(_auth)])
async def notify_conflicts(ns: str, threshold: float = Query(0.78)):
    for c in engine.conflicts(ns, threshold):
        data = c.model_dump(); data.setdefault("namespace", ns)
        await stream.broadcast_conflict(data)    # in TestClient's loop
    return {"broadcast": ...}

def test_ws_receives_broadcast(client):
    with client.websocket_connect("/ws/conflicts/test") as ws:
        r = client.post("/namespaces/test/conflicts/notify", params={"threshold": 0.6})
        assert r.status_code == 200
        received = ws.receive_json()
        assert received["namespace"] == "test"
```

## Registry + cleanup pattern (so disconnect assertions pass)

```python
_CONNECTIONS: dict[str, list[WebSocket]] = {}

def register(ns, ws): _CONNECTIONS.setdefault(ns, []).append(ws)
def unregister(ns, ws):
    conns = _CONNECTIONS.get(ns)
    if conns and ws in conns:
        conns.remove(ws)
        if not conns: _CONNECTIONS.pop(ns, None)
def get_connection_count(ns=None):
    return sum(len(v) for v in _CONNECTIONS.values()) if ns is None else len(_CONNECTIONS.get(ns, []))

async def broadcast_conflict(conflict_dict):
    ns = conflict_dict.get("namespace")
    conns = list(_CONNECTIONS.get(ns, [])) if ns is not None else [w for l in _CONNECTIONS.values() for w in l]
    dead = []
    for ws in conns:
        try: await ws.send_json(dict(conflict_dict))
        except Exception: dead.append((ns, ws))
    for n, w in dead:
        if n is not None: unregister(n, w)
```

WS route:

```python
@app.websocket("/ws/conflicts/{namespace}")
async def ws_conflicts(websocket: WebSocket, namespace: str):
    await websocket.accept()
    register(namespace, websocket)
    try:
        while True: await websocket.receive_text()   # stays open until client closes
    except Exception: pass
    finally: unregister(namespace, websocket)
```

After `with client.websocket_connect(...) as ws:` exits, the socket closes and
`get_connection_count(ns) == 0` holds.

## Direct broadcast call is only safe with zero subscribers

With no connected clients, `broadcast_conflict` has nothing to await — safe from
any loop:

```python
def test_broadcast_no_subscribers_is_safe():
    asyncio.run(broadcast_conflict({"namespace": "nobody", ...}))
```

## Conflict-detector gating (domain, not FastAPI)

If the broadcast only fires when `store.detect_conflicts` flags a conflict, know
its gating: many detectors require BOTH high similarity AND *opposing polarity*
(one text contains a negation like "not"/"never", the other doesn't). Seed
opposing-polarity content ("Server is up." / "Server is not up.") to make a
conflict actually fire; unrelated or same-polarity texts silently yield 0. The
broadcast test then fails to receive anything — looks like a WS bug but is really
a seed-content bug.

## Minimal / non-breaking

- Add WS + notify routes inside the app factory; don't touch existing REST handlers.
- Reuse the existing auth `Depends` for the notify route.
- No pyproject change: `websockets` is a transitive FastAPI/Starlette dep and
  `TestClient` supports `websocket_connect` natively.

## Verify

`env -u PYTHONPATH python -m pytest tests/ -q` → new WS tests PASS, all
pre-existing REST/engine tests still PASS. Report the exact pass count.
