# gstack Hermes runbook (tested 2026-07-23)

gstack's SKILL.md bodies are Claude-Code-shaped. They load and work in Hermes,
but several assumptions are wrong here. This file is the verified adaptation so a
future session starts already knowing it. (Captured driving /health + /review on
the Automated-Video-Generator TS/Node project.)

## Where gstack actually lives
- Suite: `~/.hermes/skills/gstack/` (NOT `~/.claude/skills/gstack/`).
- Already installed + generated (find it: `find ~/.hermes/skills/gstack -name SKILL.md | wc -l` > 100).
  The install recipe in the parent SKILL.md is moot if it's present — just load.
- Working/state dir: `~/.gstack` (portable; set `GSTACK_HOME=~/.gstack`).
- Bin helpers live at `~/.hermes/skills/gstack/bin/`. Verified runnable:
  `~/.hermes/skills/gstack/bin/gstack-config get proactive` → `true`.
  Set `GSTACK_DIR=~/.hermes/skills/gstack` before calling any bin helper.
- Sub-skill bodies: `~/.hermes/skills/gstack/<name>/SKILL.md` (health, qa, ship,
  investigate, spec, plan-eng-review, cso, review, etc.). Load any via
  `skill_view(name="<name>")`.

## Tool mapping (Claude Code → Hermes)
- `Skill` → `skill_view(name)` then follow the sub-skill's steps.
- `AskUserQuestion` → **`clarify`** (prose fallback if clarify unavailable).
- `Read/Edit/Write/Grep/Glob` → `read_file` / `patch` / `write_file` / `search_files`.
- `Bash` → `terminal`.
- `Agent` → `delegate_task` (but keep MAX 3 children; RAM-constrained box).

## Running the /health stack on a TS/Node project
1. Detect: `node -v`; read package.json `scripts` (typecheck/lint/test); check
   `tsconfig.json` / `eslint.config.mjs` / `biome.json`.
2. Run sequentially, capture counts:
   - Typecheck: `npx tsc -p tsconfig.json --noEmit` → count `error TS` lines.
   - Lint: `npx eslint src/ remotion/ -f unix` → grep severity-2 lines = ERRORS
     (CI blocks on errors only; 1000s of warnings are non-blocking noise).
   - Tests: see below.
3. `knip` and `shellcheck` are NOT installed in the default Hermes env → those
   /health categories are SKIPPED (redistribute weight), NOT failed. State this in
   the dashboard so you don't penalize the score.
4. /health Step 1's "persist `## Health Stack` to CLAUDE.md" gate is a no-op in
   Hermes — write the section directly if useful, skip the AskUserQuestion loop.

## Running node:test in Hermes background (PITFALL 6)
- RAW `node --test "src/**/*.test.ts" "remotion/**/*.test.ts" "tests/**/*.test.ts"`
  with `--experimental-test-module-mocks` FAILS in the non-interactive terminal
  (multi-glob form exits 1 with no output). Per-file runs work.
- DO: run the project's npm script instead —
  `npm run test:unit > .gstack/test-run.log 2>&1` (background + notify_on_complete).
- The output dir MUST exist before the redirect or the redirect itself fails:
  `mkdir -p .gstack` first.
- Parse from the log: `# tests` / `# pass` / `# fail` / `# skipped` and `^not ok `
  lines. Lines ending ` # SKIP host unreachable:` are expected network skips,
  NOT failures.
- Per-file smoke: `node --import tsx --test "path/to/file.test.ts"` works fine.

## Fix-pass isolation (worktree)
- Create a git worktree so main stays clean and commits stay atomic:
  `git worktree add -b <branch> ../<repo>-<branch>`
- Do all edits + verification in the worktree. Re-run /health there after install.
- `npm install` in a fresh worktree is SLOW on large dep trees — launch it
  background + notify, and keep applying source-only edits while it runs.

## Patch-tool false-lint quirk (worktree only, PITFALL 7)
- Editing files inside a git worktree, the `patch` tool's auto-lint reports bogus
  `error TS6053: File '...' not found` — it runs tsc on the absolute path outside
  the worktree cwd. IGNORE this status. Real verification is the in-worktree
  `tsc --noEmit` / `eslint` after `npm install` finishes.
- `read_file` on paginated files emits a "re-read whole file before overwrite"
  warning — honor it before a `write_file`/overwrite.

## Ship gate (AVS-style repos)
- Read `.github/workflows/ci.yml`: gates on `npm run typecheck` + `npx eslint`
  (errors only) + `npm run test:unit`. CI is RED if any fail — that is the
  objective "green" target before declaring done.
- NEVER push without the user's explicit "go" / "push".

## Verified /health numbers on Automated-Video-Generator (2026-07-23 baseline)
- `tsc --noEmit`: CLEAN (0 errors).
- `npx eslint src/ remotion/`: 4 errors + 1923 warnings (CI blocks on errors only).
  The 4 errors were: `prefer-const` (agentic-batch.ts), `no-useless-escape`
  (export-fx.ts), `no-unused-expressions` (orchestrator/ffmpeg.ts),
  `no-empty-object-type` (ccmixter.ts).
- Tests: 569 run / 549 pass / 9 real failures / 11 network-skips.
- "Green" = 0 ESLint errors + 0 `not ok` (excl. SKIPs) + typecheck clean.
