---
name: git-worktree-isolation
description: Create an isolated git worktree to do hardening, refactoring, or feature work on a branch without disturbing another agent/branch that owns the main checkout. Covers the node_modules symlink trick (Windows + path-format pitfall), offline test verification inside the worktree, and the commit-then-push discipline.
---

# Git Worktree Isolation

## When to use
- Another agent/model is actively working on `main` (or another branch) of the same repo and you must NOT touch it.
- You need to do a batch of edits (hardening, refactors, test additions, bug fixes) that you want reviewed/committed separately, with zero risk of colliding with in-flight work.
- You want a real branch where failures can't corrupt the primary checkout.

This is the conflict-free way to "work on the project while someone else owns main."

## Core workflow
1. Pick a base commit (usually the repo's last commit, from `git log`) and a descriptive branch name.
2. Create the worktree:
   `git worktree add -b <branch> <absolute-path> <base-commit>`
   e.g. `git worktree add -b improvement/pipeline-hardening C:/one/avs-improvements fe22038`
3. `cd` into the worktree and do the work. Keep edits standalone + backward-compatible (don't delete/modify old code — add a shim if behavior must change).
4. Verify (typecheck + tests) INSIDE the worktree.
5. Commit locally. Push only after explicit user go-ahead.

## The node_modules problem (critical)
A fresh worktree has NO `node_modules` (it's gitignored). Running tests fails with
`Cannot find module 'axios'` / `ERR_MODULE_NOT_FOUND` even though the main checkout has everything installed.

Fix: symlink the main checkout's `node_modules` into the worktree.

### Windows (MSYS / git-bash)
Use `cmd /c` with a PLAIN Windows path (NOT an MSYS `/c/...` path) as the target:
```
cd /c/one/avs-improvements
cmd /c "mklink /D node_modules C:\one\Automated-Video-Generator\node_modules"
```
PITFALL: if you pass an MSYS-style or double-prefixed path (e.g. `/c/C:/one/...` or via `cmd //c`),
the symlink target becomes malformed and module resolution silently breaks — `tsx` then reports
`Cannot find module 'axios'` for packages that DO exist. The resolved link must point at a real
`C:\...` (or canonical `/c/...`) path. Verify with:
`node -e "console.log(require.resolve('axios'))"` → must print the main checkout's path.

### Linux / macOS
`ln -s /abs/path/to/main/node_modules /abs/path/to/worktree/node_modules`

The symlink is untracked (gitignored) so it will NOT be committed/pushed — safe.

## Verifying inside the worktree
- Typecheck: `npx tsc -p tsconfig.json --noEmit` (expect exit 0).
- Tests (node:test + tsx): `npx tsx --test "src/agentic/**/*.test.ts"` — glob works.
- Projects with injected fakes + offline unit tests: run the new tests here to prove no regression.
- Environment-dependent integration tests (need a live backend / venv / network) should `t.skip()`
  when the resource is absent, so the suite stays green offline. Pattern:
  ```ts
  test('X via live backend', async (t) => {
    if (!(await ensureBackend())) { t.skip('backend unavailable'); return; }
    // ... real assertions
  });
  ```
- Confirm the would-be-pushed diff is exactly the intended files:
  `git diff --stat origin/<branch>..HEAD` and `git check-ignore node_modules`.

## Commit / push discipline
- Commit locally as soon as a coherent unit is done.
- Do NOT push until the user explicitly says go (e.g. "push it"). Then verify, then push:
  `git push origin <branch>`.
- After push, confirm `git status -sb` shows `ahead 0` and `git log origin/<branch> -1` matches HEAD.

## Merge back into main

When the worktree branch is complete and approved, merge it back into `main`. See
`references/merge-back-workflow.md` for the exact step-by-step.

### TL;DR sequence
1. **Commit all pending worktree changes** — `git add -A && git commit`
2. **Dry-run merge** — `git merge --no-commit --no-ff <branch>` from the main repo
3. **Resolve conflicts** — prefer the more complete version (branch is typically a superset); fix escaping issues with Python, not sed
4. **Commit merge** with a summary of what the branch brought
5. **Verify** — typecheck + run the conflicted test file specifically
6. **Prune** stale worktree refs — `git worktree prune`
7. **Push** — `git push origin main`
8. **Post-push** — verify main worktree is still on `main` (bots may have switched it); see `references/merge-back-workflow.md §9`
9. **Docs audit** — update docs/ to reflect what the branch added; see `references/merge-back-workflow.md §10` for the systematic checklist

### Pitfalls
- **JS backslash escaping** in test assertions: patching via `patch` tool can double-escape. Fix directly with Python `writelines()` on the raw file bytes when escaping is critical — sed and fuzzy patch will both fight you.
- **`git worktree prune` must come after merge** — stale entries for deleted worktree dirs show as `prunable` in `git worktree list`. Prune to keep the list readable.
- **Dry-run first**: `git merge --no-commit --no-ff` lets you inspect the merge without committing. Abort with `git merge --abort` if conflicts are too complex, then fix the branch before retrying.
- **Vendored vs external dependencies in docs**: when updating documentation about third-party integrations, always verify whether the dependency is vendored in-repo (e.g. `src/speech/` for Voicebox) or installed externally. Docs describing an external setup for a vendored dep is a common stale-doc pattern — check `git log` for vendored-in paths and scan for `/* VENDORED */` or `VENDORED.md` markers in the source.

## User discipline (this user — PREM KUMAR) — MANDATORY on their projects
These rules came straight from the user and are non-negotiable for their repos:
- **NEVER delete or modify old code.** New behavior goes in a NEW file/module
  alongside the old one; if behavior must change, add a backward-compat shim that
  re-exports/forwards from the original path. The worktree is the safe place to do
  this without touching `main`.
- **Commit locally when a unit is done; PUSH only after an explicit "push" / "go".**
  Words like "continue" / "okay go" mean *keep working*, NOT push.
- **Everything must be testable, including visually.** For a video/asset pipeline,
  prefer real-engine smoke tests (download a real file, run ffmpeg, generate a
  real WAV) over unit-only or skip-gated checks. The user rejects "blocked" as a
  final answer — find a free/zero-cost way to prove each feature executes.
- **"finfigure dynamically"** = advanced features must be controllable from the
  job/input JSON (e.g. `agentic-scripts.json`), each one optional/off-by-default so
  omitting it leaves prior behavior intact. Encode every new capability as an
  optional field + a dispatch branch, never a forced global change.

## Pitfalls / what to look for
- **Retry loops that bail early**: a `for (...; !replaced; ...)` style loop stops retrying the moment
  a candidate object is produced, even if later re-verification REJECTS it. If a "replace" decision
  should retry up to N times, loop on the attempt count and only mark rejected if no replacement was
  approved. (Found & fixed in an agentic gateway stage this way.)
- Don't let the `node_modules` symlink get staged — keep it untracked/gitignored.
- Symlinks created with the wrong target path fail silently at test time, not at creation time.

## References
- `references/windows-node_modules-symlink.md` — exact commands + the double-prefix pitfall transcript.
- `references/worked-example-avs.md` — full reproduction of an isolated pipeline-hardening session
  (worktree creation, symlink fix, offline stage tests, gateway retry bug, graceful test skip, push).
