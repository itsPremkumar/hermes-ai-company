---
name: code-quality-fix-campaign
description: >-
  Systematic multi-bug fix campaign: audit all code-quality issues across
  any codebase, prioritize by real impact, then fix one-by-one with
  verification after each fix and commit-before-approval discipline.
  Bridges the gap between source-audit (catalog only) and
  systematic-debugging (single-bug root cause).
---

# Code Quality Fix Campaign

## Overview

When an audit reveals a backlog of bugs (FIXMEs, `: any`, `@ts-ignore`,
`console.log`, broken providers), fix them systematically — never in one
big batch. Each fix gets verified and committed independently so nothing
breaks silently and every change is revertable.

## User Preference

The user's standing rule is:

> **Fix bugs one-by-one, verify each, commit before approval.**
> Never batch unrelated fixes into one commit.
> Never delete/modify old code when adding new architecture — build
> standalone alongside, then add backward-compatible shim.

Follow this pattern literally. One `patch` call, one commit per fix.

## Trigger

Use when:
- User says "fix all the bugs one by one"
- User says "completely fix all the available bugs"
- You've run an audit (via `source-audit` or `search_files` sweep) and have
  a catalog of issues
- A previous session catalogued issues but didn't fix them (resume from
  the catalog)

## The 5-Phase Workflow

```
Phase 1:  AUDIT      — catalog ALL issues across all dimensions
Phase 2:  PRIORITIZE — rank by real output impact, not code smell
Phase 3:  FIX × N    — one fix per iteration, verify each
Phase 4:  VERIFY     — full typecheck + test suite + VISUAL verification (render + inspect)
Phase 5:  PRESENT    — summary table, commit log, user approval → push
```

## Phase 3b: Parallelizing independent fixes (subagent waves)

When the audit yields many **independent, well-isolated** fixes (e.g. 3
different modules each with its own failing tests), dispatch them as
parallel leaf subagents instead of fixing serially. The user's RAM limit caps
this at **3 concurrent** — use waves `3 → 3 → 1` for 7 tasks.

- Write a self-contained goal per subagent: the exact failing assertions
  (copy them from the test file), the source file:line, the fix rules
  (root-cause only, no delete/modify old code, shim if signature changes),
  and the verification command. Do NOT make subagents guess.
- Each subagent commits **locally only** (never push).
- After all return, **re-verify yourself** (subagent self-reports are not
  trusted): run the targeted test suites + full `npm test` + typecheck.
- Pitfall: concurrent edits to the SAME file cause mid-edit races (one
  subagent reported a transient `TS1470 import.meta` error from a sibling's
  in-flight edit). Resolve by running typecheck after merge; the race
  resolves once both commits land.
- See `references/production-readiness-techniques.md` for the full pattern
  and the reusable goal-prompt template.

## Phase 4b: Visual verification (the part most agents skip)

For any project that renders video/images, "tests green" is NOT enough.
Actually render a real sample and inspect the output:

1. Produce a real artifact end-to-end (offline if possible — use local
   assets / stubbed adapters so the run doesn't depend on network).
2. `ffprobe`/`ffmpeg -i` the output: confirm Video + Audio streams exist,
   duration matches, correct dimensions/orientation.
3. **Black-frame check** (mandatory for video):
   `ffmpeg -i out.mp4 -vf blackdetect=d=0.3:pix_th=0.15 -f null -`
   → expect "NO black frames" (no `blackdetect` line in stderr).
4. Extract 3–5 frames (`ffmpeg -i out.mp4 -vf fps=1/2 -vframes 3 frame_%02d.png`)
   and run `vision_analyze` on each: confirm real rendered scenes (not
   blank/garbage), correct assets used, captions legible.
5. If visual check FAILS: root-cause (render stage? codec? missing asset?)
   and fix — don't just assert "render succeeded".

This is the difference between "tests pass" and "production-ready".
See `references/production-readiness-techniques.md` for the ffmpeg/ffprobe
recipes and the vision-inspection checklist.

---

## Phase 1: Audit (No Fixes)

Catalog every issue BEFORE touching any code. Use these sweeps:

| Dimension | Command |
|-----------|---------|
| `FIXME` | `search_files(pattern='FIXME', path='src/', limit=100)` |
| `TODO` | `search_files(pattern='TODO', path='src/', limit=100)` |
| `BUG` | `search_files(pattern='BUG', path='src/', limit=50)` |
| `HACK` / `WORKAROUND` | `search_files(pattern='HACK|WORKAROUND', path='src/')` |
| `@ts-ignore` | `search_files(pattern='@ts-ignore', path='src/')` |
| `@ts-expect-error` | `search_files(pattern='@ts-expect-error', path='src/')` |
| `eslint-disable` | `search_files(pattern='eslint-disable', path='src/')` |
| `console.log` in `src/` | `search_files(pattern='console.log', path='src/')` |
| `: any` annotations | `search_files(pattern=': any', path='src/')` |
| Dead exports | Terminal: `grep -rn "^export.*function\|^export.*const\|^export.*class" src/` |

For each dimension, note:
- **File** (absolute or repo-relative)
- **Count** of matches
- **Pattern category** (e.g. "all in legacy module", "spread across 15 files")

**Output:** An audit summary that quantifies every dimension.

---

## Phase 2: Prioritize

Rank the catalog by **real output impact** — NOT by how many matches exist:

| Priority | Criteria | Examples |
|----------|----------|---------|
| **P0 Critical** | Breaks every output | Silent failure in core pipeline, all music = pink noise, all videos have black frames, all tests fail |
| **P1 High** | Degrades every output | One broken provider that was primary, `console.log` flooding production logs, type errors that hide real bugs |
| **P2 Medium** | Degrades some outputs | One backup provider returns 404, a gate check fails but doesn't block rendering |
| **P3 Low** | Code quality only | Dead comments, unused imports, minor `any` that doesn't affect runtime |

Build a ranked table:

```
| Priority | File | Issue | Impact |
|----------|------|-------|--------|
| P1 | `src/orchestrator/pipeline.ts` | Loose `any` on pipeline state | Causes undetected runtime type errors in render | ...
```

---

## Phase 3: Fix One-by-One

For EACH item in the ranked list:

### 3a. Read the Context
```
read_file(path=file, offset=LINE-5, limit=20)
```

### 3b. Apply One Atomic Fix
One `patch` call. Never fix two different issues in the same edit.

### 3c. Verify Immediately
```
npm run typecheck  ── must pass (0 errors)
npm run test:unit  ── existing tests must still pass
npm run lint       ── if available
```

### 3d. Commit
```
git add <files>
git commit -m "fix: <file>: <one-line description of what was fixed>"
```

### 3e. Cycle
Move to the next priority item. Never fix two bugs before verifying the
first one.

---

## Phase 4: Final Verification

After ALL fixes are committed:

```
npm run typecheck    → 0 errors (required)
npm run test:unit    → same or fewer failures than before
Pipeline smoke test  → runs end-to-end with a known topic
```

---

## Phase 5: Present for Approval

Deliver a summary table:

| # | Fix | Files | State |
|---|-----|-------|-------|
| 1 | P1: xxx | `file.ts`, `file2.ts` | ✅ committed |
| 2 | P2: yyy | `file3.ts` | ✅ committed |

Then list the git log:

```
76b69d1 fix: env docs, music system docs, cache format, IA fix...
c8a3f2e fix: add 5 bundled ambient MP3s
```

Ask: "Push to origin/main when ready." Do NOT push without explicit
approval.

---

## Scope Creep Guard

| Situation | Response |
|-----------|----------|
| Fix reveals a NEW bug | Record in task list. Do NOT fix it now. |
| Fix takes >3 attempts | STOP. Question architecture (P4 step 5 of systematic-debugging). |
| User says "also fix X while you're there" | Only if X is already cataloged. New item → new campaign. |
| Existing test starts failing | Investigate the regression. It blocks the campaign. |
| Too many "while I'm here" improvements | Refer to `ponytail` discipline: simplest thing that works. |

---

## Backward Compatibility Rule

When adding NEW architecture alongside old code:

```
OLD CODE:    src/lib/free-music.ts  ← NEVER touch
NEW CODE:    src/music-system/      ← build standalone
SHIM:        src/lib/free-music.ts  ← add thin routing wrapper
                                     that calls new engine
```

The shim pattern:
1. Keep old file untouched (preserve all imports/exports/signatures)
2. Build new system independently
3. In old file, add `ensureEngine()` that creates the new engine
4. Route old function through the new engine
5. If new engine fails, fall back to old logic

---

## Related Skills

- `source-audit` — Phase 1 of this workflow (static bug-hunt, no edits)
- `systematic-debugging` — single-bug root cause analysis (use within a single fix item when the fix isn't obvious)
- `verify-codebase` — verifying an unfamiliar codebase before fixing
- `verify-untested-repo` — when the repo has no CI/test/lint commands
- `multi-provider-media-architecture` — for fixing media-provider issues
- `ponytail` — lean-code discipline to avoid over-engineering during fixes
