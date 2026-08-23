# pytest / langsmith plugin crash (this box)

## Symptom
`python -m pytest -q` dies before collecting any test, with a traceback ending in:

```
File ".../pydantic/version.py", line 94, in _ensure_pydantic_core_version
    raise SystemError(
SystemError: The installed pydantic-core version (2.46.4) is incompatible with
the current pydantic version, which requires 2.41.5.
```

The crash originates in `langsmith/pytest_plugin.py` (loaded as the `langsmith_plugin`
`pytest11` entry point), NOT in Jarvis' own code. Because it happens at pytest
startup, it looks like "no tests ran" / "0 tests" — Jarvis' 35 tests are actually fine.

## Root cause
Environment has mismatched pydantic stack:
- `pydantic 2.12.5`
- `pydantic-core 2.46.4`  (pydantic 2.12.5 wants pydantic-core 2.41.5)
- `langsmith 0.7.4` whose pytest plugin imports `pydantic` at load time

`-p no:langsmith` does NOT disable it (entry-point name is `langsmith_plugin`).

## Fix (shipped in repo, commit 98e01ca)
`pytest.ini` at repo root:
```ini
[pytest]
addopts = -p no:langsmith_plugin
testpaths = tests
```
Now `python -m pytest -q` (run from repo root so the ini is found) -> **35 passed**.

## Manual one-shot workaround (no ini needed)
```
PYTHONPATH="C:/Users/PREM KUMAR/prems-jarvis-hermes" python -m pytest -q -p no:langsmith_plugin tests/
```
Note: pass a REAL Windows path to PYTHONPATH (`C:/Users/...` or `C:\Users\...`),
never the MSYS `/c/Users/...` form — the native Windows python turns `/c/Users`
into `C:\c\Users\...` and `import jarvis` fails.
