# Windows Python isolation + Voicebox install (CORRECTED 2026-07-18)

This box (Windows 10, ~6 GB RAM, **RTX 3050 Laptop GPU 4 GB VRAM + CUDA 12.6**,
Hermes shell) has traps that silently break any `pip`/`uv` Python install. The
earlier version of this file was WRONG about one critical thing — read the
"CORRECTION" box first.

> ## ⚠️ CORRECTION (supersedes earlier "3.86 GB OOM" claim)
> The earlier note said "Kokoro is 3.86 GB → cannot load on this laptop." That
> was a misdiagnosis. The 3.86 GB download was **Qwen 1.7B** (`Qwen/Qwen3-TTS-12Hz-1.7B-Base`),
> which `/models/load` pulls because that endpoint is **Qwen-only**. The actual
> Kokoro engine is **`hexgrad/Kokoro-82M` ≈ 350 MB** and runs FINE on this box.
> The earlier OOM was **CPU torch loading the Qwen model into system RAM** — not
> a Kokoro problem. Fix: install **CUDA torch** so models load into **VRAM**, not
> system RAM. Verified: Kokoro-82M uses ~819 MB VRAM, system RAM untouched, 5.3 s
> WAV synthesized successfully. **Voicebox DOES work on this laptop via the GPU.**

## Trap 1 — the Hermes `PYTHONPATH` leak (the big one)

The Hermes desktop shell exports a global `PYTHONPATH`:
```
PYTHONPATH=C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent;C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages
```
Every Python process (including a fresh venv's `python.exe`) prepends Hermes's
site-packages to `sys.path` ahead of its own `.venv`. Symptoms:
- Wrong package versions resolve (e.g. `huggingface_hub==1.2.3` from Hermes instead
  of your venv's pinned version).
- Import-time version clashes (transformers demands hf_hub>=1.5 but resolves Hermes's 1.2.3).

### Fix (do BOTH, in this order)
1. **Build the venv with uv's managed standalone CPython, NOT the Hermes `python`.**
   `python` on PATH == Hermes's venv python, so `python -m venv` creates a
   *venv-of-a-venv* that inherits Hermes's site-packages. Use:
   ```bash
   uv venv --python 3.11 .venv      # uv fetches a clean CPython 3.11, not Hermes's
   ```
2. **Strip PYTHONPATH for every install AND every run** with empty-assignment:
   ```bash
   env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe <pkgs>
   env PYTHONPATH= .venv/Scripts/python.exe -m backend.main ...
   ```
   Verify clean: `env PYTHONPATH= .venv/Scripts/python.exe -c "import sys; print([p for p in sys.path if 'hermes' in p])"` → must print `[]`.

## Trap 2 — stale backend holding the port (silent bind failure)

`uvicorn` fails with `[Errno 10048] ... only one usage of each socket address is
normally permitted` when a PREVIOUS backend launch wasn't fully killed. All your
calls then hit the DEAD/old backend.

### Fix
Before every relaunch, free the port:
```bash
netstat -ano | grep ":17493" | grep LISTENING        # find PID
taskkill /F /PID <pid>                                # kill it (MSYS: /F not //F)
sleep 2
netstat -ano | grep ":17493" | grep LISTENING || echo FREE
```

## Trap 3 — Windows long-path extraction failure (CUDA torch)

`uv pip install torch==2.13.0+cu126` fails to extract on this box:
`failed to create file ... cublasLt64_12.dll: The system cannot find the path
specified` — the uv temp path + nested dll exceeds 260 chars.

### Fix — point TMPDIR + UV_CACHE_DIR at a short path:
```bash
mkdir -p C:/tmp
env PYTHONPATH= TMPDIR=C:/tmp UV_CACHE_DIR=C:/tmp/uvcache \
  uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cu126 "torch==2.13.0+cu126" "torchaudio==2.11.0+cu126"
```

## Voicebox headless backend — GPU-aware install (VERIFIED WORKING)

Repo: `jamiepine/voicebox` (MIT). Headless backend = `backend/` (FastAPI).
**You have an RTX 3050 (4 GB VRAM) + CUDA 12.6** → install CUDA torch so models
load into VRAM, not system RAM. This is what makes it work on the 6 GB box.

```bash
git clone --depth 1 https://github.com/jamiepine/voicebox.git C:/one/voicebox
cd C:/one/voicebox
uv venv --python 3.11 .venv
# 1) CPU-side deps + backends. misaki[en] ONLY (NOT [ja]/[zh] → pyopenjtalk → cmake).
env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe \
  --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-minimal-cpu.txt
#    backend import chain also needs (not all in minimal list):
env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe \
  fastmcp pedalboard Pillow aiofiles whisper qwen-tts
# 2) GPU: CUDA torch → models load into VRAM. Defeats the OOM.
env PYTHONPATH= TMPDIR=C:/tmp UV_CACHE_DIR=C:/tmp/uvcache \
  uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cu126 "torch==2.13.0+cu126" "torchaudio==2.11.0+cu126"
# Verify:  .venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())" -> True
```

`requirements-minimal-cpu.txt` (CPU-only base, **misaki[en] only** to avoid cmake):
```
--extra-index-url https://download.pytorch.org/whl/cpu
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
sqlalchemy>=2.0.0
alembic>=1.13.0
python-multipart
transformers>=4.36.0,<=4.57.6
accelerate>=0.26.0
huggingface_hub>=0.20.0
soundfile
librosa
kokoro>=0.9.4
misaki[en]>=0.9.4          # [en] ONLY — [ja,zh] pulls pyopenjtalk which needs cmake (absent here)
en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
pyloudnorm
```
Pitfalls hit (still valid):
- `--index-url` (not `--extra-index-url`) for torch CPU → makes PyPI unreachable
  ("No matching distribution for alembic"). Use `--extra-index-url`.
- `misaki[ja,zh]` → `pyopenjtalk` → **cmake required, absent → build fails**. Use `misaki[en]`.
- `qwen-tts` pulls an old `huggingface_hub` (1.2.3); harmless once `PYTHONPATH=` is
  cleared so the venv resolves its own pinned version, not Hermes's. Keep `qwen-tts`
  (Voicebox's import chain imports it even if you only use Kokoro).

### Run
```bash
env PYTHONPATH= .venv/Scripts/python.exe -m backend.main \
  --host 127.0.0.1 --port 17493 --data-dir C:/one/voicebox/.voicebox-data
# log prints:  GPU: CUDA (NVIDIA GeForce RTX 3050 Laptop GPU); Ready
```

## Voicebox API reality (the flow that ACTUALLY works)

- **`POST /models/load` is Qwen-only** — it calls `load_model_async` →
  `qwen-tts-{size}` (1.7B / 0.6B). Sending `{"model_size":"kokoro"}` is IGNORED
  (JSON body, not the `model_size` query param) and it defaults to loading
  **Qwen 1.7B (3.6 GB)** → OOM on CPU. **Do NOT use `/models/load` for Kokoro.**
- **Kokoro + clone engines load LAZILY on first `/speak`** via
  `get_tts_backend_for_engine(engine)`. No manual load needed.
- **Voicebox is PROFILE-BASED**: every generation (even plain Kokoro narration)
  needs a voice `profile`. Kokoro has built-in PRESET voices (no reference audio):
  `af_heart`, `af_bella`, `am_adam`, … Create a preset profile once:
  ```bash
  curl -X POST http://127.0.0.1:17493/profiles -H "Content-Type: application/json" \
    -d '{"name":"Narrator (Kokoro Heart)","voice_type":"preset",
         "preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}'
  # -> {"id":"<PROFILE_ID>", ...}   export VOICEBOX_PROFILE_ID=<PROFILE_ID>
  ```
- **Synthesis flow (verified):**
  1. `POST /speak`  `{ text, profile, engine:"kokoro", language }` → `{ id, status:"generating" }`
  2. poll `GET /generate/{id}/status` (SSE stream; first frame `data: {...}`) until `status:"completed"`
  3. `GET /audio/{id}` → WAV (24 kHz mono PCM)
- `/models/status` lists all 7 engines + loaded/downloaded flags (useful health check).

## VRAM/RAM budget on this box (RTX 3050 4 GB VRAM)
- **Kokoro-82M (recommended):** ~800 MB VRAM, ~0 system RAM — fits comfortably,
  even with Remotion rendering on the iGPU.
- **Qwen 1.7B (~3.6 GB):** needs >4 GB VRAM → will NOT fit this card. Use Kokoro
  for narration; reserve Qwen for a bigger-GPU machine. Chatterbox-Turbo (~1.5 GB)
  is the smallest clone option if you must clone on this GPU.
- Always launch with `PYTHONPATH=` cleared so the backend uses only `.venv`.

## Companion Node-side integration (AVG project — ALREADY WIRED + committed)
- `src/lib/voicebox-lifecycle.ts` — spawn backend (with `PYTHONPATH=` cleared), check `/models/status`, kill process.
- `src/lib/api-tts-provider.ts` `generateVoiceoverWithVoicebox()` — `POST /speak`
  (profile + engine), poll status to completion, `GET /audio/{id}` → WAV. **Requires
  `VOICEBOX_PROFILE_ID`** (set to the Kokoro preset profile). Fails safe to Edge-TTS.
- Env: `TTS_PROVIDER=voicebox`, `VOICEBOX_API_URL`, `VOICEBOX_ENGINE` (default `kokoro`),
  `VOICEBOX_PROFILE_ID` (**required**), `VOICEBOX_BACKEND_DIR`, `VOICEBOX_PYTHON`.
