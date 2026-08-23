# AVS Network-Resilience (flaky media fetch)

Zero-cost / no-API-key video generation depends on Openverse + Wikimedia
(plus Pexels/Pixabay only if a key is set). On a bad-network day these blip,
and the symptom is **variety jobs silently collapsing to 1/3 scenes** —
the scene-image encode `return`s on a failed fetch, dropping the scene, and
the final video is a degenerate short clip (e.g. 60 frames / 2.4 s instead of
~9 s / 3 scenes). This was the single biggest cause of "render looks wrong /
outro never appears" during the Wave-F..H campaign.

## Two-layer fix (verified 2026-07-24)

### Layer 1 — `withRetry` around free-source fetches
In `src/lib/visual-fetcher/search.ts`:

```ts
export async function withRetry<T>(fn: () => Promise<T>, label: string, maxAttempts = 3): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try { return await fn(); }
    catch (e) {
      lastError = e;
      if (attempt < maxAttempts - 1) {
        const delay = Math.min(800 * Math.pow(2, attempt), 5000);
        console.log(`  [RETRY ${attempt + 1}/${maxAttempts}] ${label} failed, waiting ${delay}ms...`);
        await sleep(delay);
      }
    }
  }
  throw lastError;
}

// wrap the two free providers so a single transient blip recovers:
const openverse = await withRetry(() => searchOpenverseImages(query, count), `openverse:${query}`);
const sourceResults = await withRetry(() => freeImageAdapter.searchAll(query, {count}), `free-image:${query}`);
```

### Layer 2 — offline placeholder fallback
`fetchVisualsForScene` ends with:

```ts
console.log(`  No visual assets found for "${query}" from any source — generating offline placeholder card.`);
try { return await generatePlaceholderAsset(query, orientation); }
catch (e) { console.log(`  Placeholder generation also failed: ${(e as Error).message}`); return null; }
```

`generatePlaceholderAsset` (same file) builds a local gradient card via
ffmpeg (no network) and returns it as a `MediaAsset` so the slideshow keeps
its full scene count:

```ts
const dir = resolveProjectPath('workspace', 'cache', 'placeholders'); // AVS containment: NEVER system TEMP
fs.mkdirSync(dir, { recursive: true });
const [W, H] = orientation === 'portrait' ? [720, 1280] : [1280, 720];
execFileSync(ffmpegPath(), [
  '-y', '-v', 'error',
  '-f', 'lavfi', '-i', `color=c=0x1a2b4c:s=${W}x${H},format=yuv420p`,
  '-frames:v', '1',
  '-vf', `drawtext=fontfile='${placeholderFont()}':text='${label}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2`,
  out,
], { timeout: 30000 });
```

### Music fallback
Reorder `defaultProviders()` in `src/lib/free-music.ts` to put
`FallbackToneProvider` (name `'bundled'`, the offline ffmpeg-generated
ambient tone) **first**, so `resolveFreeBackgroundMusic`'s legacy loop
resolves music instantly instead of hanging on 15 s CcMixter/InternetArchive
timeouts. (The online music engine is tried first only when not preferring
`'bundled'`.)

## Proof
- `resilience.test.ts` 4/4 (`withRetry` retry-then-success / rethrow-after-
  max / default-attempts).
- `waveF_outro_card` (kitchen-sink) went from repeatedly collapsing to 1 scene
  → composing all 3 scenes once retries were in place.
- `waveH_kitchen_sink` / `_portrait_mix` / `_square_stack` all rendered 3/3
  scenes with every overlay burning (vision-confirmed).

## Pitfall
Retries recover TRANSIENT blips, not a SUSTAINED outage. On a fully-down
network, retries still fail fast and the placeholder fallback kicks in — so the
video still renders (with placeholder cards), never silently 1/3.
