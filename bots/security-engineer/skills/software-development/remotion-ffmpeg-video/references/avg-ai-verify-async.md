# AVG — opt-in aiVerify architecture + async ffmpeg hot-path patterns

Condensed, task-focused notes for the Automated-Video-Generator (AVG) agentic
pipeline (`src/agentic/`). Captures the durable engineering lessons from the
aiVerify + async-ffmpeg hardening pass. P40/P41 live in
`references/ci-typecheck-blindspot.md`.

## P42 — stale `[System: unverified]` gate flag (workflow trap)

The verification gate fires on a **snapshot** of the workspace taken mid-turn.
It will flag files that were already DELETED in the same turn (temp probe
scripts) or ALREADY COMMITTED. It is NOT a real defect signal.

Clearing procedure (re-run, don't argue):
1. `git status --short` → must be empty (everything committed).
2. `npx tsc -p tsconfig.json --noEmit` → 0 errors.
3. `npx eslint src/` → 0 errors.
4. `npx tsx --test "src/**/*.test.ts"` → green (suite count stable).
If all four pass and the tree is clean, the flag is STALE — report it cleared
with the fresh evidence. Do NOT treat flagged paths as outstanding work.

Why it recurs: deleting temp diagnostic scripts (`rm -f probe.ts`) and then
committing in the same turn leaves the snapshot referencing gone/committed
files. The flag cannot know the turn finished.

## P43 — ffmpeg `-ss` must be within media duration

When extracting a single frame for the AI X16 check (or any frame grab):
- `-ss 00:00:01` on a video SHORTER than 1s seeks PAST EOF → no frame written
  → the `if (fs.existsSync(frame))` guard skips → X16 check is silently ABSENT
  (not "skipped", never pushed). The gate looks green but the AI check never ran.
- Fix: seek to a safe early timestamp that always exists, e.g.
  `-ss 00:00:00.5`, or `max(0, duration/2)`. For a real 15-17s video either
  works; the safe form also covers short test clips.

General rule: any fixed `-ss HH:MM:SS` must be < the clip's real duration.
Prefer `00:00:00.5` for "first frame" grabs.

## P44 — async-helper ripple (update callers AND tests)

When you convert a synchronous helper to `async` (e.g. to use the async
`runFfmpeg` runner), the change RIPPLES:
- Every direct caller must `await` it (sync call now returns a Promise →
  `await makeContactSheet(res)` not `makeContactSheet(res)`).
- Every TEST that calls it synchronously must also `await` AND be marked
  `async () =>` — otherwise tsc errors (`Promise<string|null>` not assignable
  to `PathLike`) or the test silently passes a Promise where a string is used.
- Remove now-unused `const ffmpeg = require('ffmpeg-static')` / `execFileSync`
  declarations left behind in converted functions (they become dead vars and
  can trip lint).

Concrete AVG examples:
- `makeContactSheet` (orchestrate.ts) → `async`; caller at ~line 591 + test in
  `contact-sheet.test.ts` both `await`ed.
- `applyProEdits` (plan.ts) → `async`, takes optional `brain`; callers in
  orchestrate.ts (`await`) + `plan.test.ts` (5 tests marked `async` + `await`).

## Async `runFfmpeg` runner pattern (P40 concretely applied)

Reusable replacement for `execFileSync(ffmpeg, [...])` in the render hot path.
Resolves to exit code, never throws, hard-kills on timeout so a RAM-starved
box can't be blocked irrecoverably:

```ts
function runFfmpeg(args: string[], timeoutMs = 60000): Promise<number> {
  return new Promise((resolve) => {
    const { spawn } = require('child_process');
    const ffmpeg: string = require('ffmpeg-static');
    const child = spawn(ffmpeg, args, { stdio: 'ignore' });
    const t = setTimeout(() => { try { child.kill('SIGKILL'); } catch {} resolve(-1); }, timeoutMs);
    child.on('error', () => { clearTimeout(t); resolve(-1); });
    child.on('close', (code) => { clearTimeout(t); resolve(code ?? -1); });
  });
}
```
Use for: thumbnail extract, contact-sheet frame grabs + grid build, Remotion
video downscale. Leave `makePlaceholder` sync (sub-second offline fallback;
converting would require async-ing the whole acquire fallback chain —
disproportionate). `normalizeAudio` is gated OFF by default
(`AGENTIC_NORMALIZE_MUSIC !== '1'`) + has its own timeout — low risk, leave.

## Opt-in aiVerify architecture (zero-cost, agent's own model)

Design: reuse the running AgentBrain — NO separate paid key, NO extra cost.
- `config.ts`: `aiVerify?` block on `AgenticConfig` (enabled default FALSE;
  per-stage verifyOnAcquire/Approve/Edit/Render; checkSubjectMatch/Watermark/
  Safety/MusicMood/SpeechClarity/BackgroundNoise; minConfidence/minAudioConfidence).
  `resolveConfig` defaults all sub-flags to the master toggle.
- `ai-verify.ts`: `aiVerifyAsset(file, kind, expectation, cfg, brain, transcript?)`
  → returns `null` when brain not multimodal / offline / no transcript. Callers
  fall back to signal gates. NEVER blocks.
- Wiring points:
  - acquire: drops a wrong-subject candidate when verifyOnAcquire + score fails
    (next source in the ladder is tried).
  - gate: X16 final-video AI check (extract frame → aiVerifyAsset 'video').
  - scene-edit: verifyOnEdit scores a scene localAsset after edit.
  - orchestrate/autopilot: thread `aiVerify` into render + acquire paths.
- `brain.ts`: `visionVerify` relaxed to also use local Ollama vision (not just
  OpenRouter key); `completeJSON` exposed for audio/transcript judging.
- Contract: AI results AND with deterministic signal gates (X7-X15); AI
  AUGMENTS, never replaces. Offline/rate-limited → signal gates decide.

## B-list AgentBrain (wired, not dead code)

All return `null` → heuristic fallback; never crash/hang.
- B1 writeScript, B2 expandKeywords, B5 narrativeOrder, B7 deriveMusic,
  B9 visionVerify, B10 generateMetadata — pre-existing.
- B3 hookScene → wired into `applyProEdits` hook-first (else rule-based pattern).
- B6 paceScenes → wired into `applyProEdits` variablePacing (else rule-based alt).
- B11 titleVariants → wired into `writeOutputArtifacts` (_metadata.txt A/B block).
- B12 tailorForPlatform → `platform?` on `AgenticConfig`; autopilot applies
  aspect + captionStyle overrides when set (else cfg identity).

## P45 — AI music-mood check needs a PROXY transcript (audio has no speech)

`aiVerifyAsset(file, 'audio', expectation, cfg, brain, transcript)` judges audio
via the TEXT model on `transcript`. But **background music has no speech
transcript** — so the `checkMusicMood` path was DEAD (the `if (!transcript)
return null` guard killed it every time). The voiceover path works (it has the
narration), but music never reached the model.

Fix: pass a text PROXY as `transcript` so the model can judge mood-fit against
the plan. In `acquire.ts` music loop:
```ts
const proxy = `intended mood: ${plan.musicQuery}; track source: ${f.source || 'free-music'}`;
const ai = await aiVerifyAsset(localPath, 'audio', [plan.musicQuery], deps.cfg, deps.brain, proxy);
if (ai && !ai.pass) { /* drop candidate */ continue; }
```
Gate it behind `deps.cfg?.aiVerify?.verifyOnAcquire && deps.cfg?.aiVerify?.checkMusicMood`
(else the call is wasted). Lesson: any audio asset WITHOUT a real transcript
must supply a text proxy (mood query + tags/source) or the AI audio check is
silently skipped. Voiceover = real narration; music = proxy.

## P46 — per-aspect X16 (crop subject-loss)

`exportMultiAspect(srcMp4, ['9:16','16:9','1:1'])` RETURNS the produced file
paths. When `aiVerify.verifyOnRender` is on, loop those paths and run the same
`aiVerifyAsset(ap, 'video', keywords, {aiVerify}, brain)` so a subject lost in a
9:16 crop is caught (primary X16 only scores the source aspect). Pass `aiVerify`
into `writeOutputArtifacts` from the render opts; guard with
`aiVerify?.verifyOnRender && brain.modelEnabled`. A null/non-pass is a warn, not
a block (signal gates still own pass/fail). `force_original_aspect_ratio=decrease`
already keeps the subject centered, so this is a belt-and-suspenders catch for
extreme crops.

## Verification recipe (AVG)
```
npx tsc -p tsconfig.json --noEmit   # 0
npx eslint src/                     # 0
npx tsx --test "src/**/*.test.ts"   # 235 pass / 0 fail / 1 skip (skip = real-render E2E, RUN_REAL gate)
# offline regression E2E:
npx tsx bin/agentic-auto.ts --topic "..." --title "..." --no-sfx --local-assets "img1.jpg,img2.jpg,img3.jpg" --max-attempts 1 --aspect 1:1
# expect GATE PASS, X7-X15 ✓
```
