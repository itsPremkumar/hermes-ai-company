# Network resilience — NO-KEY media path (Wave G)

Scope: `src/lib/visual-fetcher/search.ts`. Why this exists: with no `PEXELS_API_KEY`,
`fetchVisualsForScene` uses Openverse → Wikimedia (free ladder). A blip there used to
return `null` and drop the scene, collapsing a 3-scene video to 1 scene (degenerate
60-frame / 2.4s render — exactly the `waveF_outro_card` failure all session).

## File:line map (as of 2026-07-24)
- `withRetry<T>(fn, label, maxAttempts=3)` — exported helper, exp backoff `min(800*2^n, 5000)`.
- `searchFreeImages(query, count)` — calls `withRetry(() => searchOpenverseImages(...))`
  and `withRetry(() => freeImageAdapter.searchAll(...))` (was unguarded before).
- `fetchVisualsForScene(...)` — terminal branch: on total failure prints
  `generating offline placeholder card` and returns `generatePlaceholderAsset(query, orientation)`
  (previously `return null`).
- `generatePlaceholderAsset(query, orientation)` — ffmpeg `color=c=0x1a2b4c:s=WxH,format=yuv420p`
  + `drawtext` (keyword, `placeholderFont()` = `C:/Windows/Fonts/arial.ttf` or DejaVu) →
  `resolveProjectPath('workspace','cache','placeholders')/ph_<slug>.png`.
  Portrait `720x1280`, landscape `1280x720`. Cache-hit reuse if file > 1000 bytes.
- Tests: `src/lib/visual-fetcher/resilience.test.ts` (4/4, offline, deterministic).

## Reproduce the offline-placeholder path (no network needed)
Force every provider down and assert a placeholder asset comes back (non-null, local path):
```bash
cd C:/one/Automated-Video-Generator
OPENVERSE_ENABLED=false PEXELS_API_KEY= npx tsx -e "
const { fetchVisualsForScene } = require('./src/lib/visual-fetcher/search.ts');
fetchVisualsForScene(['zzz_nobody_query_xyz'], false, 'portrait').then(a => {
  console.log('asset:', a && a.type, a && a.url);
  process.exit(a && a.url && a.url.endsWith('.png') ? 0 : 1);
});
"
# Expect: 'generating offline placeholder card' in log, asset.type='image', url ends .png
```
NOTE: `OPENVERSE_ENABLED=false` only disables Openverse; `freeImageAdapter` (Wikimedia)
also needs to fail. On a box where Wikimedia IS reachable this returns a real image, not
a placeholder — that's correct. To force a placeholder deterministically, temporarily
stub `freeImageAdapter.searchAll` to throw (monkeypatch in a test) — see resilience.test
pattern; not needed for normal verification.

## Retry vs placeholder — what each covers
- `withRetry`: transient blip (DNS, 5xx, 429 after sleep). 3 attempts, then throws.
- `generatePlaceholderAsset`: catches the thrown `null`-path and synthesizes a card.
- TOTAL outage (both providers down the whole run): retries ALL fail → placeholder card.
  This is INTENDED. A fully-offline run yields a complete N-scene video of placeholder
  cards (verifiable, legible keyword), NOT a blank/degenerate 1-scene clip.
- Retries do NOT recover a sustained outage — don't "fix" that; the placeholder IS the fix.

## Verification signals in a compose log
- `RETRY 1/3 openverse:...` → transient, recovered.
- `generating offline placeholder card` → total outage, placeholder substituted (ok).
- `No visual assets found ... returning null` → REGRESSION (pre-fix only).
