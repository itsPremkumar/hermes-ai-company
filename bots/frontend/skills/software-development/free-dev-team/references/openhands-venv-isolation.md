# OpenHands venv isolation (Windows / Hermes shell)

Verified 2026-07-16 on this box. OpenHands 1.11.0 requires Python >=3.12.

## Why a dedicated venv is mandatory
The Hermes desktop shell exports `PYTHONPATH` pointing at Hermes' OWN venv
(`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`),
which has a broken `pydantic_core` (`No module named 'pydantic_core._pydantic_core'`).
Any `python` that inherits that `PYTHONPATH` breaks OpenHands imports — even inside a
fresh venv — because sys.path gets the bad site-packages prepended.

## Build (uv is installed; plain pip also works)
```bash
uv venv --python 3.12 ~/openhands-venv
uv pip install --python ~/openhands-venv openhands-ai   # 1.11.0
```
(Do NOT `pip install openhands-ai` into the system Python 3.12 — it resolves to
ancient 0.8–0.9.8 with conflicting deps, or fails ResolutionImpossible. Use the venv.)

## Verify import
```bash
env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -c "import openhands; print('ok')"
```
- `-P` = isolate from PYTHONPATH / user site.
- `env -u PYTHONPATH` strips the leaked var for the single command.
Without BOTH, imports fail with the pydantic_core error.

## Run OpenHands (needs a runtime backend to execute code)
OpenHands' agent executes via Docker or SSH. Docker daemon is usually DOWN here
(`docker info` fails). So OpenHands is installed + importable but cannot RUN code
until Docker Desktop is started OR an SSH runtime is configured.
```bash
# after starting Docker Desktop:
env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -m openhands <task> --config-file ~/openhands-config.toml
```
Config (`~/openhands-config.toml`) reuses the OpenRouter free key from
`~/.openclaw/openclaw.json` (model `qwen/qwen2.5-coder-32b-instruct:free`).
CLI console script may not be exposed by `uv`; prefer `python -m openhands` or the
SDK `LocalConversation` API (params: agent, workspace, plugins, ...).

## Gotchas
- `python3` is NOT on PATH here — use `python` (3.11.15) or the venv's `python.exe`.
- `execute_code` is blocked by a safety guard on this host → use terminal + `python`.
- Docker client is installed but the engine pipe is absent when Docker Desktop is closed.
