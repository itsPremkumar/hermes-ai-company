---
name: free-dev-team
description: Assemble and operate a complete $0 software-engineering team — Hermes (orchestrator, free model) + Ruflo (multi-agent swarm, Ollama/OpenRouter-free, COMPULSORY for builds) + OpenHands (coder, free model) + gstack (QA/security methodology, reference) + ponytail (lean-code discipline). Use when the user wants to build production software with NO paid keys, when they say "free models only", "free AI", "build a dev team", "agentic coding team", "use Ruflo / the swarm / multiple agents", or reference gstack/ponytail/OpenHands/Ruflo/Claude Code. Covers install, the PYTHONPATH-isolated venv fix, Ruflo provider/key verification, gstack partial-port workaround, ponytail discipline injection, and the review loop.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Free Dev Team — complete $0 software-engineering stack

Build production-ready software with **no paid keys**. Four parts, all free / open-source:

| Role | Tool | Free model | How it runs |
|---|---|---|---|
| CEO / Orchestrator | **Hermes** (this agent) | `tencent/hy3:free` (OpenRouter) | native |
| Multi-agent swarm | **Ruflo** (v3.32.7, node) | local **Ollama** (`llama3.2:1b`) OR OpenRouter `:free` — **Anthropic EXCLUDED** | `ruflo swarm coordinate --agents N` |
| Coding agent | **OpenHands** | OpenRouter free coder (e.g. `qwen/qwen2.5-coder-32b-instruct:free`) | isolated venv (py3.12) |
| QA / Security methodology | **gstack** (reference library) | n/a (instructions) | Hermes reads SKILL.md bodies |
| Lean-code discipline | **ponytail** (`AGENTS.md`) | n/a (instructions) | Hermes injects into every coding prompt |

**Ruflo is COMPULSORY for builds** (user directive 2026-07-18: "use the software team / Ruflo
compulsory with its multiple agents") — but understand what Ruflo ACTUALLY does here, or you
will misreport the build (this happened live 2026-07-18):

- Ruflo is a **coordination/topology harness**, NOT an executor. `ruflo swarm coordinate`,
  `ruflo agent spawn`, `ruflo hive-mind init/spawn` create the topology and QUEUE tasks, but
  **do NOT execute agent work** in this stack. Confirmed: `hive-mind status` → "No workers in
  hive"; `hive-mind task` → stays "pending dispatch". The only documented execution path is
  `hive-mind spawn --claude` = **Claude Code** (paid Anthropic, EXCLUDED by mandate).
- So: **Ruflo cannot self-execute on a free model.** Do not claim "Ruflo built X". The real
  multi-agent executor in this $0 stack is **`delegate_task` subagents on `tencent/hy3:free`**
  (Hermes = Queen/orchestrator/verifier). That IS the user's "multiple agents" team — just not
  Ruflo-powered.
- **Ruflo exec unlock — VERIFIED recon (2026-07-19), OLD CLAIM WAS WRONG:**
  Earlier text claimed Ruflo calls the Anthropic API *shape* and a LiteLLM proxy
  unlocks free execution. **That is FALSE for v3.32.7.** Reading
  `src/mcp-bridge/index.js` proves Ruflo executes agents by **shelling the
  `claude` BINARY** (`spawn("claude",["mcp","serve"])`, line 258; `claude-code`
  group env-gated by `MCP_GROUP_CLAUDE_CODE=true`). It is a binary shell-out, NOT
  an Anthropic API call. So the real unlock is an **OSS `claude`-compatible
  binary on PATH** — user's instinct (OpenCode) was RIGHT; LiteLLM-API theory
  was wrong. VERIFY by reading the exec source before claiming which proxy unlocks.
  - OpenCode shim built: `bin/claude-free.sh` maps `claude mcp serve` →
    `opencode serve`; `bin/shim/claude` PATH-shim. Verified the translation works.
  - OpenCode CHAT works on FREE model `opencode/hy3-free` (launched TUI, took prompts).
  - **BLOCKER (unresolved):** `opencode serve` (the MCP-server mode Ruflo needs)
    is a **STUB** in v1.1.35 — prints help, exits code 1, never binds a port.
    So Ruflo's claude-code group has no MCP server to connect to.
  - **Honest status:** Ruflo = coordinator/memory/MCP provider WORKING (327 tools,
    memory round-trip proven). Ruflo autonomous EXEC on free model STILL BLOCKED
    (now by "OpenCode serve is a stub", not "paid key"). OpenCode as *separate*
    free coding agent (chat) WORKING.
  - To finish: (A) find another OSS `claude`-compatible MCP server that serves;
    (B) use OpenCode as a Hermes `delegate_task` alternative (separate win);
    (C) wait/patch OpenCode `serve` upstream. Do NOT claim "Ruflo unlocked".
  - **(D) THE WORKING UNLOCK — built + verified 2026-07-19:** Ruflo's `claude-code`
    group is DORMANT (set `MCP_GROUP_CLAUDE_CODE=true`, prepend `bin/shim/claude`
    to PATH → Ruflo still never spawns `claude`; `tools/list` shows 0 claude
    tools, blind `claude__Write` → "Tool not found"). So instead of injecting
    into Ruflo, build `freecode` — a standalone stdio MCP server implementing
    Claude-Code-compatible tools (Write/Read/Edit/Bash/Glob/Grep) via LOCAL
    exec + optional Ollama, $0, no Anthropic key — and register it in Hermes
    as its own MCP server (`hermes mcp add freecode --command bash --args
    bin/freecode-stdio.sh`). Proven: `Write` tool wrote a real file on disk.
    This gives the agent a FREE local coding backend directly, parallel to
    Ruflo (coordination/memory) and HY3-free subagents. Full recipe +
    mcp-SDK gotchas + the ONLY reliable verify method in `references/freecode-gateway.md`.
  Full repro recipe in `references/ruflo-exec-unlock-verified.md`.
- **Ruflo's MCP server DOES connect to Hermes (verified working 2026-07-19) — but only via
  stdio + a stdout-stripping wrapper.** The recipe that works:
  1. Ruflo prints an `[INFO] Starting in stdio mode` line to **stdout** before the JSON-RPC
     stream. Hermes's Python MCP client desyncs on it → "Connection closed".
  2. A naive `grep` pipe to strip it is **block-buffered** → Hermes times out (40s) waiting.
  3. FIX: wrapper `bin/ruflo-mcp-stdio.sh` = `ruflo mcp start | grep --line-buffered -vE '...INFO...'`.
  4. Register: `hermes mcp add ruflo --command bash --args bin/ruflo-mcp-stdio.sh --connect-timeout 60`
     → `hermes mcp test ruflo` (Connected, 327 tools) → `hermes tools enable 'ruflo:*'`.
  5. Live proof: a client using the wrapper called `memory_store` (success) + `memory_search`
     (round-trip) — real data, not just discovery.
  See `references/ruflo-reality.md` for the full recipe + the traps that DON'T work.
- **Traps that do NOT work (don't retry):** `npx ruflo@latest` (hangs on download — use the
  local `ruflo` v3.32.7 binary); `ruflo mcp start -t http` (prints "Running" but never binds
  the port on Windows/MSYS — `/rpc` + `/health` return empty); plain `grep` without
  `--line-buffered` (40s timeout). The product's own MCP (e.g. SAMM `samm/mcp_server.py`) also
  works for Hermes↔product, but Ruflo's is the one for swarm/memory coordination tools.
- Honest framing for the user: "Ruflo = compulsory coordinator (topology, hive-mind, consensus,
  task queue). Agent brains run on HY3-free via our subagent team." Document this in the repo
  (e.g. AGENT_TEAM.md / RUFLO_STATUS.md) so you never imply Ruflo executed the work.

Build pattern: init Ruflo in repo (`ruflo init`) for the topology artifact, configure a zero-cost
backend (so the config is "real"), then **dispatch the actual coding to `delegate_task`
subagents** (≤3 concurrent for RAM); Hermes verifies each subagent's REAL test output before
merge. Reusable build pitfalls (sqlite-vec, FastAPI) → `references/samm-build-pitfalls.md`.

Clones (verified live, 2026-07-16):
- gstack → `~/.hermes/skills/gstack` (59 SKILL.md; `garrytan/gstack`, 122k★, MIT)
- ponytail → `~/.hermes/skills/ponytail` (`DietrichGebert/ponytail`, 84k★, MIT; core rules in `ponytail/AGENTS.md`)

## When to use
- User wants a coding team but refuses paid keys. **Claude Code CAN work at $0 via OpenRouter**
  with the correct config: set `ANTHROPIC_BASE_URL=https://openrouter.ai/api` (NOT `/api/v1`),
  `ANTHROPIC_AUTH_TOKEN` (not `ANTHROPIC_API_KEY`), and `ANTHROPIC_API_KEY=""` (explicitly
  empty). Verified working with `tencent/hy3:free` (pricing 0/0) — 32 MCP tools including
  Write/Read/Edit/Bash/Glob/Grep/Agent/WebFetch. The earlier exclusion (this skill said
  "needs paid Anthropic key") was WRONG — the cookbook config and a free model slug fix it.\n- "ponytail" the user mentions is NOT Claude Code — it is `DietrichGebert/ponytail`, a lean-code discipline layer. Include it.
- Build with LangGraph/Supabase/n8n/Grafana/Paperclip ONLY if the product needs them — they are product deps, NOT team members.

## Install / run OpenHands (CRITICAL: read references/openhands-venv-isolation.md)
Two valid shapes on this box — know which one you have:

**Shape A — frozen `.exe` launcher (what is ACTUALLY installed here):**
`openhands.exe` lives at `Python312\Scripts\` (OpenHands SDK v1.21.0). It is a
PyInstaller-style frozen launcher that bundles its own interpreter. The bug: when
the Hermes terminal exports `PYTHONPATH` pointing at the Hermes venv, the launcher's
`runpy` import picks up an incompatible `pydantic` and crashes with
`ImportError: pydantic_core._pydantic_core`. Fix is a **thin wrapper** that unsets
`PYTHONPATH` before launch:
```bash
#!/usr/bin/env bash
# bin/openhands.sh — launch OpenHands with a clean environment.
# SAFEGUARD: Hermes terminal may export PYTHONPATH at the Hermes venv, which can
# pull an incompatible pydantic and crash openhands.exe on import. Unsetting it is
# deterministic + harmless (no-op when no contamination present).
set -euo pipefail
cd "$(dirname "$0")/.."
env -u PYTHONPATH openhands.exe "$@"
```
Verify: `bash bin/openhands.sh --version` → must print `OpenHands SDK v1.21.0` with NO
Traceback. This wrapper is the correct, idempotent fix even when no contamination is
present in the current session.

**Shape B — isolated uv venv (alternative, from references/openhands-venv-isolation.md):**
`uv venv --python 3.12 openhands-venv` → `uv pip install --python openhands-venv openhands-ai`.
Verify: `env -u PYTHONPATH openhands-venv/Scripts/python.exe -P -c "import openhands"`.

Common to both: **the Hermes shell leaks `PYTHONPATH`** at the Hermes venv → MUST launch
with `env -u PYTHONPATH`. Docker daemon is usually DOWN here, so OpenHands needs a
runtime backend (Docker/SSH) to *execute* code — install is native, execution waits on Docker.

## Ruflo — multi-agent coordinator (COMPULSORY as topology, NOT as executor)
Installed via nvm: `ruflo` (v3.32.7). It is the agent-ORCHESTRATION/TOPOLOGY harness: `swarm
coordinate --agents 15` (hierarchical mesh), `agent spawn -t coder`, `hive-mind init/spawn`
print the topology and queue tasks. **These commands do NOT execute agent work** (see the
COMPULSORY-build note above — only `hive-mind spawn --claude` executes, and that needs Claude
Code). Use Ruflo for the coordination artifact; dispatch real coding via `delegate_task`.

**Zero-cost backends (your mandate excludes paid Anthropic):**
- **Ollama (local, preferred when no key):** `ollama serve` (background), model `llama3.2:1b`
  already pulled. `ruflo providers configure -p ollama -m llama3.2:1b` → `providers test`
  shows "Ollama: Connected". No API key, no network.
- **OpenRouter free:** `ruflo providers configure -p openrouter --base-url https://openrouter.ai/api/v1 -m tencent/hy3:free -k $KEY`.
  **SLUG CORRECTIONS (live 2026-07-18):** `meta-llama/llama-3.2-1b-instruct:free` is WRONG
  (OpenRouter returns 404 "model unavailable for free" — the free slug drops `:free` → use
  `meta-llama/llama-3.2-1b-instruct`). The actual HY3 free model the user wants is
  **`tencent/hy3:free`** (pricing 0/0, confirmed returns `OK`). Verify a slug with a direct
  `curl POST https://openrouter.ai/api/v1/chat/completions` before trusting Ruflo's config.

**CRITICAL key-verification pitfall:** a provider shows "Not configured" until a REAL key
is set. A masked/empty value in an `.env` (e.g. `OPENROUTER_API_KEY=` or `sk-or-...`)
is NOT a usable key — `providers configure -k "$KEY"` with it will "save" but calls fail.
Before claiming Ruflo is wired to OpenRouter: extract the key, check `echo ${#KEY}`
is >20 chars (a real `sk-or-...` is ~40+), and run a direct curl chat completion. If the
on-disk value is empty/masked, ask the user to paste the full key — do NOT claim it's
configured. (Seen live 2026-07-18: Hermes `.env` had `OPENROUTER_API_KEY=` empty; a grep
matched a minified JS blob, not the key — the agent must not mistake that for a working secret.)

Build pattern with Ruflo: init in repo (`ruflo init`), configure a zero-cost backend, then
dispatch phases to a swarm; Hermes verifies each agent's test output before merge. Reusable
build pitfalls (sqlite-vec, FastAPI) → `references/samm-build-pitfalls.md`.


- **PyPI name collision** — `pip install <cool-name>` often installs an UNRELATED package.
  Real example: `pip install paperclip` → a Django file-attachment library (2.7.4), NOT the
  autonomous "agent company" app `paperclipai/paperclip` (74k★, Docker-deployed). Before
  `pip install X`, confirm the PyPI package's description/owner matches the project you mean.
  When the real project is a Docker app (Paperclip, many agent stacks), install = `git clone`
  + `docker compose`, never `pip install`. See references/package-name-collisions.md.
- **Environment-state-dependent bugs** — a crash that reproduces in one terminal turn may NOT
  reproduce in the next, because Hermes snap-sessions re-export `PYTHONPATH`/env non-deterministically.
  DO NOT force a "100% reproducible crash" claim you can't produce on demand. Instead: (1) prove
  the FIX is deterministic and harmless (`env -u PYTHONPATH` wrapper always launches clean), and
  (2) state honestly that the bug was environment-state-dependent and is neutralized regardless.
  Fabricating a reproducible crash to "show the fix worked" is worse than reporting the limitation.
- **gstack path** — it lives at `~/.hermes/skills/gstack` (NOT `$APPDATA/hermes/skills`). Check the
  real path before declaring a skill "missing".

## gstack: reference library, NOT loaded as skills
`gen:skill-docs --host hermes` is a PARTIAL port (52/55 skills still hardcode `~/.claude` + Claude tools). Reliable path: Hermes READS the SKILL.md and runs the equivalent with native tools (`Bash`→`terminal`, `Read`→`read_file`, `Edit`→`patch`, `Grep/Glob`→`search_files`). Skip `~/.claude/...` bin calls; methodology is in the body.
- Report-only skills safe for autonomous use: `cso` (OWASP/STRIDE security), `health` (typecheck/lint/test), `review` (auto-fix OFF), `qa-only`.
- AVOID unattended: `autoplan`, `office-hours`, `plan-ceo-review` (they ask questions → hang).

### Running gstack gates through Hermes (proven 2026-07-18 on SAMM)
gstack's slash-commands are Claude-Code-native. Do NOT claim you "ran /review". Instead
execute the gate *workflow* with native tools and produce the same artifacts (findings +
fixes + regression tests). The mapping that worked:
- **`/review`** → read the core source files (`store.py`, `api.py`, `engine.py`); look for
  real bugs (wrong math, unhandled paths, perf on hot loops); write a repro, then fix.
- **`/qa`** → start the app (`samm -m samm.cli serve ...` in background), then `curl` every
  endpoint: health, write-without-token (expect 401), write-with-token (200), search,
  conflicts. Assert real responses, not just 200s.
- **`/cso`** → audit auth: is the server fail-open when no token is set? Are WebSockets
  unauthenticated? Compare secrets with `==` (not constant-time)? Fix to fail-closed.
- Always finish each gate with a **regression test** asserting the bug stays fixed, then
  re-run the full suite + ruff before commit. This is the "production-grade" bar.

## ponytail: inject discipline into every coding task
Prepend the "lazy senior dev ladder" (YAGNI → reuse → stdlib → native → installed dep → one line → minimum) to every OpenHands/Hermes coding prompt. Core rules live in `ponytail/AGENTS.md` — agent-agnostic, works for OpenHands. Never skip: trust-boundary validation, error handling, security, accessibility. Mark deliberate simplifications with a `ponytail:` comment.

## The build loop (Hermes drives)
1. Hermes plans → small verifiable tasks.
2. Hermes hands task to coder (OpenHands if runtime up, else Hermes directly) with ponytail discipline prepended.
3. Hermes runs gstack methodology: `/health` (pytest/tsc/eslint), `/cso` (security), `/review`.
4. **Re-run verification IN THE SAME TURN edits happen** (harness flags otherwise). See references/real-exit-code-pitfall.md.
5. Ship when green.

## Verification discipline (standing quality bar)
- No project "done" until tests pass.
- Capture REAL exit codes: `npm run typecheck >log 2>&1; echo "EXIT=$?"` — NOT `npm run typecheck && echo "EXIT=$?"` (that captures `echo`'s exit, not tsc's). See references/real-exit-code-pitfall.md.
- Prefer offline/fake backends in tests so CI needs no API key.

### Terminal tool has a HARD 60s cap — run slow suites as background jobs
The `terminal` tool kills ANY command at ~60s regardless of a longer `timeout` you pass.
A suite that takes >60s (live MCP subprocess tests, heavy imports) will be
silently killed mid-run if you call it foreground. **Fix:** launch it as a background
job, then read the log file:
```bash
# launch (no 60s tool cap on the background runner)
terminal(background=true, command='cd "/c/Users/<user>/samm" && env -u PYTHONPATH /c/Users/PREM\ KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/ -q -p no:cacheprovider --tb=line > /tmp/samm.log 2>&1; echo "EXIT=$?" >> /tmp/samm.log')
# then: process(action='wait') OR poll, and read_file('/tmp/samm.log')
```
Reading pytest's final "X passed in Ys" line from the log: it is often pushed
ABOVE a `RequestsDependencyWarning` block, so `grep "passed"` may miss it —
count the progress dots (`.` = pass, `F` = fail) and trust `EXIT=0` + zero `F`.
This is the only reliable way to verify a slow suite here.

### Subagent leaves stray debug files — clean before commit
`delegate_task` leaf subagents routinely drop scratch files in the repo
(`_dbg.py`, `_probe.py`, `_probe2.py`, `_probe_ruflo.py`, `_probe4.txt`, etc.).
After a subagent delivers code, `git status` and `rm -f` those before `git add -A`,
or they get committed as junk. The bridge build (2026-07-19) left 6 such files;
caught + removed before push. Make "rm stray `_*` debug files" a standing step
in the build loop (step between subagent delivery and commit).

### CRITICAL: delegation "completed" banner can LIE — verify on disk
A `delegate_task` batch can report "ASYNC DELEGATION BATCH COMPLETE"
with status `completed` while producing **ZERO** repo changes. Two distinct failure modes seen live:
- **(A) Owner-exit, work LOST** (2026-07-19): delegation owner exited before
  recording a terminal result; subagents' output was discarded. `git diff HEAD` empty,
  no test files landed, `git status` clean. The batch "completed" but nothing shipped.
- **(B) Owner-exit, work SURVIVED** (2026-07-19, Wave 1): same "completed"
  banner, but `git diff HEAD --stat` showed real edits + new test files existed on disk.
  The summary's pass-count was still UNTRUSTED until re-run locally.
**Standing rule:** when a batch returns, BEFORE trusting its summary, run in this order:
  1. `git status --short`  (clean tree ⇒ mode A ⇒ re-dispatch)
  2. `git diff HEAD --stat` + `ls` the claimed new files  (confirm edits + files exist ⇒ mode B)
  3. Re-run the FULL suite myself in a background job (terminal has a HARD 60s cap that
     kills slow suites; use `terminal(background=true, notify_on_complete=true)` then `process(action='wait')`
     or read the log). Trust the on-disk `EXIT=0` + dot-count, not the summary's "N passed".
If mode A → re-dispatch the same tasks (mechanism works; transient crash).
Never tell the user "Wave N done" from the banner alone. Verify, then report.
Also: leaf subagents routinely drop scratch files (`_dbg.py`, `_probe.py`,
`_pytest_final.txt`, `hello.py`) — `rm -f` them before `git add -A` or they commit as junk.

### Subagent SUMMARY TEXT can be HALLUCINATED — trust only re-run tests
Beyond the green/empty-code trap above, the *prose* in a subagent's returned summary
can contain **model-fabricated irrelevant claims** that were never part of the task.
Two distinct hallucination patterns seen live:

- **(A) Fabricated citations** (2026-07-19): a Wave-2 subagent appended a
  multi-paragraph "how to connect Claude Code to OpenRouter" tutorial with
  **fabricated [1]..[6] bibliography-style markers** referencing real-looking
  URLs (GitHub repos, cookbook pages, Medium articles). None of these citations
  were part of its task — it invented them to make prose look authoritative.
  The model treats [N] markers as a stylistic device for credibility, even when
  the source material was never loaded.
- **(B) Off-topic padding** (less severe): subagent adds "you can also use X for Y"
  recommendations, tutorial paragraphs, or "you may want to consider" advice that
  was not in its instructions.

**Detection heuristics:** if a subagent summary contains anything beyond file
paths, diff stats, or test-pass counts, suspect hallucination. Specifically:
  - Numbered/referenced bibliography markers ([1], [2], etc.) — a coding
    subagent almost never needs to produce citations.
  - Tutorial paragraphs or recommendation language ("you may want to", "consider").
  - Claims about tool/API behavior the subagent was never instructed to evaluate.
  - URLs to external resources without being told to research.

**Rule:** read a subagent summary for *what files changed + what command was run*,
then independently re-run the suite. **Ignore any explanatory/narrative claims**
(tutorials, recommendations, "you can also do X", cited references) unless you
verify them yourself. Do not act on, repeat, or build on subagent narrative. If a
summary contains such text, treat it as noise — it is not evidence.

### Ruflo runtime state pollutes the repo — gitignore it
Ruflo + SAMM write VOLATILE runtime artifacts that must NOT be committed:
`.claude-flow/`, `hive-mind/`, `.swarm/`, `data/memory/` (sqlite indexes,
daemon state, HNSW vectors). If they were committed before you noticed,
`git rm -r --cached` them (keeps files on disk), add to `.gitignore`
(`*.swarm/`, `.claude-flow/`, `data/memory/`), and commit. The SAMM v1.0
build (2026-07-19) needed exactly this cleanup before push.

## Resource guards (RAM-starved ~6GB box)
- OpenHands native venv, NOT docker (daemon down; container overhead risks OOM).
- One coding task at a time. Bound every command with `timeout`.
- Kill stale procs before builds (`wmic` for node, not /proc).

## Free asset CREATION (ffmpeg-only, zero downloads)
When the product needs to *generate* assets (not just download stock), build a
**free, offline ffmpeg-static engine** — no network, no keys, no node-canvas.
Reference implementation: `<workspace-root>\asset-creator` (10 functions, 14 passing tests).
It creates: background/title/quote images, Ken-Burns/kinetic/countdown video clips,
procedural background music, 5 SFX kinds, GIF, and branded placeholders. Wire it into
AVG's `src/agentic/acquire.ts` as a fallback source (self-healing when stock fails).
**CRITICAL ffmpeg-static quirks** (missing filters, fontfile requirement, invalid
colors, no wrap_width) → `references/static-ffmpeg-gotchas.md`. Read before writing
any ffmpeg drawtext/audio filter code.

## ADVANCED asset generation — drive the laptop via computer_use (cua-driver)
Beyond ffmpeg primitives, the **free advanced path** is to let the agent operate
the user's actual desktop: open websites, navigate + type, capture screenshots,
and record the screen as video — all free, no GPU, no paid keys. The agent "sees"
the screen through the **model's native vision** on the captured PNG (NOT a
separate vision API — user directive: "use your model to see the image").

Reference implementation: `<workspace-root>\computer-agent` (Python; `src/driver.py` wraps
`cua-driver call`, `src/agent.py` = observe/act/generate loop, `demo_record.py`
= open-site + type + record-MP4 proof). Verified live: launched Chrome, navigated
+ typed, recorded a valid 1920×1080 H.264 MP4.

**User environment decisions (captured 2026-07-16):**
- **No Blender** on this box → drive the **Chrome browser** for advanced generation
  (HF Spaces SDXL, browser tools). Drop Blender entirely.
- Agent vision = native model vision on screenshot; do NOT wire a separate vision API.
- cua-driver API quirks that break naive wrappers → `references/cua-driver-quirks.md`
  (base64 PNG not path; `set_config capture_scope=desktop` required; `list_apps`
  returns `{"apps":[...]}`; recorder disabled → use ffmpeg `gdigrab`). READ IT
  before writing any cua-driver wrapper.

## References
- `references/claude-code-openrouter-cookbook.md` — The correct env vars to run Claude Code on free models via OpenRouter (ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, empty API_KEY; model slug tencent/hy3:free). Corrects the old "requires paid Anthropic key" exclusion.\n- `references/ruflo-reality.md` — VERIFIED evidence: Ruflo is coordinator-only (no free-model execution; Claude Code + OpenRouter-free proxy FAILED, do not retry) BUT its **MCP server connects to Hermes via the stdio wrapper** (working recipe inside) + OpenRouter free-slug corrections. READ before claiming Ruflo "built" anything or wiring Ruflo MCP.
- `references/ruflo-exec-unlock-verified.md` — VERIFIED exec recon (2026-07-19): Ruflo 3.32.7 shells the `claude` BINARY (`spawn("claude",["mcp","serve"])`), NOT the Anthropic API. So OSS `claude` shim (OpenCode) is the right unlock; LiteLLM-API theory was WRONG. OpenCode chat works free, but `opencode serve` is a STUB (exit 1) → exec still blocked. Do NOT claim "Ruflo unlocked".
- `references/freecode-gateway.md` — THE WORKING UNLOCK (different perspective): Ruflo's `claude-code` group is DORMANT (env var set + shim on PATH, but Ruflo never spawns `claude` — tools/list shows 0 claude tools, blind `claude__Write` → "Tool not found"). So don't inject into Ruflo: build `freecode` — a standalone stdio MCP server (Write/Read/Edit/Bash/Glob/Grep) backed by LOCAL exec + optional Ollama, $0, no Anthropic key — and register it in Hermes as its own MCP server (`hermes mcp add freecode`). Includes the mcp-SDK gotchas (`Server.run_stdio_async` doesn't exist; use `stdio_server()` + `APP.run`) and the ONLY reliable verify method for a long-running stdio server (terminal-pipe JSON-RPC, NOT `subprocess.Popen` which deadlocks; assert file via Python `os.path.exists`, not bash `[ -f ]` which breaks on MSYS `C:/tmp` paths).
- `references/samm-build-pitfalls.md` — reusable debugging paths from building SAMM (Shared Agent Memory Mesh): sqlite-vec embedding binding format, FastAPI 422 with `from __future__ import annotations`, multi-Python-interpreter test execution, and **vec0 cosine distance exceeds 1 with unnormalized embeddings → clamp scores to [0,1]** (real negative-score bug).
- `references/openhands-venv-isolation.md` — exact venv build + PYTHONPATH leak fix + launch command (OpenHands/py3.12).
- `references/package-name-collisions.md` — PyPI name-collision trap (paperclip Django lib ≠ paperclipai/paperclip), env-state-dependent bug verification discipline, gstack real path.
- `references/windows-python-voicebox-isolation.md` — DEEPER Python isolation mechanics for ANY pip/uv install on this box: why `python -m venv` is broken (venv-of-venv inherits Hermes site-packages), use `uv venv --python 3.11` + `env PYTHONPATH=` for every install/run, the stale-port-17493 kill step, the Windows long-path CUDA-torch extraction fix (`TMPDIR=C:/tmp UV_CACHE_DIR=C:/tmp/uvcache`), a **GPU-aware** Voicebox headless-backend recipe, and the real OOM root cause. CORRECTION: the 3.86 GB download was **Qwen 1.7B**, NOT Kokoro; Kokoro-82M ≈ 350 MB runs FINE via **CUDA torch** (loads into the RTX 3050's 4 GB VRAM, ~819 MB, system RAM untouched). Voicebox WORKS on this laptop with the GPU. The old "Kokoro 3.86 GB → cannot load" claim is WRONG — read the CORRECTION box in that file. Read BEFORE any Python backend install.
- `references/real-exit-code-pitfall.md` — how to capture real tsc/eslint/pytest exit codes (the `&& echo $?` trap).
- `references/free-models.md` — current OpenRouter free coder models + how to reuse the OpenClaw key.
- `references/static-ffmpeg-gotchas.md` — ffmpeg-static missing filters, fontfile requirement, invalid colors, no wrap_width (from building asset-creator).
- `references/cua-driver-quirks.md` — cua-driver real API quirks + the free advanced-asset (Chrome-driven) path (from building computer-agent).
