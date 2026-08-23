# Batch render: Windows SAPI hang + orientation/aspect ignored

Two production blockers found + fixed in the agentic BATCH path
(`wave-scheduler.ts` → `renderAgenticSlideshow`) on 2026-07-25.
Both are invisible to `npm run typecheck` and unit tests; only a live
render + `vision_analyze` of the output caught them.

## BUG #6 — Windows SAPI voiceover HANG (commit `b9e32b3`)

Symptom: batch render frozen 10+ min after "Auto-selected free music";
no ffmpeg running; stock already acquired; log stuck.

Root cause (file:line):
- `src/lib/voice-generator.ts` → `generateSceneVoiceoverWithWindowsSapi`
  called `runPowerShellEncoded()` from `src/lib/voice-engine.ts:50`,
  which used `spawnSync('powershell.exe', [...], { timeout: 120000 })`.
- On Windows, when powershell.exe spawns a `conhost.exe` grandchild
  that keeps the stdio pipe open, killing the direct child at the
  timeout does NOT make spawnSync return. The `await` hangs forever.

Fix:
- Added `runPowerShellEncodedAsync()` in `voice-engine.ts` — spawns
  ASYNC, races a hard timer that KILLS THE PROCESS TREE
  (`taskkill /F /T /PID <pid>`, conhost included) at the timeout,
  plus a 2x-timeout force-resolve so the await can NEVER hang.
- `voice-generator.ts` Windows-SAPI caller now uses it (handles
  `timedOut` + `status`).
- Added a SILENT-TRACK ultimate fallback in `generateSceneVoiceoverWithRetry`:
  `makeSilentTrack()` emits a short silent WAV (ffmpeg `anullsrc`, or a
  hand-built 44-byte WAV header) so the render completes instead of
  aborting. "Better a silent video than a hung one."
- Test `src/lib/voice-engine.async.test.ts` (2/2): a 600s sleep is
  killed at ~2s (`timedOut:true`, elapsed <8s) — empirical proof.

Reproduce the hang pre-fix:
```
node -e "const {runPowerShellEncoded}=require('./src/lib/voice-engine.js');
const t=Date.now();
const r=runPowerShellEncoded('Start-Sleep -Seconds 600', process.env, 2000);
console.log('returned after',((Date.now()-t)/1000).toFixed(0)+'s');"  # never returns
```
Post-fix: use `runPowerShellEncodedAsync` → returns at ~2s.

## BUG #7 — orientation/aspect IGNORED in batch render (commit `72d01cf`)

Symptom: a `square` (1:1) job came out 720x1280 portrait;
vision confirmed "not square, it's portrait with black letterbox bars…
missing the required emoji, progress bar". The `_1x1`/`_16x9` exports
were only POST-CROP variants, not the canonical file.

Root cause:
- `wave-scheduler.ts:16` imported `renderAgenticSlideshow` from
  `src/agentic/orchestrator/render.ts` (the hardcoded 720x1280 renderer),
  NOT the orientation-aware `compose.ts`. So the agentic batch path
  bypassed the orientation fix entirely.
- `render.ts` hardcoded: `const W = opts.dimensions?.w ?? 720,
  H = opts.dimensions?.h ?? 1280;`

Fix:
- Added `resolveRenderDims(orientation, aspect)` (exported) to `render.ts`,
  mirroring compose.ts precedence (aspect > orientation > portrait):
  square → 720x720, landscape/16:9 → 1280x720, portrait/9:16 → 720x1280.
- Wired `orientation: job.orientation, aspect: job.aspect` into the
  `renderAgenticSlideshow` call in `wave-scheduler.ts:189`. Canonical
  output now matches the requested frame size.
- A discriminated-union value flowing AgenticCliJob → `buildPipelineRequest`
  → `PipelineRequest` → `render.ts` `opts` must be widened in EVERY
  type (`cli-job.ts`, `orchestrator/types.ts`, `render.ts` `opts`).
- Test `src/agentic/orchestrator/render.dims.test.ts` (5/5).

Verify (real proof, not exit code):
```
# square job should be 720x720 DAR 1:1
ffmpeg -i "output/waveh_square_stack/WAVE H square stack — ...mp4" 2>&1 | grep "Stream"
# → Video: h264 ... 720x720 [SAR 1:1 DAR 1:1]
```

## Reusable patterns
- `spawnSync({timeout})` on Windows is UNSAFE for long-lived
  commands with conhost grandchildren. Use async spawn + process-tree
  `taskkill` + guaranteed-reject timer. Applies to ANY Windows
  child-process call in this repo.
- When a render "ignores orientation", find which renderer the
  ACTUAL call site uses. Two parallel renderers (compose.ts for
  single-feature, render.ts for batch) can BOTH need the same fix.
- The agentic batch path is `bin/variety-run.ts` →
  `runBatchWaves` (wave-scheduler.ts) → `runAgenticPipeline`
  (pipeline.ts) → `renderAgenticSlideshow` (render.ts). Keep this
  chain in mind when tracing batch-only defects.
