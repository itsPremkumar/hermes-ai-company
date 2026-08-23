# AVS voice/music/audio path — bug-hunt notes (2026-07-28)

## Harness pitfalls (workspace/bug-hunt/harness.mjs, agentic-modular CLI)

1. **`[Visual:]` tags only bind when the file lives under `input/visuals/`.**
   `script-parser.ts:375` calls `inputAssetPath(effectiveVisual)` →
   `resolveProjectPath('input','visuals',...)` which THROWS/normalizes away
   absolute paths and `..` (path-safety). An absolute Windows path in a
   `[Visual:]` tag → `localAsset: undefined` → `visuals --no-acquire` warns
   "scene N has no localAsset — skipping in manifest" → render dies with
   `Fatal: No approved visuals to render.` FIX for test jobs: copy assets to
   `input/visuals/` and reference **bare filenames** in the tag.
   (Also: backslashes in JSON script strings → "Bad escaped character in JSON".)

2. **Voice-lock file** `workspace/bug-hunt/.voice.lock` serializes Kokoro across
   parallel subagents. Check PID liveness (`powershell Get-Process -Id <pid>`)
   before deleting a stale lock; `tasklist //FI` does not work in git-bash
   (MSYS mangles `/FI`).

## A3 — render crash on missing `voiceovers.scenes` — ✅ CLOSED (2026-07-28 audit)
- WAS: `src/agentic/orchestrator/render.ts:736` (segmented branch):
  `res.voiceovers?.scenes[clip.idx]` — the optional chain covered `voiceovers`
  but NOT `.scenes`, so `voiceovers = {voiceoverDriven,sceneCount,fallbackUsed}`
  (the slim shape the modular CLI writes when no per-scene WAVs exist) →
  `TypeError: Cannot read properties of undefined (reading '0')`, killing every
  CLI render for fallback-voice jobs.
- FIX (commit merged to main, `095149e`): extracted a defensive
  `sceneVoicePath(voiceovers, idx)` accessor (optional chain on `.scenes`) used
  at the crash site; AND `agentic-modular.ts` now always normalizes
  `result.voiceovers.scenes` to a real array (on-disk WAVs, else `[]`) so the
  slim shape can never reach the renderer. Unit test `render.test.ts` +
  `repro-a3.ts` prove BEFORE throws the exact TypeError, AFTER returns
  `undefined` (silent anullsrc fallback).
- Repro pattern that MUST stay green: `npx tsx --test src/agentic/orchestrator/render.test.ts`.

## SIBLING BUG CLASS — audio-less `[0:a]` crash (BUG #4 family) — ✅ CLOSED same audit
The crash class recurs across SEPARATE modules whenever a filter_complex
references `[0:a]`/`[1:a]` unconditionally on an audio-less input
(`Stream specifier ':a' matches no streams`). Fixed in this audit:
- `edit.ts` `changeSpeed`/`addAudio`/`silenceRemove` — guard via `hasAudioStream()`.
- `agentic-editor.ts` `speed` (COMMANDS['speed']) — probe via `getMediaInfo()`,
  skip `[0:a]` branch + `-an` when no audio.
- `silence.ts` `removeSilence` — probe via `probeMedia().hasAudio` (added to
  `MediaInfo`), drop the `[a]` filter branch + map + codec when absent.
- `render.ts` voiceover indexing — `sceneVoicePath` (see A3 above).
- **Audit sweep recipe (reuse):** `grep -rn "\[0:a\]\|\[1:a\]\|voiceovers?.scenes\[" src/`
  and confirm every hit probes/guards before referencing the audio stream or
  array. `probeMedia()` exposes `hasAudio` for the guard.

## Suspects noted (not fully verified — render crash blocked e2e audio checks)
- Procedural ambient music is very quiet: `procedural.ts` `volume=0.12` +
  render-stage `AUDIO_FULL_LEVEL=0.18` duck → near-inaudible bed. Verify with
  ffmpeg `volumedetect` on final output before filing.
- `music-system/processing/looper.ts:36` uses `aloop=loop=N-1:size=0` (size=0
  may not loop as intended on some builds) while `operations/sfx.ts:117`
  uses the robust `-stream_loop -1 -t` — two inconsistent loop helpers.
- Kokoro backend: model-loads lazily inside /speak (no /models/load — 500s on
  "kokoro", already handled by `preloadable = engine !== 'kokoro'` in
  voice-controller.ts:439). Kokoro generate() returns 1s SILENCE fallback when
  pipeline yields no chunks (kokoro_backend.py:286) — a silent-voiceover output
  can therefore be a Kokoro empty-chunk case, not an ffmpeg mixing bug.

## Audio verification recipe (once an MP4 exists)
```
ffprobe -v error -select_streams a -show_entries stream=duration -of default=nw=1:nk=1 out.mp4
ffprobe -v error -select_streams v -show_entries stream=duration ...   # diff < 0.5s
ffmpeg -i out.mp4 -map 0:a -af volumedetect -f null - 2>&1 | grep mean_volume  # non-silent
```
Music-mixed check: extract audio, compare mean_volume of speech gaps vs a
voice-only render.
