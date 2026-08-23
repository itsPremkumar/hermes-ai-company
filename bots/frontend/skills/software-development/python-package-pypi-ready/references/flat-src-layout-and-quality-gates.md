# Flat src-layout + ruff/mypy gate gotchas

Session-proven pitfalls when productionizing a Python repo that uses a **flat
src-layout** (modules live directly under `src/` and are imported flat, e.g.
`import server`, `import errors` — NOT `from src.server import ...`). This is the
layout used by e.g. free-llm-router, where `main.py` does `sys.path.insert(0, "src")`.

## PITFALL — do NOT add `src/__init__.py` to a flat src-layout
Adding `src/__init__.py` to expose `__version__` breaks mypy with:

```
src/errors.py: error: Source file found twice under different module names:
"src.errors" and "errors"
```

mypy now sees the modules both as top-level (`errors`) and as a package
(`src.errors`) and refuses to check. **Fix:** delete `src/__init__.py`. Put the
version string in `pyproject.toml` (`[project] version`) and, if code needs it at
runtime, in the main module — not in a `src` package init. A flat src-layout is
intentionally *not* a package.

Corollary for pyproject packaging of a flat layout:
```toml
[tool.setuptools]
package-dir = { "" = "src" }
[tool.setuptools.packages.find]
where = ["src"]
```
and set `pythonpath = ["src"]` under `[tool.pytest.ini_options]` so tests import
flat too. Add a `tests/conftest.py` that also `sys.path.insert(0, "src")` for
runners that ignore the pytest config.

## PITFALL — ruff B904 vs a custom exception hierarchy that already chains
If the project has structured errors that explicitly chain the cause (e.g.
`RouterError(msg, cause=e)` which sets `self.__cause__ = cause`), ruff's `B904`
("raise ... from err inside except") fires on every `raise` even though chaining
is already correct. Rewriting dozens of raises to `raise X(...) from e` is churn
that duplicates what `cause=` already does. **Fix:** ignore B904 in config rather
than rewrite:
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501", "B008", "B904"]
```
Let `ruff check --fix .` auto-handle the safe fixes (import sorting = `I`, etc.);
only the intentional design choices (B904 here) get ignored.

## PITFALL — aiohttp handler return-type annotations for mypy
Handlers that can return either `web.json_response(...)` (a `web.Response`) OR a
streamed `web.StreamResponse` must be annotated `-> web.StreamResponse`, not
`-> web.Response`. `Response` is a subclass of `StreamResponse`, so the broader
type accepts both; the narrower one makes mypy reject the streaming return path:
```
error: Incompatible return value type (got "StreamResponse", expected "Response")
```
Apply the same to any helper (e.g. `_err_response`) that may emit SSE.
Also: if a helper's value can be `str | SomeResult`, coerce to the expected type
at the call site (`text = text if isinstance(text, str) else text.text`) rather
than widening the callee.

## Production-readiness bundle (broader than PyPI)
When the ask is "make this repo production-ready" (not just pip-installable), the
deliverable set beyond `pyproject.toml` is:
- `LICENSE` (match declared SPDX), `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
  (Keep a Changelog format, first entry = the version you just set).
- `requirements.txt` (runtime) + `requirements-dev.txt` (`-r requirements.txt` +
  pytest/ruff/mypy).
- Env-var config with **CLI-flag-wins precedence** (12-factor without breaking
  existing CLI usage): a `_env_default(name, fallback)` helper feeding argparse
  `default=`. Document every var in `.env.example` and a README config table.
- Docker: `Dockerfile` (non-root user, deps layer cached, `HEALTHCHECK` hitting a
  real endpoint), `docker-compose.yml` (restart policy + healthcheck), `.dockerignore`.
- CI: `.github/workflows/ci.yml` matrix (py3.10/3.11/3.12) running lint + type +
  test. Run tests with the offline flag (`SKIP_LIVE=1` or equivalent) so CI never
  depends on flaky network/live providers; keep live tests as a separate opt-in.
- Three green gates before committing: `ruff check .` (exit 0), `mypy src`
  (exit 0), `pytest` (offline run passes). Then prove end-to-end with a real
  execution (boot the server, curl the endpoints) — not just unit tests.

## Backward-compat discipline (this user)
Never delete/modify existing behavior to add production polish: new files +
additive config only. Env vars must *fall back* to the old hardcoded defaults so
existing `python main.py serve --port X` keeps working unchanged. Commit locally;
push only after explicit "push"/"go".
