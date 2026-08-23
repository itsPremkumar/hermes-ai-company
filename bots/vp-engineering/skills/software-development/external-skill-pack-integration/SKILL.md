---
name: external-skill-pack-integration
description: Integrate a third-party agent "skill pack" (slash-command skill suite) into the Hermes skills directory so it is usable from Hermes/Paperclip/OpenClaw. Covers TWO classes — (1) methodology suites like garrytan/gstack (55+ engineering-role skills, reference-library integration, Bun-on-Windows workaround, --host hermes partial-port pitfall, human-in-the-loop autonomy caveat) and (2) discipline/style layers like DietrichGebert/ponytail (lean-code behavior modifier; applicable to a free OpenHands+Hermes stack WITHOUT needing paid Claude Code). Use when the user says "install gstack", "add ponytail", "set up <agent skill suite>", or wants an external Claude-Code-style pack usable from Hermes.
---

# External Skill Pack Integration (Hermes)

Many high-quality skill suites are authored for **Claude Code** as a folder of `SKILL.md`
files (e.g. [garrytan/gstack](https://github.com/garrytan/gstack) — 55+ engineering-role
skills: /review, /cso, /qa, /design-html, etc.). Hermes CAN host them, but the port is
not automatic and has a sharp edge. This skill records the verified procedure and the
pitfalls so the next session does not re-discover them.

There are **two distinct classes** of external pack — do not conflate them:

1. **Methodology / role-playbook suites** (e.g. gstack) — folders of `SKILL.md` that
   encode multi-step engineering workflows. Integrate as a *reference library* (read the
   body, execute with Hermes tools). See PITFALL 2 + the manual-execution recipe below.
2. **Discipline / style layers** (e.g. [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail),
   84k★, very active, MIT-style) — NOT a coding engine. It is a *behavior modifier*:
   prompt/rule files (`.claude-plugin`, `.codex-plugin`, `.cursor/rules`, `.clinerules`,
   `.devin-plugin`, `.agents`) that tell the agent to "think like the laziest senior dev —
   write minimal code, avoid premature abstraction, mark intentional corner-cuts with
   `ponytail:`". It plugs into Claude Code / Codex / Cursor / Claude / Devin, and ships a
   generic `.agents/` folder that OpenHands-style agents can also read. **Hermes can apply
   its principles by injecting them into task prompts** even without native plugin support.

**Key distinction for the free-only user:** ponytail's *primary* host is Claude Code (paid),
but you do NOT need Claude Code to benefit — its rules are plain text Hermes can read and
re-apply to OpenHands task specs. This makes ponytail a valuable *optional* lean-code
discipline layer on a free OpenHands + Hermes stack (it stops the coder from over-building
on a RAM-starved box). It is NOT required for the team to function.

## When to use
- User wants gstack, ponytail, or any external agent skill/rule pack installed or applied.
- You are evaluating whether an external suite improves our product-engineering rigor.
- User mentions "ponytail", "Claude Code plugins", "agent discipline", "lazy senior dev".

## Verified install procedure (gstack, Windows/Git-Bash)

1. **Bun is required** (gstack's `./setup` and `gen:skill-docs` are Bun scripts). Node alone
   is NOT enough. Check: `bun --version`. If missing, see the Bun workaround below.
2. Clone shallow + single-branch into the Hermes skills dir:
   ```bash
   cd ~/.hermes/skills
   git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git gstack
   ```
3. `./setup --host hermes` only prints guidance — the real step is skill generation:
   ```bash
   export PATH="$HOME/.bun/bin:$PATH"   # if bun installed manually
   cd ~/.hermes/skills/gstack
   bun install                            # 339 pkgs; fast if lockfile satisfied
   bun run gen:skill-docs --host hermes   # writes 55 skills, 113 SKILL.md files
   ```
4. Verify: `find ~/.hermes/skills/gstack -name SKILL.md | wc -l` should be > 100.

## PITFALL 1 — Bun installer fails on space-containing Windows username

The official `curl -fsSL https://bun.sh/install | bash` writes to a path derived from
`$HOME` and **fails** when the username has a space (e.g. `C:\Users\PREM KUMAR`) — it
errors "Failed to download bun ... client returned ERROR on write". Workaround:
```bash
cd /tmp
curl -fsSL -o bun.zip "https://github.com/oven-sh/bun/releases/latest/download/bun-windows-x64.zip"
mkdir -p "$HOME/.bun" && unzip -q -o bun.zip -d "$HOME/.bun"
export PATH="$HOME/.bun/bin:$PATH"          # bun.exe lives at $HOME/.bun/bin/bun.exe
echo 'export PATH="$HOME/.bun/bin:$PATH"' >> "$HOME/.bashrc"
```
This yields Bun ~1.3.x and persists across sessions via `.bashrc`.

## PITFALL 2 — `--host hermes` is a PARTIAL port (CRITICAL)

`gen:skill-docs --host hermes` generates the skills but does **NOT** fully rewrite the
Claude-specific content. Verified by reading the generated bodies:
- 52 of 55 skills still hardcode `~/.claude/skills/gstack/bin/...` paths (NOT `~/.hermes/...`).
- `allowed-tools` frontmatter still lists Claude-native tools: `Bash, Read, Edit, Write,
  Grep, Glob, Agent, AskUserQuestion` — NOT Hermes tools (`terminal, read_file, patch,
  search_files, delegate_task`).
- Bodies still say `CLAUDE.md`, not `AGENTS.md`.

The `hosts/hermes.ts` config *declares* path/tool rewrites (`~/.hermes/...`, `terminal`,
`patch`, `delegate_task`, `AGENTS.md`) but `gen:skill-docs` only kept `name`/`description`
via `keepFields`. So **as generated, skills are not drop-in loadable by Hermes** — the
`~/.claude/...` paths 404 and tool names do not match.

**What actually works:**
- The bin helpers (`bin/gstack-paths`, `bin/gstack-update-check`, etc.) are **env-driven**,
  not hardcoded. They resolve their own root via `GSTACK_DIR` / `GSTACK_HOME` / dynamic
  detection, so you can override with:
  ```bash
  export GSTACK_DIR=~/.hermes/skills/gstack
  export GSTACK_HOME=~/.gstack
  ```
- State root correctly uses `~/.gstack` (portable) when env is set.
- The **methodology** in each SKILL.md is plain Markdown instruction — Hermes can read
  `gstack/review/SKILL.md`, `gstack/cso/SKILL.md`, etc. and execute the workflow with its
  own tools, substituting the `~/.claude/...` bin calls.

**Two integration strategies:**
1. *Reference library (fast, recommended first):* Don't load as skills. Hermes reads the
   SKILL.md files on demand and follows the instructions via its own tools. Best for
   `/cso`, `/review`, `/qa`, `/design-html`.
2. *Proper port (slower):* Patch `hosts/hermes.ts` / the gen template so paths+tools
   rewrite, regenerate, then expose via a thin router skill. Worth a PR upstream or local
   fork if gstack becomes a daily driver.

## PITFALL 5 — `npm install gstack` installs the WRONG package (sharp trap)

`npm i gstack` / `npm install gstack` does **NOT** fetch `garrytan/gstack` (the
122k★ engineering skill suite). It resolves to an **unrelated, abandoned npm
package** also named `gstack` (v0.8–0.9.8) whose ancient deps conflict with the
local Python 3.12 env (`pydantic` / `pydantic_core` resolution errors) and which
is NOT the skill suite. Verified 2026-07-16: the registry returned this stale
package and `npm i gstack` "succeeded" while giving you nothing useful.

**Rule:** NEVER `npm install gstack`. Always `git clone` the GitHub repo:
```bash
cd ~/.hermes/skills
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git gstack
```
(The shallow clone is fast and is the real suite. You do NOT need Bun or npm for
reference-library use — only if you later run `gen:skill-docs`.)

Same class of trap: any skill-suite name that collides with an npm package —
prefer the explicit `git clone` over a package-manager install unless you have
confirmed the npm package IS the canonical source.

## Manual methodology-execution recipe (when skills are NOT drop-in)

Because of Pitfall 2, the reliable way to *use* gstack from Hermes today is to read the
generated SKILL.md and execute its workflow with native Hermes tools. The preamble's
`~/.claude/...` bin calls are just version/state checks — **skip them**; the real
methodology is in the body. Concrete recipe:

1. Read the skill: `read_file ~/.hermes/skills/gstack/<skill>/SKILL.md` (e.g. `cso`, `review`, `health`).
2. Translate tool names: `Bash`→`terminal`, `Read`→`read_file`, `Edit`→`patch`,
   `Grep`/`Glob`→`search_files`, `Agent`→`delegate_task`. Set `GSTACK_DIR=~/.hermes/skills/gstack`
   only if you actually call a bin helper.
3. Run the equivalent native commands. For `/health`: `npm run typecheck && npm run lint &&
   npm run test:unit`. For `/cso`: secrets grep → `npm audit --omit=dev` → OWASP pattern
   grep (`eval(`, `child_process`, `innerHTML` unescaped, `../` traversal) → review `bin/`
   (spawn/shell) and web views.
4. Report findings in gstack's voice (confidence-gated, concrete exploit scenario per
   finding). This is exactly how the autonomous loop should invoke gstack report-only skills.

**Verified worked example:** see `references/gstack-manual-run-example.md` — a real
`/cso` + `/health` run against `Automated-Video-Generator` (v5.0.0) that produced a
genuine DOM-XSS finding and proved the methodology executes end-to-end. Use it as the
template for future repo audits.

### PITFALL 6 — node:test multi-glob FAILS in the Hermes terminal (verified 2026-07-23)
RAW `node --test "src/**/*.test.ts" "remotion/**/*.test.ts" "tests/**/*.test.ts"`
(with `--experimental-test-module-mocks`) exits 1 with **no output** in the
non-interactive Hermes terminal (the shell does not expand the globs the way the
interactive CLI does). Per-file runs work fine. **DO:** run the project's npm
script instead — `npm run test:unit > .gstack/test-run.log 2>&1` (background +
notify_on_complete). The output dir MUST exist first (`mkdir -p .gstack`) or the
redirect itself fails noisily. Parse `# tests`/`# pass`/`# fail`/`# skipped` and
`^not ok ` lines from the log. Lines ending `# SKIP host unreachable:` are
expected network skips, NOT failures. Same applies to any `node --test` with
multiple quoted globs under `terminal(background)`.

### PITFALL 7 — `patch` tool emits bogus TS6053 on git-worktree paths (verified)
Editing files inside a git worktree, the `patch` tool's auto-lint reports
`error TS6053: File 'C:\...\worktree\...' not found` — it runs tsc against the
absolute path outside the worktree cwd. **IGNORE this status;** the edit applied
correctly. Real verification is the in-worktree `tsc --noEmit` / `eslint` after
`npm install` finishes. (Also affects `read_file` partial-view warnings on
paginated files — re-read whole file before an overwrite, as the warning says.)

### Tool-name mapping addendum (Hermes runtime, verified 2026-07-23)
- `AskUserQuestion` (gstack gates) → **`clarify`** (Hermes tool). Prose fallback
  if clarify is unavailable.
- `Skill` (load a sub-skill) → **`skill_view(name="<subskill>")`** then follow the
  body. Sub-skills are already generated at `~/.hermes/skills/gstack/<name>/SKILL.md`
  (health, qa, ship, investigate, spec, plan-*, cso, review, etc.).
- State env that the bin helpers want: `export GSTACK_DIR=~/.hermes/skills/gstack`
  `export GSTACK_HOME=~/.gstack` before calling any `bin/gstack-*` helper.

### Verified /health numbers on Automated-Video-Generator (2026-07-23 baseline)
- `tsc --noEmit`: CLEAN (0 errors). `npx eslint src/ remotion/`: **4 errors** +
  1923 warnings (CI blocks on errors only). Tests: 569 run / 549 pass / 9 real
  failures / 11 network-skips. So "green" = 0 ESLint errors + 0 `not ok` (excl.
  SKIPs) + typecheck clean. CI file = `.github/workflows/ci.yml` (gates on
  typecheck + `npx eslint` + `npm run test:unit`). NEVER `git push` without the
  user's explicit "go"/"push".


The Hermes harness flags any turn that edited code but did not itself run the
verification command that turn with "Verification status: unverified". If you ran
`tsc`/`eslint`/`test` in a PREVIOUS turn and only commit/summarize this turn, the
flag fires even though the code is fine. **Rule:** after editing files for a
gstack health/review/cso pass, run the verification command(s) in the SAME turn you
edit, read the output, and only then claim "verified". Re-running is cheap (typecheck
~seconds, eslint ~60s, the AVG suite ~50s) and is the only accepted evidence. Even
if the prior turn's run was green, re-run on the current tree before stating pass.

### Repo-specific lint-gate knowledge (Automated-Video-Generator)
The AVG `eslint.config.mjs` is intentionally tuned so the gate is meaningful, not
noisy. Do NOT "fix" the remaining warnings into errors or rewrite the 700+ style
issues (`no-explicit-any`, `prefer-nullish-coalescing` are deliberate `warn`).
- `no-require-imports` / `no-var-requires` MUST stay **`warn`** — `ffmpeg-static`,
  `ffprobe-static`, and `edge-tts` have NO ESM default export / type decls, so they
  are loaded via `require()`. Converting to `import` breaks at runtime (the `.path`
  property disappears). This is the #1 thing a naïve "make lint green" pass gets wrong.
- `eqeqeq` is set to **`smart`** (allows idiomatic `== null` / `!= null`). Do not
  change to `always` — it would flag legitimate null-checks.
- Real, safe fixes that DO turn the gate green: `prefer-const`, `no-var`, genuine
  `no-self-assign` (e.g. a dead `x = x;` line), and unescaped `innerHTML` XSS sinks
  (use `textContent`/`createElement`). See `references/avg-lint-gate.md`.

## Parallel-agent isolation (when another Hermes/agent is editing the SAME repo)

gstack-driven work often runs *alongside* another agent building features in the same
repo (e.g. one agent runs `/autoplan` on `src/agentic/*` while you harden the rest).
**Never let your gstack pass touch the other agent's in-flight files.** Verified recipe:

1. **Fork an isolated branch from the last CLEAN commit** (not `main` with uncommitted
   edits): `git checkout -b gstack/<topic> $(git rev-parse <clean-sha>)`. The other
   agent's `M`/`??` files stay in the working tree, untouched.
2. **Scope to non-overlapping files only.** Audit which files you'll change, then
   `git diff <base> -- <your files>` to PROVE they had no other-agent edits before you
   start. If a target file is in the other agent's diff, skip it.
3. **Stage ONLY your files** at commit: `git add file1 file2 file3 file4` (never `git add -A`).
   Confirm with `git diff --cached --name-only` = exactly your set. The other agent's
   files remain `M`/`??` and uncommitted by you.
4. **Leave pre-existing lint debt in their area alone.** If your audit finds errors in
   the other agent's subsystem (e.g. `prefer-const` in `src/agentic/orchestrate.ts`),
   do NOT fix them — that's a collision risk. Note them in the PR body as "intentionally
   left for the other workstream."
5. **Push the isolated branch + open a PR for boss-approval** (see
   `github-no-gh-workflow` for the MSYS `--data @-` PR trick). The PR merges
   independently of the other agent's branch.

This lets gstack run as a true parallel sprint: you harden the product surface on one
branch while the other agent ships features on another, zero collisions.

## PITFALL 3 — gstack is HUMAN-IN-THE-LOOP (autonomy mismatch)

gstack is saturated with `AskUserQuestion` gates (plan approvals, design choices,
upgrade prompts, telemetry opt-in). The `headless` mode is explicitly `BLOCKED` at decision
points. Our autonomous money/company loop (Hermes cron → Paperclip → OpenClaw) is
unattended, so a gstack skill hitting a gate will **hang**.

**Use in autonomous mode only the report-only / non-interactive skills:**
- `/cso` — OWASP+STRIDE security audit (one-shot, safe)
- `/qa-only` — bug report, no code changes
- `/review` — with auto-fix OFF
Avoid `/office-hours`, `/plan-ceo-review`, `/autoplan`, `/design-review` in unattended
crons (they ask questions). Boss agents (Hermes/Paperclip) can invoke the interactive
ones where a human or boss makes the go/no-go call.

## FREE CODING AGENT: OpenHands (verified 2026-07-16, Windows)

When the user wants a **free** coding agent (no paid Claude Code key), OpenHands is the
drop-in coder. It runs on free OpenRouter models (e.g. `qwen/qwen2.5-coder-32b-instruct:free`)
or local Ollama. Hermes drives it; gstack verifies; ponytail disciplines. This is the
"complete free dev team" assembly. The install has TWO sharp edges — capture both.

**Edge 1 — Python version + isolated venv (CRITICAL).**
- `openhands-ai` >=0.10 requires **Python >=3.12**. On a box with 3.11/3.12/3.13, build the
  venv on 3.12 (NOT 3.11 — old pins 0.8-0.9.8 conflict and fail to resolve).
- Use `uv` (not `pip`) so the venv is clean: `uv venv --python 3.12 openhands-venv` then
  `uv pip install --python openhands-venv openhands-ai`. Installs `openhands-ai` 1.11.x
  (SDK reports 1.34.0). Venv lands at `~/openhands-venv`, ~865 MB.
- **The Hermes shell leaks `PYTHONPATH`** (points at Hermes' own venv, which has a broken
  `pydantic_core`). Running the venv's `python.exe` WITHOUT stripping it fails every import
  with `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`.
  **FIX — always launch OpenHands with the path stripped:**
  ```bash
  env -u PYTHONPATH OPENHANDS_SUPPRESS_BANNER=1 ~/openhands-venv/Scripts/python.exe -P -m <entry>
  ```
  (`-P` ignores `PYTHONPATH`/sys.path[0] mods; `env -u PYTHONPATH` removes the leak.)
  Verify import works: `env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -c "import openhands; print(openhands.__version__)"`.

**Edge 2 — OpenHands needs a RUNTIME BACKEND to execute code.**
- The agent cannot run code unless a backend is present: **Docker** (default) or an **SSH** box.
- On this Windows box Docker *client* is installed but the *daemon* is DOWN (`docker info`
  fails). So OpenHands installs + imports fine but **cannot execute** until Docker Desktop
  is started (or an SSH runtime is configured).
- Free-model config lives at `~/openhands-config.toml` (reuse the OpenRouter key from
  `~/.openclaw/openclaw.json` — grep `sk-or-v1-...`, never print it). Launch after Docker up:
  ```bash
  env -u PYTHONPATH ~/openhands-venv/Scripts/python.exe -P -m openhands <task> --config-file ~/openhands-config.toml
  ```
  If `python -m openhands` front-end entry is unavailable, drive via the SDK
  `openhands.sdk.conversation.LocalConversation` (params: `agent`, `workspace`, `plugins`,
  `max_iteration_per_run`, ...).

**Free OpenRouter coder models:** `qwen/qwen2.5-coder-32b-instruct:free` (recommended),
`mistralai/mistral-7b-instruct:free`, `meta-llama/llama-3.1-8b-instruct:free`. Free tier
rotates — verify at https://openrouter.ai/models?filters=free.

**Verified end-to-end proof (no Docker needed):** the gstack `/health` gate runs WITHOUT
OpenHands — Hermes writes ponytail-disciplined code, gstack verifies with `pytest`. A
demo at `~/team-demo` (stdlib-only slugifier, 6 passing tests) proved the loop.
Full copy-paste recipe in `references/openhands-free-coder.md`.

## ponytail — discipline layer integration (verified this session)

`DietrichGebert/ponytail` is the canonical *style* pack. It is free and very active
(84k★, commits within hours). Integration is lighter than gstack:

- **Clone:** `git clone --single-branch --depth 1 https://github.com/DietrichGebert/ponytail.git ~/.hermes/skills/ponytail`
- **Do NOT** expect the `.claude-plugin` / `.codex-plugin` / `.cursor/rules` files to load
  natively in Hermes or OpenHands. They are host-specific.
- **What works:** read `ponytail`'s core rules (look for the `ponytail:` marker convention
  and the "lazy senior dev" principles) and **inject them into every OpenHands task prompt**
  Hermes writes. Example injected line: *"Follow ponytail discipline: write the minimal code
  that solves the task; avoid premature abstraction; if you intentionally cut a corner,
  comment it with `ponytail:` and why."*
- **Why it matters on this box:** the user's machine is RAM-starved (~70–150MB free). A
  discipline layer that discourages over-engineering directly protects build stability.
- **Status:** optional, not required. The free team (Hermes + OpenHands + gstack) functions
  without it; ponytail is the *lean-code* add-on.

## Memory / resource note
- gstack's browse engine pulls Playwright + a 22MB ML classifier + Chromium. On a
  low-RAM box, invoke `/qa` / `/browse` sparingly, never inside a tight cron loop.
- Pin a version; do NOT `git pull` blindly inside an autonomous loop (fast-moving repo,
  daily commits, 400+ open PRs).

## Reference material
- `references/gstack-hermes-install-and-pitfalls.md` — exact copy-paste commands, the
  Bash evidence for the partial-port pitfall, the env-escape hatch, and the autonomy-safe
  skill subset. Read this before (re)installing gstack or any similar pack.
- `references/gstack-manual-run-example.md` — a REAL `/cso` + `/health` run against
  `Automated-Video-Generator` (v5.0.0): exact commands, real output, and the one
  actionable DOM-XSS finding. Use as the template for future repo audits when gstack
  skills are invoked as a methodology reference rather than loaded skills.
- `references/avg-lint-gate.md` — AVG-specific eslint gate knowledge: which rules are
  intentional (`require()` for ffmpeg-static/ffprobe-static/edge-tts, `eqeqeq: smart`),
  which fixes are safe (`prefer-const`, `no-self-assign`, unescaped-`innerHTML` XSS),
  and the exact verify commands to re-run in-turn.
- `references/openhands-free-coder.md` — FULL copy-paste recipe for OpenHands as the free
  coding agent: `uv` venv on Python 3.12, the `env -u PYTHONPATH ... -P` isolation fix,
  `~/openhands-config.toml` free-model setup, the Docker/SSH runtime-backend requirement,
  and the Docker-free `pytest` proof. Read this before installing/launching OpenHands.
- `references/gstack-hermes-runbook.md` — the TESTED Hermes runbook for driving gstack:
  exact skill paths, tool mapping (incl. ASKUserQuestion→clarify), running the TS
  health stack, node:test in background, worktree isolation, the patch-tool TS6053
  quirk, and the AVG ship gate. Read when actually executing a gstack workflow in Hermes.

## Verification checklist
- [ ] `bun --version` works (manual install if official installer failed)
- [ ] `~/.hermes/skills/gstack` cloned, `bun install` clean
- [ ] `gen:skill-docs --host hermes` produced >100 SKILL.md files
- [ ] Spot-check one skill: confirm it is NOT silently expected to resolve `~/.claude/...`
      without `GSTACK_DIR` set, and that you will use it as a methodology reference
- [ ] For autonomous use, restrict to report-only skills (see Pitfall 3)
- [ ] **OpenHands (free coder):** `uv venv --python 3.12 ~/openhands-venv` then
      `uv pip install ... openhands-ai`; import verified via `env -u PYTHONPATH ... -P`;
      `docker info` checked (daemon up?) before expecting code execution; free-model
      `~/openhands-config.toml` written reusing the OpenRouter key (never printed).
