---
name: voicebox-integration
title: Voicebox Integration — Local GPU TTS for Production Pipelines
description: >-
  Complete end-to-end guide to integrating Jamie Pine's Voicebox (MIT) as a
  production-grade, GPU-accelerated TTS engine into any pipeline. Covers Python
  environment isolation, CUDA GPU detection, lifecycle auto-start, and audio
  quality tuning. Verified against the Automated Video Generator pipeline
  (Remotion/ffmpeg).
---

# Voicebox Integration Skill

This skill captures all the lessons from integrating Voicebox as a local,
GPU-accelerated TTS engine into a Node.js/TypeScript pipeline. Follow these
steps to avoid the three silent killers: **PYTHONPATH pollution**, **wrong
spawn cwd**, and **default AAC bitrate** destroying voice quality.

---

## 1. One-Time Installation

```bash
git clone --depth 1 https://github.com/jamiepine/voicebox.git <target-dir>
cd <target-dir>
uv venv --python 3.11 .venv

# CPU deps
env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -r requirements-minimal-cpu.txt

# GPU deps (CUDA 12.6)
env PYTHONPATH= uv pip install --python .venv/Scripts/python.exe \
  --index-url https://download.pytorch.org/whl/cu126 \
  "torch==2.13.0+cu126" "torchaudio==2.11.0+cu126"
```

> **ALWAYS** run Voicebox commands with `PYTHONPATH=` cleared. The host agent
> (Hermes, etc.) may set PYTHONPATH to its own venv which has CPU-only torch
> — this silently shadows Voicebox's CUDA torch.

### Verify GPU
```bash
env PYTHONPATH= .venv/Scripts/python.exe -c "
import torch
print('CUDA:', torch.cuda.is_available(), '| PyTorch:', torch.__version__)
"
# Expected: CUDA: True | PyTorch: 2.13.0+cu126
```

---

## 2. Env Vars Required

| Variable | Required | Purpose |
|----------|----------|---------|
| `TTS_PROVIDER=voicebox` | ✅ | Activates Voicebox TTS path |
| `VOICEBOX_API_URL=http://127.0.0.1:17493` | ✅ | Server endpoint |
| `VOICEBOX_ENGINE=chatterbox_turbo` | ✅ | TTS engine (or `kokoro`, `chatterbox`, `qwen-3-tts`) |
| `VOICEBOX_PROFILE_ID=<uuid>` | ✅ | Cloned voice profile ID (treat as local credential) |
| `VOICEBOX_BACKEND_DIR=C:/one/voicebox` | For auto-start | Path to cloned repo root |
| `VOICEBOX_PYTHON=<dir>/.venv/Scripts/python.exe` | For auto-start | Python interpreter in Voicebox venv |

**Security note:** `VOICEBOX_PROFILE_ID` is a local credential — anyone with it
can use the cloned voice while the server is running. Do NOT commit the real
UUID to .env files in public repos.

---

## 3. Lifecycle Controller (TypeScript) — Critical Fixes

When writing a `voicebox-lifecycle.ts` that spawns the backend:

### Fix 1: Spawn cwd

```typescript
// ❌ WRONG — python -m backend.main needs the repo root, not backend/
cwd: path.join(dir, 'backend'),

// ✅ CORRECT
cwd: dir,
```

`python -m backend.main` adds `cwd` to `sys.path`, then resolves
`backend.main` as `backend/main.py` relative to that path. If cwd is
`backend/`, it looks for `backend/backend/main.py` — wrong.

### Fix 2: Detached mode

```typescript
// ❌ WRONG — server dies when pipeline exits
detached: false,

// ✅ CORRECT — server persists for hot reuse
detached: true,
windowsHide: true,  // no console window pops up
```

Without `detached: true`, the Voicebox process is killed when the parent
(Node.js) exits. With `detached: true` + `windowsHide: true`, it runs
headlessly in the background and survives pipeline restarts.

### Fix 3: PYTHONPATH pollution

```typescript
// ❌ WRONG — child inherits CPU torch from parent venv
env: { ...process.env },

// ✅ CORRECT
env: { ...process.env, PYTHONPATH: '' },
```

The Hermes agent (or other orchestration tool) may set PYTHONPATH to its own
venv's site-packages, which typically has CPU-only torch. Clearing
PYTHONPATH ensures the child uses Voicebox's own CUDA torch.

---

## 4. Audio Quality — The Silent Killer

The ffmpeg AAC encoder defaults to **~69 kbps for mono** when no `-b:a` flag
is specified. For voiceover narration, this sounds muddy and noisy.

### Fix: Explicit high bitrate on ALL render paths

```typescript
// Segment per-scene encoding:
'-c:a', 'aac', '-b:a', '192k', '-shortest', '-y', seg,

// Non-segmented render:
...(audioMap.length ? ['-c:a', 'aac', '-b:a', '192k'] : ['-an']),

// Music+SFX mixing pass:
'-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-y', out,
```

### Verification

```bash
ffprobe -v error -select_streams a:0 -show_entries stream=bit_rate output.mp4
# Expected: >160000 (160+ kbps)
```

---

## 5. Lifecycle Sequence (Production Flow)

```
Pipeline starts → ensureBackend() checks /models/status
  ├─ Already running? → Reuse (instant)
  └─ Dead? → Spawn with 3 fixes above → poll up to 40s → Ready

Then per scene:
POST /speak {text, profile, engine, language}
  → Engine loads lazily on 1st call (~45s for chatterbox_turbo)
  → Subsequent scenes reuse loaded model (instant)
  → GET /audio/{id} → WAV (24kHz mono PCM)

Pipeline finishes → Server stays alive (detached:true)
Next run → Instant reuse (backend already up)
```

---

## 6. Secrets & Docs Checklist

- [ ] Mark credential env vars in `.env.example` with `⚠️ WARNING: treat like a password`
- [ ] Create a `docs/VOICEBOX_SETUP.md` covering: install, clone, pipeline
      integration, auto-start, quality tuning, troubleshooting, safe-to-share table
- [ ] Document which vars are safe to commit vs local credentials

---

## 7. Verification Test

Drop a self-contained lifecycle test script into any project:

```typescript
import { ensureBackend, isBackendUp } from './src/lib/voicebox-lifecycle.js';

async function test() {
  console.log('Backend up?', await isBackendUp());
  if (!(await isBackendUp())) {
    const ok = await ensureBackend();
    console.log('Auto-start result:', ok);
  }
  const health = await fetch('http://127.0.0.1:17493/health').then(r => r.json());
  console.log('GPU:', health.gpu_available ? '✅' : '❌');
}
test();
```

## Pitfalls

- **PYTHONPATH pollution is invisible** — the server starts normally but runs
  on CPU. Always verify with `/health` endpoint, not just server startup.
- **Default AAC bitrate (~69k) is terrible for voice** — always set `-b:a 192k`
  on every render path, including segment pre-renders.
- **Wrong spawn cwd gives `ModuleNotFoundError: No module named 'backend'`**
  even though the module exists. cwd must be the repo root, not `backend/` subdir.
- **`detached: false` kills the server** when the parent process exits. Use
  `detached: true` + `windowsHide: true` for background persistence.
- **Database mismatch (profiles not found).** Profiles created by SQLite INSERT
  may land in a different database than the server reads. Voicebox's default
  data directory is `./data/` (relative to cwd) when `--data-dir` is NOT passed
  at launch. If you query `.voicebox-data/voicebox.db` but the server uses
  `data/voicebox.db` (the default), you'll see profiles but `/speak` won't find
  them. **Fix: always create profiles via `POST /profiles` API, which lands in
  the server's actual database.** To determine the server's data-dir, inspect
  the process command line with `wmic process where "processid=<PID>" get commandline`.
  See `voicebox-tts-integration` skill's `references/voicebox-database-mismatch.md`
  for a full diagnosis trace.
