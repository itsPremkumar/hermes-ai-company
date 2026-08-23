# Voicebox headless integration into the agentic video pipeline (AVG)

Verified recipe from the session that cloned jamiepine/voicebox, installed the
headless backend on a 6 GB Windows laptop, and wired it into the pipeline's
`src/lib/api-tts-provider.ts` + new `src/lib/voicebox-lifecycle.ts`.

## Architecture (RAM-safe on low-spec box)
Voicebox is a SEPARATE Python process, NOT embedded in Node. The pipeline owns
its RAM lifecycle: **wake -> load one engine -> generate -> unload -> kill**.
- `ensureBackend()` spawns `python -m backend.main` if `/models/status` is down.
- `loadEngine(modelSize)` -> `POST /models/load {model_size}`.
- `unloadEngine(modelSize)` -> `POST /models/{name}/unload` (frees RAM, backend stays up).
- `killBackend()` terminates the process (zero RAM until next run).
- `api-tts-provider.ts generateVoiceoverWithVoicebox()` loads engine, calls
  `POST /generate`, then unloads in a `finally`. Fails safe -> Edge-TTS fallback.

Verified endpoints (read from `backend/routes/models.py` source, NOT guessed):
`POST /models/load`, `POST /models/unload`, `POST /models/{model_name}/unload`,
`GET /models/status`, `POST /models/download`, `DELETE /models/{model_name}`.
Generate endpoint is `POST /generate` (NOT `/speak`/`/tts_to_audio` - those are
the xtts/openai-local providers in the same file). Engines are separate modules:
`kokoro_backend.py`, `chatterbox_turbo_backend.py`, `qwen_custom_voice_backend.py`, etc.

## Install recipe (Windows, base python is itself a venv -> `python -m venv` BROKEN)
`python -m venv` on this box produces a NON-ISOLATED env (base python = Hermes's
venv; pip resolves deps from Hermes's site-packages and does NOT install into
`.venv`). **Use `uv` instead - it creates a properly isolated venv.**

```bash
git clone --depth 1 https://github.com/jamiepine/voicebox.git C:/one/voicebox
cd C:/one/voicebox
uv venv .venv
uv pip install --python .venv/Scripts/python.exe \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -r requirements-minimal-cpu.txt
```
`requirements-minimal-cpu.txt` (CPU-only, Kokoro + backend, NO clone engines):
```
--extra-index-url https://download.pytorch.org/whl/cpu
fastapi>=0.109.0 uvicorn[standard]>=0.27.0 pydantic>=2.5.0
sqlalchemy>=2.0.0 alembic>=1.13.0 python-multipart
torch>=2.2.0 transformers>=4.36.0,<=4.57.6 accelerate>=0.26.0
huggingface_hub>=0.20.0 soundfile librosa
kokoro>=0.9.4 misaki[en]>=0.9.4
en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
pyloudnorm
# backend import chain also needs:
fastmcp pedalboard pydub numpy scipy "qwen-tts>=0.0.5"
```

## PITFALLS (each cost a real debug cycle)
1. **`python -m venv` is broken here** - base python is a venv. Use `uv venv`.
2. **`--index-url` (torch CPU) breaks the rest** - it redirects ALL packages to
   the torch-only index, so `alembic` etc. get "no matching distribution". Use
   `--extra-index-url` so PyPI stays primary.
3. **`misaki[ja,zh]` needs cmake** (pulls `pyopenjtalk`, no compiler on box).
   Use `misaki[en]` only - English Kokoro needs no Japanese/Chinese G2P.
4. **Backend import chain requires ALL engine packages importable** even to load
   ONE engine (`services/tts.py` imports every backend module at load time). So
   you must install `qwen-tts`, `fastmcp`, `pedalboard`, etc. just to use Kokoro.
   "load-on-demand" saves RAM, NOT install footprint. Keep disk headroom ~6-8 GB.
5. **`qwen-tts` downgrades `huggingface-hub` to 1.2.3**, which the backend rejects
   (`>=1.5.0,<2.0` required). Pin `huggingface-hub>=1.5.0,<2.0` AND install
   `qwen-tts` together so they resolve compatibly; then RESTART the backend
   (a running process keeps the old imported version).
6. **Run from repo ROOT**, not `backend/`: `python -m backend.main` (package path
   is `backend.main` relative to `C:/one/voicebox`). The `main.py` entrypoint
   accepts `--host 127.0.0.1 --port 17493 --data-dir <dir>`. Default port 8000;
   pipeline uses 17493 (`VOICEBOX_API_URL`).
7. **PyPI timeouts** (e.g. `pooch`) are transient - re-run `uv pip install`, it
   resumes from cache.

## Launch + verify cycle
```bash
cd C:/one/voicebox
.venv/Scripts/python.exe -m backend.main --host 127.0.0.1 --port 17493 \
  --data-dir C:/one/voicebox/.voicebox-data
# in another shell:
curl http://127.0.0.1:17493/models/status          # expect 7-engine registry
curl -X POST http://127.0.0.1:17493/models/load -H "Content-Type: application/json" -d '{"model_size":"kokoro"}'   # downloads ~312MB first time
# POST /generate {text, model_size:"kokoro"}  -> wav stream
curl -X POST http://127.0.0.1:17493/models/kokoro/unload
```

## Env vars (documented in docs/VOICE_CLONING_GUIDE.md section 10)
`TTS_PROVIDER=voicebox`, `VOICEBOX_API_URL` (default :17493),
`VOICEBOX_BACKEND_DIR` (C:/one/voicebox), `VOICEBOX_PYTHON` (.venv python),
`VOICEBOX_MODEL_SIZE` (default kokoro; chatterbox-turbo for clone),
`VOICEBOX_PROFILE_ID` (cloned-voice profile, clone jobs only).

## RAM budget on the 6 GB box
- Kokoro: +~0.5-1 GB (feasible if Paperclip/heavy procs closed).
- Clone engine (chatterbox-turbo): +~1.5-2 GB - load ONLY for the clone job,
  then `unloadEngine` immediately. Never keep two engines resident.
