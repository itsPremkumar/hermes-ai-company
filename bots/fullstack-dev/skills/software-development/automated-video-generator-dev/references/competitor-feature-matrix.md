# Competitor Feature Matrix (Research from 2025-2086)

## Source Projects
- **MoneyPrinterTurbo** (104k stars) — Auto posting, batch variants, material cache, AI gateway, version checker, cross-platform
- **CapCut** — AutoCut (scene detection), voice changer (8 effects), AI upscaler, auto captions
- **HeyGen** — Voice cloning (XTTS-v2), video translation + dubbing (175+ languages)
- **Synthesia** — AI avatar presenter, template-based generation
- **InVideo AI** — URL/Article → Video, auto voiceover + subtitles
- **Runway Gen-3** — Text-to-video, image-to-video (retired July 2026)

## Features Borrowed → Implemented

| Feature | Source | AVS Module | Pattern |
|---------|--------|------------|---------|
| Cross-platform posting | MPT | upload-post.ts | API key opt-in |
| Batch variants | MPT | batch-variants.ts | Always works |
| Material cache | MPT | material-cache.ts | Always works |
| AI gateway | MPT | ai-gateway.ts | Env opt-in |
| Version checker | MPT | version-checker.ts | Always works |
| Error sanitize | MPT | error-sanitize.ts | Always works |
| Multiple resolutions | MPT | resolutions.ts | Always works |
| Audio ducking | MPT | audio-ducking.ts | ffmpeg |
| ElevenLabs TTS | MPT | tts/elevenlabs.ts | API key |
| SiliconFlow TTS | MPT | tts/siliconflow.ts | API key |
| Coverr stock | MPT | stock-sources/coverr.ts | Public API |
| Caption styles | MPT | captions/styles.ts | Always works |
| Color grading | MPT | color-grading/presets.ts | Always works |
| Video transitions | MPT | transitions/effects.ts | ffmpeg |
| Speed ramp | CapCut | video/speed-ramp.ts | ffmpeg |
| Progress bar | CapCut | video/progress-bar.ts | ffmpeg |
| Thumbnail gen | CapCut | enhance/thumbnail.ts | ffmpeg |
| Noise reduction | CapCut | enhance/noise-reduction.ts | ffmpeg |
| AutoCut scenes | CapCut | video/autocut/scene-detect.ts | ffmpeg |
| Voice cloning | HeyGen | voice/clone.ts | API key |
| Video dubbing | HeyGen | video/dubbing/translate.ts | Whisper+TTS |
| Voice changer | CapCut | voice/changer.ts | ffmpeg |
| URL-to-video | InVideo | video/url-to-video.ts | Always works |
| Script templates | Various | services/scripts/templates.ts | Always works |
| Docker GPU | Various | Dockerfile.gpu | CUDA 11.8+ |

## Identity-Preserving Pattern (ALL features)
Every feature follows: OFF by default → opt-in via env → graceful fallback chain → never breaks pipeline.

## Hardware Reality (User's 6GB RAM + NVIDIA dGPU)
- Features that work: ffmpeg-based effects, caching, TTS fallback, script generation
- Features that need GPU: ComfyUI, CogVideoX, AnimateDiff, Real-ESRGAN, voice cloning
- Features that need API keys: ElevenLabs, SiliconFlow, cross-platform posting
- Features that always work: Edge-TTS, color grading, transitions, captions, resolutions, progress bar, thumbnails
