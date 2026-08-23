---
name: voicebox-tts-integration
description: Integrate Jamie Pine's Voicebox (MIT) as a headless TTS / voice-clone backend into an agentic video pipeline, on a GPU-laptop (e.g. RTX 3050 4GB VRAM, 6GB RAM). Covers the real control surface (/speak async flow, profile-based generation, clone via reference upload), the CUDA-torch install recipe that survives a RAM/VRAM-starved Windows box, engine sizing for 4GB VRAM (Kokoro vs Chatterbox-Turbo vs Qwen), and a multi-scenario verification harness. Use when a user wants "my own voice in the video", "clone a voice", "wire Voicebox / a local TTS", or hits OOM / CUDA-false / import errors on a small laptop. Does NOT cover famous-person voice cloning (legal/impersonation risk — reject that).
---

# Voicebox TTS / Voice-Clone Integration (headless, GPU-laptop)

Voicebox (github.com/jamiepine/voicebox, MIT) is a self-hosted TTS server with
multiple backends: Kokoro (preset narrator voices, ~350MB, NO cloning),
Chatterbox-Turbo / Chatterbox (zero-shot voice cloning from a ~10-30s reference
clip, Chatterbox-Turbo ~4GB), Qwen-TTS (1.7B, ~3.6GB — too big for 4GB VRAM).

It is **profile-based**: every generation needs a `profile_id`. A profile is
either a `preset` (built-in Kokoro voice, no upload) or a `cloned` voice
(needs a reference-audio sample uploaded once).

## When to use
- "generate video with my own voice" → clone the user's voice (Chatterbox-Turbo).
- "human-like narrator" → Kokoro preset (license-clean fictional voice).
- "wire a local TTS into the pipeline" → the `/speak` async flow below.
- NEVER implement famous-person voice cloning (right-of-publicity / impersonation
  / platform-TOS risk). Offer Kokoro presets or the user's-own-clone instead.

## Control surface (verified live)
- `GET /models/status` — registry of engines + ready state. Health probe.
- `GET /profiles` — list profiles. `POST /profiles` — create one.
  - preset: `{"name","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}`
  - cloned: `{"name","voice_type":"cloned","default_engine":"chatterbox_turbo"}`
- `POST /profiles/{id}/samples` (multipart `file` + `reference_text`) — upload
  the reference clip for a cloned profile. Min 2s, max 30s.
- `POST /speak` — `{"text","profile":<id>,"engine":"kokoro"|"chatterbox_turbo","language":"en"}`
  → returns `{"id":<gen_id>,"status":"generating"}`.
- `GET /generate/{id}/status` — SSE stream. **Unreliable for polling** — the
  SSE holds the connection and a plain `curl` loop never sees the terminal
  `completed` event. Use SQLite DB polling instead (see Pitfalls).
- `GET /audio/{id}` — the generated WAV (24kHz mono PCM). Only call AFTER the
  DB shows `status='completed'`, otherwise throws `File at path <data-dir> is
  not a file`.

NOTE: `POST /models/load` is **Qwen-only** (default 1.7B). Do NOT use it for
Kokoro — Kokoro loads automatically inside `/speak`. Using `/models/load` for
Kokoro fails with `No module named 'qwen_tts'`.

## Generation lifecycle
`generating` → (may pass through `loading_model` for first-run engine load) →
`completed` (or `error`). Chatterbox-Turbo's first generation loads ~4GB into
VRAM — expect **60-120s** at `loading_model` before it transitions.
Poll the SQLite `generations` table — not the SSE endpoint (which holds the
connection and never surfaces the terminal event to a plain `curl` loop).

## Synthesis flow (the one that works)
```
0. ALWAYS create profiles via POST /profiles API — NOT via SQLite INSERT.
   Otherwise the profile may land in the wrong database if --data-dir differs
   from default (see Pitfalls → Database mismatch).
   preset: POST /profiles {"name":"...","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}
1. Check if server is running on 127.0.0.1:17493 (start if not — see Launch).
2. POST /speak {text, profile, engine}  -> {id}
3. Poll the server's actual SQLite database (determine data-dir from process
   command line first — see references/voicebox-database-mismatch.md).
4. Copy generations/<id>.wav from data-dir (or GET /audio/{id} once completed).
5. Convert to MP3 with bundled ffmpeg (Windows-style paths) for delivery.
```

## Install on a GPU-laptop (Windows, RAM-starved) — DURABLE RECIPE
1. Clone: `git clone --depth 1 https://github.com/jamiepine/voicebox C:/one/voicebox`
2. **Use `uv venv`, NOT `python -m venv`** — the latter inherits the Hermes
   venv's pip and breaks. `uv venv --python 3.11` (uv is preinstalled).
3. **Clear the global PYTHONPATH leak**: a global `PYTHONPATH` env var points at
   the Hermes venv site-packages and pollutes every Python run. ALWAYS launch
   with `env PYTHONPATH=` (empty) so the backend uses only `.venv`.
4. Install core deps: `env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe -r requirements-minimal-cpu.txt` (use `misaki[en]` only — `misaki[ja/zh]` pulls pyopenjtalk which needs cmake and fails).
5. **CUDA torch is mandatory** for a 4GB-VRAM box (CPU torch OOMs loading any
   >1GB engine into 6GB system RAM). Install:
   `env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe --index-url https://download.pytorch.org/whl/cu126 "torch==2.13.0+cu126" "torchaudio==2.11.0+cu126"`
   - If the pytorch CDN is temporarily unreachable (HTTP 200 but 0 B/s), the
     wheel may already be in the uv cache → reinstall with `UV_OFFLINE=1` or
     copy/install the cached wheel; do NOT assume network is up.
6. Clone engine: `env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe chatterbox-tts`. This **downgrades torch** to CPU — re-run step 5 after to
   restore CUDA torch (pin the SAME cu126 versions). Verify: `env PYTHONPATH= .venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available())"` → `True`.
7. Other import gaps surface at first `/models/status` (e.g. `fastmcp`,
   `pedalboard`, `Pillow`) — install them ad-hoc with `env PYTHONPATH= uv pip install ...`.

## Launch (background, lifecycle-owned by pipeline)
```
cd /c/one/voicebox
env PYTHONPATH= .venv/Scripts/python.exe -m backend.main --host 127.0.0.1 --port 17493 --data-dir C:/one/voicebox/data > backend_run.log 2>&1
```
Log should print `GPU: CUDA (NVIDIA GeForce RTX 3050 Laptop GPU)` and `Ready`.

**⚠️ `--data-dir` MUST match whatever the quickstart / pipeline expects.**
- Omitting `--data-dir` defaults to `{cwd}/data/` (= `C:/one/voicebox/data`).
- Using `--data-dir C:/one/voicebox/data` is explicit and matches the quickstart polling code below.
- **DO NOT** mix `.voicebox-data/` (a different DB from an earlier setup) with `data/` — see `references/voicebox-database-mismatch.md`.

Free the port first if occupied: kill the PID from `netstat -ano | grep :17493`.

## Standalone audio generation (quickstart)
Use this when the user just wants one audio clip, not a full video pipeline.

```bash
# 1. Check if server is already running
curl -s http://127.0.0.1:17493/models/status > /dev/null 2>&1 && echo "RUNNING" || echo "DOWN"

# 2. Start if down (background, capture logs)
cd /c/one/voicebox
env PYTHONPATH= .venv/Scripts/python.exe -m backend.main --host 127.0.0.1 \
  --port 17493 > backend_run.log 2>&1 &
sleep 15
# Wait for "Ready" in log
tail -5 backend_run.log | grep -q "Ready" || sleep 10

# 3. Create a Kokoro preset profile via API (DO NOT use SQLite INSERT — see Pitfalls)
PROFILE=$(curl -s -X POST http://127.0.0.1:17493/profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"Quickstart Kokoro","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}')
PROFILE_ID=$(echo "$PROFILE" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Profile created: $PROFILE_ID"

# 4. Generate audio
GEN=$(curl -s -X POST http://127.0.0.1:17493/speak \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Your text here\",\"profile\":\"$PROFILE_ID\",\"engine\":\"kokoro\",\"language\":\"en\"}")
GEN_ID=$(echo "$GEN" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Generation started: $GEN_ID"

# 5. Poll SQLite — first determine the server's actual data-dir (default: ./data/)
#    See references/voicebox-database-mismatch.md for diagnosis.
env PYTHONPATH= .venv/Scripts/python.exe -c "
import sqlite3,time,os
con=sqlite3.connect('data/voicebox.db')  # ← use the actual data-dir
gid='$GEN_ID'
for _ in range(60):
    st,ap=con.execute('SELECT status,audio_path FROM generations WHERE id=?',(gid,)).fetchone()
    print(f'{time.strftime(\\\"%H:%M:%S\\\")} status={st}')
    if st in ('completed','error'): break
    time.sleep(3)
con.close()
"

# 6. Copy the WAV and convert to MP3
FFMPEG="$HOME/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
SRC="C:\\one\\voicebox\\data\\generations\\<id>.wav"  # ← matches --data-dir (see Launch section)
OUT="C:\\Users\\PREM KUMAR\\voicebox_output.mp3"
"$FFMPEG" -y -i "$SRC" -codec:a libmp3lame -b:a 192k "$OUT" && echo "DONE -> $OUT"

# 7. Deliver via MEDIA: path (Hermes desktop)
echo "MEDIA:$OUT"
```

For a fully automated one-shot script, use `scripts/generate_clone.py` (stdlib: urllib
+ sqlite3 + wave, no pip packages). See `references/verification.md` for the
detailed flow.

## VRAM sizing (RTX 3050 = 4096 MB)
- Kokoro-82M: ~0.8 GB (preset, no clone). Safe alongside Remotion iGPU render.
- Chatterbox-Turbo: ~3.8 GB loaded. FITS but tight — don't also run the dGPU
  Remotion render simultaneously (Voicebox on dGPU, Remotion on iGPU).
- Qwen 1.7B: ~3.6 GB but loads into SYSTEM RAM on CPU → OOM on 6GB box. Avoid.
- If Chatterbox-Turbo OOMs on VRAM, fall back to `chatterbox` (~3.2GB) or Kokoro.

## Pipeline wiring pattern (TypeScript)
- Provider `generateVoiceoverWithVoicebox(text, outPath, lang, {engine, profileId})`:
  POST /speak → poll SQLite generations.status (bounded, e.g. 40×3s) → copy WAV
  from data-dir. Fall back to Edge-TTS if backend down / no profile / engine load fails.
- `voice-generator.ts` passes `VOICEBOX_ENGINE` + `VOICEBOX_PROFILE_ID` from env.
- Lifecycle controller (`voicebox-lifecycle.ts`) `ensureBackend()` is called BEFORE
  every generation. It probes `/models/status` (2.5s timeout), starts the backend if
  unreachable, then polls health up to 40s.
- **Spawn env must clear PYTHONPATH**: `spawn(py, [...], { env: { ...process.env, PYTHONPATH: '' } })`.
  Without this, the global Hermes PYTHONPATH injects CPU-only torch from the Hermes venv,
  overriding Voicebox's own CUDA torch.
- **Spawn cwd must be the Voicebox root**, not `backend/` subfolder:
  `{ cwd: dir }` — NOT `cwd: path.join(dir, 'backend')`. Python's `-m backend.main`
  looks for `backend/` package under cwd; if cwd is `backend/`, it looks for
  `backend/backend/main.py` which doesn't exist.
- **Spawn must use `detached: true` + `windowsHide: true`** so the backend survives
  the pipeline process exit. With `detached: false` (default), the child is killed
  when the Node parent exits — forcing a 40s cold-start on every pipeline run.
- After generation, call `unloadEngine()` / `unloadAll()` to free GPU VRAM between
  jobs, or leave the engine loaded for reuse on the next run (faster but uses ~3.8GB).

## Render pipeline audio quality
The video pipeline's ffmpeg render (`src/agentic/orchestrator/render.ts`) must use
an explicit AAC bitrate — the default (~69 kbps for mono) destroys cloned-voice
clarity. Three paths in `render.ts` need `-b:a 192k`:

1. **Segment encoding** (line ~603): add `'-b:a', '192k'` to the per-segment ffmpeg
   args. This is the codec line that runs without music.
2. **Non-segmented path** (line ~634): same fix in the `audioMap.length` branch.
3. **Music mixing final pass** (line ~667): bump from 128k to 192k.

After fix, verify with `ffprobe` — final video audio should show ~167+ kbps AAC.
Without the fix, expect ~69 kbps and muffled/noisy voice.

## Multi-scenario verification
Build a harness that generates one clip per voice path and asserts valid RIFF WAV:
Kokoro presets (af_heart / am_adam / af_bella) + Chatterbox-Turbo clone. Run it
live against the backend; 4/4 valid audio = green. See references/harness.md.

## Hard rules
- **FREE by default; optional paid/GPU paths allowed ONLY as opt-in.** The default
  voice path is 100% free/self-hosted (Kokoro presets, your-own Chatterbox clone on
  the local GPU). If a feature needs a paid key or heavy GPU, ship it as an OPTIONAL,
  clearly-documented, opt-in upgrade that degrades gracefully to the free path when
  the key/GPU is absent (mirror how Voicebox is optional and falls back to Edge-TTS).
  Never make the free path depend on a paid dep.
- MIT/Apache backends only (Kokoro Apache, Chatterbox MIT). Self-hosted.
- No famous-person cloning (right-of-publicity / impersonation / platform-TOS risk).
  Kokoro presets + user's-own-clone only.
- Always `env PYTHONPATH=` on Windows. Always verify `torch.cuda.is_available()`.
- Commit at green (typecheck + tests pass) — don't leave integration uncommitted.
- **Chatterbox-Turbo on RTX 3050 is VERIFIED working** (4.96s clip, ~3.8 GB VRAM,
  ~4 GB model download on first gen). "FITS but tight" is confirmed, not theoretical.

## Vendoring Voicebox source into your project (copy + strip + license)

When the user wants to COPY Voicebox's backend code INTO the AVS repo (not just
run it as a sibling clone), the repo is **MIT** — copying is allowed, but MIT
covers CODE only, not the name/logo (trademark) or model weights (separate
licenses).

### What's safe to commercialize
- Code: MIT ✓ (keep LICENSE + copyright line). No copyleft, no source disclosure.
- Kokoro (Apache-2.0), Chatterbox (MIT), Qwen (Apache-2.0) engines: all free/permissive.
- Model weights download at RUNTIME via `huggingface_hub` — do NOT bundle the
  `.safetensors` into your repo/dist, then you incur zero weight-license exposure.
- Trademark (name "Voicebox", all `voicebox-logo*.png`, `*.icon/`): EXCLUDED. MIT
  does not grant name/logo rights. Run under your own product name.
- Paid surfaces (Voicebox Cloud sync, HumeAI TADA API): EXCLUDED unless you pay for
  a key + accept their ToS. The code is MIT (copying is legal) but USING them costs
  money. Since AVS is zero-cost, strip both.

### ⚠️ The naive vendoring recipe is BROKEN — use the verified one
The obvious "copy backend/, delete cloud files, remove 2 lines in `routes/__init__.py`"
**FAILS TO BOOT** (`IndentationError` at `routes/__init__.py` line 27, then
`ModuleNotFoundError: No module named 'backend'`). In practice the strip must also
touch `routes/cuda.py`+`rocm.py` registrations, `app.py` GPU-updater imports, and
`tada`/Hume references in `backends/__init__.py`, `services/profiles.py`, `models.py`,
and `build_binary.py`. The FULL 11-step VERIFIED strip list + the live boot-test that
proves completeness (expect `routes 115`) is in
`references/vendoring-and-licensing.md` → "Vendoring recipe (concrete, VERIFIED)".
Target folder in AVS: **`src/adapters/real-voice-backend/`** (NOT `voicebox-vendored/`
— that name was never used; don't create it).

### Git decision (2026-07-22): gitignore the vendored folder, do NOT commit it
The vendored `real-voice-backend/` is a LOCAL, regenerable asset — gitignored at the
root `.gitignore` (`src/adapters/real-voice-backend/`) with a scoped inner `.gitignore`
for Python artifacts, and rebuilt deterministically by
`scripts/vendor-real-voice-backend.mjs`. MIT is satisfied by keeping the LICENSE on
disk locally. Verify with `git check-ignore -v src/adapters/real-voice-backend/backend/main.py`.
(If you later want zero separate-clone steps, commit it instead — MIT permits that —
but then sync upstream periodically.) Full recipe in the same reference file section.

### Keep the clone updated
Voicebox moves fast (was 19 commits behind in one session). Update recipe:
`git -C /c/one/voicebox fetch origin && git -C /c/one/voicebox merge --ff-only origin/main`.
Use `--ff-only` (tree only had untracked test artifacts, safe). After pull, re-verify
the strip list is still valid:
`git diff --name-only OLD..NEW -- backend/routes/__init__.py backend/routes/cloud.py backend/services/cloud.py backend/backends/hume_backend.py backend/config.py`
— if those 5 are untouched, the vendoring recipe above still applies verbatim.

See `references/vendoring-and-licensing.md` for the full Tier-1/2/3 file map, the
exact endpoint/file list the AVS lifecycle controller (`voicebox-lifecycle.ts`)
depends on, the VERIFIED strip + boot-test recipe, and the gitignore decision.

## Scene visual debugging

If a scene renders white/blank but others look fine, the most likely cause is
**wrong search keywords** in the scene plan — the `writeScriptHeuristic`
`angles` array may contain hardcoded coffee/espresso terms that don't match
the actual video topic, causing Pexels to return irrelevant or empty results.

See `references/debugging-white-frames.md` for the full diagnostic protocol,
frame-extraction recipe, and the known `writeScriptHeuristic` coffee-term bug.

## Pitfalls
- `python -m venv` broken → use `uv venv --python 3.11`.
- `/models/load` is Qwen-only → use `/speak` for Kokoro.
- `chatterbox-tts` downgrades torch to CPU → reinstall CUDA torch after.
- Global PYTHONPATH leak → clear it on every python/uv/backend invocation.
  **This also applies when spawning from Node.js** — pass `env: { ...process.env, PYTHONPATH: '' }`
  to `child_process.spawn()`, not the raw `process.env`. Without this, the spawned
  Voicebox process inherits Hermes's site-packages and loads CPU torch.
- Chatterbox-Turbo first generation downloads ~4GB (slow) — that's normal.
  The DB status goes `generating` → `loading_model` (60-120s) → `completed`.
  The `loading_model` intermediate state is expected, not an error.
- 4GB VRAM can't co-run dGPU Remotion + Chatterbox-Turbo.
- **Database mismatch between SQLite query and server data-dir.** The server defaults
  to `./data/` (relative to cwd) when started WITHOUT `--data-dir`. Profiles or generations
  inserted via SQLite directly into `.voicebox-data/voicebox.db` are invisible to a server
  that was started without `--data-dir .voicebox-data`. Symptoms: `POST /speak` returns
  `"Voice profile '<id>' not found"` even though SQLite shows the profile exists, or polling
  `.voicebox-data/voicebox.db` shows generations as `not found` while they actually completed
  in `data/voicebox.db`. **Fix: always create profiles via `POST /profiles` API, which lands
  in whichever database the server actually uses.** When polling generation status by SQLite,
  first determine the server's actual data-dir: check the process command line
  (`wmic process where "processid=<pid>" get commandline`) for `--data-dir`; if absent,
  the default is `./data/` relative to the server's cwd. See references/voicebox-database-mismatch.md.
- **Placeholder `VOICEBOX_PROFILE_ID` triggers a retry storm.** The repo `.env` ships `VOICEBOX_PROFILE_ID=<your-voicebox-profile-id-here>`. dotenv re-injects it even when you run `env -u VOICEBOX_PROFILE_ID`, so `speakVoicebox` thinks a profile exists, spawns the backend (40s wait, fails: module path), then does a doomed 30s x 3 `/speak` retry **per scene** before falling back to tones. Fix: `ensureBackend()` / `speakVoicebox()` must treat the placeholder (any value containing `your-voicebox-profile-id`) as "not configured" → instant tone fallback. If logs show repeated `backend exited (code 1)` + `did not become ready in 40s; falling back`, it's the placeholder trap, not a real config error.
- **`GET /generate/{id}/status` is an SSE stream — do NOT poll it with plain `curl`.** It Server-Sends-Events and HOLDS the connection; a naive `curl` returns empty lines and never surfaces the terminal `completed` event, so a status poll loop just times out at 60s with no status. RELIABLE completion check: query SQLite `<data-dir>/voicebox.db`, table `generations`, columns `status` (`generating`→`completed`/`error`) and `audio_path` (relative, e.g. `generations\\<id>.wav`). Recipe + re-runnable generator: `references/verification.md` and `scripts/generate_clone.py`.
- **Delivering audio on Telegram (no system ffmpeg):** there is no `ffmpeg` on
  PATH, but a bundled one ships at
  `C:/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`.
  Convert WAV→MP3: `ffmpeg -y -i in.wav -codec:a libmp3lame -b:a 192k out.mp3`
  using **Windows-style paths** (MSYS collapses `/c/Users/.../x.wav` with a
  space into a broken path). Verify: `ffmpeg -i out.mp3` prints `Duration` and
  `Stream #0:0: Audio: mp3`. Telegram sends `.mp3`/`.wav` as native voice/media.
- **Delivering audio in Hermes desktop app with MEDIA: path:** after converting
  to MP3, deliver via `MEDIA:/absolute/path/to/file.mp3` in the assistant
  response. The Hermes desktop app renders it as an inline audio player. Use
  Windows absolute paths with forward slashes (`C:/Users/.../file.mp3`) in the
  MEDIA: marker. The file must already exist on disk — MEDIA: is a local-file
  reference, not an upload.
- **Premature `GET /audio/{id}` throws `RuntimeError: File at path <data-dir> is not a file`.** Fires when `audio_path` is still empty (generation not finished); the backend defaults the audio path to the data-dir and fails. Fix: only call `/audio/{id}` AFTER the DB shows `status='completed'`. Or skip `/audio` entirely and copy `<data-dir>/<audio_path>` directly.
- **Non-detached Node spawn kills the backend on pipeline exit.** With Node's default `{ detached: false }`, the Voicebox child process is terminated when the Node pipeline exits. This forces a 40s cold-start on every run. Fix: `spawn(py, args, { detached: true, windowsHide: true })` — the backend persists headless across runs and `ensureBackend()` becomes a fast health-check (no re-spawn).
- **Wrong spawn cwd causes `ModuleNotFoundError: No module named 'backend'`.** The lifecycle code used `cwd: path.join(dir, 'backend')`, but `python -m backend.main` needs the root `dir` (where `backend/` is a subdirectory). With `cwd` set to `backend/`, Python looks for `backend/backend/main.py`. Fix: `cwd: dir`.
- **Render pipeline defaults AAC to ~69k for mono (muffled/noisy voice).** The segmented ffmpeg render path (`render.ts`) specifies `-c:a aac` without `-b:a`, defaulting to ~69 kbps for mono audio. Voice cloned through Voicebox (24kHz PCM source) sounds muffled and noisy at this bitrate. Fix: add explicit `-b:a 192k` to the segment encoding, the non-segmented path, and the music-mixing final pass. Verified: 167 kbps AAC output is clear.
