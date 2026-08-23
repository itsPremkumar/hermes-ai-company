---
name: multi-agent-swarm-ops
description: Dispatch parallel subagents (delegate_task) to improve a codebase, with RAM/concurrency discipline on a starved box, branch isolation, evidence verification, and safe merge. Includes strategic 3-wave production-hardening sweep pattern with specialist roles (Bug-Hunter, Security-Scanner, Test-Coverage, DevOps/Docker, Error-Handling, CI/CD) plus CI simulation techniques (mock leak detection, test-timeout hardening, env-clean test runs). Use when the user wants "multiple subagents", "a swarm", "trigger agents to do X/Y/Z", "production-ready", "enterprise-grade", or "improve this project with agents".
---

# multi-agent-swarm-ops

Run a multi-agent improvement sweep without OOMing the box or corrupting the repo.

## Hard constraints discovered (this box)
- `delegation.max_concurrent_children = 3`. More than 3 dispatched at once are
  REJECTED (returns a tiny error, no agents run).
- Box is RAM-starved (~800 MB–1.5 GB free of 6 GB). Running several agents that
  each spawn node/ffmpeg + the Voicebox GPU backend simultaneously OOMs and agents
  **interrupt** (status=interrupted, no summary). Free RAM FIRST (kill Chrome /
  stray node / the Voicebox backend) before a heavy sweep.

## The cardinal rule: DON'T launch into an occupied slot mid-flight
- Dispatch waves of up to 3. Wait for a slot to free (you get a BATCH COMPLETE
  notification) BEFORE launching the next agent.
- Launching a 4th agent while 3 run, OR launching into the slot a just-finished
  agent freed WHILE its branch is still checked out, causes **branch-switch chaos**:
  a later agent's `git checkout` lands on the wrong branch, commits land on the
  wrong branch, and `git clean -fd` can DELETE untracked agent WIP (recoverable
  from `git stash`, but messy).
- Fix applied this session: dispatch in strict waves of 3; only launch the next
  wave after BATCH COMPLETE; never `git checkout`/`git clean` while a subagent may
  be editing.

## Branch isolation + verify-then-merge
- Each subagent works on its own branch (tell it `NEW branch X off main`).
- Subagents RETURN SELF-REPORTS — they are NOT verified facts. A subagent may
  claim "316 pass, 0 fail" while having committed **broken, unverified code**
  (seen: typecheck errors, malformed test file, stray `}` in a reg file).
- BEFORE merging: run `npm run typecheck` + `npm run test:unit` YOURSELF on the
  branch. Do NOT trust the summary.
- If the branch is broken: fix it on a clean branch of your own, or re-implement.
  Do NOT cherry-pick an unverified subagent commit onto main.
- **The subagent may keep editing its branch AFTER it looks done** — leaving
  uncommitted files and continuously rewriting the same tree. Its branch is
  never safe to edit or cherry-pick while it runs. Takeover pattern:
  `git checkout -b fix/x main`, port/re-implement the good parts there (after
  READING the agent's real on-disk signatures), verify, then merge. Never edit
  the agent's live files in place — `write_file` blocks them and the agent may
  overwrite your changes anyway.
- **`write_file` silently blocks when a subagent holds the file** (returns
  "modified since last read" / "modified since you last read it"). The tool
  reports SUCCESS but writes NOTHING — so your patch appears applied, the agent's
  OLD version is still on disk, and you then build/test against a phantom state.
  Symptom: typecheck still fails on lines you "just fixed", or the agent's
  signatures don't match what you edited. FIX: when taking over a live subagent
  branch, RE-READ the file immediately before each edit, and prefer `patch`
  (fuzzy, with a unique surrounding context) over `write_file` for surgical
  changes; if `write_file` lies about success, re-read + `patch` + re-typecheck.
  Only trust on-disk truth: `git show` / `read_file` the actual bytes, then verify
  with `npm run typecheck` before claiming a fix.
- **Sibling subagents OVERWRITE the same working file concurrently.** Two+ agents
  pointed at the same path (e.g. both write `bin/fetch-lion-proof.ts`) will race:
  each `write_file` succeeds from the agent's view but the LAST writer wins, so
  your version can be silently replaced by a sibling's divergent copy mid-session.
  Symptom: your carefully-written file suddenly shows different content + a
  "(modified by sibling subagent 'sa-...' after this agent's last read)" warning,
  or `lint` reports a phantom file-not-found for YOUR path. FIX: (a) give each
  agent a UNIQUE filename (e.g. `bin/_lionproof_mine.ts`) when the task overlaps a
  sibling's; (b) after writing, COPY your version aside and run it from the copy
  (`cp bin/fetch-lion-proof.ts bin/_lionproof_mine.ts && npx tsx bin/_lionproof_mine.ts`
  inside the project dir so relative `../src` imports still resolve), then `rm` the
  temp; (c) do NOT trust the on-disk file after a sibling write-warning — re-read
  to confirm it's still YOUR version before running/verifying.
- **Sibling agents share the box's egress IP → shared-provider rate limits.**
  When several agents all hit the same external host (e.g. `upload.wikimedia.org`)
  at once, the IP gets HTTP 429/403-throttled, so even a correct download script
  fails most attempts. Symptom: identical titles return but bytes mostly 429.
  FIX: prefer the reliable provider (archive.org rarely 429s vs Wikimedia), add
  UA header + backoff + inter-request throttle, and accept that the METADATA
  (returned titles) proves relevance even when bytes don't land. (See
  `media-asset-relevance` → `references/live-download-proof.md`.)
- **The `verification_evidence` harness verdict is UNRELIABLE.** It reports
  `status: passed` even when `npm run typecheck` emitted errors (e.g. 46 errors).
  Trust the raw `grep -c "error TS"` count — 0 is pass, anything else is fail.
- Broken-subagent signature tells: `error TS1128` (stray `}`), mismatched
  option-object shapes between an op and its caller, a `.test.ts` with a syntax
  error. Re-read the agent's ACTUAL function/interface signatures on disk; they
  often differ from a "natural" design.
- **JSDoc `*/` in a comment closes the doc block prematurely** (confirmed bug).
  If a subagent's file has 10+ parse errors all around a comment block, look for
  `*/` embedded inside the doc text — e.g. `* Scans workspace/jobs/*/render/`
  — the `*/` is parsed as the end of `/**`, and everything after is raw text
  that fails to parse. **Fix:** change the offending text to avoid literal `*/`
  (use `{id}` or `⋆/` or remove the glob). Verify with `npx tsc --noEmit`.

## Provider API rate limits can kill a whole batch mid-scaffold — salvage, don't re-dispatch

(Verified 2026-08-01: deleg_c1b98ca5 — 3 builder agents for 3 new CLIs, ALL three died within
~5 minutes with `API call failed after 3 retries: HTTP 429: Rate limit exceeded. Please try again
later.`; api_calls counts of 5–12 show how early they stopped.)

- **Signature**: every task in the batch reports the same 429 retry-exhaustion error, and each
  did only a handful of API calls. The parent session's own tool calls keep working fine — the
  throttling hits the parallel LLM calls (free-tier providers), not you.
- **Do NOT immediately re-dispatch the batch** — you will re-trip the same throttle and burn
  another ~15 minutes. Instead, SALVAGE: the agents usually die AFTER writing most of the
  scaffolding (files land fast; the slow parts — install, iterate-tests, demos — are what got cut).
- **Salvage recipe (proven, all 3 projects recovered in ~10 min)**:
  1. `find C:/one/<proj> -type f -not -path "*/node_modules/*" -not -path "*/dist/*"` in each dir
     to see what actually landed.
  2. `npm install` if missing; the dead agents often installed deps BEFORE writing devDeps into
     package.json → fix with `npm install -D typescript @types/node` and re-run.
  3. `npm test` each — frequently ALREADY green (the code was complete; only the demos/commits
     were unfinished).
  4. Audit the test script's file list against `ls dist/test/` — a source test file the agent
     never wrote will be referenced and only blow up on CI (see `node-cli-scaffolding` →
     "Stale dist/ can mask a missing test source"); write the missing test yourself.
  5. Run the live demo, commit with the standard message, then ship (create repo → push → topics).
- Note the asymmetry: builder batches that die from rate limits are still ~80% productive — the
  parent finishing the last 20% is cheaper than re-dispatching.

## Recovering a green main when a subagent broke it
- If you pulled broken subagent work onto main (e.g. via cherry-pick) and main is
  now red: `git reset --hard <last-green-sha>` then
  `git push --force-with-lease origin main`. Force-push is allowed in the
  command_allowlist; safe here because no one else builds on the broken commit.
- Keep valuable salvaged artifacts: `git stash push -u -m "salvage" -- <files>`,
  then pop onto a clean branch.

## Minimum-viable-agent principle
- User may say "use minimum subagents". Respect it: do directly-committable work
  (docs, community files, reach) YOURSELF; reserve subagents for genuinely parallel,
  reasoning-heavy tasks (bug-fixing, feature-building). 2 subagents + direct work
  beat 7 interrupted ones.

## Fragile pattern: delegate_task bug-hunt fan-out returns NOTHING
Parallel READ-ONLY bug-hunt sweeps via `delegate_task` have FAILED repeatedly on
this box — `deleg_cfca30f6`, `deleg_38f0aed6`, and `deleg_8a437091` all exited
with **"delegation owner exited before recording a terminal result"** and returned
ZERO findings. Three strikes = a durable infra failure, not a fluke.
- **Do NOT rely on the fan-out for bug-hunting.** When the user says "find all bugs
  / hunt bugs across the system", do it DIRECTLY: read the files yourself (or
  `search_files`/`grep`), form hypotheses, and RUNTIME-VERIFY each with a tiny
  probe script (`node -e`, ffmpeg, a real Chrome render). Direct audit finds the
  same real bugs (and lets you verify + fix + visually-confirm in the same pass).
- Use `delegate_task` for other task classes (long builds, research) where it has
  worked; but for bug-hunts specifically, the direct path is faster AND actually
  returns results. If you do dispatch a bug-hunt batch anyway, treat "no findings"
  as "infra failed", not "code is clean" — fall back to direct audit.

## Strategic wave planning: production-hardening sweeps

A multi-wave sweep is the right response when the user says "trigger multiple specialist subagents",
"production-ready", or "enterprise-grade". Design waves as independent role-goal pairs that
don't depend on each other's output, so they can run in parallel.

### Wave pattern for production-hardening (proven in Automated-Video-Generator)

| Wave | Subagents | What each does | Verifies |
|------|-----------|----------------|----------|
| **1 — Foundation** | Bug-Hunter | Scans all source for TODOs/FIXMEs/HACKs/STUBs/BUGs, fixes them | typecheck=0 post-fix |
| | Security-Scanner | `npm audit --omit=dev` (or pip audit), secret scan across source + git history | 0 vulns, no secrets |
| | Test-Coverage | Finds untested `.ts` files, adds tests, runs CI-simulated test suite | CI=true + cleared env vars |
| **2 — Hardening** | DevOps/Docker | npm retry resilience, Docker build in CI, .dockerignore hardening | Docker build + CI pass |
| | Error-Handling | Audits all ops for: try/catch coverage, timeout guards, empty-input edge cases | typecheck=0 |
| | Documentation | Ensures all docs match current code, fixes stale comments/JSDoc | git status clean |
| **3 — Final Mile** | CI/CD-GitHub | Close related issues, FUNDING.yml, project board, release notes | gh operations verified |
| | Performance | Bundle size, cache headers, slow-path profiling | Before/after metrics |
| | Final-Verifier | `npm run typecheck` + full `npm run test:unit` + git status | Exit 0, clean tree |

### When to use each wave
- **Full sweep (all 3 waves):** user says "production-ready", "enterprise-grade", "final push"
- **Quick pass (waves 1+2 only):** user says "harden this project", "find real bugs before ship"
- **Pre-release (wave 3 only):** user says "final verification", "last check before merge"

### Role dispatch context template
Every specialist subagent context must include:
```
## Project: <path> (<language>, <package-manager>, <test-runner>)
## Role: <Role Name> — <one-line description>
## Current state:
- Typecheck: <status>
- Tests: <N total>, <N pass>, <N fail>, <N skip>
- Git: <branch>, <clean/dirty>
## Tasks:
<numbered, specific>
## Rules:
<project-specific constraints>
```
This avoids the "implementer has zero context" trap. When a subagent task fails
because its context was too thin, it was the dispatcher's fault, not the subagent's.

## CI simulation — detect CI-only test failures BEFORE push
Network-dependent tests pass locally but often fail on CI (network restrictions,
rate limiting, missing env vars). Simulate CI locally before pushing:

```bash
# Run in CI=true mode with all external-service env vars cleared
env -u OLLAMA_URL -u OLLAMA_MODEL -u VOICEBOX_PROFILE_ID -u VOICEBOX_API_URL \
  -u PEXELS_API_KEY -u OPENROUTER_API_KEY -u GEMINI_API_KEY \
  CI=true npm run test:unit
```

**What to look for:**
- If `--test-timeout` is NOT set in package.json, Node defaults to no timeout ->
  CI runner kills the job. **Fix:** add `--test-timeout=120000` to the test script.
- If `--test-concurrency` is NOT set, Node uses `os.availableParallelism()` (16 on
  a dev box, ~2 on CI). Run with `--test-concurrency=2` to catch race conditions.
- **Global mock leaks** — a test file that patches `axios.post`/`axios.get` at
  **module scope** and NEVER restores them in `test.after()` will silently pollute
  every subsequent test. Detection: grep for `Module-scope mock` patterns or run
  tests in isolation (`node --test file1.test.ts && node --test file2.test.ts`).

### Network-flaky test guard pattern (skipIfUnreachable)
External-provider tests (Wikimedia, Archive.org, NASA, MetMuseum) are a common
source of CI-only failures. The proven fix: a `skipIfUnreachable` helper that
probes the host with a 3s HEAD request and skips the test when unreachable, PLUS
a `process.env.CI` guard that proactively skips ALL external-provider tests in CI:

```typescript
async function skipIfUnreachable(url: string, ctx: any, timeoutMs = 3000): Promise<void> {
    if (process.env.CI === 'true') {
        ctx.skip(`CI env: skipping test for ${url}`);
        throw new Error(`CI env: skipping test for ${url}`);
    }
    try {
        await axios.head(url, { timeout: timeoutMs });
    } catch {
        ctx.skip(`host unreachable: ${url}`);
        throw new Error(`host unreachable: ${url}`);
    }
}
```

**Key details:**
- `ctx.skip()` in node:test v20+ marks the test as skipped but does NOT abort
  execution — always `throw` after it to prevent the test body from continuing.
- With `CI=true`, all external tests skip in ~3s instead of timing out at 30s+.
- Without `CI=true`, the HEAD probe (3s) catches the common case of a down host,
  but cannot prevent a slow host that passes HEAD but times out on the real GET.
  The `CI=true` guard covers that edge case for CI environments.

**Count affected:** In practice, 11 tests across 1 file (free-image.test.ts) need
this guard (3 Wikimedia + 2 Archive.org + 2 NASA + 2 MetMuseum + 2 FreeImageAdapter).

### Axios mock leak detection & fix
Pattern seen in practice:
```typescript
// BAD — module-scope mock, never restored
const originalPost = axios.post;
axios.post = async function(...) { ... };  // leaks to ALL other tests
const originalGet = axios.get;
axios.get = async function(...) { ... };

test.after(() => {
    // ... cleanup temp dir but FORGETS to restore axios
});
```
**Fix:**
```typescript
test.after(() => {
    axios.post = originalPost;   // restore to prevent test pollution
    axios.get = originalGet;
    // ... other cleanup
});
```

## Evidence to require from each subagent
- branch name, files changed, `npm run typecheck` result (0 errors), and
  `npm run test:unit` final count (pass/fail/skip). No evidence = not merged.

## Free-stack / scope guardrails to pass in context
- FREE only (no paid API); optional GPU/paid paths allowed ONLY as opt-in that
  degrades gracefully. Voicebox integration untouched unless explicitly in scope.
- Match surrounding code style; additive changes; don't delete tests to fake green.

## References
- `references/sweep-avg-v8-pattern.md` — Live session data from a real 3-wave production-hardening sweep: exact subagent findings, the axios mock leak fix, CI simulation results (399 pass / 0 fail / 12 skip), and a commit-message template.
- `references/recovery-recipes.md` — Disaster recovery: force-reverting a broken subagent commit from main, salvaging untracked agent WIP.
