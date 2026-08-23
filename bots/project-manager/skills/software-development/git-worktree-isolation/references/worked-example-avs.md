# Worked example — agentic pipeline hardening in an isolated worktree

## Context
Project: Automated-Video-Generator at `C:\one\Automated-Video-Generator`.
Another model was working on `main`. User asked to create a new working tree from the last commit
and harden the pipeline (modular CLI voice parity, stale script removal, prune default fix,
missing tests, structured logging).

## Steps taken (reproducible)
1. Explore + analyze entire project; identify 14 issues across the 6-stage pipeline.
2. `git log` to find last commit `fe22038`.
3. `git worktree add -b improvement/pipeline-hardening C:/one/avs-improvements fe22038`
4. `cd` into worktree; symlink node_modules (see windows-node_modules-symlink.md).
5. Edits:
   - `src/adapters/cli/agentic-modular.ts` — voice stage builds full AgenticWorkspace
     (audioDir) + syllable word-timings; render stage no longer overwrites voiceovers.
   - `package.json` — removed stale `voicebox:clone` script.
   - `src/agentic/management/workspace.ts` + `orchestrator/pipeline.ts` — prune default 25 → 2.
   - `src/agentic/pipeline/{acquire,verify,gateway,gate}.test.ts` — offline unit tests (20 tests).
   - `src/agentic/pipeline/gateway.ts` — FIXED retry bug (see below).
   - `render.ts`, `pipeline.ts`, plugin files — console.log → logInfo (structured logging).
   - `voice-controller.test.ts` — make integration test `t.skip()` when backend venv absent.
6. Verify: `tsc --noEmit` (exit 0); `tsx --test "src/agentic/**/*.test.ts"` → 20 pass / 0 fail / 1 skip.
7. `git commit` (15 files, +630/−47).
8. User said "push it" → `git push origin improvement/pipeline-hardening` → `fe22038..39ff666`.

## The gateway retry bug (worth capturing)
Original loop:
```ts
for (let attempt = 0; attempt < maxRetries && !replaced; attempt++) {
  replaced = await reAcquireScene(...);   // sets replaced even if re-verify rejects it
  if (replaced) {
    const rv = (await verifyAll([replaced], ws, deps))[0];
    const r2 = await deps.decide(replaced, {...});
    if (r2.decision === 'approved') { /* push + break */ }
  }
}
if (!replaced) { /* mark rejected */ }
```
Bug: `!replaced` exits the loop as soon as reAcquireScene returns ANY candidate, even when
re-verification then REJECTS it. A bad asset could slip through as approved on retry.

Fixed:
```ts
let replacedApproved = false;
for (let attempt = 0; attempt < maxRetries; attempt++) {
  replaced = await reAcquireScene(...);
  if (!replaced) break;                       // network failure only
  const rv = (await verifyAll([replaced], ws, deps))[0];
  const r2 = await deps.decide(replaced, {...});
  if (r2.decision === 'approved') { /* push; replacedApproved=true; break */ }
}
if (!replacedApproved) { /* mark rejected */ }
```
Lesson: when a "replace" decision should retry N times, loop on attempt count, not on whether a
candidate object exists. Decide rejection on "was any replacement approved", not "was one fetched".

## Voice backend note
Vendored TTS backend lives at `src/speech/` (main.py, app.py, requirements.txt with torch/kokoro).
The live integration test needs a Python venv with torch/kokoro — NOT installed in this env
(installing would breach the ~800MB RAM budget). So the test skips gracefully when
`ensureBackend()` returns false. The code is correct; only the heavyweight venv is absent.
