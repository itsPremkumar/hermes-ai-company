---
name: hermes-skill-authoring
version: 1.0.0
description: >-
  Author, verify, and install local Hermes Agent skills (SKILL.md + bin/ helpers)
  in ~/.hermes/skills/<name>/. Covers the non-obvious pitfalls that bite during
  creation and testing: interpreter naming, MSYS path translation, fast-fail on
  dead model endpoints, OpenRouter free-model slug rotation + 429 handling, and
  the discovery quirk that dropped local folders are NOT indexed by
  `hermes skills list`. Use when building a new skill, debugging a skill that
  "won't load", or making a skill properly invocable.
triggers:
  - create a hermes skill
  - author a SKILL.md
  - my skill is not showing in hermes skills list
  - make a local skill invocable
  - skill won't load / not discovered
  - verify a hermes skill works
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---
# Hermes Skill Authoring

Build local skills under `~/.hermes/skills/<name>/`. A skill = a `SKILL.md`
(frontmatter + markdown body) plus optional `bin/`, `references/`, `templates/`,
`scripts/` support dirs.

## Minimum viable skill

```
~/.hermes/skills/<name>/SKILL.md
~/.hermes/skills/<name>/bin/helper.sh   (optional)
```

`SKILL.md` frontmatter (YAML):
```yaml
---
name: <name>            # matches the folder name
version: 1.0.0
description: >-         # one-line-ish; used by discovery + fuzzy match
  What it does and when to use it.
triggers:               # natural-language phrases that should activate it
  - do the thing
allowed-tools:          # tools the skill may use
  - Bash
  - Read
---
```
Body = the procedure the agent follows when the skill is active. Keep it
step-by-step with exact commands.

## Verification (do this before declaring done)

The agent-inline path is always testable; a `bin/` helper needs real execution.

1. **Syntax**: `bash -n bin/helper.sh && echo OK`
2. **Guardrail**: run with empty input → must exit non-zero with a clear message.
3. **Happy path**: stand up a mock OpenAI-compatible server (Python
   `http.server`, see `references/mock-server.md`) and point the helper at it.
   Confirm it parses `{"choices":[..]}` and prints the refined text.
4. **Failure path**: point at a dead port → must fail FAST (≤~5s), not hang.
5. Use an OS-safe temp path with a `hermes-verify-` filename prefix for any
   throwaway test scripts; clean them up after.

## CRITICAL pitfalls (learned the hard way — see references/pitfalls.md)

- **Interpreter**: `python3` is often MISSING on this box; `python` (3.11.x)
  works. Detect with `PYBIN="$(command -v python || command -v python3 || echo python)"`.
- **MSYS `/tmp` path translation**: a background `python /tmp/x.py` may resolve to
  `C:\tmp\x.py` and fail. Write temp/test scripts to a Windows-native path under
  the user home (e.g. `C:\Users\<user>\AppData\Local\Temp\`) and reference them
  with forward slashes.
- **Dead model endpoint = hang risk**: if the helper calls a local Ollama that
  isn't running, `hermes chat -q` will BLOCK trying to launch it. Prefer a direct
  OpenAI-compatible `curl` with `--max-time 5` so it fails fast. On empty RESP,
  exit 2 (unreachable) — never loop forever.
- **OpenRouter free-model slugs ROTATE**. `meta-llama/llama-3.1-8b-instruct:free`
  returns 404 ("no longer free"). Always resolve a currently-free slug at runtime
  via `GET https://openrouter.ai/api/v1/models` filtering `pricing.prompt==0 &&
  pricing.completion==0`, preferring small instruct/text models. Cache the choice.
- **429 rate-limit is transient**: free-tier shared IPs get throttled. Retry with
  backoff AND fall back across several free slugs before giving up.
- **DISCOVERY QUIRK (most important)**: dropping a folder into
  `~/.hermes/skills/<name>/` does NOT make it appear in `hermes skills list`, and
  `/skill <name>` / `skill_view` won't load it. Only hub/registry-installed
  skills (or specific registered sources) are indexed in this install. A bare
  `git init` in the folder does NOT fix it. So:
  - The skill STILL works if the agent reads `SKILL.md` directly and follows it
    (agent-inline execution is the always-available path).
  - To make it auto-discoverable/triggerable, publish to a git repo and run
    `hermes skills install <url>` (local folder paths are rejected by install).
  - Don't burn time reverse-engineering discovery internals — use the agent-inline
    path or a proper `hermes skills install` from a URL.

## Making a skill properly invocable

If the user wants `/<name>` to auto-trigger:
1. Create a GitHub repo containing the skill folder.
2. `hermes skills install <repo-url>` (pass `--name <name>` if frontmatter lacks it).
3. Verify with `hermes skills list | grep <name>`.

Until then, invoke by asking the agent to "run the <name> skill" — the agent
reads `SKILL.md` and executes its procedure.

## Support files in this skill

- `references/mock-server.md` — throwaway OpenAI-compatible mock + ad-hoc
  verification harness recipe (test a `bin/` helper without a real model).
- `references/pitfalls.md` — failure transcripts + fixes from the prompt-refine
  build session (interpreter, MSYS, dead endpoint, slug rotation, 429, discovery).
- `templates/prompt-refine/` — a copy-ready, already-verified skill
  (`SKILL.md` + `bin/refine.sh`) demonstrating the observable-ladder model call.
  Scaffold a new model-calling skill from it instead of re-deriving the pattern.

## Real example shipped this session

`~/.hermes/skills/prompt-refine/` — refines a user's garbled prompt via the
already-configured model (zero extra cost) with a non-destructive
original-vs-refined diff. Its `bin/refine.sh` applies every pitfall above.
Use it as a copy-ready template: `templates/prompt-refine/` holds the SKILL.md
and `bin/refine.sh` so you can scaffold a model-calling skill without
re-deriving the ladder.

## Calling a model from a skill: the observable ladder (reusable)

Any `bin/` helper that rewrites/queries text should use the user's OWN model,
not hard-code one. Pattern (portable, zero-cost, works for every user):

1. Read `base_url` / `api_key` / `default` from `~/.hermes/config.yaml`
   (grep + `sed`, no python dependency for the parse).
2. If `api_key` is a placeholder (`ollama`) AND a real key is in the env
   (`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`), override to that provider.
3. Call the OpenAI-compatible `/chat/completions` with `--max-time 30` and a
   strict system prompt. On 429, sleep + retry; on other errors, try the next
   candidate slug.
4. **Degrade, don't crash**: if all candidates fail, exit non-zero with a clear
   message. The agent-inline path then does the rewrite itself. Never loop.

This is the heart of `refine.sh` and applies to any skill that needs a model
call (summarizer, classifier, translator, etc.).

## Contributing a skill/idea upstream to Hermes

When the user wants the feature shipped into Hermes itself (not just local):

1. Read the install source for the real structure:
   `HERMES_DIR="$LOCALAPPDATA/hermes/hermes-agent"` → `apps/desktop/src/...`,
   and `$HERMES_DIR/AGENTS.md` for architectural invariants (renderer never
   calls models directly; state-by-authority; narrow waist). Ground any UI spec
   in the ACTUAL components (e.g. `composer/controls.tsx`, `ModelPill`,
   `useI18n`/`t.composer.*` keys) — don't invent architecture.
2. Check for an EXISTING related issue FIRST (`gh issue list --search ...`); if
   one exists, COMMENT with your extension rather than opening a duplicate.
   Cross-link. Open a new issue only if the scope is genuinely distinct.
3. Post a Tier-2 UI spec (component placement, interaction flow, backend RPC
   contract, i18n keys, tests) as a comment so a maintainer can implement.
4. `gh` is already authed as the user's GitHub account — use `gh issue create`
   / `gh issue comment` directly. Verify the comment landed
   (`gh api repos/.../issues/<n>/comments`).
