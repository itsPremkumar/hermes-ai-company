# New Services Added — August 17, 2026

This session added 14 new services/modules to the AVS project, all following the **identity-preserving pattern**: OFF by default, opt-in via env, NEVER breaks the pipeline if unavailable.

## Service Inventory

| Service | File | Purpose | Default | Requires |
|---------|------|---------|---------|----------|
| **Upload posting** | `src/agentic/services/upload-post.ts` | TikTok/Instagram/YouTube cross-posting | OFF | `UPLOAD_POST_API_KEY` |
| **Material cache** | `src/agentic/services/material-cache.ts` | Persistent TTL cache with hash-dedup | ✅ Works | Nothing |
| **AI gateway** | `src/agentic/services/ai-gateway.ts` | Cloudflare/Ollama/LiteLLM/Groq/etc. | OFF | `AI_GATEWAY_TYPE` |
| **Version checker** | `src/agentic/services/version-checker.ts` | GitHub releases API check | ✅ Works | Nothing |
| **Error sanitize** | `src/agentic/services/error-sanitize.ts` | Strip API keys from errors | ✅ Works | Nothing |
| **Batch variants** | `src/agentic/services/batch-variants.ts` | Generate N variants, pick best | ✅ Works | Nothing |
| **Audio ducking** | `src/agentic/services/audio-ducking.ts` | Auto-duck BGM during speech | ✅ Works | ffmpeg |
| **Resolutions** | `src/agentic/services/resolutions.ts` | 8 resolution presets (4K, 720p, etc.) | ✅ Works | Nothing |
| **ElevenLabs TTS** | `src/agentic/services/tts/elevenlabs.ts` | High-quality AI voices | OFF | `ELEVENLABS_API_KEY` |
| **SiliconFlow TTS** | `src/agentic/services/tts/siliconflow.ts` | Chinese-optimized TTS | OFF | `SILICONFLOW_API_KEY` |
| **TTS manager** | `src/agentic/services/tts/manager.ts` | Unified TTS with fallback chain | ✅ Works | Edge-TTS default |
| **Caption styles** | `src/agentic/services/captions/styles.ts` | 8 caption presets | ✅ Works | Nothing |
| **Voice audition** | `src/agentic/services/captions/audition.ts` | Preview voices before generating | ✅ Works | Nothing |
| **Color grading** | `src/lib/color-grading/presets.ts` | 10 presets + .cube LUT support | ✅ Works | Nothing |
| **Transitions** | `src/lib/transitions/effects.ts` | 10 video transition effects | ✅ Works | Nothing |
| **Coverr stock** | `src/lib/stock-sources/coverr.ts` | Free stock video (public API) | ✅ Works | Nothing |
| **Speed ramp** | `src/lib/video/speed-ramp.ts` | Variable speed (slow-mo, time-lapse) | ✅ Works | ffmpeg |
| **Progress bar** | `src/lib/video/progress-bar.ts` | Video progress bar overlay | ✅ Works | ffmpeg |
| **Thumbnail** | `src/agentic/services/enhance/thumbnail.ts` | Auto-generate video thumbnails | ✅ Works | ffmpeg |
| **Noise reduction** | `src/agentic/services/enhance/noise-reduction.ts` | Audio noise reduction (afftdn) | ✅ Works | ffmpeg |
| **Update checker** | `src/agentic/services/update-checker.ts` | Background update notifications | ✅ Works | Nothing |
| **Script templates** | `src/agentic/services/scripts/templates.ts` | 10 niche script templates | ✅ Works | Nothing |
| **Docker GPU** | `Dockerfile.gpu` + `docker-compose.gpu.yml` | CUDA 11.8+ GPU acceleration | ✅ Works | NVIDIA Docker |

## Graceful Fallback Chains

```
TTS: ElevenLabs → SiliconFlow → Edge-TTS → silence
Image gen: ComfyUI → FLUX3 → API → stock → placeholder
Video gen: CogVideoX → AnimateDiff → FLUX3 → API → stock → slideshow
Stock: Pexels → Openverse → Coverr → Wikimedia → Internet Archive → placeholder
AI: Local ComfyUI → API key → offline placeholder
```

## Integration Patterns

### New stock source integration
1. Create `src/lib/stock-sources/<name>.ts` with `searchVideos()`, `getDownloadUrl()`, `getPopularVideos()`
2. Export `<Name>Video` interface
3. Add to `src/lib/visual-fetcher/search.ts` as fallback provider
4. Add env vars to `.env.example` (all optional)

### New TTS provider integration
1. Create `src/agentic/services/tts/<name>.ts` with `synthesize()`, `previewVoice()`, `is<Name>Configured()`, `getVoices()`
2. Add to `src/agentic/services/tts/manager.ts` switch statement
3. Add env vars to `.env.example` (all optional)
4. Follow identity-preserving pattern: `if (!isConfigured()) return null`

### Color grading / caption / transition presets
1. Define `PRESETS: Record<PresetName, PresetConfig>` with all options
2. Export `getPreset(name)` returning config (default: 'none' or 'basic')
3. Export `listPresets()` returning all keys
4. Export `generate<FilterType>Filter(preset)` returning ffmpeg filter string
5. Add env var to `.env.example`

## New Env Vars (all optional)

```bash
# Cross-platform posting
UPLOAD_POST_ENABLED=false
UPLOAD_POST_API_KEY=
UPLOAD_POST_USERNAME=
UPLOAD_POST_PLATFORMS=tiktok,instagram

# AI Gateway
AI_GATEWAY_TYPE=
AI_GATEWAY_BASE_URL=
AI_GATEWAY_API_KEY=
AI_GATEWAY_MODEL=

# TTS
TTS_PROVIDER=edge-tts
ELEVENLABS_API_KEY=
SILICONFLOW_API_KEY=

# Video
VIDEO_RESOLUTION=portrait_1080
VIDEO_VARIANTS=3
VIDEO_PICK_BEST=false

# Visual
COLOR_GRADE=none
LUT_FILE=
CAPTION_STYLE=basic
TRANSITION_EFFECT=fade
TRANSITION_DURATION=1.0

# Security
ERROR_SANITIZE=true
```

## New CLI Commands

```bash
npm run agentic:variants    # Generate 3 variants, pick best
npm run agentic:post        # Post to TikTok/Instagram/YouTube
npm run agentic:upscale     # Upscale image (Real-ESRGAN)
npm run agentic:remove-bg   # Remove background (rembg)
npm run version:check       # Check for updates
npm run cache:stats         # View cache statistics
npm run cache:clear         # Clear material cache
```

## Verification

| Check | Result |
|-------|--------|
| Typecheck | ✅ 0 errors |
| New tests (93 total) | ✅ 93 pass, 0 fail |
| Git | ✅ Pushed to main |
| All features | ✅ Optional (identity-preserving) |

## Key Principle

**Everything is optional.** The pipeline NEVER breaks:
- ElevenLabs missing → falls back to SiliconFlow → falls back to Edge-TTS
- Coverr offline → falls back to Pexels → falls back to Openverse
- Color grade "none" → no filter applied
- Transitions "none" → simple cut
