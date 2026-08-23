# Music / Voice path bugs (AVS modular CLI) — found+fixed 2026-07-28 (commit ecac1e4)

Source of these: parallel subagent bug hunt (findings_music.md), each bug
reproduced via real harness renders + ffprobe/volumedetect, then fixed and
re-verified. Keep for regression awareness — the same failure classes recur.

## M1 — backgroundMusic resolved under input/visuals/, never input/bgm/
- Sites: agentic-modular.ts `--no-acquire` branch (~:263) AND `fetchMusic`
  (~:331). Both called `inputAssetPath(name)` → input/visuals/<name>.
- User bgm at `input/bgm/__bundled__/<name>` was silently ignored → random
  free-music fallback selected instead. NO error/warn.
- Fix: try `inputBgmPath(name)`, then `inputBgmPath('__bundled__', name)`,
  then legacy `inputAssetPath(name)`. NOTE the `__bundled__` subdir — plain
  `inputBgmPath(name)` alone still misses the bundled tracks.
- Import gotcha: agentic-modular.ts has TWO scoped dynamic imports of
  path-safety; adding `inputBgmPath` to only the second gives
  TS2448 "used before its declaration" at the first site.
- Verify: render with the bgm file present ONLY under input/bgm/__bundled__,
  check render-manifest.json music asset path.

## M2 — per-scene kokoro voice name (af_bella) treated as raw VoiceBox profile id → 404, scene narration LOST
- voice-controller.ts ~:474: non-`*Neural` voiceOverride assigned directly to
  profId. Kokoro preset names are NOT profile ids → POST /generate 404 →
  scene WAV missing, "partial (2/3)", no fallback.
- Fix: detect kokoro names (`/^af_|^am_|^bf_|^bm_|^hf_|^hm_/`) and provision a
  real preset profile (list /profiles for matching preset_engine+
  preset_voice_id, else POST create), cached per-voice next to the default
  profile cache. Mirrors resolveProfileId's auto-provision block.

## M3 — voiceover positional indexing shifts narration when a scene WAV is missing
- render.ts sceneVoicePath did `scenes[idx]` (array position). runRender only
  pushes entries for WAVs found on disk → a missing scene 2 makes scene 3's
  narration play over scene 2's visuals and scene 3 goes silent.
- Evidence method: per-window volumedetect (`-ss/-t` windows) on the final mp4
  showing which scene windows carry voice.
- Fix: entries carry sceneIndex — match `scenes.find(s=>s.sceneIndex===idx)`,
  positional fallback for legacy shapes.

## M4 — duckDepth / voiceVolume silently dropped on modular render path
- render.ts reads ONLY env AUDIO_DUCK_LEVEL (0.06) / AUDIO_FULL_LEVEL (0.18).
- Fix (pragmatic): in runRender, set those env vars from job.duckDepth /
  job.voiceVolumeByScene[0] / job.voiceVolume before renderAgenticSlideshow.

## Still open (documented, unfixed as of session end)
- M5 sfxByScene ignored on modular path; render.ts:828 also gates cut-SFX on
  music being present.
- M6 music.mood not wired (engine has queryFromOpts, adapters never call it).
- M7 compose.ts SFX via `-itsoffset` before audio input likely lands at t=0
  (use adelay=<ms> like render.ts:139); amix renormalizes gain when SFX added.
- Motion FX (shakeByScene/speedRampByScene/punchInByScene) not typed in
  cli-job.ts nor forwarded — only direct composeVideo() callers get them.
- emojiByScene dead in modular path (SKILL.md #39); palette presets
  sunset/noir silent no-op (only cyberpunk mapped in buildPaletteFilter).

## Verification recipe used
- Harness: `node workspace/bug-hunt/harness.mjs <job.json> <name>` →
  plan→voice→visuals --no-acquire→render + 4-frame vision grid.
- Audio proof: `ffmpeg -i final.mp4 -af volumedetect -f null -` (mean_volume
  around −25 dB = audible voice; −46 dB window = music bed only / lost voice).
- A/V sync: ffprobe audio vs video stream durations, accept <0.5 s diff.
