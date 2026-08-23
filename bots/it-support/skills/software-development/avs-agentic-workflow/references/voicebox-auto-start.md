# Voicebox cold auto-start — proof recipe + MSYS note

## What was broken (2026-07-26)
`src/lib/speech-backend.ts` is supposed to auto-spawn the Voicebox backend
(`python -m speech.main` from `cwd=src`) when `TTS_PROVIDER=voicebox` and no backend is up.
It TRIED but the spawned server died instantly → the pipeline silently fell back to Edge-TTS.

**Root cause:** the spawn set `env: { ...process.env, PYTHONPATH: '' }`. On Windows with the
in-repo `venv`, blanking `PYTHONPATH` suppresses the venv's `site-packages` discovery when the
module is imported as a *package*:
```
from .app import app        # speech/main.py
  -> from fastapi import FastAPI
  -> ModuleNotFoundError: No module named 'fastapi'
```
uvicorn never starts → `ensureBackend()` times out / gives up → Edge-TTS fallback.

**Fix (committed):** spawn with `env: { ...process.env }` (let the venv resolve its own
packages). No `PYTHONPATH` clearing.

## Lesson (reusable)
When a spawned child dies with `No module named X` where X IS a venv dependency, suspect a
cleared `PYTHONPATH`/`PYTHONHOME` in the spawn env — NOT a missing package. Reproduce the spawn
manually with the SAME env to confirm:
- manual spawn with inherited env → works (server up in ~2s)
- manual spawn with `PYTHONPATH=''` → exact `No module named 'fastapi'` failure

## Cold-start verification recipe (prove auto-start with NO manual server)
Run from the repo root (bash/MSYS):
```bash
# 1) Kill any running backend — confirm DOWN (health = 000)
for p in $(netstat -ano 2>/dev/null | grep 17493 | awk '{print $5}' | sort -u); do
  taskkill /F /T /PID $p      # MSYS: single slash /F, NOT //F (shell mangles //F -> /F)
done
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:17493/health   # expect 000

# 2) Run a voice stage cold (no server running)
npx tsx src/adapters/cli/agentic-modular.ts voice --file input/scripts/<job>.json > /tmp/v.log 2>&1

# 3) Check the log
grep -E "spawning speech backend|backend is up|fallback" /tmp/v.log
#   "[SPEECH-BACKEND] backend is up"        => auto-start WORKS
#   "voicebox backend unavailable ... fallback" => STILL BROKEN
```
A `000` health BEFORE + `backend is up` DURING = auto-start confirmed.

## MSYS taskkill note
The bash shell mangles `//F` → `/F`. Windows executables take `/F` under MSYS, so use
`taskkill /F /T /PID <pid>` (single slash). `taskkill //F` errors with
`Invalid argument/option - '//F'`. Confirm the kill with `netstat -ano | grep 17493`
(empty = down).

## Engine reality (CPU-only box, 2026-07-26)
- **Kokoro** (`preset` voices like `af_heart`) works fully end-to-end — real WAVs produced.
- **chatterbox_turbo** (`cloneVoiceFrom` / clone personas) returns HTTP 500 on `/models/load`
  here (no GPU). The clone *profile* is created but *speaking* it fails → falls back to kokoro.
  This is an ENVIRONMENT limit (no GPU), not a code bug — do not chase the 500. A CUDA/ROCm
  Voicebox variant would unlock cloned-voice synthesis.

## Empirical proof that shipped this session
A kokoro-persona + sceneDialogue + `voiceSpeed=1.05` + `voicePitchSemitones=2` job produced
3 valid `pcm_s16le 44100Hz` WAVs with fx applied; log line `voiceover generated via speech
backend`. `npm run typecheck` exit 0.
