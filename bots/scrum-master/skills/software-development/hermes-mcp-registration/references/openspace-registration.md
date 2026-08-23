# Worked example: registering OpenSpace (HKUDS) with Hermes

Repo: https://github.com/HKUDS/OpenSpace  (MIT, requires Python >=3.12)
Goal: expose OpenSpace's MCP tools (`execute_task`, `search_skills`, `fix_skill`,
`upload_skill`, `cloud_auth_flow`, `cloud_browse_skills`) to Hermes on Windows.

## 1. Prep
- Python 3.12 lives at `C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe`
  (the active Hermes env is 3.11, which is too old).
- Clone sparse (skip ~50 MB `assets/`):
  ```bash
  git clone --filter=blob:none --sparse https://github.com/HKUDS/OpenSpace.git
  cd OpenSpace && git sparse-checkout set --no-cone '/*' '!/assets/'
  ```

## 2. Build the venv with the REAL interpreter (not Hermes pip)
```bash
C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m venv .venv
```
Then install deps with PYTHONPATH cleared. CRITICAL: the Hermes CLI shell exports
`PYTHONPATH=<hermes venv>`; if you run `.venv/Scripts/pip` through it, pip writes into
the HERMES venv and the OpenSpace venv stays empty (`ModuleNotFoundError: rpds`).

EXTRA GOTCHA: even `env -u PYTHONPATH` does NOT save you if you call the venv's OWN
launcher (`.venv/Scripts/pip.exe` or `.venv/Scripts/python.exe -m pip`) — those are
broken shims whose shebang still resolves pip to the Hermes venv (PyPI reports
`Location: …/hermes/hermes-agent/venv/…`, and the OpenSpace venv's site-packages stays
~40 pkgs). ALWAYS invoke the interpreter explicitly: `env -u PYTHONPATH .venv/Scripts/python.exe -m pip …`.
```bash
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install "litellm==1.82.6"   # heavy; pin <1.82.7 (supply-chain)
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install "setuptools>=68.0" wheel
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install -e . --no-deps
env -u PYTHONPATH .venv/Scripts/python.exe -m pip install "mcp>=1.0.0" "flask>=3.1.0" "pyautogui>=0.9.54" "bashlex>=0.18" "anthropic>=0.71.0" "pillow>=12.0.0" "websockets>=13.0" "numpy>=1.24.0"
```
Note: pip's backtracking resolver hangs for minutes on litellm's tree — pre-install
`litellm==1.82.6` first, then the editable install resolves fast.

## 3. The failing registration (DO NOT do this)
```bash
hermes mcp add openspace --command bash --args openspace-mcp-stdio.sh --connect-timeout 60 \
  --env OPENSPACE_WORKSPACE=C:/x OPENSPACE_HOST_SKILL_DIRS=C:/y OPENSPACE_CLOUD_MODE=off
```
Result in `logs/mcp_stderr.log`:
```
server.py: error: unrecognized arguments: --connect-timeout 60 --env OPENSPACE_WORKSPACE=...
hermes mcp test openspace  ->  ✗ Connection failed (13078ms): Connection closed
```
`--args` is greedy, so `--connect-timeout`/`--env` became argv passed to openspace-mcp.

## 4. The launcher wrapper (fixes Trap 1 + Trap 2)
File: `C:/Users/PREM KUMAR/dev/OpenSpace/openspace-mcp-stdio.sh`
```bash
#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/Scripts/python.exe"
unset PYTHONPATH                      # drop Hermes venv shadowing
cd "$SCRIPT_DIR" || exit 1
export OPENSPACE_WORKSPACE="$SCRIPT_DIR"
export OPENSPACE_HOST_SKILL_DIRS="C:/Users/PREM KUMAR/AppData/Local/hermes/skills"
export OPENSPACE_CLOUD_MODE="off"
exec "$VENV_PY" -m openspace.entrypoints.mcp.server "$@"
```

## 5. Register cleanly (args LAST, absolute path, no --env)
```bash
echo "y" | hermes mcp add openspace --command bash \
  --args "C:/Users/PREM KUMAR/dev/OpenSpace/openspace-mcp-stdio.sh"
```
This time the live connect test discovers all 6 tools and saves `6/6 tools enabled`.

## 6. Verify
```bash
hermes mcp test openspace
#   ✓ Connected (1594ms)
#   ✓ Tools discovered: 6
```
Deeper round-trip (proves the engine runs, not just lists):
```bash
env -u PYTHONPATH python - <<'PY'
import subprocess, json, time
p = subprocess.Popen(["bash","C:/Users/PREM KUMAR/dev/OpenSpace/openspace-mcp-stdio.sh"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    cwd="C:/Users/PREM KUMAR", bufsize=1,
    env={k:v for k,v in __import__('os').environ.items() if k!='PYTHONPATH'})
def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
def rm():
    while True:
        l=p.stdout.readline()
        if not l: return None
        l=l.strip()
        if l:
            try: return json.loads(l)
            except: pass
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}})
time.sleep(4); print("INIT:", bool(rm()))
send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_skills","arguments":{"query":"docker monitor","limit":5}}})
time.sleep(10); m=rm(); print("RESULT:", m["result"]["content"][0]["text"][:300] if m and "result" in m else str(m)[:200])
p.terminate()
PY
```

## 7. Copy host skills into Hermes
OpenSpace ships two SKILL.md files that teach Hermes when/how to delegate:
```bash
cp -r openspace/host_skills/delegate-task    "$APPDATA/../Local/hermes/skills/"
cp -r openspace/host_skills/skill-discovery  "$APPDATA/../Local/hermes/skills/"
```

## Notes / caveats
- `execute_task` needs an LLM. VERIFIED BLOCKER (2026-07-20): NO usable key exists on this
  box — `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, and the Nous `ANTHROPIC_AUTH_TOKEN` (in
  `~/AppData/Local/hermes/.env`) are all EMPTY/placeholder. So `search_skills` + local skill
  hub + Hermes discovery all work, but `execute_task`/skill-evolution cannot run a model until
  a key is supplied. The launcher already sets `OPENSPACE_MODEL=openrouter/tencent/hy3:free`
  and `OPENSPACE_LLM_API_BASE=https://inference-api.nousresearch.com/v1`, and reads the key
  from the Hermes `.env` (`ANTHROPIC_AUTH_TOKEN`) — drop a real key there (or set
  `OPENSPACE_LLM_API_KEY` + `OPENSPACE_LLM_API_BASE=https://openrouter.ai/api/v1` for
  OpenRouter) to enable execution.
- The "Internal Server Error" JSON-RPC line on EOF during connect tests is benign.
- `patch` tool CANNOT edit `~/.hermes/config.yaml` (security guard). Repair bad registrations
  via `hermes mcp remove <name>` + `hermes mcp add`, never via the `patch` tool.
