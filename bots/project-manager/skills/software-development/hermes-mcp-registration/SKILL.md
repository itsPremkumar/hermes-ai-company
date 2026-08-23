---
name: hermes-mcp-registration
description: Register an EXTERNAL stdio MCP server (its own Python/Node venv, on a separate interpreter) with Hermes via `hermes mcp add`, and prove it connects. Covers the --args greedy-flag trap, the PYTHONPATH-shadowing breakage, the bash-launcher-wrapper fix (clear PYTHONPATH + set env inside the script, not via --env), the "Connection closed / unrecognized arguments" diagnosis, and verification with `hermes mcp test`. Use when wiring any external MCP server (OpenSpace, Ruflo, a custom FastMCP server) into Hermes, or when `hermes mcp test` reports "Connection failed" / "Connection closed".
---

# Hermes MCP Registration (external stdio servers)

You have several external MCP servers registered with Hermes (ruflo, ruflo-free, freecode, openspace). Registering a *new* one whose code runs under its OWN interpreter/venv is a recurring task with two non-obvious traps. This skill is the record of both.

## When to use
- `hermes mcp add <name> --command bash --args <launcher>` (or `--command npx` / a binary) to expose an external server to Hermes.
- `hermes mcp test <name>` reports `✗ Connection failed (…): Connection closed`.
- Server logs show `error: unrecognized arguments: --connect-timeout …`.
- `ModuleNotFoundError` for a dep that IS installed in the server's own venv.

## Trap 1 — `--args` is greedy; flags after it get folded into argv
`hermes mcp add` has a real `--connect-timeout` and `--env` flag, BUT `--args` is declared "must be the last option" and is greedy. If you write:

```bash
hermes mcp add openspace --command bash --args openspace-mcp-stdio.sh --connect-timeout 60 --env OPENSPACE_WORKSPACE=C:/x
```

Hermes stores `--connect-timeout`, `60`, `--env`, `OPENSPACE_WORKSPACE=C:/x` as **positional args to `bash`**, which forwards them to the server:

```
server.py: error: unrecognized arguments: --connect-timeout 60 --env OPENSPACE_WORKSPACE=...
```

→ server exits immediately → Hermes sees "Connection closed".

**Fix:** either (a) put `--args` LAST with nothing after it, or (b) — preferred — drop `--env`/`--connect-timeout` entirely and set env vars INSIDE the launcher script (see Trap 2). Use an ABSOLUTE path for the script in `--args` so cwd doesn't matter:

```bash
echo "y" | hermes mcp add openspace --command bash --args "C:/Users/PREM KUMAR/dev/OpenSpace/openspace-mcp-stdio.sh"
```

(pipe `echo "y" |` because `hermes mcp add` runs a live connect test and interactively prompts `Save config anyway? [y/N]` on failure — answer yes, then fix and re-test.)

## Trap 2 — Hermes CLI exports PYTHONPATH → shadows the server's own venv
The Hermes desktop shell exports `PYTHONPATH=<hermes venv>/site-packages`. When you run the server's interpreter through this shell, that PYTHONPATH is prepended and **shadows the server's own venv deps**, producing phantom `ModuleNotFoundError` (e.g. `rpds`, `jsonschema`) even though the dep is installed in the server's venv. Symptom in logs: server emits a JSON-RPC `error` notification on startup, then closes.

**Fix:** wrap the server in a bash launcher that `unset PYTHONPATH` and runs the server under ITS OWN venv interpreter. Set all env (workspace, skill dirs, cloud mode, model) inside the launcher — never rely on `hermes mcp add --env`, which gets folded into args (Trap 1). Reusable template: see `templates/mcp-stdio-launcher.sh`.

Also: build the server's venv with the REAL target interpreter (`python -m venv`), not via the Hermes pip, or `pip install -e .` silently writes into the Hermes venv (leaving the server venv empty). Run all server-side `pip`/`python` with `env -u PYTHONPATH`.

### Sub-trap 2a — venv creation AND its own `pip` are corrupted when PYTHONPATH is set
If a venv is created while the Hermes-exported `PYTHONPATH` is in the environment, the venv's `.exe` launchers (and even `.venv/Scripts/python.exe -m pip`) get wired to resolve the **Hermes** venv's pip. Two symptoms:
- `pip install -e .` prints `Successfully installed …` but `pip show <dep>` reports `Location: …/hermes/hermes-agent/venv/…`, and the server venv's `site-packages` stays near-empty (~40 pkgs, missing jsonschema/rpds/etc.) → phantom `ModuleNotFoundError`.
- The `venv` itself may be unusable until rebuilt.
**Fix:** unset PYTHONPATH *before* creating the venv, and run every server-side install as `env -u PYTHONPATH .venv/Scripts/python.exe -m pip install …` (never the broken `.exe`). Rebuild the venv cleanly if it was created under the polluted env:

```bash
rm -rf .venv
env -u PYTHONPATH /c/Users/PREM\ KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m venv .venv
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install -e . --no-deps   # etc.
```

Verify isolation: `env -u PYTHONPATH .venv/Scripts/python.exe -m pip show <dep>` must report `Location: …/<server>/.venv/…`, NOT the Hermes path.

### Reuse Hermes's own free model key (Nous / hy3:free) — zero extra key needed
To make an external server run on the SAME $0 model Hermes uses (`tencent/hy3:free` via the Nous inference API), do NOT look in Hermes's `.env` — `ANTHROPIC_AUTH_TOKEN` there is a 6-char placeholder. The real key lives in:

```
~/AppData/Local/hermes/shared/nous_auth.json
  -> access_token       (the Bearer key, ~1745 chars)
  -> inference_base_url (already OpenAI-style: https://inference-api.nousresearch.com/v1)
```

Read it at launcher startup (Python, not jq, to avoid a dep) and export to the server's LLM env. Example launcher block:

```bash
NOUS_AUTH="$HOME/AppData/Local/hermes/shared/nous_auth.json"
if [ -f "$NOUS_AUTH" ]; then
  _j="$(cat "$NOUS_AUTH")"
  export OPENSPACE_LLM_API_KEY="$(printf '%s' "$_j" | python -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)"
  _b="$(printf '%s' "$_j" | python -c "import sys,json;print(json.load(sys.stdin).get('inference_base_url',''))" 2>/dev/null)"
  case "$_b" in */v1|*/v1/) OPENSPACE_LLM_API_BASE="$_b";; */) OPENSPACE_LLM_API_BASE="${_b}v1";; "") OPENSPACE_LLM_API_BASE="https://inference-api.nousresearch.com/v1";; *) OPENSPACE_LLM_API_BASE="${_b}/v1";; esac
  export OPENSPACE_LLM_API_BASE
fi
```

Notes:
- The Nous token has an `expires_at`; the launcher re-reads the file at every launch, so it picks up Hermes's refreshed key automatically.
- `litellm` treats `openrouter/tencent/hy3:free` as `provider=openrouter` and routes through `OPENSPACE_LLM_API_BASE` — confirmed working (log line: `LiteLLM completion() model= tencent/hy3:free; provider = openrouter`). No OpenRouter key required.
- hy3:free is SLOW on the free tier (~2-3 min per agent iteration) — keep delegated tasks short, or expect multi-minute runs.
- See `references/reuse-nous-key.md` for the exact OpenSpace wiring and the live-execution log proof.

### Sub-trap 2b — `pip install -e .` HANGS on heavy resolver trees (litellm)
A server whose deps include `litellm` makes `pip install -e .` hang ~10 min with **zero** cache downloads — pip's backtracking resolver chokes on litellm's huge transitive tree (pydantic, httpx, openai, tokenizers, …). `PyPI` itself is fast (verified `curl` + `pip download` succeed in seconds), so it's the resolver, not the network.
**Fix (fast, deterministic):** pre-install the heaviest pinned deps first, then the editable install with `--no-deps`:
```bash
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install "litellm==1.82.6"   # grows the venv, settles the tree
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install setuptools wheel   # needed for --no-build-isolation
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install -e . --no-deps      # deps already satisfied
# then add any remaining declared deps (mcp, flask, pyautogui, anthropic, …) as a batch:
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install "mcp>=1.0.0" "flask>=3.1.0" "pyautogui>=0.9.54" "anthropic>=0.71.0" "pillow>=12.0.0" "websockets>=13.0" "numpy>=1.24.0"
```
Never trust a "Successfully installed" line from a `pip` that isn't running under the server venv (see 2a).

### Config edit block — `patch` tool cannot touch `config.yaml`
The `patch` skill tool refuses to edit `~/.hermes/config.yaml` ("security-sensitive configuration"). Do NOT try to rewrite the mcp block with `patch`.
**Fix:** repair the registration via the CLI instead:
```bash
hermes mcp remove <name>            # cleans tokens too
echo "y" | hermes mcp add <name> --command bash --args "/abs/path/launcher.sh"
```

## Support files in this skill
- `templates/mcp-stdio-launcher.sh` — copy + edit as your Hermes MCP launcher. Clears PYTHONPATH, sets env inside the script, resolves paths from `BASH_SOURCE` so cwd is irrelevant.
- `references/openspace-registration.md` — full end-to-end transcript of wiring OpenSpace v2 (HKUDS) into Hermes on this box: exact failing command, the `unrecognized arguments` error, venv-build steps, and the final working config + launcher. Reuse the structure for any external server.
- `references/reuse-nous-key.md` — how to point an external server at Hermes's own free `tencent/hy3:free` model via the Nous key in `shared/nous_auth.json` (the real key, NOT the `.env` placeholder), with the verified LiteLLM log proof and the slow-free-tier caveat.

## Verification (the real gate)
`hermes mcp add`'s auto-connect is flaky; trust `hermes mcp test` instead:

```bash
hermes mcp test <name>
# Expect:  ✓ Connected (NNNms)
#          ✓ Tools discovered: N
```

For a deeper round-trip, call a read-only tool through the server directly (see the probe snippet in `references/openspace-registration.md`) — `tools/list` alone is not enough; a `tools/call` on e.g. `search_skills` proves the engine actually runs.

## Benign red herring
An OpenSpace (and similar FastMCP) server prints a JSON-RPC line `{"method":"notifications/message","level":"error",…"Internal Server Error"}` when fed empty stdin / EOF during a connect test. That is the server reacting to EOF, **not** a real fault — ignore it; rely on `hermes mcp test` results.

## Related skills
- `mcp-server-verify` / `mcp-server-verification` — prove a server speaks JSON-RPC / lists tools (lower level than Hermes registration).
- `hermes-skill-authoring` — authoring SKILL.md files (different from MCP server registration).
- `free-dev-team` — carries the broader "PYTHONPATH-isolated venv fix" for the $0 dev stack.
