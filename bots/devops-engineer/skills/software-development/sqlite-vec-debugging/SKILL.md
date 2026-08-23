---
name: sqlite-vec-debugging
description: "Debug sqlite-vec (vec0) failures in Python SQLite stores — the two recurring root causes (DDL dimension not interpolated; vec table dimension mismatched against the embedder) and the 'whole suite errors at setup' shared-root-cause workflow. Use when a FastAPI/agent/SQLite store using sqlite_vec throws 'vec0 constructor error: could not parse vector column' or 'Dimension mismatch for inserted vector' and a wall of tests fail identically at fixture setup."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, sqlite, sqlite-vec, vec0, root-cause, test-suite]
    related_skills: [systematic-debugging, verify-codebase]
---

# sqlite-vec (vec0) Debugging

## When to use
A Python codebase wraps `sqlite3` + `sqlite_vec` for vector search (memory stores,
RAG backends, agent meshes). The test suite explodes with the SAME error on every
test, or inserts fail with a dimension error. Two root causes cover the vast
majority of these.

## Root cause A — vec0 DDL leaves the dimension literal
`CREATE VIRTUAL TABLE ... USING vec0(embedding float[{dim}])` inside a **plain**
(non-f) triple-quoted string passes `{dim}` verbatim to sqlite-vec, which strictly
parses the column spec and throws:

```
sqlite3.OperationalError: vec0 constructor error: could not parse vector column
'embedding float[{self._vec_dim}]'
```

This fires inside `MemoryStore.__init__` → `conn.executescript(...)`, so EVERY
test that builds the engine/app errors at fixture setup — a wall of identical
`ERROR at setup` lines, NOT many independent bugs.

**Fix:** interpolate the dimension. Either make it an f-string —
`f"CREATE VIRTUAL TABLE memories_vec USING vec0(embedding float[{dim}])"` — or
substitute on a plain string: `sql = "...float[{dim}]...".replace("{dim}", str(dim))`.

**PITFALL — wrong parenthesis placement makes the `.replace()` a silent no-op.**
If the `.replace()` is chained to the *method call's return value* instead of the
string literal, it does nothing and the literal `{self._vec_dim}` reaches sqlite-vec
(the Cursor returned by `executescript` has no meaningful `.replace`, so it silently
fails to interpolate). This is the #1 way A resurfaces after a "fix":

```python
# WRONG — replace() runs on executescript()'s return (a Cursor), not the SQL string
self.conn.executescript("""... float[{self._vec_dim}] ...""").replace("{self._vec_dim}", str(self._vec_dim))
# RIGHT — replace() closes the string, THEN the result is passed to executescript
self.conn.executescript("""... float[{self._vec_dim}] ...""".replace("{self._vec_dim}", str(self._vec_dim)))
```

Visually the two are nearly identical; the bug is which paren the `.replace(` sits
inside. If you see A's error *after* a `.replace()` was "already added", re-read the
line and count parens — the string literal must be the object `.replace` is called on.

**Verify the fix stuck:** re-run the smallest test that builds the store
(`pytest tests/test_x.py::test_remember_stores_and_reads -v`) and grep the traceback
for `vec0 constructor error` / `{self._vec_dim}`. If the error is gone the wall
collapses. If the error text shows the literal still present, the parens are wrong.

## Root cause B — vec table dimension ≠ embedder's actual dim
The vec table is sized once at creation. If built with a default that differs from
the embedder in use, every `INSERT` fails:

```
sqlite3.OperationalError: Dimension mismatch for inserted vector for the
"embedding" column. Expected 384 dimensions but received 256.
```

Usual trigger: `LocalEmbedder(use_model=False)` (zero-cost hash fallback) emits
**256**-dim vectors (`HASH_DIM`); the real model is 384 (`DIM`). If the store is
constructed BEFORE the engine resolves its embedder, the store hardcodes 384 and
inserts then mismatch.

**Fix:** resolve the embedder first, then hand it to the store so the store reads
`getattr(embedder, "dim", 384)` at vec-table creation. In an engine wrapper:

```python
def __init__(self, db_path=":memory:", embedder=None):
    self.embedder = embedder or LocalEmbedder(use_model=False)
    self.store = MemoryStore(db_path, embedder=self.embedder)  # dim flows in
```

## Workflow — shared setup failure vs. many bugs
When a full `pytest` shows the SAME error on every test, do NOT read each
traceback. They share ONE root cause: a constructor/fixture that fails for all
(e.g. `MemoryStore.__init__`). Fix that one failure, re-run; the wall collapses.

A test that **passes alone but fails in the full run** is FLAKY (shared `:memory:`
state, search-threshold sensitivity, ordering), not a regression you introduced.
Confirm with `pytest tests/test_x.py::test_name -v`; only change code under test
if it also fails alone.

**Multi-agent / co-editing hazard:** if the store file is being edited by another
process (parallel subagent, swarm, live `git pull`), the error you read may be from a
*mid-write* version, not the final one — and a stale `__pycache__` can make Python
execute code that no longer matches disk, producing error lines that don't match what
you just read. Detect busy/transient edits before "fixing" anything:

```bash
# poll mtime+size; stable across ~30s means the writer has stopped
for i in 1 2 3 4 5; do stat -c '%Y %s' samm/store.py; sleep 6; done
# clear stale bytecode so the run uses the on-disk source, then re-run
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
pytest tests/test_x.py::test_remember_stores_and_reads -q
```

Only patch once the file is stable AND a fresh pycache run reproduces the error on
disk. Patching a moving target wastes a cycle and can collide with the other writer.

## Tight repro loop
```bash
# vec0 parse error, isolated:
python -c "import sqlite3, sqlite_vec; c=sqlite3.connect(':memory:'); \
c.enable_load_extension(True); sqlite_vec.load(c); c.enable_load_extension(False); \
c.execute('CREATE VIRTUAL TABLE v USING vec0(embedding float[384])'); print('ok')"
# dimension mismatch: build store with 384 table, insert a 256-dim vector.
```

## Related
`systematic-debugging` (4-phase root cause) governs the general process; this
skill is the sqlite-vec-specific knowledge bank for the two failure classes above.
