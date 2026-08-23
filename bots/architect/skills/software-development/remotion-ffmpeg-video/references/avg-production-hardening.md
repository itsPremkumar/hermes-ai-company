# Production-Hardening Patterns for AVG Pipeline

This reference documents structural fixes applied during a production-readiness sprint.
Each pattern is reusable across video-generation pipelines.

## 1. Pexels-as-Primary Provider Architecture

**Changed:** `src/lib/visual-fetcher/search.ts` — `fetchVisualsForScene()`

### Before
```
searchVideos (Pexels) → searchPixabayVideos → freeVideoAdapter (Wikimedia/Archive)
                   ↑ all tried equally, no hierarchy logging
```

### After
```
☆ PEXELS (primary, recommended) → Pixabay (fallback) → Free sources (last resort)
  ★ banner logged once per session
  ★ [PEXELS] Selected candidate #N for "query" logged per selection
  ⚠ [PEXELS] No results for "query" — trying fallback  
  ⚡ FALLBACK [Pixabay/Free] Selected candidate #N
  ✗ No visual assets found from any source (final fallback)
```

### Key Benefits
- Pexels is most reliable (API key, high uptime, fast CDN)
- Logging makes it obvious which provider served each asset
- Free sources only queried when Pexels returns nothing
- Same architecture for both images and videos

### .env Setup
```
# Required for Pexels (RECOMMENDED)
PEXELS_API_KEY=your_key_here

# Optional fallbacks
PIXABAY_API_KEY=your_key_here
```

## 2. Plugin Double-Registration Fix

**Changed:** `src/agentic/plugins/core/registry.ts` — `register()` method

### The Bug
Plugins were registered twice:
1. Via `loadFromDirectory()` (auto-discovers all `.js`/`.ts` files)
2. Via individual `register()` calls elsewhere

Result: `"Plugin \"X\" already registered, overwriting"` warns every run.

### The Fix
Changed `register()` to be a **no-op if already registered**:
```typescript
register(plugin, config, enabled) {
    if (this.entries.has(plugin.metadata.name)) {
        return; // already registered — skip silently
    }
    // ... actual registration
}
```

### Applicability
Any plugin/extension registry with auto-discovery + manual registration paths. Return-early is safer than warn-and-overwrite.

## 3. Fallback Ambient Audio Generation

**Changed:** `src/lib/free-music.ts` — added `FallbackToneProvider`

### Problem
The two network music providers (`open-lofi`, `internet-archive`) were unreliable:
- open-lofi: GitHub-hosted catalog + track URLs returning 404
- internet-archive: API search worked but track downloads failing with 404

When both failed, the video had NO background music → audio felt empty.

### Solution
Added a **zero-network fallback** as the last provider in the chain:
```typescript
class FallbackToneProvider implements FreeMusicProvider {
    async search() {
        return [{
            id: 'fallback_ambient_drone',
            downloadUrl: '__ffmpeg_generated__',  // special marker
            // ...
        }];
    }
    
    generate(destPath, durationSeconds = 30) {
        // ffmpeg -f lavfi -i anoisesrc=color=pink:duration=N
        //        -af volume=0.08,lowpass=f=800
        //        -ac 1 -ar 44100 output.wav
    }
}
```

### Key Details
- Uses ffmpeg's `anoisesrc` filter with pink noise (natural-sounding)
- Volume via audio filter (`volume=0.08`), NOT source parameter (`anoisesrc` doesn't accept `volume`)
- Low-pass at 800Hz makes it gentle ambient, not harsh hiss
- Result cached on disk so subsequent runs reuse it

### ffmpeg Syntax Pitfall
```typescript
// WRONG — volume in source params fails with "Option not found"
'-i', `anoisesrc=color=pink:duration=${dur}:volume=-28dB`

// CORRECT — volume as separate audio filter
'-i', `anoisesrc=color=pink:duration=${dur}`,
'-af', 'volume=0.08,lowpass=f=800',
```

## 4. Universal dotenv Loading

**Changed:** All entry points in `bin/`: `agentic-run.ts`, `agentic-auto.ts`, `agentic-batch.ts`, `driver-run.ts`

### Problem
`dotenv` was in `package.json` but NO entry point called `dotenv.config()`. The `.env` file at project root was silently ignored. API keys like `PEXELS_API_KEY`, `GEMINI_API_KEY` were never loaded.

### Fix
```typescript
import dotenv from 'dotenv';
// MUST be the very first import (before any module that reads env vars)
dotenv.config();
```

### Verification
```bash
# Test that .env is loaded
node -e "require('dotenv').config(); console.log('PEXELS:', process.env.PEXELS_API_KEY ? 'SET' : 'MISSING')"
```

## 5. HTTP User-Agent for Media Downloads

**Changed:** Three HTTP clients:
- `src/lib/visual-fetcher/download.ts` (direct URL downloads)
- `src/lib/free-video/http-client.ts` (free video adapter)
- `src/lib/free-image/http-client.ts` (free image adapter)

### Problem
Custom User-Agent strings like `"Automated-Video-Generator/1.0 (free-video-integration)"` were blocked by content CDNs (Wikimedia returned 403/429).

### Fix
Use a standard browser User-Agent:
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

Wikimedia went from 403 → 429 (rate-limit, not outright block) with this fix.
