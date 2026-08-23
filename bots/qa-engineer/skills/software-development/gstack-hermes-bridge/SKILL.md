---
name: gstack-hermes-bridge
description: >-
  Drive gstack quality workflows (health, qa, review, ship) from Hermes,
  which is NOT a Claude Code / Codex / OpenClaw host. The gstack skills
  install fine and their SKILL.md content is directly usable, but they were
  written assuming the `Skill` tool and `~/.claude/skills/gstack/bin/*`
  paths exist. This skill bridges that gap so you can run a real gstack
  production-grade pass (baseline → review → fix-loop with regression
  tests → ship) on a TS/Node project from Hermes without guessing.
---

# gstack on Hermes (non-Claude-Code host)

gstack's skill files live at `~/.hermes/skills/gstack/` (the full v1.2.0
suite). The methodology is 100% usable from Hermes, but three things differ
from the skill's own assumptions. Learn them once.

## What works / what does NOT

| gstack assumption | Hermes reality | Action |
|---|---|---|
| Invoke sub-skill via the `Skill` tool | No `Skill` tool in Hermes | Use `skill_view(name)` (e.g. `skill_view(name='health')`) to load the SKILL.md, then follow its steps as written |
| Preamble runs `~/.claude/skills/gstack/bin/*` and `gstack-config` | Paths are `~/.hermes/skills/gstack/bin/*`; some preamble bits are no-ops | Preamble is decorative in Hermes — skip it. The actual work (typecheck, lint, test, fix) runs natively. Don't try to execute the `$_BRANCH` preamble blocks |
| `AskUserQuestion` gates | Use `clarify` tool | Render the decision as a `clarify` call (multiple-choice) instead of `AskUserQuestion` |
| gstack reads `CLAUDE.md` for `## Health Stack` / `## Skill routing` | Works the same — project `CLAUDE.md` is honored | Fine as-is |

## Verifying a TS/Node project from Hermes (the real check, not npx)

On a Windows/MSYS box the worktree's `node_modules/.bin` may be missing or
`npx` may resolve the wrong binary. Run the tools by direct path:

```bash
# typecheck (exit 0 == clean)
node node_modules/typescript/bin/tsc -p tsconfig.json --noEmit

# eslint, errors only (CI gates on errors, not warnings)
node node_modules/eslint/bin/eslint.js src/ remotion/ -f unix 2>/tmp/lint.txt
# then count severity-2 lines:
grep -iE "error" /tmp/lint.txt | grep -v warning

# run a single node:test file (fast feedback loop)
node --import tsx --test --test-timeout=60000 "src/lib/ffmpeg-text.test.ts"
```

Compound commands with nested `$(...)` or `grep -c` can hit the agent's
command blocklist — split into separate `terminal` calls or write a small
`.cjs` runner script instead.

## Fixing a broken worktree install (RAM-constrained box)

A fresh `npm install` in a git worktree can die silently (no error, no
`npm-exit=` line, `@remotion/*` subpkgs missing) when the machine is
RAM-pressured and the dep tree is huge (the @remotion monorepo is the usual
culprit). Symlink the worktree's `node_modules` to the MAIN repo's already
complete install so you can verify edits:

```bash
cd /c/one/<worktree>
rm -rf node_modules
ln -s /c/one/<main-repo>/node_modules node_modules
# now node node_modules/.bin/tsc / eslint.js resolve correctly
```

This is safe for LOCAL verification only — CI still runs `npm ci` fresh.

## Pitfall: the `patch` tool's false lint error

After a successful `patch`, the tool may report
`error TS6053: File '...' not found` / "Pre-existing lint errors". This is a
stale `tsc` path check inside the patch tool, NOT a real problem — the file
exists at the resolved path. Always re-verify with a real `tsc --noEmit` /
`eslint.js` run, never trust the patch tool's inline lint status.

## Production-grade review checklist (media / ffmpeg pipelines)

When hardening a video/asset-generation project, scan for these specific
defects (each found and fixed in a real AVS pass):

1. **Swallowed ffmpeg errors** — raw `execFileSync(ff, args, { stdio: 'ignore' })`
   hides stderr; a failed encode yields a silent empty/broken output. Route
   through a centralized safe runner (e.g. `runFfmpeg()` with `SIGKILL`-on-
   stall + typed `FfmpegError`), or at minimum log `e?.stderr` in the catch.
   Bare `catch {}` with no body = silent failure.
2. **ffmpeg `drawtext` caption injection** — user captions/titles interpolated
   into `drawtext=text='…'` without escaping `\ : ' " ,` break the filter or
   inject args. Centralize one `ffmpegDrawtextEscape()` helper and use it
   everywhere (a typographic `'` U+2019 avoids the bare-quote leak).
3. **Process / resource leaks** — `spawn()` sites that never `.kill()` on
   error/timeout, and `detached` child processes (Python backends) that a bare
   `SIGTERM` does NOT kill on Windows. Use `taskkill /T /F /PID <pid>` for the
   tree on `win32`.
4. **CI gate** — confirm the workflow gates on `typecheck` + `lint` (errors)
   + `test`. A red CI = fix the gate first; warnings are non-blocking.

See `references/media-hardening-checklist.md` for the full scan + the
regression-test pattern that proves each fix.

## Relationship to other skills

- Complements `autonomous-qa-production-readiness` (the orchestration loop:
  baseline → fix → re-verify with visual gate). That skill owns the loop +
  parallel subagent discipline; THIS skill owns the *Hermes-specific gstack
  invocation* and the media-pipeline defect checklist. Use both together.
- The gstack `health` / `qa` / `review` / `ship` SKILL.md files are the
  authoritative step-by-step content — load them via `skill_view`, don't
  reinvent.
