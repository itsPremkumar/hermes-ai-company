# OpenHands as a Free Coding Agent — Verified Recipe (Windows, 2026-07-16)

The complete free dev team: **Hermes** (orchestrator, `hy3:free`) + **OpenHands** (coder,
free OpenRouter model) + **gstack** (QA/security methodology) + **ponytail** (lean-code
discipline). All $0, no paid keys.

## 1. Install OpenHands in an isolated venv (Python 3.12)

```bash
# uv is already available on this box; use it for a clean venv
uv venv --python 3.12 ~/openhands-venv
uv pip install --python ~/openhands-venv openhands-ai
# -> openhands-ai 1.11.x installed; SDK reports 1.34.0; ~865 MB at ~/openhands-venv
```

Do NOT use `pip install openhands-ai` against the system Python — it resolves to old pins
0.8-0.9.8 that have conflicting deps and fail with `ResolutionImpossible`. Also do NOT use
Python 3.11 (openhands-ai >=0.10 requires >=3.12).

## 2. CRITICAL: strip the leaked PYTHONPATH before ANY OpenHands import

The Hermes shell exports `PYTHONPATH` pointing at Hermes' own (broken) venv, which has a
missing `pydantic_core._pydantic_core`. Running `~/openhands-venv/Scripts/python.exe` with
that still set breaks every import.

```bash
# Verify import works (this MUST succeed before you rely on OpenHands)
env -u PYTHONPATH OPENHANDS_SUPPRESS_BANNER=1 \
  ~/openhands-venv/Scripts/python.exe -P -c "import openhands; print(openhands.__version__)"

# SDK entry points that import cleanly:
env -u PYTHONPATH OPENHANDS_SUPPRESS_BANNER=1 \
  ~/openhands-venv/Scripts/python.exe -P -c "from openhands.sdk.conversation import LocalConversation; print('ok')"
```

`-P` makes the venv ignore `PYTHONPATH`/sys.path[0] modifications; `env -u PYTHONPATH`
removes the leak entirely. Without both, you get
`ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`.

## 3. Write the free-model config (reuse the OpenRouter key)

The OpenRouter key lives in `~/.openclaw/openclaw.json` (grep `sk-or-v1-...`). Never print it.

```toml
# ~/openhands-config.toml
[llm]
model = "qwen/qwen2.5-coder-32b-instruct:free"
base_url = "https://openrouter.ai/api/v1"
api_key = "<sk-or-v1-... from ~/.openclaw/openclaw.json>"
temperature = 0.2
top_p = 0.95

[agent]
max_iterations = 30
max_budget_per_task = 0.05

[core]
workspace_base = "C:/Users/PREM KUMAR/openhands-workspace"
```

Free models to consider: `qwen/qwen2.5-coder-32b-instruct:free` (recommended),
`mistralai/mistral-7b-instruct:free`, `meta-llama/llama-3.1-8b-instruct:free`.
Free tier rotates — verify at https://openrouter.ai/models?filters=free.

## 4. OpenHands needs a RUNTIME BACKEND to execute code

OpenHands' agent only *executes* code when a backend is present (Docker or SSH).
On this box Docker client is installed but the **daemon is DOWN** (`docker info` fails).
So OpenHands installs + imports fine but cannot run code until you either:
- start **Docker Desktop** (then `docker info` should succeed), or
- configure an **SSH runtime** in the OpenHands UI.

Launch (after Docker is up):
```bash
env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -m openhands <task> \
  --config-file ~/openhands-config.toml
```
If the `python -m openhands` front-end entry is unavailable in 1.11, drive the
`openhands.sdk.conversation.LocalConversation` API directly with `agent` + `workspace`.

## 5. End-to-end proof WITHOUT Docker (the gstack /health gate)

The team loop works without OpenHands executing — Hermes writes ponytail-disciplined
code, gstack verifies with `pytest`. Verified demo at `~/team-demo`:

```bash
cd ~/team-demo
PYTHONPATH=src python -m pytest -q      # 6 passed
python -m py_compile src/team_demo/slug.py && echo COMPILE_OK
```

That is the minimum "team works" signal when Docker is unavailable.
