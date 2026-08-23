---
name: install-run-cli-agent
description: Install/run GitHub CLI agents (prime-agent) on Windows.
---

# Install & Run a Third-Party CLI Agent (incl. Windows)

When the user wants to install and run an open-source agent/CLI from GitHub that ships installers for macOS/Linux only, follow this class-level workflow. Deliverable: a *running, verified* agent.

## 1. Inspect repo before installing
- Read README + `install.sh` (raw: `https://raw.githubusercontent.com/<owner>/<repo>/main/install.sh`).
- List release assets: `curl -fsSL "https://api.github.com/repos/<owner>/<repo>/releases/latest"` → `assets[].browser_download_url`, and `latest.json` (sha256 manifest).
- If `npm view <pkg>` → 404, the package ships as versioned `.tgz` tarballs (not on public npm).

## 2. Download + verify SHA256
```bash
curl -fsSL -o latest.json "<release>/latest.json"
curl -fsSL -o pkg-<v>.tgz "<release>/pkg-<v>.tgz"
sha256sum pkg-<v>.tgz   # MUST match sha256 in latest.json
```
Never skip the checksum — only integrity guarantee for a direct tarball.

## 3. Windows compatibility probe (before `npm i -g`)
```bash
tar -xzf pkg-<v>.tgz -C . package/package.json
node -e "const p=require('./package/package.json'); console.log(p.os, p.cpu, p.engines, p.bin, p.scripts)"
```
- Safe if `os` unset and `engines.node` <= your Node (e.g. `>=22.8.0`).
- Inspect `postinstall.cjs` / `dist/postinstall.js`: skip if it only acts when explicit env vars set (e.g. `PRIME_AGENT_BOOTSTRAP_KERNEL_ON_INSTALL`). Avoid triggering OS-shell bootstrap on Windows.
- Bin shebang should be `#!/usr/bin/env node`.

## 4. Install + verify
```bash
npm install -g ./pkg-<v>.tgz
<cmd> --version      # proves it boots on Windows
<cmd> --help
```

## 5. Reuse Hermes's stored provider keys (don't re-ask)
Mask ALL values; never print secrets.
- Scan `$USERPROFILE/AppData/Local/hermes/.env` for **uncommented** `KEY=...` lines (strip leading spaces, drop `#` lines).
- Also inspect `$USERPROFILE/AppData/Local/hermes/auth.json` `credential_pool` — entries stored only as `secret_fingerprint` (no plaintext) are NOT usable (e.g. OpenRouter).
- Cross-reference active keys against the tool's supported providers: `grep -rhoiE '[A-Z0-9_]+_API_KEY' <tool>/dist/bundle/*.js`.
- Launch with the key in an env var, read from `.env` at runtime so it never hits argv/logs:
```bash
KEY=$(grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" | grep -E '^\s*<NAME>=' | tail -1 | sed -E 's/^[[:space:]]*<NAME>=[[:space:]]*//; s/[[:space:]]*$//; s/^"|"$//g')
<CMD> --provider <p> -p "..."   # with <NAME>=$KEY exported in env
```

## 6. Force a FREE model to dodge 401 on paid default
Agents often default to a paid model → `401 No payment method`. Enumerate free models:
```bash
curl -s -H "Authorization: Bearer $KEY" https://<provider>/v1/models | grep -i free
```
Then run with `--model <free-id>`. (OpenCode Zen working free models: `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `laguna-s-2.1-free`, `longcat-2.0-free`; `ling-3.0-flash-free`/`north-mini-code-free` error. See `references/opencode-zen-models.md`.)

## 7. Bootstrap the agent's tool kernel (prime-agent class)
If the agent reports "Failed to set up the Python kernel runtime" / `uv pip install` failure:
```bash
export PATH="$USERPROFILE/AppData/Local/hermes/bin:$PATH"   # uv lives here
VENV="$USERPROFILE/.prime/agent/kernel-venv"
uv venv "$VENV"                      # --clear if it already exists partially
uv pip install --python "$VENV/Scripts/python.exe" ipykernel nest-asyncio tyro "<npm-pkg>/dist/prime-agent-runtime"
"$VENV/Scripts/python.exe" -c "import ipykernel, nest_asyncio, tyro, rlm; print('ok')"
```
prime-agent auto-detects this venv at `~/.prime/agent/kernel-venv`.

## References
- `references/opencode-zen-models.md` — verified free/paid model ids + endpoint notes from the prime-agent session.
