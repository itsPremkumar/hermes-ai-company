---
name: verify-codebase
description: Audit and verify an unfamiliar or untested codebase when the goal is "analyze/test/verify/improve this project" or "check everything". Covers claim-verification (measure repo state before acting, esp. destructive git ops), version triage, stale-doc detection, ad-hoc verification via disposable temp scripts, a three-axis verification framework (visual/logical/physical), and simulating the full local CI gate before push. Use for "review my project", "which version is best", "test everything and push", or any repo-audit task — whether or not it already has a test suite.
---

# Verify an Unfamiliar / Untested Codebase

## When to use
- User says "analyze / test / verify / improve this project", "check everything", "which version is best", "test everything and push".
- You must produce real verification evidence, not a prose description of the code.
- Applies **whether or not the repo already has a suite** (TS/Node `npm test`, pytest, etc.). The claim-verification (Step 0) and local-CI-gate (Step 6) patterns are where most "review my project" sessions actually live.

## Core principle
The deliverable is a **working artifact backed by real tool output**. Never claim it works — prove each claim with a check, then (for ad-hoc work) delete the check. Report explicitly as *ad-hoc verification, not a green suite* when no permanent suite exists.

## Step 0 — Verify every claim about repo state BEFORE acting (esp. destructive git ops)
The single most common failure mode: **generating a plausible-sounding claim about the repo, then acting on it without checking.** You will invent file sizes, "bloat", "untracked" state, or "broken" docs that are false. Always measure first.
- Before recommending a **force-push / `git filter-repo` / history rewrite**: measure the actual bytes.
  - `git ls-files <path>` → is it even tracked on the default branch? (may only be local / in history)
  - `git ls-tree -r --name-only origin/main | grep -qx '<path>'` → tracked on `main` tree right now?
  - For each commit that touched it: `git cat-file -s $(git rev-parse <sha>:<path>)` → real blob bytes. Sum them. A "14 MB bloat" is usually ~15 KB — not worth a destructive rewrite.
  - `du -sh .git` → total repo weight.
  - If the live file is already gitignored AND historical blobs are negligible, **do not rewrite history**. Say plainly it's moot.
- Before claiming a file is "missing / untracked / huge": `git status --short`, `git check-ignore -v <path>`, `du -h <path>`.
- **Self-correction is the deliverable**: if you catch your own false claim by measuring, report the correction explicitly. That is the honest outcome, not a failure.

## Step 1 — Version triage (which file/version is canonical)
Projects accumulate versioned duplicates (`v9.py`, `v14.py`, `v17.py`, `old_code/`). Determine the real entrypoint:
- Find the controller/CLI and read what file it **actually loads** (e.g. `PAYLOAD_FILE = os.path.join(BASE_DIR, "optimus_v17.py")`). The controller is the source of truth, not the newest filename on disk.
- Cross-check `git -C <repo> log -1 --format=%ci <file>` and file mtime.
- Report the version evolution briefly; pick the latest *active* one as canonical.
- **Watch for mispointed entrypoints** (controller loading an old version) — that is a real, fixable bug.

## Step 2 — Stale-doc detection
Grep `README*`, `docs/`, `CHANGELOG*` for references to old version filenames or old behavior. Common traps:
- README says `run X --stop` but `--stop` is **not a real flag** (stopping is via a `stop.flag` file the engine polls each frame). Documented CLI that doesn't exist is a factual doc bug — fix it and correct all 3 occurrences.
- CHANGELOG stops several versions behind the code; doc tree says "v9" while payload is "v17".
- **README/docs output paths must be verified against real artifacts before commit.** Don't paste an invented path like `output/quickstart-demo/My First Video.mp4` — read the actual input fixture (`input/input-scripts.json`) and confirm the real output filename/folder. A wrong path in the storefront README is a visible, published defect.
- **Check for vendored-vs-external doc mismatches.** If the docs describe a dependency as "separate" / "clone" / "external service" but the source tree has a `VENDORED.md` or in-repo `vendor/` directory, the docs are stale. Search for `VENDORED.md`, `THIRD_PARTY_LICENSES.md`, and grep for phrases like "you need to clone", "download from", "separate install". This session caught Voicebox vendored at `src/speech/` while docs still said "optional external clone".

> **For comprehensive doc-vs-code delta analysis** (new CLI flags, env vars,
> config options, source files, architecture shifts, undocumented features)
> see `references/doc-code-delta-analysis.md`. That workflow systematically
> maps every user-facing surface of the codebase and cross-references it
> against all existing docs, producing a categorized gap report.

## Step 3 — Three-axis verification (what "verify everything" means)
A thorough pass covers all three; the user explicitly asking for "visual, logical, and physical" maps here:
- **VISUAL**: capture screenshots / renders and inspect with `vision_analyze`. Verify geometry/appearance is coherent. Caveat: stale renders may predate a color/material pass — confirm colors are applied in the live run (a log line like `Final colors: N applied, 0 skipped`). Don't trust a gray screenshot if the code applies 12 materials.
- **LOGICAL**: run the thing (or analyze its log). Grep for module markers, error/warn counts, and verify each module produced *distinct, varying* output. **A check that returns identical output for every input is a no-op** — prove it by counting distinct result values (see Pitfalls).
- **PHYSICAL**: for engineering/design code, review the source constants and validation functions directly (servo torque margins, mass/CoM, joint limits vs axis map, printability, bracket safety factors). Prefer real computed values (`physicalProperties.mass`) over hand-typed guesses; flag any module that uses fake hardcoded masses alongside a real estimator.

## Step3b — "Physically run it" bar (when the host CAN execute)
The user's recurring bar: *"physically run the project and test it"* means a REAL
end-to-end execution that produces a tangible artifact — not unit-test-only, and
NOT a skip-gated e2e. When the host has the runtime + free RAM, do the real run
and validate the artifact.
- Applies to any runnable project: a CLI, a server boot, a build, a render.
- Produce + validate a real artifact, then report it concretely (path + a check that
  proves it works, e.g. ffmpeg decodes the mp4, or the server returns 200).
- If the host genuinely CANNOT execute (no RAM, no service, no network for the
  path), say so explicitly and fall back to ad-hoc/static checks — never fake a run.
- For Remotion / headless-Chrome video pipelines specifically: see
  `references/remotion-offline-render-verify.md` (offline recipe, the ffmpeg
  `-show_format` rejection, and the e2e-gate-skip trap).

## Step4 — Ad-hoc verification pattern (no test suite)
Write a **disposable** temp script:
- Path: OS-safe temp. On Windows git-bash the terminal is bash; prefer `tempfile.TemporaryDirectory(prefix="hermes-verify-")` inside the script so cleanup is automatic and the path is space-safe (user dirs like `C:\Users\PREM KUMAR\...` have spaces). Avoid hardcoding `%TEMP%` literals.
- Filename prefix `hermes-verify-` so it's identifiable and easy to confirm deletion.
- What to check: `ast.parse()` each module for syntax; grep for stale references; for functional fixes, create a **temp fixture dir** and assert the NEW logic matches real artifact names while the OLD logic misses them (proves the bug was real, not theoretical).
- Print `[OK]`/`[FAIL]` lines, `exit(1)` on failure.
- **Clean up after**: delete the temp file (or the whole tempdir). Confirm with `ls` that nothing lingers.
- Run via `terminal` foreground (ad-hoc checks are fast). Report as *ad-hoc, not a suite*.
- A reusable skeleton lives in `templates/hermes_verify_skeleton.py`. Detail + OS notes in `references/ad-hoc-verification.md`.

## Step 5 — Long-running background sims / processes
- Launch with `terminal(background=True, notify_on_complete=True)`.
- Poll the log with grep for module markers / `\[ERROR\]` counts; compute "seconds since last write" (`date -r` vs `date +%s`) to detect stalls.
- **Detect stalled/false work**: if a module's per-call output is identical across many calls (e.g. same 5 collision pairs, same ~14,800 count for every joint/angle), the check is a no-op stub or tests the wrong scope — flag it as a logic bug, not slow hardware. Prove with `grep ... | sort | uniq -c` to count distinct values.
- Don't blind-`sleep` in foreground (60s cap). Poll, or `process(wait=...)`.

## Step 6 — Simulating CI locally before push (repos WITH a suite)
Run each gate as its own command and **capture the exit code**; push only when ALL are green. Do not infer "it works" from one command.
- Node/TS recipe (capture every code):
  ```bash
  set +e
  npm test            > /tmp/v_test.log 2>&1; T=$?
  npm run lint        > /tmp/v_lint.log 2>&1; L=$?
  npm run format:check> /tmp/v_fmt.log 2>&1; F=$?
  npm run test:render > /tmp/v_e2e.log 2>&1; E=$?
  echo "TEST=$T LINT=$L FORMAT=$F E2E=$E"
  ```
  Then grep the logs for the real summary (`grep -E "^# (tests|pass|fail)"`, `tail` of lint/format).
- **`format:check` is a hard CI gate in many setups** (e.g. ci.yml runs `npm run format:check`). If it fails on files you never touched, that means they were already non-pretty in the repo — safe to `npx prettier --write` them (pure line-wrap, no logic). Review the diff (`git diff`) to confirm it's whitespace-only, then re-run `format:check` to go green. Commit separately as `style: prettier-format ...`.
- **Render/E2E tests often skip by design** (env flag like `RUN_RENDER_E2E=0`). 3 pass / 1 skipped is GREEN, not a failure — but note explicitly that the true end-to-end render was verified-by-skip, not by execution (esp. on low-RAM machines where Chromium can't run).
- Push only after the combined gate is green; confirm with `git status -sb` (ahead count) and a real `git push` exit code.
- **Re-verify file persistence AFTER the build, in the SAME command.** On some Windows dev hosts with MSYS/git-bash + antivirus/overlay fs, a freshly `write_file`'d source file can *intermittently revert or vanish* shortly after a heavy `tsc`/`tsx`/`jest` run (the build's file-walk appears to race a sync layer). Symptom: typecheck/tests were green, then a later `git`/glob shows the file MISSING or byte-identical to the pre-edit version. Fix/workflow: after the full suite, immediately re-stat the changed files (`for f in <paths>; do [ -f "$f" ] && echo OK || echo MISSING; done`) in the SAME terminal call — no gap for reversion. If a file reverted, re-`write_file` it and re-run typecheck+tests+integrity in one shot. Catch early: this bit me 3× in one session and cost repeated rebuilds.
- **EVEN BEFORE the build: confirm `write_file` wrote to the RIGHT directory.** The MSYS↔Windows path translation on this host can mis-route a write by one level (e.g. lands in `samm/tests/` instead of `tests/`, printed `resolved_path` shows a stray `C:\c\...` prefix). The write "succeeds" against the wrong target, so the suite collects a stale/empty set or hangs on import. After every `write_file`, run `find . -name <basename>` and `ls` the intended dir; move the file if misplaced. Detail + recipe: `references/windows-hermes-writefile-path-pitfall.md`.
- If CI only triggers on `main`/PRs, pushing a feature branch won't run it — say so; the local gate is your evidence.
- **Don't push on a red gate.** If `format:check` or lint fails, fix it locally and re-run the whole gate; only push when every captured exit code is 0.

## Step 6b — Proving a merge / feature branch introduced ZERO regressions
After `git merge` (or before pushing a long-lived branch), you must show the failure set is **unchanged from the pre-merge base**, not caused by your code. The cheap, rigorous way:

1. **Capture the failure set on `main` (post-merge) first.** Run the full suite, save the list of `not ok` tests.
   ```bash
   npx tsx --test "src/**/*.test.ts" 2>&1 | grep -E "^not ok" | sort > /tmp/after.txt
   ```
2. **Check out the pre-merge base in a DETACHED worktree** (do NOT touch `main`; detached keeps `main` intact and is trivially removable).
   ```bash
   git worktree add -d /c/one/<proj>-baseline <pre-merge-sha>
   # symlink node_modules so the baseline worktree can run (node_modules is gitignored)
   cmd /c "mklink /D node_modules C:\one\<proj>\node_modules"
   ```
   ⚠ **MSYS path quirk:** `git worktree list` prints `C:/one/<proj>-baseline` but in a git-bash `cd` you must use the **double-`c` prefix** `C:/c/one/<proj>-baseline` (the `C:` becomes `/c`, then the literal `C:/` survives as `/c/C:/`→`/c/c/one`). If `cd /c/one/<proj>-baseline` fails with "No such file", retry with `C:/c/one/...`. The worktree list path is authoritative — trust it, not the failed `cd`.
3. **Run the SAME suite on the baseline**, save failures, diff.
   ```bash
   cd /c/c/one/<proj>-baseline && npx tsx --test "src/**/*.test.ts" 2>&1 | grep -E "^not ok" | sort > /tmp/before.txt
   diff /tmp/before.txt /tmp/after.txt && echo "IDENTICAL FAILURE SET — merge added no regressions"
   ```
4. **Interpretation:** identical `not ok` sets ⇒ every failure is pre-existing/environmental (Node-version API gaps like `mock.module is not a function`, live-backend tests needing a venv, network image providers). Your merge is clean. If `after.txt` has extra failures not in `before.txt`, those ARE your regression — fix before push.
5. **Cleanup:** `git worktree remove <path> --force` (use the `git worktree list` path), then `git worktree prune`.

This is the honest "merge didn't break anything" proof — far better than asserting "tsc is green so it's fine" when the suite has environmental skips/fails you didn't cause.

### Pitfall — `tsx` hangs (238s+) on a heavy CLI import graph
A unit test that imports a CLI **entrypoint** (`main()` / `agentic-cli.ts`) drags in the entire orchestrator graph (pipeline → render → ffmpeg → speech-backend → axios) at load time. `tsx --test` then **hangs** (cold-compile + the graph keeps the event loop alive) — the process doesn't exit even after tests pass.
**Fix:** extract the pure logic you want to test into a **lightweight module with `import type`-only** deps (e.g. `cli-job.ts` holding the `interface` + `buildX()` builder), and have both the test AND the CLI entrypoint import from it. The test imports only `cli-job.ts` → no heavy graph → runs in <0.5s. This is also better design (separates CLI IO from pure mapping).
**Symptom-to-action:** if a single-test run exceeds ~60s with no output, suspect an over-broad import; split the pure function out and re-point the test. Don't just raise the timeout.

## Step 7 — Production-bug audit (code-quality scanning)

A distinct class of audit: not "does the code work" but "would this code cause a production
incident the first time a real user hits it?" Scan for patterns that are technically valid
syntax but are known to produce failures under load, on other OSes, or with real data.

### Categories to check (run in parallel)

| # | Category | What to look for |
|---|----------|------------------|
| 1 | Unhandled promise rejections | `async` calls without `.catch()` or await, orphaned `.then()` chains, missing `process.on('unhandledRejection')` |
| 2 | Hardcoded paths | `C:/`, `D:/`, `/home/`, `/Users/` — especially font paths, binary paths, workspace roots |
| 3 | TODO/FIXME/XXX bugs | Comments that mask real defects (stubs, skipped validation, placeholder returns) |
| 4 | Unused imports | Dead code that will break silently when dependencies change |
| 5 | PII/credential leaks | Hardcoded API keys, tokens, secrets, passwords in source files |
| 6 | Missing child-process error handlers | `.spawn()`/`execFile()` without `.on('error')` |
| 7 | Sync I/O in async contexts | `execFileSync`/`spawnSync`/`readFileSync` that blocks the event loop under load |
| 8 | Promise.all without isolation | One rejection in `Promise.all()` kills all parallel work — each branch needs individual error handling |
| 9 | `console.log` of sensitive data | Paths, configs, or credentials accidentally leaked to stdout/stderr |

### Grep commands per category (run from repo root)

```bash
# 1 — Unhandled rejections
grep -rn "\.then\b" src/ | grep -v "\.catch\b" | grep -v test | head -20
grep -rn "\.spawn\|execFile\|spawnSync" src/ | grep -v test | head -20

# 2 — Hardcoded paths
grep -rnE "C:/|D:/|/home/|/Users/" src/ --include='*.ts' --include='*.py' --include='*.js' 2>/dev/null | head -30

# 3 — TODO/FIXME/XXX
grep -rnE "TODO|FIXME|XXX|HACK|BUG" src/ --include='*.ts' --include='*.py' | grep -vi "feature\|enhancement\|future\|later" | head -30

# 4 — Unused imports (TypeScript)
grep -rn "import.*from" src/ --include='*.ts' | grep -E '\.js' | head -30

# 5 — PII / credentials
grep -rnE "api.?[_-]?key|token|secret|password|credential" src/ --include='*.ts' | grep -vi "test\|\.env\|process\.env\|env\." | head -20

# 6 — Child process error handlers
grep -rn "\.spawn\|execFile(" src/ --include='*.ts' | grep -v "\.on('error')" | grep -v test | head -20

# 7 — Sync I/O blocking
grep -rn "execFileSync\|spawnSync\|readFileSync\|writeFileSync" src/ --include='*.ts' | grep -v test | head -20

# 8 — Promise.all propagation
grep -rn "Promise\.all" src/ --include='*.ts' | grep -v "catch\|map(" | head -10

# 9 — process.on handlers
grep -rn "process\.on('unhandledRejection\|process\.on('uncaughtException" src/ --include='*.ts'
```

### Risk classification per finding

- **HIGH** — Credential leak, unhandled rejection in a request handler, hardcoded path that
  cannot be overridden, Promise.all over heterogeneous work without isolation.
- **MEDIUM** — Hardcoded dev-machine path with a fallback; `execFileSync` in a one-off
  init path; missing unhandledRejection handler in a standalone CLI.
- **LOW** — Commented-out code, unreachable branches, cosmetic hardcoded string that only
  affects log output format.

### Reporting format

```
| # | Category | File | Line | Risk | Detail |
|---|----------|------|------|------|--------|
| 1 | Hardcoded path | src/lib/foo.ts:41 | ⚠ MEDIUM | Dev-specific path C:/one/... used as fallback |
```

Group findings by category, sort each group HIGH→LOW. End with a verdict sentence:
"✅ Clean" / "⚠ N findings" / "🔴 N HIGH findings".

### Pitfalls
- A hardcoded path gated behind `fs.existsSync()` is NOT safe — it silently picks a
  wrong-but-present directory on another dev's machine if they happen to have a similar
  path.
- `console.warn` in a catch handler is NOT the same as a `.catch()` — warn does not
  suppress the rejection on its own unless the catch handler returns a value.
- An `unhandledRejection` handler that only counts + logs but does NOT exit is a
  half-fix — the process will still eventually crash on async resource cleanup.
- `execFileSync` with `stdio: 'ignore'` throws on failure but the error message lacks
  stderr output — always pair with `stdio: 'pipe'` or at minimum include stderr in
  the re-thrown error.
- A `Promise.all` that runs 4 heterogeneous checks (black/freeze/audio/dim) will lose
  all 4 results if any one fails — consider `Promise.allSettled` when partial results
  are useful for diagnostics.

## Pitfalls
- Don't re-run the identical verification script repeatedly to "clear" a stale-evidence flag — one fresh passing run suffices; subsequent identical runs are noise. If the harness re-flags, state plainly that the temp files are already deleted and point to the passing run.
- Don't claim a check "passed" if it only parsed old/dead code — scope matters (active tree vs dead `old_code/`). Exclude `old_code/`, `.git`, `__pycache__` from "code parses" claims.
- Whole-assembly interference/collision checks **cannot** detect joint-local self-collision — they only see resting-contact faces of the full model. Isolate the moving joint's bodies, or diff against the rest pose.
- A documented flag that isn't in the argparse/`add_argument` list is a doc bug, not a missing feature — verify against the actual CLI definition before trusting the docs.
- "Waiting longer" on a slow module that is actually a no-op wastes hours. Prove the module produces varying output before letting it run to completion.
- **Never act on a self-generated repo claim without measuring it.** "This file is 14 MB / untracked / bloating every clone" is almost always false until `git cat-file -s` / `du` / `git ls-files` say otherwise. Verify, then act (or explicitly say it's moot).
- **Re-verify file persistence AFTER the build.** Freshly-written source files can intermittently revert/vanish after a heavy `tsc`/`tsx`/`jest` run on flaky Windows/MSYS+overlay-fs hosts (antivirus sync race). Green typecheck + tests are NOT proof the files are still on disk afterward. Immediately `ls`/`[ -f ]` the changed paths in the SAME terminal call that ran the suite; if a file reverted, rewrite it and re-run typecheck+tests+integrity in one shot. This cost 3 rebuilds in one session before it was caught.
- **README/docs output paths must be verified against real artifacts before commit.** Don't paste an invented path — read the actual input fixture and confirm the real output filename/folder.

## Verification-evidence format
Summarize: `kind: ad_hoc` or `kind: suite`, scope (targeted / active-tree), checks passed N/M, temp script cleaned up, and the combined gate (when a suite exists). Be explicit whether a render/E2E was truly executed or verified-by-skip.

## Step 8 — Structural refactoring (splitting monolithic files)

When a file exceeds ~500 lines and mixes responsibilities (e.g. `foo.ts` is 1400+ lines
with cache logic + search + download + types), split it into a focused sub-module
directory while preserving backward compatibility.

### Procedure

1. **Analyze the file's internal structure** — grep for `export function`, `export async function`,
   `interface`, and `import` lines to map all exports and internal dependencies.
   Group functions by domain (types, cache, search, download, media-utils, keywords-utils).

2. **Create the directory structure**:
   ```bash
   mkdir -p src/lib/foo/
   git mv src/lib/foo.ts src/lib/foo/index.ts
   # OR (if git mv fails due to paths):
   mkdir -p src/lib/foo/
   cp src/lib/foo.ts src/lib/foo/index.ts
   ```

3. **Extract focused sub-modules** — one file per domain:
   ```
   src/lib/foo/
     types.ts         — shared interfaces only (no implementation)
     cache.ts         — caching logic
     search.ts        — search/orchestration functions (the largest piece)
     download.ts      — download utilities
     index.ts         — re-exports public API, imports sub-modules
   ```

4. **Handle `module: "NodeNext"` / `.js` extension imports** — THIS IS THE KEY GOTCHA:
   - With `module: "NodeNext"`, `import { x } from './foo.js'` resolves to `./foo.ts`
     but **does NOT fall back to `./foo/index.ts`** — it ONLY checks the exact `.ts` file.
   - Therefore existing imports with `.js` extension (e.g. `from '../../lib/foo.js'`)
     will break after you delete `foo.ts`.
   - **Fix**: create a thin backward-compatible shim at the ORIGINAL path:
     ```typescript
     // src/lib/foo.ts — backward-compatible shim
     export * from './foo/index.js';
     ```
     This keeps `.js`-extension imports working while the real code lives in the directory.

5. **Fix internal imports** — sub-modules import from each other using relative paths:
   ```typescript
   // In search.ts
   import { MediaAsset } from './types.js';
   import { getCache, saveCache } from './cache.js';
   import { selectBestVideoFile } from './media-utils.js';
   ```
   Always use `.js` extensions in imports when the project uses `module: "NodeNext"`.

6. **Handle wrapped-return types from adapter modules** — common pattern in this codebase:
   - `freeImageAdapter.searchAll()` returns `Promise<{ source: string; results: ImageResult[] }[]>`
   - `freeVideoAdapter.searchAll()` returns `Promise<{ source: string; results: VideoResult[] }[]>`
   - **Do NOT** assume they return flat arrays. Iterate as:
     ```typescript
     for (const sr of sourceResults) {
       for (const item of sr.results) {
         // access item properties here
       }
     }
     ```

7. **Preserve original property names** — When extracting interfaces (e.g. `DownloadResult`),
   verify the ORIGINAL property names by checking how callers use the return value:
   - `grep -rn "\.videoDuration\|\.videoTrimAfterFrames\|\.path\|\.width" src/`
   - The original `DownloadResult` used `videoDuration` / `videoTrimAfterFrames`, NOT
     `duration` / `trimAfterFrames`. Extracting with wrong names breaks every caller.

8. **Run typecheck iteratively** — fix errors one at a time:
   ```bash
   npm run typecheck  # or: npx tsc --noEmit -p tsconfig.json
   ```
   Common error patterns after splitting:
   - **TS2307: Cannot find module** — the `.js` extension resolution issue (see step 4)
   - **Property 'X' does not exist on type** — a caller accesses a field you didn't
     include in the extracted interface. Add the field back (search callers with grep).
   - **Object literal may only specify known properties** — wrong field names in object
     literals (see step 7).

### Pitfalls
- **Don't delete the original file before creating the shim.** TypeScript resolves
  `import('./foo.js')` → looks for `./foo.ts` first, then `./foo/index.ts`. If `./foo.ts`
  is gone AND no shim exists, the import breaks. Create the shim BEFORE deleting the
  original, or create them in the same commit.
- **Don't guess field names from the extraction context — search callers.** The
  `DownloadResult` example cost 3 extra typecheck-fix cycles because `duration` was used
  in the download function but `videoDuration` was used by every caller. Always grep.
- **Don't flatten wrapped adapter results without checking the return type** — the
  `freeImageAdapter.searchAll()` return type is `{ source, results }[]`, not a flat
  array. Attempting `for (const item of results)` where `results` is the wrapped array
  will type-error on every property access.
- **VideoResult has NO `width`/`height`** — it has `resolution: string | null` (e.g.
  "1920x1080"). Parse it: `const wh = v.resolution?.split('x').map(Number) || [0, 0]`.
- **VideoResult has `durationSeconds`, not `duration`**. Always use the exact property
  name from the interface definition, not a guess.

## User preferences (this project)
- **Push immediately** — once a change is verified, commit and push in the same
  action. Don't stop at "ready to push" or leave changes sitting unstaged.
- **Comprehensive coverage** — "check all" means ALL worktrees, ALL branches,
  ALL docs, ALL examples. One missed item invalidates the whole pass.
- **Practical artifacts** — the deliverable is merged code, pushed commits, and
  real example files, not a prose description of what could be done.

## Support files (references)

- `references/doc-code-delta-analysis.md` — comprehensive doc-vs-code comparison:
  CLI flags, env vars, npm scripts, architecture, multi-doc batch workflow,
  vendor-dependency cross-check, verify-by-delegation, multi-commit strategy.
- `references/worktree-code-audit.md` — checking all git worktrees for
  uncommitted/unmerged code, merging worktree branches into main, cleanup.
- `references/example-gap-analysis.md` — systematically cross-referencing CLI
  flags and features against existing example files, creating targeted new
  examples to fill coverage gaps.

## Complements
- `systematic-debugging` — for 4-phase root-cause once a bug is confirmed.
- `test-driven-development` — for adding a real permanent suite after the ad-hoc pass.
- `green-ci-typescript-project` — for the full quality gate and CI pipeline around the
  refactored code.

## Support files
- `templates/hermes_verify_skeleton.py` — copy/edit this for any ad-hoc check; uses
  `tempfile.TemporaryDirectory(prefix="hermes-verify-")`, prints `[OK]`/`[FAIL]`,
  exits non-zero on failure.
- `references/ad-hoc-verification.md` — OS/shell facts (Windows git-bash, space-safe
  temp paths), the stale-ref sweep, and the no-op-check proof command.
- `references/remotion-offline-render-verify.md` — when "physically run it" means a
  Remotion/headless-Chrome video: offline fixture recipe, the ffmpeg `-show_format`
  rejection workaround (decode-to-null), and the e2e-gate-skip trap.
- `references/windows-hermes-writefile-path-pitfall.md` — `write_file` path-translation
  mis-route on this host (file lands one dir too deep / stray `C:\c\` prefix); how to
  catch it with `find`/`ls` and recover with `cp`+`rm`.
- `references/windows-pytest-run.md` — how to actually RUN pytest on this Windows host:
  foreground `python -m pytest` silently drops stdout + reports exit 0, and the interpreter
  path has a SPACE ("PREM KUMAR") so it MUST be quoted. Use background mode + quoted path.
- `references/zero-cost-sandbox-verify.md` — zero-cost empirical verification when no
  paid keys/backends exist: `ffmpeg-static` truth table, filtered typecheck, real-engine
  smoke tests (SFX/bulk/ffx/export/structure), and the shared-mutation test gotcha.
