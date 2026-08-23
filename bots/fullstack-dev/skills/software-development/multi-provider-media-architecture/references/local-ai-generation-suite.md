# Local AI Generation Suite (AVS)

Complete architecture for self-hosted AI media generation on consumer hardware (6GB RAM).
Used in the Automated-Video-Generator (`src/lib/ai/`) to enable free, offline AI image/video
generation with graceful fallback to stock media.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Job Queue                              │
│  (serial processing — one AI job at a time for 6GB RAM)     │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────────┐
        ▼                 ▼                     ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Local AI    │  │  API Provider │  │    Stock      │
│  (ComfyUI,    │  │  (OpenAI,     │  │  (Openverse,  │
│  CogVideoX,   │  │  DashScope,   │  │  Pexels)      │
│  AnimateDiff) │  │  Kling, Luma) │  │               │
└───────────────┘  └───────────────┘  └───────────────┘
        │                 │                     │
        ▼                 ▼                     ▼
   returns ''         returns ''           returns ''
   → fall through    → fall through      → placeholder
```

## Module Map

| Module | File | Purpose | Model | RAM |
|--------|------|---------|-------|-----|
| Job Queue | `ai/job-queue.ts` | Serial AI processor | — | — |
| ComfyUI | `ai/providers/comfyui.ts` | Local image gen | SD1.5/SDXL | ~3GB |
| CogVideoX | `ai/providers/cogvideo.ts` | Local text-to-video | CogVideoX-2B | ~4GB |
| AnimateDiff | `ai/providers/animatediff.ts` | Local image-to-video | AnimateDiff | ~3GB |
| Real-ESRGAN | `ai/providers/upscale.ts` | AI upscaling | Real-ESRGAN | ~2GB |
| rembg | `ai/providers/bg-removal.ts` | Background removal | U2-Net | ~1.5GB |
| Beat-sync | `ai/intelligence/beat-sync.ts` | Beat detection | librosa | ~200MB |
| CLIP match | `ai/intelligence/clip-match.ts` | Semantic matching | CLIP ViT-B/32 | ~500MB |
| Script enhance | `ai/intelligence/script-enhance.ts` | Script optimization | Qwen2.5-7B | ~2GB |
| Translate | `ai/intelligence/translate.ts` | Multi-language subs | Whisper + NLLB | ~1GB |
| Storyboard | `ai/intelligence/storyboard.ts` | Keyframe generation | ComfyUI | ~3GB |

## Key Design Patterns

### 1. Identity-Preserving Fallback
```typescript
// ALWAYS returns '' on failure — never throws
export async function generateImage(opts: Options): Promise<string> {
    if (!await isAvailable()) return '';  // offline-safe
    try {
        const result = await doInference(opts);
        return result || '';
    } catch {
        return '';  // never crash the pipeline
    }
}
```

### 2. Local-First Provider Chain
```
gen-image.ts:  tryLocalComfyUI() → resolveGenAPI() → return ''
gen-video.ts:  tryLocalT2V() → tryAnimateDiff() → resolveVideoAPI() → return ''
```

### 3. Two-Path Providers (script OR server)
Each provider supports both a standalone Python script and an HTTP server:
```typescript
if (COMFYUI_SCRIPT && fs.existsSync(COMFYUI_SCRIPT)) {
    return await runScript(opts, dest);
} else {
    return await runServerApi(opts, dest);
}
```

### 4. Serial Job Queue (6GB RAM safety)
Running AI jobs in parallel causes OOM. The queue processes FIFO:
```typescript
export function enqueueJob(kind: AiJobKind, payload: any): string {
    // persists to workspace/ai-queue/jobs.json
    // auto-triggers processQueue() — one job at a time
    return jobId;
}
```

### 5. New Pipeline Preferences
```typescript
visualPreference: 'image' | 'video' | 'gen' | 'video-gen' | 'gen-local' | 'video-gen-local'
// 'gen-local' = local ComfyUI (free, offline)
// 'video-gen-local' = local CogVideoX/AnimateDiff (free, offline)
```

## Hardware Reality Check (6GB RAM + NVIDIA dGPU)

| Component | Works | Struggles |
|-----------|-------|-----------|
| SDXL 512px | ✅ ComfyUI with `--lowvram` | Parallel inference |
| CogVideoX-2B | ✅ 480x480, 49 frames | Higher resolution |
| AnimateDiff | ✅ 16-frame clips | Longer clips |
| Real-ESRGAN | ✅ 2x upscaling | 4x on large images |
| rembg | ✅ CPU-friendly | Large images |
| Parallel AI jobs | ❌ OOM | Queue required (one at a time) |

## Environment Variables

```bash
# ComfyUI (image gen, I2V, storyboard, thumbnail)
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_MODEL=sd15  # or 'sdxl'
COMFYUI_TIMEOUT_MS=300000

# CogVideoX (text-to-video)
COGVIDEO_SCRIPT=./scripts/cogvideo_generate.py
COGVIDEO_URL=http://127.0.0.1:8189
COGVIDEO_TIMEOUT_MS=600000

# AnimateDiff (image-to-video)
ANIMATEDIFF_TIMEOUT_MS=600000

# Real-ESRGAN (upscaling)
REALESRGAN_SCRIPT=./scripts/upscale.py
REALESRGAN_FACTOR=2
UPSCALE_TIMEOUT_MS=300000

# rembg (background removal)
REMBG_SCRIPT=./scripts/remove_bg.py
BG_REMOVAL_TIMEOUT_MS=120000

# Beat-Sync
BEAT_SYNC_SCRIPT=./scripts/beat_detect.py

# CLIP Matching
CLIP_SCRIPT=./scripts/clip_match.py

# Script Enhancement (Ollama)
OLLAMA_SCRIPT_MODEL=qwen2.5:7b
ENHANCE_TIMEOUT_MS=120000

# Translation
TRANSLATE_SCRIPT=./scripts/translate.py
WHISPER_MODEL=ggml-base.bin
NLLB_MODEL=nllb-200-distilled-600M
```

## Installation Guide

### ComfyUI (for image-gen, I2V, storyboard, thumbnail)
```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
mkdir -p models/checkpoints
# Download v1-5-pruned-emaonly.ckpt from HuggingFace
python main.py --lowvram --preview-method auto
```

### AnimateDiff Extension
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ArtVentureX/ComfyUI-AnimateDiff.git
cd ComfyUI-AnimateDiff && pip install -r requirements.txt
mkdir -p ../models/animatediff
# Download mm_sd_v15.ckpt
```

### CogVideoX
```bash
pip install diffusers transformers accelerate torch
```

### Real-ESRGAN
```bash
pip install realesrgan basicsr
```

### rembg
```bash
pip install rembg
# Or CPU-only: pip install rembg[cpu]
```

### Whisper.cpp (transcription)
```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp && make
bash models/download-ggml-model.sh base
```

### NLLB (translation)
```bash
pip install transformers sentencepiece torch
```

## Verification

### Empirical Video Verification (avs-verify.sh)
```bash
bash scripts/avs-verify.sh <video.mp4>
# Checks: black frames, freeze, volume, SAR, frame content stddev, speech zcr
```

### AI Module Integration Test
```bash
npx tsx test-ai-modules.ts
# Verifies: provider chain, job queue, fallback pattern, all modules present
```

### Typecheck
```bash
npm run typecheck  # 0 errors
```

## Git Commits (AVS feat/ai-generation-suite)

```
c55929d feat(ai): add 12-module local AI generation suite
ff7cbe7 feat(pipeline): add gen-local/video-gen-local preferences with job queue
1aadad4 fix(types): add gen-local/video-gen-local to preview.ts visualPreference
f912d4b test: add AI integration test and sample input
f9024cc test: add updated AI integration test with fallback pattern detection
```

## Pitfall: Merge Typecheck Errors

When merging branches that add `downloadWithTimeout()` (returns `string | null`),
existing code that does `localPath = await downloadWithTimeout(...)` will fail typecheck
because `localPath` is typed `string`. Fix:
```typescript
// Wrong: localPath = await downloadWithTimeout(...);
// Right:
const downloaded = await downloadWithTimeout(...);
if (downloaded) {
    localPath = downloaded;
} else {
    return; // skip this candidate
}
```

## Pitfall: Worktree Paths

AVS uses git worktrees. The active worktree is at `C:/c/one/avs-ai-gen` while the
primary repo is at `C:/one/Automated-Video-Generator`. Both share the same git state.
Path format for native tools: `C:/c/one/avs-ai-gen/...` (forward slashes work in git-bash).
