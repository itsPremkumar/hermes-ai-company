# AVS Multi-Subagent Bug Hunt (class-level technique, 2026-07-28)

When the user asks to "find and fix all the bugs, generate videos, verify visually" —
run a REAL, evidence-based hunt, not a static code read. Ground every finding in an
actual render + frame extraction + `vision_analyze` grid check.

## Why parallel subagents
Partition hunters by SUBSYSTEM so no two agents edit the same file (clean triage):
- **core-render** — `compose.ts`, `advanced-fx.ts`, `edit.ts`, `visual-fx.ts`
- **parser/planner** — `script-parser.ts`, `plan.ts`
- **audio** — `voice-controller.ts`, `speech-backend.ts`, `music-system/*`, `sfx.ts`
- **editing/plugins** — `agentic-image.ts`, `edit.ts` standalone ops, `plugins/*`

Dispatch with `delegate_task` `tasks:[...]` (max 3 concurrent; split into waves).
Each agent: TRIAGE ONLY (no source edits), write findings to
`workspace/bug-hunt/findings_<area>.md`, and produce a grid it vision-checks.

## Reusable harness
`scripts/bug-hunt-harness.mjs <jobFile.json> <outName>` renders plan to voice to visuals
--no-acquire to render and emits `workspace/bug-hunt/grids/<outName>.jpg`. It enforces the
CLI job-spec contract (see SKILL.md "CLI JOB-SPEC CONTRACT") and SERIALISES the Kokoro
voice backend with a `.voice.lock` file so parallel agents don't collide on the port or
exceed ~800MB RAM.

Seed reusable assets once: `workspace/bug-hunt/assets/{a,b,c,d}.mp4` (distinct ffmpeg
test patterns). Copy them per-job into `input/visuals/` so `[Visual:]` tags stay bare.

## Real bugs surfaced by this technique (2026-07-28, edit.ts — HIGH severity)
1. `trimVideo` / `splitVideo`: `-ss`/`-to` AFTER `-i` with `-c copy` to 0-stream (empty)
   output that still exits 0. Fix: re-encode with libx264 + validate duration via ffprobe.
2. `interpolateVideo`: filter `minterpolate=mode=blend` is an invalid option; correct is
   `mi_mode=blend`. Op could NEVER succeed. Fix applied.
3. `changeSpeed`: hard-codes `[0:a]atempo` so it crashes on audio-less AVS visuals (very
   common). Also clamps speed to [0.05,10] but atempo only accepts [0.5,100] so 0.25x
   (documented "4x slow") always fails. Needs conditional audio graph + chained atempo.
4. `silenceRemove`: `-af silenceremove` + `-c:v copy` causes A/V desync and is a silent
   no-op on audio-less input. `addProgressBar` defaults totalSec=10 instead of probing.
5. Plugin modules (`src/agentic/plugins/*`) are DEAD on the compose path — confirmed the
   orchestrator-only wiring (pairs with D2 drift note in SKILL.md).

## Fix discipline after triage
- Fix each confirmed bug with a REGRESSION TEST (e.g. `node --import tsx --test` the op on
  an asset; assert output has a video stream + positive duration).
- Re-render the affected area with the harness and `vision_analyze` the grid to prove the
  visual output is correct (empirical bar — see VERIFICATION DISCIPLINE in SKILL.md).
- Commit fixes separately from docs; push only functional code (COMMIT/PUSH DISCIPLINE).

## Other findings this session (parser, not yet fixed)
- Overlong single line to unbounded scene duration (P-1); CJK text to no sentence split
  plus junk keywords (P-2); nonexistent `[Visual:]` to filename used as search keyword
  (P-3); duplicate `[Visual:]` on a text line to second tag silently dropped (P-4). These
  are solid follow-up fixes.
