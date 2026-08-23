---
name: python-package-pypi-ready
description: Make an existing Python package publishable to PyPI (or just pip-installable) WITHOUT publishing — version bump, PEP 621 pyproject fields, core deps vs optional-dependency groups, [project.scripts] console entrypoint wiring, and a green test gate. Use when the user says "make it PyPI-ready", "publish-ready", "add a console script", "fix the pyproject", "bump to 1.0.0", or hands you a repo and wants it installable/structured for release. Also covers the Windows/MSYS pytest-summary-swallowing gotcha so you can actually prove the suite is green.
---

# Make a Python package PyPI-publish-ready

Goal: take a working Python package and bring its `pyproject.toml` + layout to a
state where `pip install .` / `pip install -e .` works and `python -m build` would
succeed — **without** ever running `twine upload` or needing a PyPI token.

## When NOT to publish
The user often says "publish-ready" but means "structurally ready". Do NOT upload.
Treat any PyPI token / `__token__` / `TWINE_*` as absent unless explicitly given.
If asked to actually publish, stop and ask for the token + confirm the index.

## Required `pyproject.toml` shape (PEP 621, hatchling backend)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "samm"
version = "1.0.0"                       # bump per task; use strict X.Y.Z
description = "One-line pitch."         # required-ish; always set
readme = "README.md"                    # file must exist
license = "MIT"                        # SPDX string, not a table, for simple cases
requires-python = ">=3.11"             # match the actual min supported
authors = [{ name = "X", email = "y@z" }]
keywords = ["a", "b", "c"]
dependencies = [                       # CORE only — what import-time needs
    "pydantic>=2.7",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlite-vec>=0.1.0",
]

[project.optional-dependencies]        # NOT core — lazy / extra features
embeddings = ["sentence-transformers>=2.7"]
server = ["uvicorn[standard]>=0.29"]
dev = ["pytest>=8.0", "pytest-cov", "httpx", "ruff"]

[project.scripts]                      # console entrypoint
samm = "samm.cli:main"                 # module.attr — must be importable & callable

[project.urls]
Homepage = "https://github.com/you/proj"

[tool.hatch.build.targets.wheel]
packages = ["samm"]                    # the import package, not the repo root

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

## Dependency triage (the part people get wrong)
- **Core** = anything imported at module load or by the default code path.
  `fastapi` (api.py top-level import), `uvicorn` (cli `serve` imports it),
  `sqlite_vec` (store.py hard `import sqlite_vec`), `pydantic` (models) → core.
- **Optional** = lazy imports inside functions, or feature flags.
  `sentence_transformers` is imported *inside* `embedder.py` only when a model is
  requested → put it in `embeddings = [...]`. Keep it OUT of core so a
  `pip install samm` doesn't pull torch/tensorflow.
- **Drop cruft**: a dep listed in `dependencies` but never directly imported in
  the package is dead weight. Verify with a grep before trusting the old file:
  `grep -rn "import <pkg>" samm/ | grep -v __pycache__`
- `numpy` is almost always transitive (via sentence-transformers / pydantic) — don't
  add it to core unless code does `import numpy` directly.
- `uvicorn[standard]` (not bare `uvicorn`) so the `[standard]` extras (watchgod,
  colorama, etc.) are present for `samm serve`.

## Entrypoint rule
`[project.scripts] samm = "samm.cli:main"` requires:
- `samm/cli.py` exists with a module-level `main()` that is **callable** and takes
  `argv: list[str] | None = None` (argparse pattern).
- Verify: `python -c "import samm.cli; print(hasattr(samm.cli,'main'))"` → `True`.
- If `main`/`run` is missing, add a thin argparse wrapper — do NOT rewrite engine logic.

## DO NOT touch core engine/store/api
The task is packaging, not behavior. Common trap: a pre-existing test calls a method
on the wrong object (e.g. `eng.count_memories()` when the method lives on
`eng.store.count_memories()`). Fix the **test's call site**, not the engine. Core
logic changes belong in a different task.

## Full production-readiness (broader than PyPI)
When the ask is "make this repo production-ready" (LICENSE + SECURITY + CI +
Docker + env-config + expanded tests), and especially for a **flat src-layout**
(modules imported flat via `sys.path.insert(0,"src")`), read
`references/flat-src-layout-and-quality-gates.md` FIRST. It has the deliverable
bundle checklist plus three hard-won pitfalls: (1) never add `src/__init__.py` to
a flat layout — it breaks mypy with "Source file found twice"; (2) ruff B904 vs a
custom exception hierarchy that already chains via `cause=` — ignore B904, don't
rewrite; (3) aiohttp handlers that may stream must be annotated
`-> web.StreamResponse`, not `-> web.Response`.

## Verification gate (prove it's green)
> **Reusable probe**: `references/pytest-windows-verification.md` has the exact
> in-process `pytest.main()` recipe + dot-bar decoding for proving a suite is green
> under git-bash/MSYS. Copy it, don't re-derive it.

1. **pyproject parses**: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` → no error.
2. **entrypoint importable**: the `hasattr(samm.cli,'main')` check above → `True`.
3. **full suite passes**: run pytest. See the Windows/MSYS pitfall below.

### PITFALL — pytest summary line swallowed on Windows/MSYS (git-bash)
Under git-bash/MSYS, pytest writes its final summary (`59 passed, 1 skipped`) with
carriage returns (`\r`) that overwrite the line in the terminal AND in redirected
output, so `pytest ... 2>&1 | grep "passed"` returns **nothing** even on a green
run. You'll see the dot-progress bar (`....s....`) but no count, and `grep` fails.

**Reliable fixes (pick one):**
- Run pytest **in-process** and print the return code — the rc is the ground truth
  (0 = all pass, non-zero = failures):
  ```bash
  PY312="/c/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe"
  "$PY312" - <<'PY'
  import sys, pytest
  rc = pytest.main(["tests/", "-q", "--no-header", "-p", "no:cacheprovider"])
  print("PYTEST_RC=", rc)
  sys.exit(0)
  PY
  echo "shell exit=$?"   # 0 means green
  ```
- Or read the dot-progress bar: `N` dots = passed, `s` = skipped, `F` = failed.
  `59 dots + 1 s` ⇒ 59 passed, 1 skipped.
- `tr -d '\r'` before `grep` sometimes helps but is flaky with the progress bar;
  the in-process `pytest.main()` approach is the dependable one.

**Interpreter note:** the default `python` on PATH may lack packages the project
needs (`sqlite_vec`, etc.). Find the real one (e.g. `Python312/python.exe`) and run
verification with it. This is environment state, not a package defect — just use the
interpreter that has the deps installed.

## Report format
End with a tight table: pyproject parses ✅, entrypoint importable ✅, suite
`N passed, M skipped (rc=0)` ✅, core logic untouched ✅. State explicitly that
nothing was published.
