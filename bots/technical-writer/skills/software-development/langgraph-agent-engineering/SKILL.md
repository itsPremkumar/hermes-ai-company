---
name: langgraph-agent-engineering
description: >-
  Build production-grade, testable AI-agent systems with LangGraph (Python):
  shared foundation kits, typed state, checkpointing, reflection/self-eval
  loops, conditional routing, and the exact dependency pins + async patterns
  that make multi-agent repos actually run and pass tests. Load whenever the
  user wants to "build a LangGraph agent", "production agent repo", "agent
  portfolio", "multi-agent orchestrator", "RAG/research/code-review agent with
  LangGraph", or hits LangGraph install/test failures.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [langgraph, agents, python, multi-agent, rag, orchestration, production, testing]
---

# LangGraph Agent Engineering (production-grade)

Patterns distilled from building a real, tested LangGraph agent portfolio
(`langgraph-agent-kit` shared library + `deep-research-orchestrator` and sibling
repos). These are the non-obvious bits that cost a full debugging session to
discover — encode them up front.

## When to load this
- User asks to build an agent / multi-agent system / orchestrator with LangGraph.
- LangGraph install fails with `langgraph-checkpoint` version conflicts.
- A LangGraph graph test errors with "coroutine was never awaited" or
  `TypeError: No signature found`.
- You need agents that run in CI without API keys (offline / fake backend).

## Core architecture (the leverage pattern)
Build ONE shared foundation package, then have each domain repo depend on it:

```
langgraph-agent-kit/              # reusable building blocks
  langgraph_agent_kit/
    state.py        # BaseAgentState (TypedDict + reducers)
    config.py       # pydantic-settings AgentSettings
    logging_conf.py # JSON structured logging (avoid shadowing stdlib 'logging')
    retry.py        # with_retry / with_async_retry (exponential backoff)
    cache.py        # MemoryCache / SQLiteCache + cached() decorator
    prompts.py      # versioned PromptManager
    tools.py        # Tool + ToolRegistry, schema inference, LangChain adapter
    memory.py       # SQLite LongTermMemory
    llm.py          # LLM abc + FakeLLM (offline) + OpenAI/Anthropic adapters
    graph.py        # build_react_agent / build_reflective_agent
    streaming.py / eval.py
deep-research-orchestrator/       # domain repo; pyproject depends on the kit
  pyproject.toml  ->  langgraph-agent-kit @ file:///${PROJECT_ROOT}/../langgraph-agent-kit
```

Key rules:
- Name the logging module `logging_conf.py`, NOT `logging.py` — a file named
  `logging.py` shadows the stdlib and breaks imports.
- `BaseAgentState` is a `TypedDict(total=False)` with `Annotated[list, reducer]`
  channels so multiple nodes can append without clobbering.
- Expose a `FakeLLM` backend so the WHOLE graph runs offline in tests/CI.

## CRITICAL: dependency pin (LangGraph 0.6.x + SQLite checkpoints)
`langgraph 0.6.x` requires `langgraph-checkpoint <4.0.0,>=2.1.0`, but
`langgraph-checkpoint-sqlite 3.1.0` requires `langgraph-checkpoint >=4.1.0`.
This is a PUBLISHED conflict — `pip install langgraph langgraph-checkpoint-sqlite`
yields an incompatible `langgraph-checkpoint 4.1.1` and
`from langgraph.checkpoint.sqlite import SqliteSaver` fails with
`ModuleNotFoundError`.

**Fix:** pin `langgraph-checkpoint-sqlite==3.0.0` (it requires
`langgraph-checkpoint >=3,<4`, which matches `langgraph 0.6.x`).

See `references/langgraph-version-pins.md` for the exact resolution recipe and
how to verify `SqliteSaver` imports before running tests.

## CRITICAL: async nodes + retry + test invocation
If any graph node is `async def`, the compiled graph is **async-only**:
`app.invoke(...)` raises; you must use `app.ainvoke(...)`. The recurring traps:

1. A retry wrapper that is `async def` but called WITHOUT `await` inside a sync
   node returns a coroutine object -> `"'coroutine' object has no attribute
   'text'"`. Either make the node `async def` and `await` the retry, OR make the
   retry wrapper itself `await` coroutine functions (see `with_async_retry`
   which detects `inscoroutinefunction` and `await`s, else runs via
   `asyncio.to_thread`).
2. In tests, call `asyncio.run(app.ainvoke(state))` — do NOT `app.invoke`.
3. `pytest-asyncio` must be in dev deps for `@pytest.mark.asyncio` tests; set
   `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`.

See `references/async-node-pattern.md` for the canonical node + test skeleton.

## Offline-testable agent design (so CI needs no API keys)
- Ship `FakeLLM` that returns deterministic, scripted, or heuristic text (e.g.
  returns `{"satisfactory": true, ...}` for reflection prompts, first quoted
  option for router prompts).
- Ship tool backends with an OFFLINE fallback (keyword search over a small
  in-repo corpus; deterministic `fetch_content`). Synthesis/verification then
  run end-to-end with zero network.
- Real backends (OpenAI/Anthropic, Tavily/SerpAPI) are adapter-swappable behind
  the same `LLM` / `Tool` interface.

## Verification discipline (matching the user's standing quality bar)
- No project is "done" until `pytest -q` passes (offline).
- Add `pytest-cov` + a `Dockerfile` whose default `CMD` runs the test suite.
- Add a GitHub Actions `ci.yml` matrix over Python 3.10/3.11/3.12.
- Capture every bug you actually hit as a regression test (the coroutine bug,
  the TTL-expiry edge, the SQLite temp-file lock on cleanup -> add `close()`
  to SQLite-backed classes and call it in tests).

## File-writing pitfall on this Windows/MSYS box
The Hermes `write_file` tool misinterprets MSYS paths like `/c/Users/PREM KUMAR/...`
and writes to `C:\c\Users\PREM KUMAR\...` (double prefix). **Use native Windows
paths** (`C:/Users/PREM KUMAR/...`) in `write_file`/`patch` paths to land files
in the right place. (Also relevant to any git/terminal work under MSYS — prefer
`C:/...`.) This bit the very first writes of this portfolio build.

## Additional pitfalls confirmed during the production build

These cost real debugging time and are now encoded so the next session skips them.

### Reflection / graph loops MUST terminate
A reflection node that routes back to itself (or to `reason`) when "not done"
WILL hit LangGraph's `Recursion limit of 25 reached` error on the dumb
`FakeLLM` (non-scripted answers fail faithfulness and never satisfy the gate).
**Fix:** the reflection/aggregate node must ALWAYS set `done=True` (it may still
record `grounded=False` / a `reject` verdict for observability); routing back to
the same node for "revise" is only safe if a hard iteration cap guarantees exit.
Prefer: reflect sets `done=True`; termination is structural, not conditional.

### hatchling needs `README.md` to exist before install
`pip install -e .` with a hatchling `pyproject.toml` that sets `readme = "README.md"`
FAILS with `OSError: Readme file does not exist` if the README isn't written yet.
**Fix:** write the repo README (and any `readme`-referenced file) BEFORE the
first `pip install`, or the editable install aborts and `pytest` reports
"ModuleNotFoundError: pytest".

### TTL cache boundary: `ttl=0` must expire immediately
`MemoryCache.set(key, v, ttl=0)` computed `expires_at = now + 0`, which is still
`> now`, so `get()` returned the value (test asserted `None`). **Fix:** in the
`get()` boundary use `if expires_at <= time.time():` (not `<`), so ttl<=0 is
already expired.

### SQLite temp-file lock on test cleanup
Tests that create `SQLiteCache`/`LongTermMemory` in a `tempfile.TemporaryDirectory`
then exit hit `PermissionError: The process cannot access the file ... used by
another process` because the connection is still open when the dir is removed.
**Fix:** add a `close()` method to every SQLite-backed class and call it at the
end of the `with tempfile.TemporaryDirectory()` block in tests.

### Offline `FakeLLM` heuristics make demos meaningful
A bare `FakeLLM` returning `"[fake] processed prompt of length N"` produces weak
reports. **Fix:** teach `FakeLLM._next` task-aware heuristics — when the prompt
contains `"Findings:"` and `"Sources:"` return a coherent cited report built from
`[chunk_id]`s found in the prompt; when it mentions "sub-questions"/"decompose"
return a JSON list `["<query>"]`; when it asks for a JSON verdict return
`{"satisfactory": true, ...}`. This makes the entire offline demo produce a real,
grounded artifact (e.g. research report with `grounding_ratio=1.0`).

### `patch` tool can silently drop a function signature
When patching near the top of a function, if the old_string includes the
`def foo(...)` line and the replacement omits it, the function header is DELETED
(`ImportError: cannot import name 'scan_code'`). Always include the full
`def` signature (and one body line) in both old and new strings. The same class
of mistake appears as a missing `path` argument on `write_file` (the call then
fails) — always pass `path`.

### `pyproject` dependency specifier: avoid `${PROJECT_ROOT}` in published deps
`langgraph-agent-kit @ file:///${PROJECT_ROOT}/../langgraph-agent-kit` is NOT a
valid PEP 508 specifier for `pip install -e .` on its own and breaks publication.
**Fix:** depend on the published name+version (`langgraph-agent-kit>=0.1.0`) and
install the local kit separately with an explicit path during dev/test.

### YAML issue templates must quote values with `?`
GitHub `bug_report.yml` with inline mappings like `label: What happened?` fails
`.yml` validation because `?` ends a YAML key. **Fix:** use block style with
quoted strings (`label: "What happened?"`) or `body:` item attributes on separate
lines. Validate `.yml` via the write_file lint (it runs YAML validation).

## References
- `references/langgraph-version-pins.md` — exact conflict + fix recipe.
- `references/async-node-pattern.md` — node + retry + test skeleton.
- `references/pitfalls.md` — consolidated bug→fix regression table (TTL, SQLite lock, recursion limit, hatchling README).
- `templates/agent_repo_skeleton.md` — copy-paste repo layout for a new domain agent.
