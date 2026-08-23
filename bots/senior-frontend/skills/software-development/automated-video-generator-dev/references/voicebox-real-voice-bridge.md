# Voicebox (src/speech) — real voice from agentic-scripts.json

Verified 2026-07-26. The Voicebox TTS backend is `src/speech/` (Python/FastAPI +
Kokoro + Chatterbox). The TypeScript client that drives it is
`src/agentic/media/voice-controller.ts`; the auto-spawner is
`src/lib/speech-backend.ts`. The agentic CLI `src/adapters/cli/agentic-modular.ts`
(`npm run agentic:modular`) is the JSON-driven entry point for `agentic-scripts.json`.

## Start the backend (standalone, for verification or before a run)
The `ensureBackend()` path auto-spawns it from `cwd=src` using the in-repo `venv`,
so a normal `npm run agentic:modular pipeline` does NOT require manual start. But if
you want to prove/inspect it, launch it correctly:

```bash
cd /c/one/Automated-Video-Generator/src
/c/one/Automated-Video-Generator/venv/Scripts/python.exe -m speech.main \
  --host 127.0.0.1 --port 17493 \
  --data-dir /c/one/Automated-Video-Generator/workspace/cache/voicebox
```
**CRITICAL launch pitfall:** run with `cwd=src`. Running
`python -m speech.main` from the repo ROOT fails with
`ModuleNotFoundError: No module named 'speech'` (the package is `src/speech`).
`speech-backend.ts` already does this (`backendDir()` = `src`), so the auto-spawn
is correct — only a manual launch must respect it.

## Verify it is up + synthesize real audio (empirical proof)
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:17493/health   # expect 200
# create a kokoro preset profile
curl -s -X POST http://127.0.0.1:17493/profiles -H 'Content-Type: application/json' \
  -d '{"name":"proof","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart"}'
# /speak -> poll /generate/<id>/status until "completed" -> GET /audio/<id>
```
ffprobe the downloaded WAV: expects `pcm_s16le, 24000 Hz, mono` for kokoro.

## Engine reality on THIS box (CPU-only, no CUDA/ROCm)
- **kokoro** (e.g. `af_heart`, `am_michael`): works. Auto-provisioned as the default
  preset profile; real neural voice, ~3-4s per short line.
- **chatterbox_turbo** (used for real voice CLONES): `/models/load` returns
  **HTTP 500** on this CPU install. So `cloneVoiceFrom` / a clone-persona *clones the
  profile successfully* (`POST /profiles` + `/profiles/<id>/samples` OK) but the
  subsequent speak **fails** (engine can't load). The voice stage then falls back to
  the default kokoro profile for the affected scene(s). This is an ENVIRONMENT limit
  (no GPU), NOT a code defect. A CUDA/ROCm Voicebox variant would unlock cloned-voice
  synthesis. Do NOT chase the 500 as a code bug here.
- Default engine resolution: `process.env.VOICEBOX_ENGINE` or `kokoro`; preset voice
  `process.env.VOICEBOX_PRESET_VOICE` or `af_heart`.

## Bridging agentic-scripts.json -> real voice (added 2026-07-26)
`src/adapters/cli/agentic-modular.ts` now threads these job fields into the pipeline:

- `runPlan`: forwards `personas`, `scenePersonas`, `sceneDialogue`, `dialogueVoices`,
  `defaultPersona` into `buildPlan(...)` (so the Plan carries the cast).
- `runVoice`:
  - `cloneVoiceFrom: "clip.wav"` -> resolves to `input/voices/<clip>` and calls the
    **exported** `cloneFromVoicesDir(clip, cacheFile)` to auto-clone a real profile;
    passes the resulting id as `useClonedVoiceId` to `runVoiceStageSafe`.
  - `kokoroVoice: "af_heart"` -> sets `process.env.VOICEBOX_PRESET_VOICE` (named preset).
  - `voicesByScene: { "0": "<kokoroOrProfileId>" }` -> sets `scene.voiceOverride` for
    non-`*Neural*` ids (Neural ids still route to Edge-TTS).
  - `voiceSpeed`, `voicePitchSemitones` -> applied to every generated WAV via ffmpeg
    (`asetrate=44100*2^(semi/12)` then `atempo=speed`, re-sample to 44100). Logged as
    `applied voice fx (speed=..., pitch=... semi) to N scene(s)`.

**Verification that the bridge works (live run, 2026-07-26):** a kokoro-persona +
sceneDialogue + voiceSpeed=1.05 + voicePitchSemitones=2 job produced 3 valid
`pcm_s16le 44100Hz` WAVs with the fx applied; log showed
`voiceover generated via speech backend` + `applied voice fx ... to 3 scene(s)`.

## Pitfalls
- **`findReferenceVoice()` auto-clones ANY `*.wav` in `input/voices/`** even when the
  job uses kokoro personas (no `cloneVoiceFrom`). Symptom: log shows
  `cloning real voice from sample_narrator.wav (engine=chatterbox_turbo)` BEFORE the
  persona resolution, and chatterbox then fails/loads-slowly. To test personas WITHOUT
  the auto-clone hijack, temporarily move the reference clip aside
  (`mv input/voices/sample_narrator.wav input/voices/_sample_narrator.wav.bak`) and
  restore after. The auto-clone is intended behavior (zero-config "clone my voice"),
  just be aware it triggers on ANY clip presence.
- **plan MUST run before voice.** `runVoice` reads `workspace/jobs/<id>/plan.json`;
  without it the CLI prints `No plan found ... Run "plan" stage first.` So a JSON
  bridge test must do `npx tsx ...agentic-modular.ts plan --file ...` then `... voice --file ...`.
- **chatterbox clone is SLOW on CPU** even when it would load — a clone+generate run
  can sit >5 min before timing out. Always assert on the artifact (WAV bytes + ffprobe),
  not on wall-clock.
- **The `patch` tool's LINT line prints `error TS6053: File '.../agentic-modular.ts' not
  found` for EVERY edited TS file** here — it is a display artifact of the lint helper
  failing to resolve the path, NOT a real type error. Trust `npm run typecheck` exit 0.
- Voicebox backend log: `workspace/logs/voicebox_server.log` (when launched manually).

## Auto-start fix (2026-07-26) — `PYTHONPATH=''` killed the spawned backend
`ensureBackend()` (`src/lib/speech-backend.ts`) spawns the backend when none is up.
It used `env: { ...process.env, PYTHONPATH: '' }`. On Windows/venv that blanked
the venv's `site-packages` discovery for a PACKAGE import, so the child died
instantly and the pipeline fell back to Edge-TTS. The exact death:
```
Traceback (most recent call last):
  File "C:\...\src\speech\main.py", line 10, in <module>
    from .app import app
  File "C:\...\src\speech\app.py", line 106, in <module>
    from fastapi import FastAPI
ModuleNotFoundError: No module named 'fastapi'
```
**Fix:** spawn with `env: { ...process.env }` (no `PYTHONPATH` clearing). After the
fix, a COLD run (no manual server) auto-spawns: kill `:17493` listeners → run a voice
stage → log shows `spawning speech backend …` then `backend is up` then
`voiceover generated via speech backend`. Verify with the cold-start recipe in the
SKILL.md "Voicebox auto-start bug + fix" subsection (health `000` before, `backend is
up` during). Reproduce the bug manually: `PYTHONPATH='' python -m speech.main` fails
with the trace above; without the clearing it boots in ~2s.
