# AVS Voice Backend — vendored `src/speech/` (jamiepine/voicebox, MIT)

Condensed detail bank for the Automated-Video-Generator (AVS) voice integration.

## License reality
- Voicebox (jamiepine/voicebox) is MIT. Vendored wrapper code is MIT.
- The MODELS are NOT Jamie's: Kokoro-82M = hexgrad (Apache-2.0), Chatterbox =
  ResembleAI (MIT), Qwen3-TTS = Alibaba (Apache-2.0). Kept as runtime
  downloads from HuggingFace; never bundled.
- Stripped from vendored copy: `hume_backend.py` (paid HumeAI), `routes/cloud.py`
  + `services/cloud.py` (Voicebox Cloud paid sync), `cuda.py`/`rocm.py` (GPU
  updaters), `tada` engine, `dac_shim.py` (unused), `build_binary.py` tada
  hidden-imports.
- Retained LICENSE at `src/speech/LICENSE` (Copyright (c) 2026 Voicebox
  Contributors).

## Profile API schema (auto-provisioning)
`POST /profiles` body:
```json
{ "name": "agentic-kokoro-af_heart-<ts>",
  "voice_type": "preset",
  "preset_engine": "kokoro",
  "preset_voice_id": "af_heart" }
```
Response: `{ "id": "<uuid>", ... }`. Idempotency rule: `GET /profiles`, find
one where `preset_engine === engine && preset_voice_id === voice`, reuse it;
else create with a UNIQUE name (timestamp) — a fixed name 400s on run 2
because profiles persist in the sqlite DB.

## Generation flow
1. `POST /speak` `{ text, profile, engine, language }` -> `{ id }`
2. poll `GET /generate/{id}/status` (SSE — parse first `data:` frame) until
   `completed`/`complete`/`done`
3. `GET /audio/{id}` (stream) -> WAV bytes

## The db-leak fix recipe (root cause + fix)
Root cause: `config.py` does `_data_dir = Path("data").resolve()` relative to
`cwd`. Spawned with `cwd=src`, the DB landed at `src/data/voicebox.db` ->
Untracked in git (the "U" file the user saw in VS Code Source Control).

Fix (two layers):
1. Spawn with `--data-dir <repo>/workspace/cache/voicebox` so the DB goes to a
   gitignored cache.
2. `.gitignore` adds `src/data/`, `*.db`, `voicebox.db` as defense-in-depth.

## Spawn contract (final)
- Command: `python -m speech.main --host 127.0.0.1 --port 17493
  --data-dir <repo>/workspace/cache/voicebox`
- cwd: `<repo>/src` (so `speech` package imports)
- venv python: `C:/one/voicebox/.venv/Scripts/python.exe`
- Controller: `src/agentic/media/voice-controller.ts` (ensureBackend ->
  resolveProfileId -> loadEngine(kokoro) -> per-scene generate -> unloadAll ->
  killBackend)
- Wired into orchestrator `src/agentic/orchestrator/pipeline.ts` voiceover
  stage as PRIMARY, with Edge-TTS fallback in the catch.

## Zero-config verification transcript (real, this session)
```
# no VOICEBOX_*/TTS_PROVIDER env set
VOICEBOX_* present? false
TTS_PROVIDER= undefined
Kokoro-82M loaded successfully
reusing existing kokoro/af_heart profile 803527d5-...
[100%] voiceover generated via speech backend
voiceoverDriven: true  profile: 803527d5-...
audio size: 188444
ZERO-CONFIG OK
```
Run twice: same profile reused (idempotent), no "already exists" 400.

## Test commands
- Integration: `node --import tsx --test src/agentic/media/voice-controller.test.ts`
  (Kokoro cold-load ~35-60s; timeout 240000).
- Boot probe: `python scripts/boot_voice_backend.py --pkg speech --src <repo>/src
  --venv <venv>/python.exe --port 17497 --cache <repo>/workspace/cache/voicebox`
- Full suite: `npm test` (typecheck + all unit). 15 pre-existing failures in
  this sandbox are network/provider/visual tests (Wikimedia/MetMuseum offline),
  unrelated to voice.
