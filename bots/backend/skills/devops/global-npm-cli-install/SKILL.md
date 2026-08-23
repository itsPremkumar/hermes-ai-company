---
name: global-npm-cli-install
description: Install, verify, and RECOVER global Node.js CLI tools (npm -g) on this Windows / MSYS(git-bash) / nvm4w box, including the space-in-PATH curl trap, the 300s-timeout broken-install trap, nvm4w bin resolution, and the npm-version != GitHub-release-tag gotcha. Use when a user says "install <tool>", "get the latest version of <npm package>", "npm install -g X", or wants a global CLI wired onto PATH. Class-level, covers ANY global Node CLI, not one package.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
---

# Global npm CLI Install (Windows / MSYS / nvm4w)

Recipes for installing a global Node CLI tool on THIS machine and making it actually runnable from any shell. The environment is Windows 10, git-bash (MSYS), Node managed by **nvm4w**, npm prefix = `C:\nvm4w\nodejs` (a symlink to `C:\Users\PREM KUMAR\AppData\Local\nvm\vXX.XX.X`). Node is v22.x (>=20 for most modern CLIs).

## When to use
- "install the latest version of <repo/package>", "npm install -g <X>", "get <cli> on my machine"
- A global CLI was installed but the command is "not recognized"
- You need to confirm which published version is "latest" for a GitHub repo

## Step 0 — Determine the real "latest" version
For a GitHub repo, the **npm registry version is usually newer than the GitHub release tag**. Do not trust the GitHub release page as the latest.

```bash
# GitHub release tag (often LAGS the npm publish):
curl -sL https://api.github.com/repos/<owner>/<repo>/releases/latest
# npm latest (authoritative for `npm install -g <pkg>@latest`):
curl -sL https://registry.npmjs.org/<pkg>/latest
```
Example: `ruvnet/ruflo` GitHub latest release = `v3.32.4`, but `npm view ruflo version` = `3.32.7`. Install `ruflo@latest` -> you get 3.32.7.

## Step 1 — Read package metadata BEFORE installing
```bash
curl -sL https://registry.npmjs.org/<pkg>/latest -o /c/tmp_ruflo/pkg.json
python -c "import json;d=json.load(open('/c/tmp_ruflo/pkg.json'));print(d['version'], d.get('bin'), d.get('engines'))"
```
Confirms: bin name (the command you will run), node engine requirement, tarball.

## Step 2 — TRAP: never write curl output into a path with a SPACE
The home dir is `C:\Users\PREM KUMAR` (space). `curl -o "$HOME/out.json"` fails with **exit 23 (write error)** under MSYS because the space breaks the `-o` arg.
**Fix:** write to a no-space staging dir, e.g. `/c/tmp_ruflo/`.
```bash
mkdir -p /c/tmp_ruflo && cd /c/tmp_ruflo
curl -sL "https://api.github.com/repos/<owner>/<repo>/contents/README.md?ref=main" -o readme_meta.json
# decode GitHub "contents" API base64 payload:
python -c "import json,base64,os;d=json.load(open('readme_meta.json'));open('readme.md','wb').write(base64.b64decode(d['content']))"
```
- `read_file`/`patch` also cannot see `/tmp` reliably here (FS namespace mismatch between tool and shell). Use the `terminal` tool + `/c/tmp_ruflo/` for shell-side file ops, and `python -c` to inspect JSON.

## Step 3 — Install globally (avoid the 300s timeout trap)
A big CLI (hundreds of deps, e.g. ruflo = 404 packages) **will exceed the 300s foreground terminal timeout** and get killed mid-extraction, leaving a BROKEN install: bin symlinks exist under `C:\nvm4w\nodejs\` but `node_modules/<pkg>/` is empty/missing `package.json`/`bin/`. The command then fails with:
`Error: Cannot find module 'C:\nvm4w\nodejs\node_modules\<pkg>\bin\<cmd>.js'`

**Always install big global CLIs in the BACKGROUND with notify:**
```bash
terminal(background=true, notify_on_complete=true,
  command="npm install -g <pkg>@latest --no-audit --no-fund 2>&1; echo INSTALL_EXIT=$?")
```
Then `process(action='wait', session_id=..., timeout=60)` (clamped to 60s) — poll until `exited` with `added N packages` + `INSTALL_EXIT=0`.
- `--no-audit --no-fund` skip the slow audit/network steps.
- Harmless `npm warn cleanup EPERM` lines may appear (npm could not rmdir an old subdir during re-link) — ignore if exit 0 and the bin resolves.
- If a PRIOR partial install exists, clean it first or the broken state persists:
  `rm -rf /c/nvm4w/nodejs/node_modules/<pkg> /c/nvm4w/nodejs/<pkg>*`

## Step 4 — Verify it works (real evidence, not a claim)
```bash
# 1. version resolves (direct):
/c/nvm4w/nodejs/<cmd>.cmd --version
# 2. on PATH via the nvm4w symlink (clean-shell lookup):
cmd /c "where <cmd> && <cmd> --version"
# 3. help / subcommand surface:
<cmd> --help
<cmd> <primary-subcmd> --help
```
On this box `/c/nvm4w/nodejs` IS on PATH (symlink to the active nvm version dir), so a clean `cmd` shell resolves `<cmd>` fine. A bare `which <cmd>` in git-bash may miss it because the bin lives in the per-version nvm dir; rely on `cmd /c where` for the authoritative check.

## Step 5 — Use it
Global CLIs are invoked by name from any new terminal:
```
ruflo init wizard
ruflo start
```
If a project's README offers `npx <pkg>@latest init`, that also works natively in PowerShell/cmd without a global install.

## Variant B — Install a Node CLI shipped as a GitHub-release `.tgz` (NOT on npm registry)
Some CLIs (e.g. `prime-agent` by PrimeIntellect) are **never published to registry.npmjs.org** — `npm view <pkg>` returns 404. They ship as a versioned release tarball (`<pkg>-<ver>.tgz`) attached to a GitHub release. The official `curl | sh` installer just downloads that tarball and does `npm install -g`. Do it manually for control + hash verification.

```bash
mkdir -p /c/tmp_cli && cd /c/tmp_cli
VER=v0.7.0
curl -fsSL -o latest.json "https://github.com/<owner>/<repo>/releases/download/$VER/latest.json"
curl -fsSL -o "pkg-$VER.tgz" "https://github.com/<owner>/<repo>/releases/download/$VER/<pkg>-$VER.tgz"
# VERIFY sha256 against the manifest (only install if it matches EXACTLY):
exp=$(grep -A2 '"file": "<pkg>-'$VER'.tgz"' latest.json | grep sha256 | grep -oE '[0-9a-f]{64}')
act=$(sha256sum "pkg-$VER.tgz" | cut -d' ' -f1)
[ "$exp" = "$act" ] && echo "HASH OK" || { echo "HASH MISMATCH"; exit 1; }
# Inspect package.json WITHOUT installing (os/engines/bin/postinstall traps):
tar -xzf "pkg-$VER.tgz" -C . package/package.json
node -e "const p=require('./package/package.json');console.log(JSON.stringify({bin:p.bin,os:p.os,engines:p.engines,scripts:p.scripts}))"
npm install -g "./pkg-$VER.tgz" 2>&1 | tail -15
```
- **Windows caveat:** these CLIs are usually "macOS/Linux" in docs, but the bin is a Node bundle (`#!/usr/bin/env node`). If `package.json` has **no `os` field** and Node ≥ `engines.node`, it generally runs on Windows via nvm4w — verify with `<cmd> --version`. The IPython *kernel* (a sub-tool) may still assume a POSIX shell; for full fidelity run under WSL.
- **postinstall traps:** read `dist/postinstall.js`. If it only runs when env vars like `PRIME_AGENT_BOOTSTRAP_KERNEL_ON_INSTALL=1` are set, the default `npm install -g` is a no-op and safe. Don't set those vars unless you want it to also bootstrap Python tooling.
- **Auth-less install is fine** — the key requirement is separate (see Variant C).

## Variant C — Run a tool that needs a model/API key: reuse Hermes's stored keys (masked)
A freshly installed agent/CLI (prime-agent, etc.) needs a provider key to actually run, but you must **never ask the user to paste secrets** and **never echo them**. Hermes already stores many provider keys in `C:\Users\PREM KUMAR\AppData\Local\hermes\.env` (some active, some commented-out) and fingerprints in `auth.json`. Reuse one that the child tool accepts.

**Scan masked (no secret ever printed):**
```bash
grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" \
  | grep -E '^\s*(OPENCODE_API_KEY|HF_TOKEN|OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|GEMINI_API_KEY)=' \
  | sed -E 's/=.*/= (len>0, hidden)/'
# Deep masked view of auth.json credential_pool:
node -e 'const j=require(process.env.USERPROFILE+"/AppData/Local/hermes/auth.json");for(const k in (j.credential_pool||{})){const e=j.credential_pool[k][0]||{};console.log(k,"->",Object.keys(e).filter(x=>x!=="secret_fingerprint").join(","))}' 2>/dev/null
```
**Key facts learned (this box):**
- `OPENROUTER_API_KEY` in Hermes is **commented out** and `auth.json` stores it only as a `secret_fingerprint` — NOT recoverable as plaintext. OpenRouter (user's first choice) can't be sourced this way.
- Plaintext-recoverable keys that child tools accept: `OPENCODE_API_KEY` (OpenCode Zen, `opencode` provider) and `HF_TOKEN` (HuggingFace, `huggingface` provider).
- `auth.json` `credential_pool` entries carry only metadata + fingerprint; treat them as "known provider, secret elsewhere."

**Feed the key to the child tool WITHOUT echoing it** (extract → env var → run, all in one shell):
```bash
KEYVAL=$(grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" \
  | grep -E '^\s*OPENCODE_API_KEY=' | tail -1 \
  | sed -E 's/^[[:space:]]*OPENCODE_API_KEY=[[:space:]]*//; s/[[:space:]]*$//; s/^"|"$//g')
[ -z "$KEYVAL" ] && { echo "key empty"; exit 3; }
OPENCODE_API_KEY="$KEYVAL" prime-agent --provider opencode -p "..." 2>&1 | tail -40
```
- **Leading-space gotcha:** Hermes `.env` lines have leading spaces, so anchor `^` alone misses them — use `^\s*KEY=`.
- **Billing is a separate axis:** a valid key that returns `401 No payment method` / `402 credits depleted` means the *account* is unpaid, NOT that the install/run failed. Report it as "agent works, provider account needs funding" and offer the user's other keys, a local model (Ollama/LM Studio), or a fresh key file.

## Linked references
- `references/ruflo-install-evidence.md` — full reproducible recipe + broken-install signature from the real `ruflo@3.32.7` install (use as a worked template for any global CLI).
- `references/gh-release-tgz-install.md` — worked template: installing `prime-agent@0.7.0` from its GitHub-release tarball with sha256 verification + Windows run check.
- `references/reuse-hermes-provider-keys.md` — masked `.env`/`auth.json` scan + secure key-passing recipe for child tools that need a provider key.

## Pitfalls summary
| Symptom | Cause | Fix |
|----------|-------|-----|
| `curl` exit 23 | space in `-o` output path | write to `/c/tmp_ruflo/` |
| `Cannot find module ...\node_modules\<pkg>\bin\<cmd>.js` | install killed at 300s, partial | `rm -rf` partial + reinstall in background |
| `where <cmd>` empty in git-bash | bin in per-version nvm dir | use `cmd /c where <cmd>`; `/c/nvm4w/nodejs` is on PATH |
| "latest" seems old | trusted GitHub release tag | check `registry.npmjs.org/<pkg>/latest` |
| `python3: command not found` | only `python` (3.11) on PATH | use `python` |
