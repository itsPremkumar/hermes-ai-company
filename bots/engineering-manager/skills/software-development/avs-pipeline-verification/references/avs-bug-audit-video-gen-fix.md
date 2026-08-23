# AVS Bug Audit — audit/video-gen-fix (2026-07-28)

## Scope
Multi-agent audit of the AVS video pipeline. Worktree `audit/video-gen-fix`
branched from `da01b10`, merged to main at `095149e`.

## Bugs found & status

### A3 — voiceover render crash (FIXED)
- **Site**: `src/agentic/orchestrator/render.ts:736` (segmented branch) +
  `src/adapters/cli/agentic-modular.ts:564`.
- **Symptom**: `TypeError: Cannot read properties of undefined (reading '0')`
  when rendering a job whose voice stage produced no per-scene WAVs.
- **Root cause**: the modular CLI set `result.voiceovers = voiceoverMeta`
  where `voiceoverMeta = {voiceoverDriven, sceneCount, fallbackUsed}` has
  NO `scenes` array. `render.ts` then did
  `res.voiceovers?.scenes[clip.idx]?.audioPath` → `.scenes` is undefined →
  indexing throws.
- **Fix**:
  1. `render.ts` — extracted `sceneVoicePath(voiceovers, idx)` (optional
     chain on `.scenes`) used at the crash site; returns `undefined` →
     silent `anullsrc` track instead of crashing.
  2. `agentic-modular.ts` — after the on-disk WAV scan, ALWAYS normalize
     `result.voiceovers.scenes` to a real array (on-disk WAVs, else `[]`).
- **Reproduction**: `src/agentic/orchestrator/repro-a3.ts` — constructs the
  slim shape, shows BEFORE throws the exact TypeError, AFTER returns
  `undefined`. `render.test.ts` pins `sceneVoicePath` (4/4).
- **Regression guard**: if this crash reappears, grep `result.voiceovers = {`
  in `agentic-modular.ts` and confirm a `scenes:` array is always present —
  a future refactor could drop the normalization.

### edit.ts re-encode hardening (FIXED, ported from uncommitted main)
- **BUG #1/#2**: `trimVideo`/`splitVideo` used `-c copy`; stream copy over a
  non-keyframe split point yields a 0-stream empty file that still exits 0.
  Fix: re-encode (`libx264`); validate output `duration > 0` via ffprobe.
- **BUG #4**: `changeSpeed` built `[0:a]atempo` even when input has no audio
  → "Stream specifier ':a' matches no streams". Fix: skip audio branch when
  `!hasAudioStream(file)`.
- **BUG #6**: `addAudio(mix)` on a video with no source audio → amix with one
  input. Fix: degenerate to "replace" (`-map [1:a]`).
- **BUG #7**: `silenceRemove` on audio-less input → crash. Fix: refuse.
- **BUG #9**: `addProgressBar` defaulted `totalSec=10` → bar never filled on
  short clips. Fix: default to probed duration.
- **BUG #11 / G12 (NEW real defect caught by test)**: `mergeVideos` audio
  branch built concat inputs as `[v0][v1][0:a][1:a]` (all videos then all
  audios) → ffmpeg "Media type mismatch" → whole merge fails. Fix: interleave
  per segment `[v0][0:a][v1][1:a]`. This is a filtergraph-STRING ordering bug
  that `tsc` NEVER flags — only a real ffmpeg run catches it.

### G10 / G11 music+voiceover hangs (VERIFIED CLOSED — no re-fix)
- Already fixed in current code: `free-music.ts` uses `withSignal` (hard
  timer in `music-system/providers/base.ts`); `voice-generator.ts` uses
  `runPowerShellEncodedAsync` (taskkill /F /T tree-kill). Proven by existing
  tests `with-signal.test.ts` (3/3) and `voice-engine.async.test.ts` (2/2).
  Do NOT "fix" G10/G11 again unless code regresses.

## Techniques / reusable patterns
- **Empirical edit test harness** (`src/agentic/operations/edit.test.ts`):
  generate synthetic clips with
  `ffmpeg -f lavfi -i color=c=blue:s=WxH:d=N:r=25 [-f lavfi -i sine=frequency=440:duration=N -c:a aac]`, re-encode to
  `libx264 -pix_fmt yuv420p`, then probe
  `ffprobe -show_streams -show_format` and assert `{video, audio, durSec}`.
  Catches silent empty-output + stream-specifier crashes that tsc cannot.
- **TDZ patch pitfall**: a `patch` that references a variable declared LATER
  in the same function compiles under `tsc` but throws `ReferenceError` at
  runtime (observed: referenced `voiceScenes` at line 564 while declared at
  line 571). Before inserting a patch that touches locals, READ THE WHOLE
  FUNCTION REGION and place the mutation AFTER the variable's declaration.
- **Visual gate**: after a merge/render fix, extract a mid frame with
  INPUT-seek (`-i file -ss N`, never `-ss N -i file` — G8) and run
  `vision_analyze` to confirm a non-corrupt frame.

## Before/after metrics
- edit.ts suite: 0 → 9 passing empirical tests (plus pre-existing 10 in
  `edit-regression.test.ts`).
- A3: crash → 4/4 unit + repro green.
- Full regression suite: 36/36 ops+parser, 5/5 G10/G11, 23/23 edit.
