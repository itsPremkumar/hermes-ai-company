# Bug bank — real crashes found by varied-input dogfooding (AVS editor pipeline)

Each entry: symptom → root cause → fix. All discovered by running the function on
a matrix of resolutions × audio-presence × durations, NOT by narrow unit tests.

## 1. restitch concat "dimension mismatch" on non-portrait
- Symptom: `restitchMaster` worked on 720x1280 portrait only; landscape/square/1080p
  failed with ffmpeg "Error reinitializing filters! / Invalid argument".
- Root cause: partA was trimmed from the master WITHOUT rescaling (kept native res),
  but `norm` (new scene) was force-scaled to hardcoded `scale=720:1280`. Concat filter
  needs identical dimensions → mismatch.
- Fix: probe master native W/H via ffprobe JSON (see #4); scale BOTH partA and norm to
  `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:...`.

## 2. restitch crash on silent (no-audio) master
- Symptom: `restitch failed: ... [i:a] ... matches no streams` for video-only masters.
- Root cause: concat filter spec `[i:v][i:a]` references an audio stream the silent
  master doesn't have. (Also hung: anullsrc is an ENDLESS source.)
- Fix: if master has no audio, add a finite silent track per part:
  `-f lavfi -i anullsrc=channel_layout=mono:sample_rate=44100:duration=<sceneDur>` and
  map `[2*i:v][2*i+1:a]`; append `-shortest` so the endless source can't hang the run.

## 3. render crash "reading 'replace'" AFTER video already rendered
- Symptom: `Cannot read properties of undefined (reading 'replace')` at
  render.ts ~154 (writeOutputArtifacts). Video had completed; crash at artifact-write
  discarded the whole output.
- Root cause: `res.plan.scenes.flatMap(s => s.searchKeywords)` — when a scene lacks
  `searchKeywords` (undefined), flatMap emits undefined, then `k.replace` throws.
  Scope-aware revise plans and many real plans omit searchKeywords.
- Fix: `s.searchKeywords ?? []` + `.filter(k => typeof k === 'string')`. Also default
  `voiceoverText ?? ''`. Same guard for kinetic-caption `cue.text.replace` (render.ts)
  and style-engine `s.voiceoverText.split` — wrap with `String(x ?? '')`.

## 4. ffprobe line-position parse misalignment (CRLF)
- Symptom: `probeVideo` returned `{width:720, height:720, codec:"1280"}` for a
  720x1280 clip — fields shifted.
- Root cause: `-of default=nw=1:nk=1` output parsed by array position; CRLF split
  misaligned width/height/codec/fps.
- Fix: use `-of json` and read `parsed.streams[0].width/height/codec_name` by KEY.

## 5. estimateAudioDurationSafe ceiling
- Symptom: 4.04s clip measured as 5s; broke duration comparisons.
- Root cause: `return Math.ceil(d)`.
- Fix: return precise float; round only at display.

## 6. revise full-pipeline hangs on network
- Symptom: `revise --auto` blocked forever fetching real media for a job with no cache.
- Fix: critiqueAndRevise prefers cached-workspace fast path (scope:'captions') so
  auto-fixes self-heal with ZERO network; full pipeline path bounded by
  AGENTIC_REVISE_TIMEOUT_MS (default 240s), fails safe instead of hanging.

## 7. revise missing output dir
- Symptom: `ffmpeg ... No such file or directory` when rendering revision.
- Fix: `fs.mkdirSync(outDir, {recursive:true})` before renderAgenticSlideshow.

## 8. music-duck `volume=eval=frame+between()` crashes ffmpeg with ENOMEM (Windows gyan.dev build)
- Symptom: pass2 (music mix) fails with
  `Failed to set value '[1:a]volume=eval=frame:volume='<expr>'[a];...' for option 'filter_complex': Invalid argument`
  then exit code `4294967294` (== -2, AVERROR(ENOMEM)) — EVEN when the exact same
  filter_complex string succeeds standalone against `-f lavfi -i anullsrc` synthetic
  audio. It fails against REAL audio input (mp4/mp3) but not anullsrc. Triggered by
  the per-caption-segment duck expression `full-(d1*between(t,a1,b1)+d2*between(t,a2,b2)+...)`
  where each `di` is a per-scene musicIntensity depth.
- Root cause: this ffmpeg build (gyan.dev 6.1.1 Windows static) runs out of memory
  evaluating the `between()`-heavy frame-eval volume expression over real PCM/compressed
  audio. NOT a syntax error — the string is valid and parses fine on synthetic input.
- Fix (graceful, render still completes): wrap pass2 in try/catch; on failure fall
  back to a flat `volume=${full}` (no frame-eval ducking). Also harden
  `buildDuckExpression` to `return null` (→ flat volume) when `full`/`duck`/per-scene
  delta are non-finite (NaN from an unset `AUDIO_FULL_LEVEL` env would otherwise
  produce `NaN-(...)` which ffmpeg rejects too). The render output is valid; music
  just ducks uniformly instead of per-caption. DO NOT "fix" by switching ffmpeg builds
  — the fallback is the correct portable behavior.
- Isolation pattern: run the EXACT filter_complex standalone with the REAL input files
  (not anullsrc) to reproduce the crash; swap to `volume=${full}` and confirm it
  completes. This proves the expression is valid but the build can't eval it on real audio.

## 9. agentic CLI reports dryRun jobs as "Gate FAIL"
- Symptom: every job run with `dryRun: true` printed `❌ Gate FAIL` and counted as failed
  in the Summary, even though planning/parsing succeeded perfectly.
- Root cause: the CLI's result handler checked `if (result.gate.pass && result.manifest)`
  to count success, but `runAgenticPipeline` hardcodes `gate = { pass: false }` in the
  dryRun early-return (no gate/manifest is produced by design). So dryRun always looked failed.
- Fix: treat `req.dryRun` results as completed (planning succeeded) — count completed and
  print `✅ DRY RUN OK — N scenes planned, Xs`. The dryRun path is the fast, offline way to
  validate the FULL control surface (all inline tags + top-level config) without network/voice.

## 10. voice backend hangs 120s×N before Edge-TTS fallback
- Symptom: every real render wasted ~120s (or more, with double-spawn ~240s) trying to
  start the vendored speech backend (torch/kokoro venv) which can NEVER work (missing
  `fastapi`/torch under RAM-limited setups) before falling back to Edge-TTS.
- Root cause: `ensureBackend` polled for `VOICEBOX_STARTUP_TIMEOUT_MS` (120s) waiting for
  `/health` even after the spawned python process had already exited with an import error.
- Fix: in `ensureBackend`, set an `exited`/`backendExited` flag on `backendProc.on('exit')`
  and break the poll loop immediately when the process is dead — fail-fast in ~1s instead of
  120s. The caller then falls back to Edge-TTS (or Windows offline speech) without the wait.
- Use the SAME fail-fast shape anywhere a child process is polled for readiness: detect
  process death, don't just poll a health endpoint on a dead process.
