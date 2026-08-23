---
name: fastapi-websocket-testing
description: "Test FastAPI/Starlette WebSocket broadcast endpoints with fastapi.testclient.TestClient under pytest — the event-loop pitfall and the in-loop trigger pattern. Use when adding/testing a WS route that pushes server-initiated messages (conflict streams, live updates, notifications) and the test must assert the client receives JSON."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, fastapi, starlette, websocket, testclient, async, pytest]
    related_skills: [test-driven-development, verify-codebase]
---

# Testing FastAPI / Starlette WebSocket broadcast endpoints

## When to use

You added (or must test) a WebSocket route that the **server** pushes messages to
— e.g. `WS /ws/conflicts/{ns}` fed by a `broadcast_conflict(...)` coroutine, a
live-notifications socket, a progress stream. The test must open the socket with
`TestClient.websocket_connect` and assert the client receives a JSON message when
the broadcast fires.

## The trap (the one thing that will bite you)

`TestClient.websocket_connect(...)` runs the ASGI app — and therefore *owns* the
WebSocket connection — inside an **anyio worker thread with its own event loop**.
A `starlette.websockets.WebSocket` captures the loop it was born in.

Trying to fire the broadcast from the main test thread fails:

```python
# WRONG — RuntimeError: no current event loop
asyncio.get_event_loop().run_until_complete(broadcast_conflict(data))
# WRONG — asyncio.run spins a NEW loop; socket lives in TestClient's loop
asyncio.run(broadcast_conflict(data))   # "different loop" error on send
```

There is no public accessor to reach TestClient's internal loop, so don't fight it.

## The fix: trigger the broadcast inside the app's loop

Invoke the broadcast through an HTTP route that runs in TestClient's loop — i.e. an
endpoint that awaits your broadcast coroutine. Sender and receiver then share a loop
and the message arrives reliably.

```python
# ---- app side (in-loop) ----
@app.post("/namespaces/{ns}/conflicts/notify", dependencies=[Depends(_auth)])
async def notify_conflicts(ns: str, threshold: float = Query(0.78)):
    for c in engine.conflicts(ns, threshold):
        data = c.model_dump(); data.setdefault("namespace", ns)
        await stream.broadcast_conflict(data)   # runs in TestClient's loop
    return {"broadcast": len(...)}              # BroadcastConflicts → clients

# ---- test side ----
def test_ws_receives_broadcast(client):
    with client.websocket_connect("/ws/conflicts/test") as ws:
        r = client.post("/namespaces/test/conflicts/notify",
                        params={"threshold": 0.6})
        assert r.status_code == 200
        received = ws.receive_json()             # arrives reliably
        assert received["namespace"] == "test"
```

See `references/fastapi-websocket-testclient.md` for the full recipe, the
registry/cleanup pattern, and the domain conflict-detector gating note.

## Direct broadcast call is only safe with zero subscribers

`broadcast_conflict` iterates the registry and `await ws.send_json(...)` per
socket. With **no** connected clients there is nothing to await, so calling it
from any loop is fine — use that as a standalone "does not raise" test:

```python
def test_broadcast_no_subscribers_is_safe():
    asyncio.run(broadcast_conflict({"namespace": "nobody", ...}))
```

## Keep changes minimal / non-breaking to REST tests

- Add WS + notify routes inside `create_app` (or equivalent factory). Don't touch
  existing REST handlers.
- The notify route can reuse the same auth `Depends` as other write routes.
- No new pyproject dependency: WebSocket support ships with Starlette/FastAPI
  (`websockets` is a transitive dep) and `TestClient` handles `websocket_connect`
  natively.

## Verification

Run the full suite the way the project expects, e.g.:
`env -u PYTHONPATH python -m pytest tests/ -q`
Assert: new WS tests PASS, and ALL pre-existing REST/engine tests still PASS
(no regressions). Count exact pass total and report it.
