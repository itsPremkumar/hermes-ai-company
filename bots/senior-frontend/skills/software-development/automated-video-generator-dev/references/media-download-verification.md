# Media Download Verification (empirical, not static)

When the user asks "are images/videos actually downloading from all sources?", PROVE it by
execution — import the project's REAL fetchers and exercise each source with a byte-on-disk
assertion. Do NOT trust `grep` alone. This is the recipe from the 2026-07-26 session where we
found (and fixed) four real download-robustness bugs.

## The 16 source families (verified present in src)
Keyed (tried first): Pexels, Pixabay, Openverse. Free/CC (auto-fallback): Wikimedia Commons,
Internet Archive, NASA, MetMuseum, Flickr (via Openverse), Coverr, ccMixter, OpenLofi,
Procedural, Local/bundled BGM. URL/local: custom `downloadUrl`, YouTube (reference),
`input/visuals/` + `input/voices/`.
Fallback chain: Pexels → Pixabay → Openverse → Wikimedia → Archive → (NASA/Met for images) →
local/assets/procedural. `agentic-batch.ts` only reads `agentic-scripts.json`.

## Reusable empirical test harness
`scripts/verify-download-sources.ts` (committed to the repo) imports the project's own
functions and downloads one image + one video per source, asserting bytes landed on disk:
- keyed: `searchPexelsImages`/`searchPexelsVideos` (download via `downloadMedia(url, dir, name)`)
- keyed-bulk: `runBulkImageFetch(query, 1, dir)` (no `runBulkVideoFetch` exists — use
  `searchPexelsVideos` + `downloadMedia` for videos, or `FreeVideoAdapter.searchAndDownloadFirst`)
- free-image: `freeImageAdapter.searchBest(keyword)` → `downloadMedia(best.downloadUrl, dir, name)`
- free-image-failover: `freeImageAdapter.searchAndDownloadFirst(keyword, dir)` (candidate failover)
- free-video: `new FreeVideoAdapter().searchAndDownloadFirst(keyword, dir)`
- `fetchVisualsForScene(keywords, preferVideo, orientation)` (returns ONE `MediaAsset`|null, NOT an array)

Run it in the BACKGROUND (downloads exceed 60s foreground; large Pexels clips are 30–66MB):
```bash
cd /c/one/Automated-Video-Generator
node_modules/.bin/tsx scripts/verify-download-sources.ts > workspace/verify-downloads-run.log 2>&1
# then poll: sed -n '/DOWNLOAD SOURCE TEST RESULTS/,$p' workspace/verify-downloads-run.log
```
Harness gotchas that cost a debug cycle:
- `ImageResult`/`VideoResult` use field `downloadUrl` (NOT `.url`).
- `MediaAsset` (from `fetchVisualsForScene`) uses `.url`.
- `searchImages(...)` returns `MediaAsset[]` with `.url`.
- `downloadMedia(url, dir, filename)` returns a `DownloadResult` object `{path, ...}` — call
  `.path`, NOT the raw return. (`path` not `file`.)
- `fetchVisualsForScene` returns a SINGLE asset (or null), so do `const a = Array.isArray(r)?r[0]:r`.
- Bump the per-source `withTimeout` to 120000ms so legit 30–66MB videos aren't killed by the test.

## Results interpretation
A `PASS` with bytes >1KB (image) / >5KB (video) = source works end-to-end. A `FAIL`/`ERROR`
can be THREE different things — diagnose before concluding "broken":
1. **Harness bug** (wrong field name, wrong return shape) — check the log line; "Invalid URL" /
   "path argument must be of type string" = harness, not pipeline.
2. **Live rate-limit** (HTTP 429 from Wikimedia/Archive under burst, or slow-throttled transfer) —
   the pipeline's retry/failover handles it; re-run later or check the URL with `curl -I`.
   Confirm sources are alive: `curl -s -o /dev/null -w "%{http_code}" "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=nature&srlimit=1"`.
3. **Real code defect** — see the four below (all now FIXED 2026-07-26).

## The four download-robustness bugs found + fixed (2026-07-26)
Root cause: the KEYED path (`downloadMedia`) was LESS robust than the free path, and the
free-image path had no source failover.

1. **`downloadMedia` (src/lib/visual-fetcher/download.ts) had NO retry + a 30s TOTAL timeout.**
   A first 429/5xx threw immediately; a slow-but-alive >30s video was killed.
   FIX: wrapped the stream in `withRetry` (from `agentic/operations/retry.ts`, 3x backoff,
   `shouldRetry` on 429/5xx/timeout/stall/network); replaced the total `timeout` with a
   CHUNK-STALL guard (resets on every chunk); added HTTP `Range` RESUME so a partial `.part`
   continues instead of restarting.
2. **Free-image path had NO source failover** (src/lib/free-image/adapter.ts). A throttled
   Wikimedia image didn't fall through to Archive.
   FIX: added `searchAndDownloadFirst()` with candidate failover (mirrors FreeVideoAdapter);
   wired `fetchVisualsForScene`'s free-image branch to use it.
3. **Free-video stall window = 30s** (src/lib/free-video/download/downloader.ts). Slow free
   streams died at 30s of no-chunk.
   FIX: default stall window raised 30s -> 90s (env `FREE_VIDEO_DOWNLOAD_STALL_TIMEOUT_MS`).
4. **Free-video retry retried permanent 4xx** (free-video/utils.ts `withRetry`). Wasted 3
   attempts on 404s.
   FIX: added `shouldRetry` that skips 4xx (except 429).

After fixes: keyed image (388KB) + keyed large video (31MB) + free-image (16MB, via failover)
PASS; free-video free CC hosts were rate-limiting at test time but URLs returned HTTP 200 and
the same `.webm` files downloaded successfully on other passes — i.e. environmental throttling,
not a code defect. `npm run typecheck` clean (0 errors) after the changes.

## Probe pattern for a single source (background)
When you need to isolate ONE source's health, write a tiny `scripts/probe-*.ts` (NOT `tsx -e`,
which can't resolve `.ts` import paths) and run it in the background:
```ts
import { config as loadEnv } from 'dotenv'; loadEnv();
import { FreeVideoAdapter } from '../src/lib/free-video/adapter.js';
(async () => {
  const a = new FreeVideoAdapter();
  const r = await a.searchAndDownloadFirst('nature forest', 'workspace/probe', 'portrait');
  console.log(r?.localPath ? `OK ${require('fs').statSync(r.localPath).size}` : 'NULL');
})().catch(e => console.error('ERR', e.message));
```
Then check the source URLs directly: `a.searchAll(...)` -> `for v: fetch(v.downloadUrl,{method:'HEAD'}).then(r=>r.status)` (expect 200).

## Verification gate for "did the download fix work?"
- `npm run typecheck` exits 0.
- `scripts/verify-download-sources.ts` shows the keyed paths (Pexels image + 31MB video) PASS.
- Free-image PASS via failover. Free-video PASS when hosts aren't throttling (re-run later).
- Do NOT conclude "broken" from a single 429/timeout — confirm with a direct `curl -I`/HEAD probe.
