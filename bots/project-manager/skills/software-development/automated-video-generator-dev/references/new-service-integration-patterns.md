# New Service Integration Patterns

> Reference for adding new services to the AVS pipeline. All services follow the identity-preserving pattern: OFF by default, opt-in via env, NEVER breaks the pipeline if unavailable.

## Stock Source Integration

To add a new stock source (e.g., Coverr):

1. Create `src/lib/stock-sources/<name>.ts` with:
   - `searchVideos(query, limit): Promise<Video[]>`
   - `getDownloadUrl(videoId): Promise<string | null>`
   - `getPopularVideos(limit): Promise<Video[]>`
   - Export `<Name>Video` interface

2. Add to `src/lib/visual-fetcher/search.ts` as a fallback provider

3. Add env vars to `.env.example` (all optional)

4. Add tests in `tests/<name>.test.ts`

**Example: Coverr** (`src/lib/stock-sources/coverr.ts`)
- Public API, no key required
- `searchVideos('nature', 10)` returns video metadata
- `getDownloadUrl(id)` returns direct download URL
- `getPopularVideos(10)` returns trending videos

## TTS Provider Integration

To add a new TTS provider (e.g., ElevenLabs, SiliconFlow):

1. Create `src/agentic/services/tts/<name>.ts` with:
   - `synthesize(text, options): Promise<string>` — returns path to audio file
   - `previewVoice(voice?): Promise<string>` — returns path to preview audio
   - `is<Name>Configured(): boolean` — checks if API key is set
   - `getVoices(): Voice[]` — returns available voices

2. Add to `src/agentic/services/tts/manager.ts` switch statement:
   ```typescript
   case '<name>': {
       const outputPath = await <name>Synthesize(options.text, { voice_id: options.voice });
       return { outputPath, provider: '<name>' };
   }
   ```

3. Add env vars to `.env.example` (all optional)

4. Follow identity-preserving pattern:
   ```typescript
   export function is<Name>Configured(): boolean {
       return !!process.env.<NAME>_API_KEY;
   }
   ```

**Example: ElevenLabs** (`src/agentic/services/tts/elevenlabs.ts`)
- High-quality AI voices with voice cloning
- `ELEVENLABS_API_KEY` required
- `getVoices()` fetches from API
- `previewVoice(voiceId)` generates short sample

**Example: SiliconFlow** (`src/agentic/services/tts/siliconflow.ts`)
- Chinese-optimized TTS with CosyVoice2
- `SILICONFLOW_API_KEY` required
- Hardcoded voice list (alex, anna, bella, etc.)

## Color Grading / Caption / Transition Presets

All preset-based features follow the same pattern:

1. Define presets:
   ```typescript
   export const PRESETS: Record<PresetName, PresetConfig> = {
       none: { name: 'None' },
       cinematic: { name: 'Cinematic', contrast: 1.2, saturation: 0.9 },
       // ...
   };
   ```

2. Export getter:
   ```typescript
   export function getPreset(name: PresetName): PresetConfig {
       return PRESETS[name] || PRESETS.none;
   }
   ```

3. Export filter generator:
   ```typescript
   export function generateFilter(preset: PresetName): string {
       const config = getPreset(preset);
       if (preset === 'none') return '';
       // Build ffmpeg filter string
   }
   ```

4. Add env var to `.env.example`:
   ```bash
   COLOR_GRADE=none
   CAPTION_STYLE=basic
   TRANSITION_EFFECT=fade
   ```

**Example: Color Grading** (`src/lib/color-grading/presets.ts`)
- 10 presets: none, cinematic, warm, cool, vintage, noir, vivid, sunset, cyberpunk, muted
- LUT support: drop `.cube` files into `resource/luts/`
- `generateEqFilter()` returns ffmpeg `eq=` filter
- `generateColorBalanceFilter()` returns `colorbalance=` filter

**Example: Caption Styles** (`src/agentic/services/captions/styles.ts`)
- 8 presets: basic, typewriter, lowerthird, karaoke, minimal, bold, neon, softCard
- `generateAssStyle()` returns ASS subtitle format
- `generateDrawtextFilter()` returns ffmpeg `drawtext` filter

**Example: Transitions** (`src/lib/transitions/effects.ts`)
- 10 effects: none, fade, slide, zoomblur, glitch, lightleak, whippan, dissolve, wipe, push
- `generateXfadeFilter()` returns ffmpeg `xfade` filter
- All effects are ffmpeg-based (no external deps)

## Audio Ducking

Uses ffmpeg sidechain compression:

```typescript
// Detect voice activity + duck BGM
const filter = `[1:a]asendcmd='0.0 afftdn -20.0',[1:a]volume=${bgmVolume}`;
```

- Always works (ffmpeg is bundled)
- Fallback: simple `amix` with reduced BGM volume
- No external dependencies

## Cross-Platform Posting

```typescript
// src/agentic/services/upload-post.ts
export async function uploadToPlatform(videoPath, title, platform, description?, tags?): Promise<UploadResult>
export async function uploadToAllPlatforms(videoPath, title, description?, tags?): Promise<BatchUploadResult>
```

- Uses upload-post.com API
- `UPLOAD_POST_API_KEY` + `UPLOAD_POST_USERNAME` required
- Platforms: tiktok, instagram, youtube, youtube_shorts

## AI Gateway

```typescript
// src/agentic/services/ai-gateway.ts
export function getGatewayConfig(): GatewayConfig | null
export async function chatCompletion(messages, options): Promise<ChatResponse>
```

- Supported: cloudflare, ollama, litellm, oneapi, modelscope, aihubmix, aimlapi, evolink, groq, pollinations
- `AI_GATEWAY_TYPE` required to enable
- Falls back to direct provider if gateway not configured

## Material Cache

```typescript
// src/agentic/services/material-cache.ts
export function getCached(url, ttlMs?): string | null
export function putCache(url, localPath, metadata?): void
export function getCacheStats(): CacheStats
export function cleanupCache(ttlMs?, maxSize?): void
```

- Persistent JSON index at `workspace/cache/materials/cache-index.json`
- SHA-256 hash-based dedup
- TTL expiration (default: 7 days)
- LRU eviction when size exceeds limit (default: 5 GB)

## Error Sanitization

```typescript
// src/agentic/services/error-sanitize.ts
export function sanitizeError(error: unknown): string
export function sanitizeUrl(url: string): string
export function createSanitizedError(original: Error): Error
```

- Strips: URLs with credentials, Bearer tokens, Basic auth, query param secrets
- Always works (pure string manipulation)
- Recommended: `ERROR_SANITIZE=true`

## Graceful Fallback Chains

```
TTS: ElevenLabs → SiliconFlow → Edge-TTS → silence
Image gen: ComfyUI → FLUX3 → API → stock → placeholder
Video gen: CogVideoX → AnimateDiff → FLUX3 → API → stock → slideshow
Stock: Pexels → Openverse → Coverr → Wikimedia → Internet Archive → placeholder
AI: Local ComfyUI → API key → offline placeholder
```

## Post-Merge Re-application Pattern

When merging a feature branch into main, **feature branch edits to existing files can be silently overwritten** by main's version. After EVERY merge:

1. `git diff main..feat-branch -- <file>` to see what the branch changed
2. Check if those changes survived: `grep -n "key_symbol" <file>`
3. If lost, re-apply the edits manually (don't blame git — verify)
4. This happened with `gen-video.ts` losing CogVideoX + AnimateDiff local providers

## File Locations

```
src/
├── agentic/
│   ├── services/
│   │   ├── upload-post.ts      ← Cross-platform posting
│   │   ├── material-cache.ts   ← Persistent cache
│   │   ├── ai-gateway.ts       ← AI gateway compatibility
│   │   ├── version-checker.ts  ← GitHub releases check
│   │   ├── error-sanitize.ts   ← Security sanitization
│   │   ├── batch-variants.ts   ← Batch video variants
│   │   ├── audio-ducking.ts    ← Auto-duck BGM
│   │   ├── resolutions.ts      ← Resolution presets
│   │   └── captions/
│   │       ├── styles.ts       ← Caption style presets
│   │       └── audition.ts     ← Voice preview
│   └── ai/
│       ├── providers/
│       │   ├── comfyui.ts      ← Local image gen
│       │   ├── cogvideo.ts     ← Local T2V
│       │   ├── animatediff.ts  ← Local I2V
│       │   ├── upscale.ts      ← Real-ESRGAN
│       │   └── bg-removal.ts   ← rembg
│       └── intelligence/
│           ├── beat-sync.ts    ← Beat detection
│           ├── clip-match.ts   ← CLIP matching
│           ├── script-enhance.ts ← Ollama enhancement
│           ├── translate.ts    ← Whisper + NLLB
│           └── storyboard.ts   ← Keyframe gen
├── lib/
│   ├── color-grading/
│   │   └── presets.ts          ← Color grading + LUT
│   ├── transitions/
│   │   └── effects.ts          ← Video transitions
│   └── stock-sources/
│       └── coverr.ts           ← Coverr stock video
tests/
├── ai-suite.test.ts            ← AI module tests
├── services.test.ts            ← Service tests
├── tts-stock.test.ts           ← TTS + stock tests
└── captions-color.test.ts      ← Caption + color tests
```
