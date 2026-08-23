# Worked Example — Automated-Video-Generator (AVS) Gap Analysis

Real application of the `codebase-gap-analysis` method on the user's project at
`C:\one\Automated-Video-Generator` (HEAD `fc20286`). This is a reference for the
*shape* of findings, not a live report — verify against current source before acting.

## Declared vs implemented (the headline gap)
- `src/agentic/operations/route.ts` declares **37** TaskKind intents.
- `src/agentic/operations/dispatch.ts` implements **26** switch cases.
- **11 dead intents** (classified, never execute): `convert`, `to_gif`,
  `convert_audio`, `images_to_video`, `video_to_images`, `social_download`,
  `separate_audio`, `separate_video`, `mute_video`, `write_script`, `unknown`.
- Failure mode surfaced: `route.ts` classifyOne for `convert` has **no default
  fallback**, so "convert x.mp4 to webm" mis-routes to `full_video` (rebuilding the
  whole video instead of transcoding).

## Orphaned state machine
- `src/agentic/delivery/revision.ts` defines a full review lifecycle
  (`requestChanges`, `resolveRound`, `approve`).
- Grep `-l` proves `requestChanges` / `resolveRound` appear ONLY in `revision.ts`
  itself. `pipeline.ts` calls `openReview()` at render time but nothing downstream
  reads `revision-state.json` to drive a re-render.
- Consequence: the "client review -> request change -> re-edit" loop is phantom.
  The tool is an excellent generator but a weak interactive editor.

## Inconsistency (divergent paths)
- Modular CLI voice: `agentic-modular.ts:354` uses `generateAgenticVoiceovers`
  (Edge-TTS dispatcher).
- Orchestrator voice: `orchestrator/pipeline.ts:492` uses `runVoiceStage` (kokoro
  self-driving). QA_REPORT.md explicitly flags this as an integration gap.

## Edit-path defects
- `agentic-modular.ts:631` `runEdit` renders a standalone `scene_N_edit.mp4` but does
  NOT re-stitch it into the master timeline (user must re-run full `render`, which
  rebuilds everything, not a non-destructive splice).
- `agentic-modular.ts:595` voice re-edit regenerates the WAV but does NOT re-extract
  `captionSegments` -> caption/audio desync.

## Strengths (so a fix doesn't break them)
- `management/autopilot.ts:120` autoRunVideo — 3-attempt self-heal loop.
- `pipeline/gate.ts:130` verifyRenderedVideo — X7-X16 post-render QA (black/freeze/
  loudness/clipping/dimensions/codec + opt-in AI vision).
- `acquire.ts:114` offline ffmpeg fallback (never ships blank scenes).
- QA_REPORT: 499 unit tests pass / 0 fail, typecheck clean.

## User's standing constraints that shaped the design
- ZERO-COST / NO-PAID-KEY: ffmpeg-static, openverse/pexels, kokoro/edge TTS.
- BACKWARD-COMPAT NON-NEGOTIABLE: add new impls/shims; never delete declared intents
  or working code. Fix dead intents by *implementing* them.
- Wants DETAILED root-cause with file:line; reports must trace data flow.

## Prioritized fix plan produced
- P0: wire `revision.ts` into a real `npm run agentic:revise` + MCP `agentic_revise`;
  implement the 11 dead intents (or flag them).
- P1: re-stitch master timeline on edit; regen captions on voice change; unify voice
  path to kokoro.
- P2: "Director's Critique" — self-analyze rendered video via existing
  `video-analyzer.ts` + opt-in vision, feed suggestions back into revise.
- P3: inter-scene transitions + reorder tool; whisper transcription for voice clone
  (`voice-controller.ts:112` TODO).
- P4: edit UI controls; reduce `any` debt (~323 occurrences).

## IMPLEMENTED (commit `089683d`) — technique notes for next time

### Dead intents → 11 `case` branches in `dispatch.ts`
Reused existing thin op modules: `convert.ts` (`convertFormat`/`toGif`/`convertAudio`),
`image-video.ts` (`imagesToVideo`/`videoToImages`), `social-dl.ts` (`downloadSocial`).
Added two new small standalone modules: `demux.ts` (`separateAudio`/`separateVideo`/
`muteVideo`, ffmpeg `-vn`/`-an` stream copies) and `script.ts` (`writeScript`, uses
`AgentBrain.writeScript(topic, title)` — 2 args, not 1). Also added a standalone
`to_gif` regex in `route.ts` BEFORE the generic convert block (it was buried inside
the convert block and never fired for "make a gif").

### Orphaned `revision.ts` → `revise.ts` driver (the real fix)
`reviseJob(originalJobId, notes, hints)`:
- `loadRevision` → `round = currentRound + 1`.
- **FAIL-SAFE FIRST (lesson):** check `readJson(ws,'plan.json')` exists BEFORE
  `requestChanges`. The old order called `requestChanges` (which `writeFileSync`s
  `revision-state.json`) on a missing job dir → `ENOENT` from `save()`. Hit this in
  the test, fixed by reordering.
- `requestChanges` → `runAgenticPipeline` into `jobId = \`${orig}_r${round}\``
  (non-destructive) → gate → `renderAgenticSlideshow` → `resolveRound(newId)`.
- `critiqueAndRevise` = `critiqueVideo` → `critiqueToPlanOverride` (applies each
  `fix` to the matching scene) → `reviseJob({ planOverride })`. Self-healing loop.
Exposed as MCP `agentic_revise` (`autoCritique` flag) + `agentic_critique`, and CLI
`npm run agentic:revise` / `agentic:critique`.

### Director's Critique → `critique.ts` `critiqueVideo(mp4, {planPath})`
Reuses `video-analyzer.ts` (`detectBlackFrames`/`detectFreezeFrames`/`analyzeAudio`/
`analyzeDimensions`). Flags landscape-in-portrait vs `plan.orientation`; caption
overlap (bottom caption + logo/music). Vision is **opt-in and guarded**:
`(brain as any)?.visionVerify?.(frame, [])` in try/catch — and it is `visionVerify`
NOT `visionVerifyFrame` (that name does not exist on `AgentBrain`; a typecheck error
we fixed). `suggestions[].scope` is the 0-based scene index → CLI prints
`scene ${scope + 1}`.

### Consistency fixes
- Voice parity: `agentic-modular.ts runVoice` now calls `runVoiceStageSafe` (kokoro)
  with `generateAgenticVoiceovers` (Edge-TTS) as fallback — matches orchestrator path.
- Caption desync: `runEdit --voice` now re-runs `syllableWordTimings(text, dur)` and
  writes `captionSegments` back to `plan.json`.
- Clone fidelity: `voice-controller.ts` `cloneFromVoicesDir` now reads a sidecar
  `.txt`/`.srt` next to the reference clip as `reference_text` (was a hardcoded
  placeholder).

### Verification (AVS-specific — committed to memory of this skill)
- `npm test` = `typecheck` + `node --import tsx --test --test-timeout=120000 ...`.
  The framework is Node's **built-in `node:test`**, NOT jest/vitest.
- Tests: 519 total, 511 pass, 0 fail (8 pre-existing manual/network skips) after the
  change. New: 9 route-intent tests + 3 critique/revise fail-safe tests.
- **Windows `search_files` tool is broken here** (returns `os error 3` on
  `C:/one/...` paths). Grep via `execute_code` + `subprocess.run(["rg","-n",pat,"-n",path])`.
