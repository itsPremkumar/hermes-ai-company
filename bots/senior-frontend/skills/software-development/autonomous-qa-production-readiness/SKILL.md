---
name: autonomous-qa-production-readiness
description: >
  Make a project "production-ready" autonomously: find bugs (static + dynamic +
  visual), fix them with root-cause analysis, and PROVE the fixes with real
  passing tests + a visual-render verification gate. Use when the user says
  "make this production-ready", "find and fix all bugs automatically", "QA this
  project", "auto-fix + visual verification", or hands you a goal-prompt that
  asks an agent to harden a codebase end-to-end. Encodes the baseline→fix→
  re-verify loop, parallel subagent bug-fix waves (with the "subagent self-report
  is NOT trusted" rule), the network-failure→clean-SKIP conversion, and the ffmpeg
  blackdetect + frame-extract + vision_analyze visual gate that most QA passes skip.
---

# Autonomous QA → Production-Ready

A reusable playbook for taking a codebase from "works on my machine" to
"proven green with visual evidence". Works on any TS/Node (node:test), Python,
or media-generation project. The pattern is tool-agnostic but the recipes below
are battle-tested on a Windows/MSYS box with `npm test`, `node --import tsx
--test`, ffmpeg-static, and Hermes `vision_analyze`.

## Hard constraints to carry into the goal prompt (from the user)
- ZERO-COST: no paid API keys, no cloud TTS, no Claude Code. Local/FOSS only.
- BACKWARD COMPAT: never delete/modify working code. New code stands alongside;
  if a signature must change, keep a shim. (See `ponytail` for the lean angle.)
- NO PUSH without explicit user approval. Commit locally; stop for approval.
- RAM discipline: keep only Hermes + the process under test alive. Kill RAM
  hogs (stray python/uvicorn/remotion) via `taskkill -F -PID <id>` between phases.
- MAX 3 parallel subagents (RAM limit). Use waves 3→3→1 for ~7 tasks.
- Commercial-safe: don't introduce GPL/AGPL or paid deps.

## The loop (PHASES)
0. **Baseline** — `npm run typecheck`; `npm test > /tmp/full.log`; `git status`
   clean?; grep TODO/`console.log`/`: any`. Write `QA_BASELINE.md` with numbers.
1. **Static** — `gstack: health` + `devex-review`, or `tsc --strict` + grep for
   unhandled rejections / `any` leaks / missing error boundaries.
2. **Dynamic** — exercise the app/CLI. Reproduce each failure; classify
   `[NETWORK]` (offline sandbox) vs `[REAL BUG]`. See references/network-skip.md
   for the clean-SKIP recipe.
3. **Fix** — root cause (file:line), fix at cause, add/extend a test that FAILS
   before and PASSES after. Do NOT weaken assertions.
4. **Visual verification** — render a real artifact; prove it with ffmpeg +
   vision_analyze. See references/visual-verification.md (the part most agents skip).
5. **Hardening** — add a `qa:smoke` script; confirm CI runs typecheck+test.
6. **Report** — `QA_REPORT.md`: baseline vs after, every bug (file:line, root
   cause, fix, proving test), visual evidence, remaining risks, verdict.

## Parallel subagent bug-fix waves (the force-multiplier)
- Dispatch 3 `delegate_task` leaf agents (max concurrency 3), one cluster of
  failures each, with PRECISE failing-assertion text pasted into the prompt.
- Each commits locally, does NOT push.
- **CRITICAL: a subagent's "all tests pass" summary is a SELF-REPORT, not a
  fact.** After they return, YOU re-run the targeted suites + full `npm test`
  and confirm the numbers. In this session a subagent claimed a TS1470 error was
  "someone else's"; the actual full-suite re-run was green — verify, don't trust.
- Concurrency hazard: 3 agents editing the same working tree simultaneously can
  step on each other (one hit another's in-flight edit). Verify `typecheck` after
  merge of all waves; fix any cross-edit breakage locally.

## Definition of Done (gate before reporting)
- [ ] `npm run typecheck` exits 0
- [ ] `npm test` pass count > baseline; pre-existing failures fixed OR converted
      to clean SKIPs (no red on a clean machine)
- [ ] ≥1 new/extended test per fixed REAL bug (fails-before/passes-after proven)
- [ ] Real artifact rendered end-to-end; visual checks PASS (no black frames,
      audio present, in-sync); evidence in QA_REPORT.md
- [ ] No new paid/GPL deps; license intact; no secrets committed
- [ ] Working tree clean or intentionally-staged; PUSH pending user approval

## Key recipes (support files)
- `scripts/check_render.sh` — ffprobe/blackdetect probe for a rendered video.
- `references/visual-verification.md` — frame extraction + vision_analyze gate.
- `references/network-skip.md` — convert host-unreachable test failures to clean SKIPs.
- `references/parallel-wave-prompt.md` — template subagent prompt with assertions.

## Overlaps (curator note)
Complements `green-ci-typescript-project` (build green TS/Node), `verify-codebase`
(audit + simulate local CI), `rendered-media-qa` (media verification), and
`gstack: qa` (systematic web-app QA). This skill is the ORCHESTRATION layer that
combines them with parallel subagent execution + the visual gate for an
end-to-end "production-ready" pass. Pull from those skills for depth; this one
owns the loop + the trust-but-verify subagent discipline.
