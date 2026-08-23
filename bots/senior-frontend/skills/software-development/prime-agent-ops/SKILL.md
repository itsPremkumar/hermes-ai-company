---
name: prime-agent-ops
description: Install and run Prime Agent on Windows; fix setup errors.
---

# Prime Agent Ops (Windows)

Prime Agent (https://github.com/PrimeIntellect-ai/prime-agent) is an open-source RLM coding/research agent. It is a **Node CLI** but needs a **Python IPython kernel** for its file/shell tools, and a **model provider** to think. On Windows the two official assumptions (a POSIX installer + a clean Python) break. This skill captures the verified-working path (tested on a Windows 10 / Node 22 / nvm4w box).

## 1. Install on Windows (no install.sh)
The repo `install.sh` is macOS/Linux-only and just wraps `npm install -g` of a versioned tarball. `prime-agent` is **not** on the public npm registry (404). Install the release tarball directly:

```bash
# latest version + sha256 live in latest.json
curl -fsSL -o latest.json "https://github.com/PrimeIntellect-ai/prime-agent/releases/latest/download/latest.json"
# pick the CLI tarball (package "prime-agent", e.g. prime-agent-0.7.0.tgz)
curl -fsSL -o prime-agent.tgz "https://github.com/PrimeIntellect-ai/prime-agent/releases/download/v0.7.0/prime-agent-0.7.0.tgz"
sha256sum prime-agent.tgz        # compare to tarballs[].sha256 in latest.json
npm install -g ./prime-agent.tgz
prime-agent --version            # -> 0.7.0
```
- `package.json` has **no `os` field** so npm installs fine on Windows. `engines.node >= 22.8.0` (use Node 22+).
- `postinstall.cjs` is a **no-op unless** `PRIME_AGENT_BOOTSTRAP_KERNEL_ON_INSTALL=1` / `PRIME_AGENT_BOOTSTRAP_TOOLS_ON_INSTALL=1` are set. A plain global install triggers no shell/bootstrap steps.
- The `prime-agent-runtime` (kernel shim, Python module `rlm`) is **shipped inside the npm package** at `<npm-global>/prime-agent/dist/prime-agent-runtime` — it is NOT on PyPI. You need this path for the kernel fix in section 3. Find it with `npm root -g`.

## 2. Providers and the OpenCode Zen free-model trap
prime-agent supports many providers (env var or `~/.prime/agent/auth.json`). The agent itself is just a harness; **without a funded model key it cannot answer**.

**Critical gotcha:** prime-agent's default `opencode` model is a **paid** model. If your OpenCode Zen account has no payment method, you get `401 No payment method` even though the key is valid and the API is reachable. **Force a free model** with `--model`:

```bash
prime-agent --provider opencode --model deepseek-v4-flash-free -p "your task"
```

OpenCode Zen exposes 7 free models (list via `GET https://opencode.ai/zen/v1/models` with `Authorization: Bearer <key>`). Verified-working free ids: `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `laguna-s-2.1-free`, `longcat-2.0-free`. **Avoid** `ling-3.0-flash-free` (404 "unavailable for free") and `north-mini-code-free` (401 upstream). See `references/opencode-zen-free-models.md` for the probe transcript.

**Reading your key without printing it** (Hermes stores the OpenCode Zen key plaintext in `~/.hermes/.env`):
```bash
KEY=$(grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" | grep -E '^\s*OPENCODE_ZEN_API_KEY=' | tail -1 | sed -E 's/^[[:space:]]*OPENCODE_ZEN_API_KEY=[[:space:]]*//; s/[[:space:]]*$//; s/^"|"$//g')
OPENCODE_API_KEY="$KEY" prime-agent --provider opencode --model deepseek-v4-flash-free -p "..."
```
Never echo the key. OpenRouter is **not recoverable** from Hermes (only a `secret_fingerprint` is stored; `.env`'s `OPENROUTER_API_KEY` is commented out) — ask the user for a fresh key in a file.

## 3. Windows IPython-kernel bootstrap fix (the real blocker)
Symptom: prime-agent launches and authenticates, but every tool call fails with `Failed to set up the Python kernel runtime ... uv.exe pip install ... failed with exit code 2`, or the agent reports "missing ipykernel". The model works; only its "hands" (file/shell) are dead.

**Why it fails on this machine:**
- Hermes's bundled `uv` builds the kernel venv from its *managed* Python; that venv's `python.exe` ignores its own `site-packages` when launched standalone (sys.path hijacked to Hermes's `hermes-agent/venv`), and `pyvenv.cfg` can go missing so `ipykernel` import fails in a fresh shell.
- The venv's own `pip` **cannot resolve DNS** (`files.pythonhosted.org -> getaddrinfo failed`) — but `uv` HAS working network.
- A `_virtualenv.pth` hijack redirects sys.path. Removing it helps, but the uv-managed venv still does not persist packages.
- `uv pip install --python <venv>` **redirects installs** when `VIRTUAL_ENV`/UV_* env vars are set.
- prime-agent's bootstrap looks for `kernel-venv/bin/python` (Linux path), not `Scripts/python.exe`.

**Verified-working fix (durable):**
1. Build the kernel venv from a **standalone Python 3.12** (persists correctly), NOT uv's managed Python:
   `C:\Users\PREM KUMAR\AppData\Local\Programs\Python\Python312\python.exe -m venv <VENV>`
2. Install deps with `uv` (working network), **with env redirects unset**, including the LOCAL runtime dir:
   ```bash
   unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_VENV_DIR PYTHONPATH CONDA_PREFIX
   uv pip install --python <VENV>/Scripts/python.exe \
     ipykernel nest-asyncio tyro requests httpx pyyaml "pandas<3" numpy dill \
     "<npm-global>/prime-agent/dist/prime-agent-runtime"
   ```
   - Use `pandas<3` — pandas 3.0.5 has a binary incompatibility (`ImportError: cannot import name 'ops' from 'pandas._libs'`) here.
   - `<npm-global>/prime-agent/dist/prime-agent-runtime` is the local wheel source (hatchling build).
3. Put the venv **off prime-agent's bootstrap path** (`~/.prime/agent/kernel-venv`) to avoid fights — use `~/.prime/kernel-venv`.
4. Tell prime-agent to skip its broken bootstrap:
   `export PRIME_AGENT_KERNEL_PYTHON="<VENV>/Scripts/python.exe"`
5. **Verify in a FRESH shell** (this is the real test — same-shell success is misleading):
   `bash -lc "'<VENV>/Scripts/python.exe' -c \"import ipykernel, rlm; print('OK')\""`
   prime-agent checks `hasIpykernel && hasPrimeAgentRuntime(rlm) && bootstrapVersionCurrent`.

A ready-to-run build script is in `scripts/build_prime_kernel.sh`. Full pitfall detail in `references/windows-kernel-bootstrap.md`. OpenCode Zen free-model ids + probe recipe in `references/opencode-zen-free-models.md`.

## 4. Run it
```bash
cd <project-dir>   # agent operates in CWD; use a disposable clone
export PRIME_AGENT_KERNEL_PYTHON="$USERPROFILE/.prime/kernel-venv/Scripts/python.exe"
OPENCODE_API_KEY="$KEY" prime-agent --provider opencode --model deepseek-v4-flash-free
```
An autonomous agent run can exceed 300s — launch with `terminal(background=true, notify_on_complete=true)` and read `prime_run*.log`, stripping control chars:
`cat prime_run.log | tr -cd '\11\12\15\40-\176'`

## Verification checklist
- [ ] `prime-agent --version` prints a version
- [ ] `--provider opencode --model <free>` returns a real model answer (not 401/402)
- [ ] FRESH-shell `import ipykernel, rlm` succeeds in the kernel venv
- [ ] A tool-using task (e.g. "list files in CWD") completes
