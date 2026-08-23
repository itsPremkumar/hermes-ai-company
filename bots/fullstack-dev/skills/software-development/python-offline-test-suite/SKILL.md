---
name: python-offline-test-suite
description: "Offline pytest: respx, mock, tmp_path. For no-network tests."
---

# Build an Offline Python Test Suite

## When to use
- The project's existing tests hit live internet (flaky, slow, can't run in CI).
- You're adding the first test suite to an untested Python project.
- CI must run without network access or API keys.
- The project depends on `httpx`/`requests` and third-party APIs (e.g. `ddgs`, `openai`, `googleapis`).

## Core technique: three-layer isolation

An offline suite mocks three things:

1. **HTTP layer** — `respx` intercepts every `httpx` request and returns canned responses.
2. **Third-party libraries** — `unittest.mock` replaces external APIs (e.g. `ddgs.DDGS`) with fakes.
3. **Filesystem/state** — `tmp_path` + `monkeypatch` redirects config/cache dirs so tests never touch the real filesystem.

## The conftest.py pattern

Create `tests/conftest.py` with shared fixtures:

```python
import sys
from pathlib import Path
from unittest import mock

import httpx
import pytest
import respx


# --- Home / config redirect ---
@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch):
    """Point Path.home() at a tmp dir so ~/.app-config is isolated."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    # Also patch module-level CONFIG_DIR / CONFIG_FILE if the app uses them.
    monkeypatch.setattr("myapp.config.CONFIG_DIR", tmp_path / ".myapp")
    monkeypatch.setattr("myapp.config.CONFIG_FILE", tmp_path / ".myapp" / "config.yaml")
    return tmp_path


# --- Third-party API fake ---
class _FakeDDGS:
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def text(self, query, max_results=5, **kwargs):
        return [
            {"title": f"{query} — result {i}", "href": f"https://example.com/{i}",
             "body": f"Snippet {i}"}
            for i in range(max_results)
        ]


@pytest.fixture
def fake_ddgs(monkeypatch):
    """Replace ddgs.DDGS everywhere, including lazy imports."""
    fake_mod = mock.MagicMock()
    fake_mod.DDGS = _FakeDDGS
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)


# --- httpx mock ---
@pytest.fixture
def respx_mock():
    with respx.mock(assert_all_called=False) as rp:
        yield rp


# --- Fresh app instance ---
@pytest.fixture
def app(tmp_home, fake_ddgs):
    from myapp.core import MyApp
    return MyApp()
```

## Canned response helpers

Add helpers to conftest.py for common responses:

```python
def html_page(title="Test Page", body="Hello"):
    return f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{body}</p></body></html>"

def robots_txt(allow="/"):
    return f"User-agent: *\nDisallow: /admin/\nAllow: {allow}\n"

def sitemap_xml(urls):
    items = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'
```

## Writing tests

```python
def test_search_returns_results(app, fake_ddgs, respx_mock):
    respx_mock.route(host="html.duckduckgo.com").respond(200, text="<html></html>")
    respx_mock.route(host="www.google.com").respond(200, text="<html></html>")
    # ... mock all backends the search hits

    result = app.search("query", limit=3, use_cache=False)
    assert result["success"]
    assert result["data"]["web"]
```

## CI workflow

Add `.github/workflows/ci.yml`:

```yaml
name: CI
on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[test]"
      - run: python -m pytest tests/ -v --tb=short
      - run: |
          pip install build
          python -m build
```

## pyproject.toml config

```toml
[project.optional-dependencies]
test = ["pytest>=7.0.0", "respx>=0.21.0", "responses>=0.23.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-ra -q --strict-markers"
markers = [
    "slow: marks tests as slow",
    "network: marks tests that require network access",
]
```

## Pitfalls

- **Module-level instantiation breaks isolation.** If the app does `search = MyApp()` at module top-level, importing the test file triggers real network calls. Fix: refactor to lazy init, or use the `tmp_home` fixture to redirect before import.
- **Lazy imports need sys.modules patching.** `from ddgs import DDGS` inside a function won't be caught by `monkeypatch.setattr("myapp.core.DDGS", ...)`. Patch `sys.modules["ddgs"]` instead (see conftest above).
- **respx `assert_all_called=False`.** Without it, respx fails if a test doesn't consume every mocked route. Set it to keep tests focused.
- **Windows/MSYS pytest summary swallowing.** On git-bash/MSYS, pytest's final summary line is overwritten by carriage returns, so `grep "passed"` returns nothing even on green runs. Run pytest in-process and check the return code instead. See `references/windows-pytest-verification.md` under `python-package-pypi-ready`.
- **Import-time side effects.** If importing the app triggers network calls (e.g. at module load), the test collection itself hangs. Use `tmp_home` + `fake_ddgs` fixtures before any import, or restructure the app to defer initialization.

## Verification

```bash
python -m pytest tests/ -q
# Expect: N passed in X.XXs
```

## Complements
- `python-package-pypi-ready` — Windows pytest gotcha, packaging, entrypoint wiring.
- `test-driven-development` — TDD workflow (RED-GREEN-REFACTOR).
- `verify-untested-repo` — ad-hoc verification when no suite exists.
- `verify-codebase` — full repo audit (claim-verification, CI gate, production-bug audit).
