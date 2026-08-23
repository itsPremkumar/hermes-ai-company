# Parallel bot-mode profile dispatch — full recipe

Used to build multi-agent projects where each agent is produced by a real
Hermes bot-mode profile (architect, backend, devops, frontend, qa-engineer, ...).

## 1. Write one brief per bot
Put each task brief in `.prompts/<bot>.txt`. Keep briefs tight: state the deliverable
files (absolute paths), the shared-package import line, hard constraints
(zero API key, stdlib only), and require the bot to RUN its own test with REAL output
and report it back. Forbid context-blowups (e.g. "do NOT run git log -p on the whole
repo").

## 2. Launch in parallel (detached)
```bash
cd /c/one/project
nohup hermes chat -p architect -Q --in /c/one/project -q "$(cat .prompts/architect.txt)" > .prompts/architect.out 2>&1 &
nohup hermes chat -p backend   -Q --in /c/one/project -q "$(cat .prompts/backend.txt)"   > .prompts/backend.out   2>&1 &
# ... one per profile
echo "all launched"
```

## 3. Poll the real children
```bash
# WRONG: the nohup wrapper PID exits immediately
# RIGHT: count the actual hermes chat children
ps -ef | grep "hermes.exe chat -p" | grep -v grep | wc -l
```
When it reaches 0, check delivery:
```bash
for d in agents/*/ ; do echo "$d: $(ls $d 2>/dev/null | tr '\n' ' ')"; done
ls tests/
```

## 4. The sys.path fix (apply to EVERY agent module)
Tests imported from the repo root pass, but `python agents/<name>/agent.py` fails with
`ModuleNotFoundError`. Insert repo root into sys.path at the top of each agent:

```python
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # agents/<name>/agent.py -> root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from prem_agents import web_search, web_extract, save_state, load_state, ok  # noqa: E402
```
(For a `tools/<name>/agent.py` layout the root is `parent.parent`.)

## 5. Deliverable checklist (per agent/tool)
- [ ] `agents/<name>/agent.py` with `def main():` + `if __name__ == "__main__": main()`
- [ ] `agents/<name>/README.md`
- [ ] `tests/test_<name>.py` that RUNS FOR REAL and asserts observable behavior
- [ ] Passes both `python tests/test_<name>.py` AND `python agents/<name>/agent.py --help/--demo`
- [ ] No `ModuleNotFoundError` on direct CLI invocation
- [ ] No stray runtime state (`state/`, `__pycache__/`, preview dirs) left in tree

## 6. Common failure modes observed
- A bot "stalled" with only a tiny `.out` file = it blew context on a giant
  environment probe (e.g. full `git diff`). Re-dispatch with a tighter brief that
  forbids large dumps.
- A bot delivered `agent.py` but NO test = ran out of room. Write the missing test
  yourself (Chief-of-Staff QA pass) rather than re-dispatching.
- Windows path gotcha: native `python.exe` does NOT understand MSYS `/tmp/...`
  paths — pass `C:/one/...` style native paths in agent CLIs and tests.
- A repo created via `gh repo create` may have NO `origin` remote locally even
  though the GitHub repo exists. `git remote add origin <url>` before push.
