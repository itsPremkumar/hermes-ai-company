---
name: worktree-isolated-development
description: Run parallel/risky work in a git worktree instead of a branch on the main checkout — so two agents (or two models) can edit the same repo without colliding, and so you can verify a fix on a clean base commit. Covers the node_modules symlink trick for gitignored deps and the heavy-import-graph test-hang fix (extract pure function into a lightweight module with type-only imports).
---

# Worktree-Based Isolated Development

Run parallel/risky work in a **git worktree** instead of a branch on the main checkout. Two agents (or two models) can then edit the same repo without stepping on each other, and you can finish/abandon a line of work without disturbing `main`.

## When to use
- Another process/model is actively editing `main` (e.g. user says "another model is also working on the project").
- You want to harden / refactor / experiment but keep `main` shippable.
- You need to verify a fix on a clean base commit before merging.

## Create the worktree (Windows git-bash / MSYS)
```bash
cd /c/one/YourRepo
git worktree add -b feat/my-branch C:/one/my-worktree <base-commit>
```
- Use a Windows-style absolute path for the worktree dir (MSYS also resolves `/c/one/...`).
- Base it on the commit you want to branch from (e.g. `git log --oneline -1` → `fe22038`), **not** necessarily `HEAD`, if `main` has since advanced.

## Run the test suite inside the worktree
`node_modules` is gitignored, so a fresh worktree has **no `node_modules`** → imports fail (`Cannot find module 'tsx'`, `axios`, etc.).

**Fix: symlink the main checkout's `node_modules` into the worktree.**
- Windows (from inside the worktree): **use a PowerShell Junction** — `mklink /D` needs admin and silently fails from git-bash, and `cmd //c "mklink ..."` arg-passing is flaky under MSYS (reports exit 0 but creates nothing). This works first try, no admin:
  ```bash
  powershell -Command "New-Item -ItemType Junction -Path node_modules -Target 'C:\one\YourRepo\node_modules' | Out-Null; Test-Path node_modules"
  ```
- Linux/macOS:
  ```bash
  ln -s /abs/path/to/YourRepo/node_modules node_modules
  ```
Verify: `node -e "console.log(require.resolve('axios'))"` should resolve. Then run tests normally. The symlink is untracked — keep it out of commits (`git reset HEAD node_modules` if `git add -A` staged it).

## Pitfall: heavy import graph makes unit tests hang
If a test imports a CLI/module that transitively pulls the full orchestrator (pipeline, render, speech-backend, ffmpeg), `tsx` + `node:test` can take **200s+** just to load (observed: **238s before SIGTERM**). The suite may show some tests passing, then hang.

**Fix: extract the unit-under-test into a lightweight module.**
- Move the pure function (e.g. `buildPipelineRequest`) and any types it needs into a separate file.
- Use **`import type`** for every heavy dependency (`PipelineRequest`, `AgenticConfig`, …). Type imports are erased at runtime, so the lightweight module loads instantly and the test runs in **<0.5s**.
- Have the original module re-export/import from the lightweight one (backward-compatible).
- Test the lightweight module directly.

Detection tip: if `tsc --noEmit` passes but `npx tsx --test` times out, suspect a top-level heavy import in the test's import chain.

## Pitfall: ALL subtests pass but the test process hangs until timeout/cancel
A second, distinct hang class (AVS prod-hardening session): `node:test` shows every
subtest `ok`, then the file times out at 120s and reports `cancelled 1`. Cause is a
**lingering event-loop handle**, not slow tests. Diagnose in one shot with a probe
preloaded via `--import`:
```js
// probe-handles.mjs (must live INSIDE the project dir — tsx rejects /tmp file: URLs on Windows)
setTimeout(() => {
  for (const h of process._getActiveHandles?.() ?? [])
    console.log(h?.constructor?.name, h?.spawnargs?.slice(0,6));
  process.exit(99);
}, 45000).unref?.();
```
`node --import tsx --import ./probe-handles.mjs the.test.ts` → prints e.g.
`ChildProcess ["...ffprobe.exe", ...]`. Root causes found & fixed:
- **Child spawned with `stdio: ['pipe','pipe','pipe']`** — the open stdin pipe makes
  ffprobe/ffmpeg-style children linger after exit-worthy work. Use
  `stdio: ['ignore','pipe','ignore']` (+ `windowsHide: true`).
- **Guard timers not `unref()`'d** — `withTimeout` wrappers, "safety" 2x-timeout
  timers, stall-detector `setInterval`s. Every watchdog timer must be `unref()`'d
  AND cleared on the close/success path (assign it to a const so `close` can
  `clearTimeout` it — an anonymous safety `setTimeout` can never be cleared).
- On timeout-kill under Windows, `child.kill('SIGKILL')` misses conhost children;
  use `spawnSync('taskkill.exe', ['/F','/T','/PID', pid])` first.
Fix the whole class: grep the repo for `setInterval|setTimeout` without `unref` and
`stdio: ['pipe'` in spawn sites — sibling call paths usually share the flaw.

## Verify before committing
1. `npx tsc -p tsconfig.json --noEmit` → exit 0
2. `npx tsx --test "path/to/test.test.ts"` → all green
3. Stage only source: `git add -A && git reset HEAD node_modules`
4. Commit; **push only after explicit user go-ahead** (this user's standing rule).

## Pitfalls
- **Broken symlink path**: if you see `Cannot find module` and the symlink target looks like `/c/C:/one/...`, the MSYS path got concatenated onto a Windows path. Recreate it with a proper absolute Windows path (`C:\\one\\YourRepo\\node_modules`).
- **Don't commit the symlink**: `git add -A` can stage `node_modules` as a file even though it's gitignored. `git reset HEAD node_modules` first.
- **Base-commit drift**: if `main` advanced since you branched, deliberately rebase/re-branch from the new HEAD — don't assume your worktree is current.
- **WRONG-WORKTREE WRITE (cost a wasted turn in the AVS session).** When you have TWO worktrees open (e.g. an earlier `avs-improvements` from a prior task AND a new `avs-script-control`), the shell's default cwd may still be the OLD one. A `patch`/`write_file` with a relative path — or even an absolute path you *think* points at the new worktree — can silently land in the stale worktree. Symptom: edits "vanish" from the branch you're working on, or `git diff` on the new worktree shows nothing. **Protocol:** before the first edit of a session, `cd` explicitly into the intended worktree and `git rev-parse --show-toplevel` + `git branch --show-current` to confirm you're in the right one. After any edit, `git status` in the intended worktree to confirm the change appears there (and `git checkout --` the stray one if you hit the wrong tree).
- **False-alarm verification**: before "fixing" a feature, trace the actual data flow end-to-end (parser → converter → consumer). A suspected bug (e.g. a field "never reaches" the pipeline) may already work once you follow every hop. Confirm with a targeted test, not assumption. (In the AVS session a suspected `[Trim:]` parser bug was disproved by tracing `plan.ts` `parseTimeToSeconds` — no code change needed.)

## References
- `references/worktree-recipes.md` — full command recipes + the AVS case study (238s hang → `cli-job.ts` extraction with type-only imports).
- `references/worktree-audit-and-merge.md` — discovering stale worktrees, checking for uncommitted+unmerged code, merging back to main, conflict resolution, prune cleanup (real-world qa/production-hardening case study).
- `references/event-loop-leak-casebook.md` — AVS prod-hardening case study: active-handle probe, ffprobe stdin-pipe leak, git-ignored-asset test failures, MSYS /tmp + tsx --import gotchas.
