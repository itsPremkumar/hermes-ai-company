# Local AI Generation Suite (v5.0.0)

## Overview

12 optional local AI modules under `src/lib/ai/` for advanced video generation. All modules follow an **identity-preserving pattern**:

- `isEnabled()` → boolean (false when offline / no model / no hardware)
- `generate(opts)` → Promise<string> (returns `''` on any failure, never throws)
- **Provider chain**: local → API → stock → placeholder (always works)

## Provider Chain

```
gen-image.ts:  comfyui (local) → flux3 (free tier) → api (keyed) → stock → placeholder
gen-video.ts:  cogvideo-local (local) → animatediff (local I2V) → flux3 → api → stock → slideshow
```

## Hardware Constraints (6GB RAM)

| Module | Model | RAM | GPU | Est. Time |
|--------|-------|-----|-----|-----------|
| `comfyui.ts` | SD1.5/SDXL (lowvram) | ~3GB | CUDA, ~2GB VRAM | 15-30s |
| `cogvideo.ts` | CogVideoX-2B | ~4GB | CUDA, ~3GB VRAM | 60-120s |
| `animatediff.ts` | AnimateDiff | ~3GB | CUDA, ~2GB VRAM | 30-60s |
| `upscale.ts` | Real-ESRGAN x4 | ~2GB | CUDA, ~1GB VRAM | 10-20s |
| `bg-removal.ts` | rembg/U2-Net | ~1.5GB | CPU | 5-10s |
| `beat-sync.ts` | librosa | ~200MB | CPU | <1s |
| `clip-match.ts` | CLIP ViT-B/32 | ~500MB | CPU/CUDA | <1s |
| `script-enhance.ts` | Qwen2.5-7B | ~2GB | CUDA offload | 10-30s |
| `translate.ts` | Whisper + NLLB | ~1GB | CPU | 30-60s |
| `storyboard.ts` | ComfyUI | ~3GB | CUDA | 20-40s |

**Rule:** Run ONE AI job at a time. No parallel AI inference on 6GB RAM.

## Job Queue (`job-queue.ts`)

Serial AI job processor. On 6GB RAM hardware, running AI jobs in parallel causes OOM. The queue runs ONE AI job at a time, in FIFO order, persisted to JSON.

```typescript
import { enqueueJob, getJobResult } from './ai/job-queue.js';

const jobId = await enqueueJob('image-gen', {
    prompt: 'cinematic sunset',
    outDir: 'output/scene_01',
    filename: 'generated.png',
    orientation: 'landscape'
});

const result = getJobResult(jobId);
```

## Integration Points

| File | Change |
|------|--------|
| `gen-image.ts` | `tryLocalGenImage()` tries ComfyUI before API |
| `gen-video.ts` | `tryLocalGenVideo()` tries CogVideoX + AnimateDiff before API |
| `acquire.ts` | `gen-local`/`video-gen-local` preferences wired to job queue |
| `types.ts` | `visualPreference` union extended |
| `preview.ts` | `visualPreference` union extended |
| `gateway.ts` | `gen-local`/`video-gen-local` → `AssetKind` coercion |

## ⚠️ Merge Pitfall (Verified Post-Merge)

A naive `git merge` of the AI suite branch can **overwrite** the local provider wiring in `gen-video.ts`. After any merge involving the AI suite, verify:

```bash
cd /c/one/Automated-Video-Generator
grep -c "cogvideo\|animatediff\|tryLocal" src/lib/gen-video.ts  # should be > 0
grep -c "enqueueJob" src/agentic/pipeline/acquire.ts              # should be > 0
```

If `grep` returns 0 for `gen-video.ts`, the local providers were reverted — re-apply `tryLocalGenVideo()` from the AI suite branch.

## Installation (All Optional)

Each provider works standalone — no API keys needed:

```bash
# ComfyUI (image-gen, I2V, storyboard, thumbnail)
git clone https://github.com/comfyanonymous/ComfyUI.git && cd ComfyUI
pip install -r requirements.txt && python main.py --lowvram --preview-method auto

# CogVideoX-2B (text-to-video)
pip install diffusers transformers accelerate torch

# AnimateDiff (image-to-video) — ComfyUI extension
cd ComfyUI/custom_nodes && git clone https://github.com/ArtVentureX/ComfyUI-AnimateDiff.git

# Real-ESRGAN (upscaling)
pip install realesrgan basicsr

# rembg (background removal)
pip install rembg

# Beat detection
pip install librosa numpy

# CLIP matching
pip install clip torch

# Script enhancement
ollama pull qwen2.5:7b

# Whisper.cpp (transcription)
git clone https://github.com/ggerganov/whisper.cpp.git && cd whisper.cpp && make
```

## Environment Variables

```
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_MODEL=sd15
COGVIDEO_SCRIPT=
ANIMATEDIFF_TIMEOUT_MS=600000
REALESRGAN_SCRIPT=
REMBG_SCRIPT=
BEAT_SYNC_SCRIPT=
CLIP_SCRIPT=
OLLAMA_SCRIPT_MODEL=qwen2.5:7b
TRANSLATE_SCRIPT=
WHISPER_MODEL=ggml-base.bin
NLLB_MODEL=nllb-200-distilled-600M
MAX_AI_QUEUE_SIZE=10
```
