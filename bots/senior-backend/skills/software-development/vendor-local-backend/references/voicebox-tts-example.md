# Reference: Voicebox TTS vendored into AVS (concrete example)

This is the worked example behind the `vendor-local-backend` skill, using the
Automated-Video-Generator (AVS) project. Reuse the *structure*, not just the names.

## Source
- Upstream: https://github.com/jamiepine/voicebox (MIT, © 2026 Voicebox Contributors)
- Cloned at `C:/one/voicebox` (commit `52f8d8d`, branch main).
- Venv with torch+kokoro: `C:/one/voicebox/.venv/Scripts/python.exe`
- Regenerator script: `scripts/vendor-real-voice-backend.mjs` (copies + strips).

## Final layout (after rename churn: real-voice-backend → tts → speech)
- Backend: `src/speech/` (flattened Python pkg, `python -m speech.main`, cwd=`src/`).
- TS lifecycle: `src/lib/speech-backend.ts` (renamed from `voicebox-lifecycle.ts`).
- TS stage: `src/agentic/media/voice-controller.ts` + `voice-controller.test.ts`.
- Orchestrator hook: `src/agentic/orchestrator/pipeline.ts:493` → `runVoiceStage(plan, workspace, req.voice, onProgress)`.
- Workspace: `AgenticWorkspace.audioDir = <root>/audio` (added to type in `workspace.ts`).

## Backend API contracts (verified live)
- Health: `GET /health` → 200 `{"status":"healthy",...}`
- Profiles list: `GET /profiles` → `[{id, preset_engine, preset_voice_id, ...}]`
- Profile create: `POST /profiles` body
  `{"name":"agentic-kokoro-af_heart-<ts>","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart"}`
  → returns `{id}` (400 if name collisions; use unique name).
- Speak: `POST /speak` body `{"text":...,"profile":<id>,"engine":"kokoro","language":"en"}` → `{id}`
- Poll: `GET /generate/<id>/status` (SSE) → `data: {"status":"completed"}`
- Audio: `GET /audio/<id>` → WAV stream.
- Models load: `POST /models/load` with **query param** `?model_size=kokoro` (NOT body).
  NOTE: 500s for kokoro (drives default Qwen/Chatterbox loader) — skip preload for kokoro.
- Engines: kokoro (preset, ~0.8GB, loads lazily), chatterbox_turbo, qwen (need `/models/load`).
- MCP: backend mounts `/mcp` (optional deeper agent-tool integration, not done).

## Env vars (kept as READ aliases in speech-backend.ts; defaults hardcoded)
- `TTS_PROVIDER` default `voicebox` (ensureBackend gated on this; empty = proceed).
- `VOICEBOX_ENGINE` default `kokoro` (was `chatterbox_turbo` — changed).
- `VOICEBOX_PYTHON` default `C:/one/voicebox/.venv/Scripts/python.exe`.
- `VOICEBOX_BACKEND_DIR` default `<cwd>/src` (resolves `src/speech`).
- `VOICEBOX_PORT` / `VOICEBOX_API_URL` default `:17493`.
- `VOICEBOX_DATA_DIR` default `<cwd>/workspace/cache/voicebox` (DB leak fix).
- ZERO-CONFIG: with none set, system still generates real voice (defaults kick in).

## Spawn command (in speech-backend.ts)
```
python -m speech.main --host 127.0.0.1 --port <port> --data-dir <workspace>/cache/voicebox
cwd = src/
env: { ...process.env, PYTHONPATH: '' }   # so backend uses its own torch
```

## Gotchas caught live (don't repeat)
1. `src/data/<pkg>.db` leak → pass `--data-dir`, gitignore `src/data/`, `*.db`.
2. `/models/load` JSON body 500 → use query param; skip preload for kokoro.
3. Profile "already exists" 400 on 2nd run → GET /profiles reuse + unique create name.
4. `ensureBackend` bail on missing `VOICEBOX_PROFILE_ID` → gate on `TTS_PROVIDER` instead
   (profile provisioned later by controller).
5. MSYS `patch` tool races on re-read of edited .ts files → anchor on a stable unique line
   (e.g. first `import`) when re-patching; don't loop on the same old_string.

## Test commands
- Typecheck: `npm run typecheck`
- Voice integration: `node --import tsx --test --test-timeout=240000 src/agentic/media/voice-controller.test.ts`
- Zero-config proof: clear all `<PKG>_*`/`TTS_PROVIDER` env, run controller → real WAV.
- Full suite (CI): `npm test` (typecheck + unit). Note: 15 pre-existing fails are offline
  image/visual/provider tests in sandbox — unrelated to voice.
