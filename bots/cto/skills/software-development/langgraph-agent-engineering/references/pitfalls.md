# LangGraph agent build — consolidated pitfalls (bug → fix)

Every entry below was hit and fixed during a real production-agent build
(langgraph-agent-kit + deep-research-orchestrator + enterprise-rag-assistant +
autonomous-code-reviewer). Each is a regression you can assert in tests.

| # | Symptom | Root cause | Fix |
| --- | --- | --- | --- |
| 1 | `ModuleNotFoundError: langgraph.checkpoint.sqlite` | `langgraph 0.6.x` + `langgraph-checkpoint-sqlite 3.1.0` pull incompatible `langgraph-checkpoint 4.1.1` | pin `langgraph-checkpoint-sqlite==3.0.0` (needs `checkpoint>=3,<4`) |
| 2 | `TypeError: No signature found for bound method` / `coroutine never awaited` | async graph node called `with_async_retry` without `await` (sync node) | make node `async def` and `await`; OR have retry detect coroutine-fns and `await` (else `asyncio.to_thread`) |
| 3 | `app.invoke` raises for async graph | graph has any `async def` node → compiled async-only | use `asyncio.run(app.ainvoke(state))` in tests; `pytest-asyncio` + `asyncio_mode="auto"` |
| 4 | `Recursion limit of 25 reached` | reflection node routes back to itself when not "done" (dumb FakeLLM never satisfies gate) | reflection/aggregate MUST set `done=True` (record verdict/grounded for observability); termination structural, not conditional |
| 5 | `OSError: Readme file does not exist` on `pip install -e .` | hatchling `readme="README.md"` but file not yet written | write README before first `pip install` |
| 6 | TTL test fails: `set(ttl=0)` still returns value | boundary `if expires_at < now` excludes `== now` | use `if expires_at <= time.time():` |
| 7 | `PermissionError: file used by another process` on tempdir cleanup | SQLite conn open when `TemporaryDirectory` removed | add `close()` to SQLite-backed classes; call before block exit |
| 8 | `ImportError: cannot import name 'scan_code'` | `patch` dropped the `def scan_code(...)` signature line | include full `def` header in both old/new strings |
| 9 | `write_file` fails "missing required field 'path'" | `path` arg omitted on a batched call | always pass `path` |
| 10 | `write_file` lands at `C:\c\Users\...` | MSYS path `/c/Users/...` double-prefixed | use native `C:/Users/...` paths |
| 11 | `pip install` rejects `file:///${PROJECT_ROOT}/../kit` | invalid PEP 508 specifier for standalone editable install | depend on `kit>=0.1.0`; install local kit via explicit path separately |
| 12 | `.yml` issue template rejected | `label: What happened?` — `?` ends a YAML key | quote values / block style |
| 13 | weak offline demo output | `FakeLLM` returns `"[fake] processed prompt..."` | task-aware heuristics: synthesis→cited report from `[id]`s; planner→JSON list; verdict→`{"satisfactory":true}` |

## Minimal regression assertions
- cache: `c = MemoryCache(ttl=0); c.set("a",1); assert c.get("a") is None`
- sqlite: open in tempdir, write, `close()`, then `shutil.rmtree` succeeds
- graph: `asyncio.run(app.ainvoke(state))` reaches `done is True` with no recursion error even on the dumb FakeLLM
- yaml: `bug_report.yml` parses (the write_file lint validates `.yml`)
