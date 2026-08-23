# Single-source model sync: catalog.py -> Hermes UI

Problem: Hermes UI reads `providers.free-llm-router.models` from `config.yaml`
verbatim; it does NOT poll the router `/v1/models`. Two lists drift. Solution:
`catalog.py` is the ONE source; a sync script regenerates the config list; the
supervisor runs it on startup. Verified working 2026-07-20 on Windows.

## 1. catalog.py — add the WORKING toggle + helpers
```python
# Provider ids that actually answer anonymously ($0, no key) from THIS host.
# The single switch you flip: add when it works, remove when it dies.
WORKING: set[str] = {"opencode", "opencode_go", "pollinations_text", "kilocode"}

def all_models(*, working_only: bool = False) -> list[tuple[str, str]]:
    out = []
    for pid, models in CATALOG.items():
        if working_only and pid not in WORKING:
            continue
        for m in models:
            out.append((pid, m))
    return out

def working_models() -> list[tuple[str, str]]:
    return all_models(working_only=True)
```

## 2. sync_hermes_models.py (repo root, stdlib + PyYAML)
Key points that avoid pitfalls:
- Resolve config path: `$HERMES_HOME/config.yaml` else
  `%LOCALAPPDATA%/hermes/config.yaml` (Windows) else `~/.hermes/config.yaml`.
- `yaml.safe_load` then `yaml.safe_dump(cfg, f, default_flow_style=False,
  sort_keys=False, allow_unicode=True)` — `sort_keys=False` PRESERVES the
  human-authored key order of the whole config; only the provider's `models`
  list is rewritten, every other section is left intact.
- `desired_models(working_only=True)` prepends the catch-all `"free"` then
  `f"{pid}:{m}"` for each catalog pair.
- Flags: default = working-only (clean UI); `--all` = full catalog;
  `--check` = report drift only, `return 1` if drift, change nothing (usable in
  CI / a pre-commit hook).
- Return codes: 0 = success/in-sync, 1 = drift (under --check), 2 = config not
  found.

```python
def sync(path, *, check, working_only=True):
    import yaml
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    prov = cfg.setdefault("providers", {}).setdefault("free-llm-router", {})
    wanted = ["free", *[f"{p}:{m}" for p, m in all_models(working_only=working_only)]]
    if list(prov.get("models", [])) == wanted:
        return False
    if check:
        return True
    prov.update({"api": "http://127.0.0.1:17498/v1", "name": "Free LLM Router",
                 "default_model": "free", "models": wanted})
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return True
```

## 3. run_server.py — auto-sync on startup (non-fatal)
Right after writing the PID file, before the launch loop:
```python
try:
    rc = subprocess.run([sys.executable, os.path.join(HERE, "sync_hermes_models.py")],
                        cwd=HERE, capture_output=True, text=True, timeout=30)
    for line in (rc.stdout + rc.stderr).splitlines():
        if line.strip():
            _log(f"model-sync: {line.strip()}")
except Exception as e:  # noqa: BLE001
    _log(f"model-sync skipped ({type(e).__name__}: {e})")
```
Wrapping in try/except is REQUIRED: a sync failure (e.g. PyYAML missing, config
locked) must never stop the router from serving.

## Verification (all passed 2026-07-20)
- `python -m pytest tests/ -q` -> `10 passed`.
- Ad-hoc: `working_models()` is a strict subset of `all_models()`; sync to a
  throwaway config writes only WORKING providers (no duckduckgo/mimocode/
  pollinations_gen/freemodel in the list); `--all` writes the full catalog;
  `--check` exits 0 after a real sync (idempotent).
- Supervisor log shows `model-sync: [sync] ... N models (working)` on startup.
- Live UI config = 21 working models (was ~78 with fakes/dead entries).

## Net workflow for the user
Edit `free_llm_router/catalog.py` -> restart the router -> Hermes UI updates.
Reminder to give the user: **restart Hermes** (relaunch or gateway `/restart`)
so the desktop re-reads `config.yaml` — config is loaded once at startup.
