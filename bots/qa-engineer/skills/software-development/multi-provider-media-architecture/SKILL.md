---
name: multi-provider-media-architecture
description: Build extensible multi-provider media/audio systems with provider registry, priority chain, parallel fan-out, processing pipeline, and procedural fallback generation. Covers the exact architecture pattern used for the Automated-Video-Generator music system overhaul — but applies to any media source (images, video, audio, TTS).
---

# Multi-Provider Media Architecture

Build extensible media provider systems with:
- **Provider Registry** — plugin-based, priority-ordered
- **Parallel Fan-Out** — query all providers simultaneously
- **Processing Pipeline** — transform downloaded assets
- **Procedural Fallback** — generate assets when all providers fail

## Trigger

Use when the user wants to:
- "Add a new provider for X" (music, images, video, TTS)
- "Make the provider system extensible"
- "Add fallback when providers fail"
- "Improve the music/audio/image system architecture"
- Or any task involving multiple interchangeable media sources with priority ordering

## Architecture Pattern

```
                    ┌─────────────────────┐
                    │   Consumer Code     │
                    │ (engine.ts / client)│
                    └─────────┬───────────┘
                              │ query
            ┌─────────────────▼────────────────┐
            │         Provider Registry         │
            │  (sorted by priority ascending)   │
            │                                   │
            │  Tier 1: Bundled (offline)        │
            │  Tier 2: Local files (offline)    │
            │  Tier 3: Primary API (online)     │
            │  Tier 4: Fallback API (online)    │
            │  Tier 5: Procedural (always)      │
            └────────┬────────────────┬─────────┘
                     │ parallel       │
            ┌────────▼───┐   ┌────────▼───┐
            │ Provider A │   │ Provider B │ ...
            │ .search()  │   │ .search()  │
            │ .download()│   │ .download()│
            └────────────┘   └────────────┘
                     │
            ┌────────▼────────────────────────┐
            │  Processing Pipeline            │
            │  Trim → Fade → Normalize → Loop │
            └─────────────────────────────────┘
```

## Implementation Steps

### 1. Define the Provider Interface

```typescript
interface MediaProvider {
    readonly name: string;
    readonly label: string;
    readonly priority: number;     // 1 = highest
    readonly requiresNetwork: boolean;
    search(query: MediaQuery): Promise<MediaTrack[]>;
    download(track: MediaTrack, destPath: string): Promise<string>;
    verify?(localPath: string): Promise<boolean>;
}
```

Key rules:
- `search()` returns empty array for "no results" — never throws
- `search()` throws only on genuine errors (timeout, auth failure)
- `download()` creates parent directories and returns absolute path

### 2. Implement a Provider Registry

```typescript
class ProviderRegistry {
    private providers = new Map<string, MediaProvider>();

    register(provider: MediaProvider): void {
        if (this.providers.has(provider.name)) return; // idempotent
        this.providers.set(provider.name, provider);
    }

    getAll(): MediaProvider[] {
        return [...this.providers.values()]
            .sort((a, b) => a.priority - b.priority);
    }

    getOffline(): MediaProvider[] { /* filter !requiresNetwork */ }
    getOnline(): MediaProvider[] { /* filter requiresNetwork */ }
}
```

### 3. Implement Parallel Fan-Out

```typescript
async function resolveMedia(query: MediaQuery): Promise<ResolvedMedia | null> {
    const providers = registry.getAll();

    // Query all providers
    const results = await Promise.allSettled(
        providers.map(p => raceWithTimeout(
            p.search(query),
            { timeout: 10_000, label: p.name }
        ))
    );

    // Collect successful results, sorted by priority
    const candidates = results
        .filter(isFulfilled)
        .flatMap(r => r.value.tracks);

    // Pick best
    const best = candidates[0];
    if (!best) return fallbackProvider.generate(query);

    // Download + process
    return downloadAndProcess(best, query);
}
```

### 4. Implement Processing Pipeline

Chain of ffmpeg-based transformation stages:

```typescript
class ProcessingPipeline {
    async run(input: string, output: string, opts: Options): Promise<Result> {
        let current = input;
        if (opts.trimToDuration)    current = await trim(current, opts.targetDuration);
        if (opts.applyFade)         current = await fade(current, opts);
        if (opts.normalizeLoudness) current = await normalize(current);
        if (opts.enableLooping)     current = await loop(current, opts.targetDuration);
        fs.renameSync(current, output);
        return { finalDurationSec: await probeDuration(output) };
    }
}
```

### 5. Implement Procedural Fallback

The last-resort provider that generates content via ffmpeg synthesis (no network, always works):

```typescript
class ProceduralProvider implements MediaProvider {
    readonly priority = 99; // Always last

    async search(query: MediaQuery): Promise<MediaTrack[]> {
        // Return a single generated track
        return [{ id: 'procedural_...', downloadUrl: '__ffmpeg_generated__' }];
    }

    async download(track: MediaTrack, destPath: string): Promise<string> {
        // Generate using ffmpeg lavfi
        const args = [
            '-f', 'lavfi', '-i', 'sine=f=261.63:d=30',
            '-f', 'lavfi', '-i', 'sine=f=329.63:d=30',
            '-filter_complex', 'amix=inputs=2:duration=longest',
            '-y', destPath,
        ];
        await spawnFfmpeg(args);
        return destPath;
    }
}
```

### 6. Backward Compatibility (Shim Pattern)

```typescript
// Old API — wraps new engine, exported from original location
export async function resolveLegacyMedia(opts: LegacyOpts): Promise<LegacyResult | null> {
    const result = await engine.resolveMedia({ topic: opts.query });
    if (!result) return null;
    return { localPath: result.localPath, track: mapToLegacy(result.track) };
}
```

## Provider-Specific Integration Patterns

### ccMixter (ccmixter.org)

Free CC-licensed music. No API key. **Primary network provider** in the music chain.

**API:** `GET https://ccmixter.org/api/query?limit=N&tags=TAGS&f=json`

**Critical Gotchas:**
- **Referer header required for download** — the Apache server blocks hotlinking (403 Forbidden). Always send `Referer: https://ccmixter.org/` on download requests.
- **AND tag semantics** — comma-separated tags are AND'ed. Limit to 2-3 tags max; more tags = empty results.
- **Slow but reliable** — responses take 5-15s. Set provider timeout to 15_000ms minimum.
- **User-Agent** — do NOT use `axios/1.x` UA. Use a real browser UA string.

**Response format:**
```json
[{
  "upload_id": 71027,
  "upload_name": "Track Title",
  "user_name": "Artist",
  "license_url": "https://creativecommons.org/...",
  "files": [{"download_url": "https://ccmixter.org/content/User/File.mp3"}]
}]
```

### Internet Archive (archive.org)

Public domain audio. Free, no key. **Tier 4 fallback.**

**API:** `GET https://archive.org/advancedsearch.php?...&output=json`

**Critical Gotchas:**
- **Download URL is NOT `{identifier}/{identifier}.mp3`** — filenames vary. Resolve per-track via `https://archive.org/metadata/{identifier}`.
- **Two-step resolution:** search &rarr; get identifier &rarr; fetch metadata &rarr; find first playable .mp3/.ogg (not spectrogram, not zip, not source).
- **License filter** — append `AND (licenseurl:*)` to the search query for CC-licensed works.

### Bundled Provider Metadata Format

Ship pre-made audio in `input/bgm/__bundled__/` with `metadata.json`:

```json
[
  {
    "filename": "ambient_piano.mp3",
    "title": "Ambient Piano",
    "mood": ["calm", "meditation"],    // "mood" (array) NOT "moods"
    "durationSec": 60,
    "format": "mp3"
  }
]
```

**Pitfall — aggregated array, NOT per-track sidecars:** `BundledProvider.loadMetadata()`
reads `metadata.json` as an **array of `{ filename, ... }`** objects keyed by `filename`.
It does NOT expect individual `<base>.json` sidecar files (it only reads those if present,
and excludes `metadata.json` itself). A sidecar-only or single-object `metadata.json` makes
every track fall back to `durationSec: 0` + `mood: undefined` → tests like "track has
duration" and "mood includes X" fail. The map key is the filename with extension stripped
(`filename.replace(/\.[^.]+$/, '')`).

**Pitfall — unknown mood must return empty:** `search()` must require mood metadata to match
a specific mood. If `query.mood !== 'any'`, a track with NO mood metadata must be *excluded*
(not passed through). Otherwise an unknown mood (e.g. `'metal'`) returns all tracks instead
of 0. The match is `meta.mood.some(m => m.toLowerCase() === query.mood)`.

### Black Frame Trimming (X10 Fix)

Pexels stock clips often have 0.5-1s fade-in. Trim after download:
```typescript
const detectCmd = `ffprobe -v quiet -f lavfi -i "movie=${path},blackframe=0.1:30" -show_entries frame=pkt_pts_time -of csv=p=0`;
const firstNonBlack = Math.min(...execSync(detectCmd).toString().trim().split('\n').map(Number));
if (firstNonBlack > 0.3) {
  execSync(`ffmpeg -i "${path}" -ss ${firstNonBlack}s -c copy -avoid_negative_ts 1 -y "${trimmed}"`);
}
```

### Processing: MP3 vs WAV Output

When pipeline outputs `.mp3` instead of `.wav`:

| Stage | WAV codec | MP3 codec |
|-------|-----------|-----------|
| Trim | `-c copy` | `-c copy` |
| Fade | `-c:a pcm_s16le` | `-c:a libmp3lame -b:a 192k` |
| Normalize | `-c:a pcm_s16le` | `-c:a libmp3lame -b:a 192k` |

MP3 reduces file size ~5x (5.3MB &rarr; ~1MB for 30s).

## Pitfalls

### The `withTimeout` Bug
The most common timeout bug: creating an `AbortController` but **not passing its signal** to the HTTP call. The timeout fires but the request keeps running, causing confusing interleaved errors.

**Fix:** Always pass `signal` to axios:
```typescript
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), timeoutMs);
try {
    return await Promise.race([
        axios.get(url, { signal: controller.signal }),  // ← MUST pass signal
        new Promise((_, rej) => controller.signal.addEventListener('abort', () => rej(new Error('timeout')))),
    ]);
} finally {
    clearTimeout(timer);
}
```

### Provider Registration Order
Higher-priority providers (lower number) are queried first, but ALL are queried in parallel for speed. The first successful highest-priority result wins. If a high-priority provider is slow, the fan-out doesn't wait for it — but its result, if it arrives, is preferred.

### Processing Pipeline Cleanup
Processing stages create temp files (`__trim_`, `__fade_`, etc.). Always rename the final result and let the temp files be cleaned by the OS or a periodic `workspace/cache` cleanup.

### Early Exit on Offline Providers
When an offline/bundled provider returns results, skip network providers entirely. This keeps the system fast when cached assets are available.

### Legacy Shim Provider-List Drift (AVG `src/lib/free-music.ts`)
`listFreeMusicProviders()` returns `defaultProviders().map(p => p.name)`. This list DRIFTS
from the new registry (`src/music-system/providers/index.ts` `registerDefaultProviders()`).
A test "listFreeMusicProviders includes the music sources" asserts specific names.

**Rule:** when a provider is added/removed from the new registry's `registerDefaultProviders()`,
mirror the change in the legacy `defaultProviders()` (add a `XxxFreeProvider` wrapper that
delegates to the new provider's `search()` + `mapToLegacy`). Do NOT leave the legacy list
naming a provider the new registry no longer registers (e.g. `open-lofi` was removed upstream
because its audio files were deleted — keep `ccmixter` instead). If the test requires a name
the new registry actually registers, the legacy list is the one to fix, not the test.

### Don't "Fix" Real Logic Bugs by Weakening Assertions
When a test fails with `AssertionError` (not a network/host error), root-cause the SOURCE.
For the AVG music system the real bugs were: (1) `loadMetadata()` reading the wrong metadata
shape, (2) the mood filter passing through tracks with no mood metadata, (3) the legacy shim
provider list missing a provider the new registry registers. Never delete or soften assertions
to make tests pass — fix at cause. See `references/avg-music-system-debugging.md`.

## Verification

After implementing:
1. `typecheck` — zero errors
2. Test with all providers disabled — verify procedural fallback works
3. Test with only network providers — verify real assets are fetched
4. Test backward-compatible shim — old callers unchanged
5. Verify processing pipeline produces valid audio (ffprobe duration + codec check)

## Related Files

This skill's `references/` directory contains:
- `references/procedural-ffmpeg-recipes.md` — exact ffmpeg filter graph recipes for 3 profiles (ambient/upbeat/cinematic) plus utility commands
- `references/internet-archive-audio.md` — Internet Archive audio search + download resolution (two-step metadata pattern)
- `references/free-music-api-research.md` — verified status of free music APIs (working, broken, methodology to find new ones)
- `references/bundled-provider-format.md` — shipped offline tracks with metadata.json
- `references/avg-music-system-debugging.md` — root-cause + fix patterns for AVG music-system test failures (BundledProvider metadata shape, unknown-mood filtering, legacy-shim provider-list drift)
