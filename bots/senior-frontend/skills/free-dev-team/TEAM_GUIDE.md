---
name: free-dev-team
description: The complete FREE software-engineering team — Hermes (orchestrator, free model) + OpenHands (coder, free model) + gstack (QA/security methodology) + ponytail (lean-code discipline). Use when building production software with no paid keys.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Free Dev Team — Operating Guide

The complete, $0 software-engineering team. No paid keys. All open-source / free-tier.

## Team members (the 4 parts)
| Role | Tool | Free model source | How it runs |
|---|---|---|---|
| CEO / Orchestrator | **Hermes** (this agent) | `tencent/hy3:free` via OpenRouter | native |
| Coding agent | **OpenHands** | OpenRouter free coder model (e.g. `qwen/qwen2.5-coder-32b-instruct:free`) | native (pip `openhands-ai`) |
| QA / Security methodology | **gstack** (reference library) | n/a (instructions) | Hermes reads SKILL.md bodies |
| Lean-code discipline | **ponytail** (AGENTS.md rules) | n/a (instructions) | Hermes injects into every OpenHands prompt |

Location of parts:
- gstack: `~/.hermes/skills/gstack` (59 SKILL.md files)
- ponytail: `~/.hermes/skills/ponytail` (core rules in `ponytail/AGENTS.md`)
- OpenHands: installed via `pip install openhands-ai`

## The build loop (Hermes drives this)
1. **Hermes plans** — break the product into small, verifiable tasks. Write a spec.
2. **Hermes launches OpenHands** per task, with the ponytail discipline prepended to the prompt (see below) and a FREE model configured.
3. **OpenHands builds** the feature / edits files / opens a PR or commits to a branch.
4. **Hermes runs gstack methodology** on the result:
   - `/health` → typecheck + lint + unit tests
   - `/cso` → OWASP/STRIDE security audit (read-only, safe for autonomous use)
   - `/review` → code review with auto-fix OFF
   - `/qa-only` → bug report, no changes
5. **Hermes verifies in the SAME turn it edits** (re-run tests after any change — never cite prior-turn evidence).
6. **Hermes ships** when green.

## ponytail discipline (PREPEND to every OpenHands task prompt)
Copy this block into the task you hand to OpenHands:

```
You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.
Before writing any code, stop at the first rung that holds:
1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.
Rules: no unrequested abstractions, no new deps if avoidable, deletion over addition, fewest files possible.
NOT lazy about: input validation at trust boundaries, error handling that prevents data loss, security, accessibility, understanding the problem first.
Mark deliberate simplifications with a `ponytail:` comment naming the ceiling and upgrade path.
Non-trivial logic leaves ONE runnable check behind (one small test file). Trivial one-liners need no test.
```

## gstack methodology reference (Hermes executes these, not loads as skills)
gstack skills are Claude-Code-oriented and only partially port to Hermes (paths hardcode `~/.claude`, tools are `Bash/Read/Edit`). So Hermes READS the SKILL.md and runs the equivalent with native tools:
- `Bash` → `terminal`, `Read` → `read_file`, `Edit` → `patch`, `Grep/Glob` → `search_files`, `Agent` → `delegate_task`.
- Skip the `~/.claude/...` bin calls in the preamble (version/state checks). The real methodology is in the body.
- Most useful skills for autonomous use (report-only, no hanging gates):
  - `gstack/cso/SKILL.md` — OWASP+STRIDE security audit
  - `gstack/health/SKILL.md` — typecheck/lint/test gate
  - `gstack/review/SKILL.md` — code review (auto-fix OFF)
  - `gstack/qa-only/SKILL.md` — bug report only
- AVOID in unattended crons: `autoplan`, `office-hours`, `plan-ceo-review`, `design-review` (they ask questions → hang).

## OpenHands — install state (VERIFIED 2026-07-16)
- Installed: `openhands-ai` 1.11.0 in an isolated venv at `~/openhands-venv` (Python 3.12).
- SDK `Conversation` / `LocalConversation` import cleanly (SDK v1.34.0).
- **CRITICAL ISOLATION NOTE:** the Hermes environment leaks `PYTHONPATH` (points at Hermes' own broken venv, which has a missing `pydantic_core`). To run OpenHands you MUST strip it:
  ```bash
  env -u PYTHONPATH OPENHANDS_SUPPRESS_BANNER=1 ~/openhands-venv/Scripts/python.exe -P -m <entry>
  ```
  The `-P` flag + `env -u PYTHONPATH` makes the venv self-contained. Without this, every import fails with `No module named 'pydantic_core._pydantic_core'`.

## OpenHands — how to actually RUN it (runtime backend required)
**OpenHands' agent needs a RUNTIME BACKEND to execute code — either Docker or an SSH box.**
- On this machine **Docker daemon is currently DOWN** (`docker info` fails). So OpenHands is installed but cannot execute code until Docker is started OR you point it at an SSH runtime.
- To enable execution: start **Docker Desktop** (then `docker info` should succeed), OR configure an SSH runtime in the OpenHands UI.
- Config file already written at `~/openhands-config.toml` (reuses the OpenRouter free key from `~/.openclaw/openclaw.json`; free model `qwen/qwen2.5-coder-32b-instruct:free`).
- Launch (after Docker is up):
  ```bash
  env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -m openhands <task> --config-file ~/openhands-config.toml
  ```
  (exact CLI entry depends on the 1.11 front-end; if `python -m openhands` is unavailable, use the SDK `LocalConversation` API with a `workspace` + `agent` configured.)

## OpenHands — free models to use (OpenRouter)
- `qwen/qwen2.5-coder-32b-instruct:free`  (recommended coder)
- `mistralai/mistral-7b-instruct:free`
- `meta-llama/llama-3.1-8b-instruct:free`
Verify current free availability at https://openrouter.ai/models?filters=free (free tier rotates).

## Resource guards (this box is RAM-starved ~6GB)
- Run OpenHands natively (pip), NOT docker (Docker daemon not running; container overhead risks OOM).
- One OpenHands task at a time. Never parallel OpenHands + heavy Node build.
- Bound every terminal command with `timeout`.
- Kill stale processes before starting a build (`wmic` for node procs, not /proc).

## Verification discipline (standing quality bar)
- No project "done" until tests pass.
- After editing code, re-run the verification command IN THE SAME TURN, read output, THEN claim verified.
- Prefer offline/fake backends in tests so CI needs no API key.

## What is NOT part of the team (add only if the product needs it)
- LangGraph / pydantic-ai — only if building agent products
- Supabase / Postgres — only if the app needs a database
- n8n — only if automation/glue is needed
- Grafana — only if monitoring real traffic
- Paperclip — only for 24/7 autonomous company mode
- Claude Code — EXCLUDED (paid key; "ponytail" the user mentioned is NOT Claude Code — it is the DietrichGebert/ponytail lean-code discipline repo, already included above)
