# AVS audio subsystem — verified findings & probe recipes (music/SFX/voice bug hunt)

Confirmed by rendering via `workspace/bug-hunt/harness.mjs` and ffprobe/volumedetect (July 2026). Full report: `workspace/bug-hunt/findings_music.md`.

## Architecture facts (save re-discovery time)
- TWO independent audio-mix paths:
  1. **Modular render path** (`agentic-modular.ts` runRender → `orchestrator/render.ts`): duck level comes ONLY from env `AUDIO_DUCK_LEVEL` (0.06) / `AUDIO_FULL_LEVEL` (0.18). Job fields `duckDepth`, `voiceVolumeByScene`, `sfxByScene` are NOT read here.
  2. **Compose path** (`operations/compose.ts` via single-feature/wave-scheduler): DOES read `duckDepth`/`voiceVolumeByScene`/`sfxByScene`/`loopMusic`/`normalizeLufs` via `advanced-fx.ts` `sceneDuckGain`/`sceneVoiceVolume`.
  When testing an audio job field, first check WHICH path the run takes — most "field ignored" bugs are path-routing, not logic.
- `backgroundMusic` is resolved with `inputAssetPath()` = **input/visuals/**, never `input/bgm/` (agentic-modular.ts ~263/331, pipeline.ts ~416). Workaround: copy the mp3 into `input/visuals/`.
- `voicesByScene` values that aren't `*Neural` are forwarded as raw VoiceBox **profile ids** (voice-controller.ts ~474). A kokoro preset name like `af_bella` → backend 404 → that scene's WAV is missing, no fallback.
- Missing scene WAV + positional indexing bug: modular runRender builds `voiceovers.scenes` only from WAVs found on disk, but `sceneVoicePath()` (render.ts ~315) indexes by **array position**, not `entry.sceneIndex` → all later narrations shift onto wrong scenes. Detect with per-window volumedetect (a near-silent tail window ≈ music bed only, mean ~−46 dB).
- `render.ts:828` gates SFX on `opts.sfx && music` — no music ⇒ no SFX at all on the modular path.
- compose.ts times SFX with `-itsoffset` before an audio input feeding filter_complex/amix — unreliable; `adelay=<ms>` (as in render.ts:139) is the correct idiom.
- `job.music.mood` (structured music object) is not wired anywhere in adapters; only `job.musicQuery` reaches the free-music resolver.

## Probe recipes
- Per-scene loudness windows (finds shifted/silent narration):
  `"$FF" -ss <t> -t 3 -i out.mp4 -map 0:a -af volumedetect -f null - 2>&1 | grep mean_vol`
- A/V duration diff: `ffprobe -show_entries stream=codec_type,duration -of csv out.mp4` (pass if <0.5 s).
- ffprobe-static binary lives at `node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe`.

## Terminal gotcha (this repo, git-bash agent shell)
Multi-command lines mixing `VAR=path; for ... ; done` with quoted .exe paths trip the agent's hardline command blocker. Split into separate simple `A && B` commands, one ffmpeg/ffprobe invocation per command where possible.
