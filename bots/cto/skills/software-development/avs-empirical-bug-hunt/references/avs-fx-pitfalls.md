# AVS FX / Render Pitfalls — verified bug inventory (2026-07-28 session)

This is the consolidated list of REAL bugs found + fixed via the empirical
bug-hunt loop. Each was reproduced with a real render/frame/vision or ffprobe
before fixing. Use as a checklist when auditing AVS.

## Fixed (committed)
- **M1 — bgm path blind to `__bundled__`** (`agentic-modular.ts`): `backgroundMusic`
  resolved via `inputBgmPath(name)` → `input/bgm/<name>`, but bundled tracks live
  in `input/bgm/__bundled__/`. Fix: check both, prefer `__bundled__`.
  Verified: manifest picks `input/bgm/__bundled__/local_demo_ambient.mp3`.
- **M2 — per-scene kokoro voice 404** (`voice-controller.ts`): `scene.voiceOverride`
  like `af_bella` treated as a VoiceBox profile id → 404, scene voiceover LOST.
  Fix: detect kokoro voice name, provision preset profile via `resolveProfileId`.
  Verified: all 3 scene WAVs generated.
- **M3 — voiceover positional indexing** (`render.ts` `sceneVoicePath`): matched
  `voiceovers.scenes[idx]` by position; a failed scene shifted narration to the
  WRONG visual. Fix: match by `sceneIndex`.
- **M4 — duck/voice ignored on modular path** (`agentic-modular.ts`): forwarded
  `AUDIO_DUCK_LEVEL` / `AUDIO_FULL_LEVEL` from `job.duckDepth` / `voiceVolume`.
- **C1 — keyframe zoompan `t` undefined** (`render.ts`): zoompan expr used `t`
  (undefined in zoompan) + illegal `\\,` escaping → always failed. Fix: `time` +
  clean commas.
- **C2 — silent segment drop** (`render.ts`): failed segment passed
  `fs.existsSync` with a 0-byte file → scene silently dropped at concat. Fix:
  require ffmpeg success + plausible size (≥2 KB), fail loud.
- **C3 — ken-burns `d=1` static** (`render.ts`): `zoompan=z=zoom+0.0008:d=1` reset
  zoom every frame → no motion. Fix: `z='1+0.04*time'` center-anchored.
- **M1/M2 speed-ramp** (`advanced-fx.ts`): numeric `speedRampByScene` (e.g. 1.5)
  was a silent no-op; setpts used a non-integral expression (non-monotonic PTS,
  mass frame drops). Fix: numeric→constant speed; integral log formula for ramps.
  Verified: probe 1.5 → 5.32 s from 8 s source; ramps monotonic.
- **M4 punch-in** (`advanced-fx.ts`): values 0..1 clamped to 1.05 (near-no-op).
  Fix: map 0..1 → 1+v (0.4 → 1.4).
- **M5 parallax** (`advanced-fx.ts`): static micro-zoom. Fix: animated crop drift.
- **M3 motion-FX CLI wiring** (`agentic-modular.ts`): shake/speedRamp/punchIn/
  parallax only applied by `composeVideo`, silently dropped on CLI path. Fix:
  pre-process per-scene video assets through advanced-fx appliers in `runRender`.
- **A1/A2 jCut + exportAspects** (`render.ts`/`agentic-modular.ts`): `jCutSec` and
  `exportAspects` (incl. '4K') written to job-meta but never forwarded to renderer.
  Fix: forward + honor in `writeOutputArtifacts`.
- **A3 paletteFilter sunset/noir** (`compose.ts`): documented but mapped to '' with
  no diagnostic. Fix: real grades + warn on unknown preset.
- **A4 workspace.jobId** (`agentic-modular.ts`): missing in CLI PipelineResult →
  output named `_seg_undefined.mp4`. Fix: set `jobId: id`.
- **C4 emoji stickers** (`render.ts`): `emojiByScene` dead on orchestrator path.
  Fix: burn 96px drawtext per scene (Segoe UI Emoji win / Noto Color Emoji linux).
  Verified via vision grid (fire on scene 1, rocket on scene 2).
- **voice.split crash** (`voice-generator.ts`): `job.voice` may be
  `{backend, voice}` → `.split` crashed. Fix: coerce defensively.
- **SFX gated on music** (`render.ts`): `opts.sfx` ignored without a music bed.
  Fix: build SFX layer whenever `opts.sfx` on; mix even without music.
- **W5-1 — `noir`/`sunset`/`cyberpunk` grades silent no-op** (`style-engine.ts`
  `gradeFilter`): only `warm/cool/cinematic/vivid/neutral` were mapped; the three
  declared enums in INPUT_FORMAT.md fell into `default` → a near-neutral `eq`
  (no visual grade applied). ALSO job-level `grade` was never forwarded into
  `computeStylePlan` (only `preset` was passed), so `"grade":"noir"` at job level
  did nothing at all. Fix: extend `GradeKind` union + `GRADES` pool with the three;
  add real filter strings (`noir` = `hue=s=0,eq=contrast=1.35` grayscale via YUV
  hue — NOT `format=gray` which forces a slow RGB→gray path on ffmpeg-static CPU;
  `sunset` = warm `hue=h=18:s=1.15`; `cyberpunk` = `hue=h=-22:s=1.25`). Forward
  `opts.grade` → `stylePlan` `gradeBias` (all scenes) in `render.ts`; forward
  `job.grade` in `agentic-modular.ts`. Verified: standalone ffmpeg encodes all
  three grades in seconds; grades now apply on the production (segmented) path.
- **W5-2 — `zoompan` INFINITE ENCODE HANG + OOM** (`render.ts`): `zoompan`'s `d`
  is OUTPUT FRAMES PER INPUT FRAME, not a duration. With `d=1` on a still image,
  zoompan emits 1 frame; the downstream `trim=duration=<dur>` can't stretch it →
  ffmpeg LOOPS the zoompan input forever (MULTI-HOUR encode; observed
  `time=05:10` at 1000× speed, never terminates). Hits EVERY image scene with
  ken-burns (DEFAULT for image scenes) → can hang the whole pipeline.
  **THE FIX THAT SHIPS (do NOT just bump `d`):** `d=${Math.round(dur*25)}` STILL
  OOMs — zoompan BUFFERS all `d` frames (~180MB for a 2.6s/25fps scene) and
  SIGKILLs the 6GB box (observed `RENDER_EXIT=137` at 346MB free). Replace
  `zoompan` ENTIRELY with a streaming `scale`+`crop` pan (no frame buffer, no loop,
  no OOM) at ALL four sites:
  - segmented default kenburns (~L835):
    `scale=${Math.round(W*1.04)}:${Math.round(H*1.04)}:force_original_aspect_ratio=increase,crop=${W}:${H}:x='(iw-${W})*(t/${dur})':y='(ih-${H})*(t/${dur})'`
    (the `tpad=stop_mode=clone:stop_duration=${dur}` BEFORE it provides the timed
    stream so `t` advances).
  - segmented punchIn (~L923): `scale=${Math.round(W*punch)}:${Math.round(H*punch)}:...:crop=...:x='(iw-${W})*(1-(t/${dur}))':y='(ih-${H})*(1-(t/${dur}))'`
    (zooms from `punch`→1 as t→dur).
  - segmented keyframe zoom (~L907): `scale='iw*(${expr})':'ih*(${expr})':force_original_aspect_ratio=increase,crop=${W}:${H}:x='(iw-${W})/2':y='(ih-${H})/2'`.
  - non-segmented default (~L632): same form as the segmented default.
  Verified: standalone `scale`+`crop` produces correct bounded `<dur>` output; the
  Grades job then renders with RAM holding 400–1100MB (was SIGKILL at 346MB with
  `zoompan d=dur*25`).
- **W5-2b — voice-mix `amix duration=longest` on AUDIO-LESS `silent` = SECOND hang
  class** (`render.ts` final music pass): `[0:a][a]amix=inputs=2:duration=longest`
  where input 0 is the concatenated `silent` video (no audio track when no scene
  had voiceover). `duration=longest` waits on the video's (nonexistent) audio →
  muxer copies the video stream forever (observed 4h+ for a 4s source;
  `render.test.ts` timed out at 79%). FIX: append `-shortest` to that mux. Symptom
  differs from the zoompan hang: `time=` climbs in the PASS2/voice-mux ffmpeg stderr
  WHILE SEGMENTS completed fine. (Committed separately as `f09c04a` by a sibling
  agent during the same session — merge, don't re-fix.)

## Stale / NOT a real bug (re-checked this session)
- "render.ts crashes on voiceovers" — a `sceneVoicePath` guard already exists at
  `render.ts`; re-render produced a valid MP4. Do NOT re-fix.

## Open at session end (uncommitted / triaged)
- BUG A6 (`audio-track.ts` addAudioTrack "drops audio on silent file"): the repro
  test FAILED but the raw ffmpeg mux + isolated `addAudioTrack` calls SUCCEEDED →
  looks like a flaky harness probe, NOT a real source defect. Do NOT ship a fake
  fix; isolate first (see references/flaky-isolation.md).
- Parser P-1/P-3/P-4 (long-line duration, bogus filename keyword, dropped duplicate
  tag) from earlier findings_parser.md — triaged, NOT yet patched in source.
