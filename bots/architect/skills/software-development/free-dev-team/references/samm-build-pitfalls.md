# SAMM build pitfalls (Shared Agent Memory Mesh) — reusable debugging paths

Captured while building `samm` (self-hosted shared agent memory) with the free-dev-team.
These bites apply to ANY local SQLite + vector-search + FastAPI Python project on this box.

## 1. sqlite-vec embedding binding format
`sqlite-vec` (vec0 virtual table) does NOT accept a Python `list` as the embedding value.
- WRONG: `cur.execute("INSERT INTO memories_vec(rowid, embedding) VALUES (?,?)", (rowid, record.embedding))`
  → `sqlite3.ProgrammingError: Error binding parameter 2: type 'list' is not supported`
- RIGHT: pass a **JSON array string**: `json.dumps(record.embedding)`.
- Reading back from vec0 returns its **packed internal blob**, NOT JSON — do NOT
  `json.loads(row["embedding"])` on a vec0 SELECT; it raises `UnicodeDecodeError`.
  Instead store/retrieve embeddings via a plain `TEXT` column (`embedding_json`) in the
  main table, decoupled from the vec0 blob. The vec0 table is only for KNN `MATCH`.

## 2. FastAPI 422 with `from __future__ import annotations`
A Pydantic request model param (`def remember(req: RememberReq)`) is treated as a
**query parameter** (→ 422 "Field required: req") when the module uses
`from __future__ import annotations`, because FastAPI sees a stringified annotation and
fails to resolve it as a body. FastAPI's own `TestClient` surfaces it as 422, not 500.
- Fix: **remove `from __future__ import annotations`** from the API module (or annotate
  the param explicitly as `Body()`). Verified: removing the future import made
  `POST /memories` parse the JSON body correctly.

## 3. SQLite thread-safety in FastAPI/TestClient
FastAPI `TestClient` runs sync endpoints in a worker thread, so a connection created in
the main thread raises "SQLite objects created in a thread can only be used in that same
thread."
- Fix: `sqlite3.connect(path, check_same_thread=False)` + a `threading.Lock()` around
  all writes (`put`, `update`). Verified: removed the thread error and all API tests passed.

## 4. Multiple Python interpreters on this box — run tests with the RIGHT one
`python` resolves to the **Hermes venv** (3.11.x, NO sqlite-vec, NO fastapi). The deps
(sqlite-vec 0.1.6, fastapi, httpx) are installed under **Python312**
(`C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe`). A `pytest`
invoked via `python -m pytest` silently uses uv's python and reports ImportError.
- Fix: always run project tests with the explicit interpreter that has the deps:
  `/c/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/ -q`
- Note: `env -u PYTHONPATH` is still wise (avoids the Hermes-venv pydantic leak).

## 5. Ad-hoc verification pattern (standing bar)
When a project has no canonical test command, write a disposable temp script under
`$TMP` with a `hermes-verify-` prefix, run it, then delete it. Report it explicitly as
ad-hoc smoke, NOT a green suite. Do not fabricate "all checks passed" — if a check is
environment-dependent and you cannot reproduce it on demand, state the limitation and
prove the FIX is deterministic instead.

## 6. Where the OpenRouter key actually lives (if needed)
The Hermes `.env` (`AppData/Local/hermes/.env`) may show `OPENROUTER_API_KEY=` EMPTY or
masked. A grep that "finds" `sk-or-...` may be matching an unrelated minified blob in the
same file. Treat an empty/masked value as "no key" and ask the user to paste the full
`sk-or-...` secret rather than configuring Ruflo/OpenHands with a non-working key.

## 7. vec0 cosine distance can exceed 1 with UNNORMALIZED embeddings → negative scores
`samm search()` returned scores like **-0.4142**. Root cause: vec0's `MATCH` returns
**cosine distance** in [0, 2], but the code did `score = 1.0 - distance` with no clamp.
When the embedder produces **unnormalized** vectors (e.g. the hash embedder — sparse,
non-unit-norm), cosine distance can be > 1, so `1.0 - distance` goes negative.
- Fix: `score = max(0.0, min(1.0, 1.0 - float(distance)))`. Also de-dup by memory id
  (keep best score) since KNN can return the same id via multiple vec rows.
- Lesson: NEVER trust `1 - distance` as a [0,1] score unless embeddings are unit-normalized.
  Always clamp. Add a regression test asserting `score >= 0`.
- Bonus inefficiency found same fix: `search()` was calling a per-record `INSERT/SELECT`
  (`_rowid_for`) on every call. Read the `mem_rowid` table read-only instead (SELECT by id),
  no writes on the hot path.
