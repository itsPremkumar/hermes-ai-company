# Async node + retry + test invocation pattern

## Symptom 1: "'coroutine' object has no attribute 'text'"
A graph node called an `async def` retry wrapper synchronously:

```python
# WRONG (sync node calling async retry without await)
def reason(state):
    resp = with_async_retry(llm.agenerate, prompt)  # returns a coroutine!
    text = resp.text                                  # AttributeError
```

Fix option A — make the node async and await:

```python
async def reason(state):
    resp = await with_async_retry(llm.agenerate, prompt)
    text = resp.text
```

Fix option B — make the retry wrapper handle coroutine functions itself:

```python
async def with_async_retry(func, *args, **kwargs):
    is_coro = inspect.iscoroutinefunction(func)
    for attempt in range(1, max_attempts + 1):
        try:
            if is_coro:
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)
        except NON_RETRYABLE:
            raise
        except retryable as exc:
            last_exc = exc
            if attempt == max_attempts: break
            await asyncio.sleep(backoff)
    raise last_exc
```

## Symptom 2: graph is async-only after one async node
If ANY node is `async def`, `graph.compile()` returns an async graph.
`app.invoke(state)` then raises. Use `app.ainvoke`:

```python
out = asyncio.run(app.ainvoke(state))   # in tests / sync entrypoints
# or inside an async def:
out = await app.ainvoke(state)
```

## Symptom 3: @pytest.mark.asyncio "Unknown config option: asyncio_mode"
`pytest-asyncio` wasn't installed. Add it to dev deps:

```toml
dev = ["pytest>=8.2,<9", "pytest-cov>=5.0,<6", "pytest-asyncio>=0.23,<1", "ruff>=0.5,<1"]
```
and set under `[tool.pytest.ini_options]`:
```toml
asyncio_mode = "auto"
```

## Canonical reflective-node skeleton (verified working)
```python
async def reason(state: BaseAgentState) -> dict:
    goal = state.get("meta", {}).get("goal", "")
    prompt = _build_prompt(goal, state)
    try:
        resp = await with_async_retry(llm.agenerate, prompt, max_attempts=3)
        text = resp.text
    except Exception as exc:                      # noqa: BLE001
        return {"errors": [{"node": "reason", "error": str(exc)}], "done": False}
    if text.strip().startswith("FINAL:"):
        return {"final_answer": text[len("FINAL:"):].strip(), "done": True}
    return {"messages": [{"role": "assistant", "content": text}],
            "iterations": state.get("iterations", 0) + 1, "done": False}

def route(state) -> Literal["act", "finish"]:
    if state.get("done") or state.get("iterations", 0) >= MAX: return "finish"
    ...
```

Conditional routing uses `graph.add_conditional_edges(node, route_fn, {branch: target})`.
Checkpointing: `with SqliteSaver.from_conn_string(path) as saver: return graph.compile(checkpointer=saver)`.
