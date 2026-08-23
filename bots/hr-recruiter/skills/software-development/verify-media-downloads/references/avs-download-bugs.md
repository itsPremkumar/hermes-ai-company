# AVS Download Source Defects (found & fixed, session 2026-07-26)

## Context
User reported image/video downloads "not working" in Automated-Video-Generator (AVS).
Investigated `src/lib/visual-fetcher/`, `src/lib/free-image/`, `src/lib/free-video/`.

## Source inventory (AVS)
KEYED (needs .env keys): Pexels (image+video), Pixabay (image+video+music), Openverse (image+video, aggregator).
FREE CC: Wikimedia Commons (img+vid), Internet Archive (img+vid+music), NASA (img), Met Museum (img), Flickr (img, via Openverse), Coverr (vid).
URL/LOCAL: custom downloadUrl, YouTube (reference only), input/visuals/ + input/bgm/ + procedural.

## Real defects found (NOT environmental)
1. `src/lib/visual-fetcher/download.ts` `downloadMedia()` (the KEYED Pexels/Pixabay path):
   - Had NO retry. A single 429/5xx/stall threw immediately.
   - Used axios `timeout: DOWNLOAD_STALL_TIMEOUT_MS` (30s) as a TOTAL timeout — killed slow-but-alive large videos (31–66MB) at 30s.
   - No HTTP Range resume; a partial `.part` was discarded.
   - The FREE path (FreeDownloadManager) already had retry+stall+resume → asymmetric: recommended keyed path was WEAKER than the free path.
2. `src/lib/free-image/adapter.ts` `FreeImageAdapter`: had NO download-with-failover.
   `searchBest` returned a candidate but the download step had no Wikimedia→Archive failover (unlike the video adapter's `searchAndDownloadFirst`).
3. `src/lib/free-video/download/downloader.ts`: stall window defaulted to 30s → slow Wikimedia/Archive streams died at 30s of no-chunk.
4. `src/lib/free-video/utils.ts` `withRetry`: retried on ANY error, including permanent 4xx (404/403) → wasted 3 attempts.

## Fixes applied
1. `download.ts`: wrap `streamToFile` in `withRetry` (3×, base 800ms, max 8s, jitter, `shouldRetry` on 429/5xx/timeout/stall/network/ECONN*); replace total timeout with a CHUNK-stall timer (resets on every `data` chunk); add HTTP Range resume (`supportsResume = status===206`, append mode).
   `isDownloadRetryable(err)` returns true for status 429, 5xx, network codes, /timeout|stall|reset/ messages, AxiosError.
2. `free-image/adapter.ts`: added `searchAndDownloadFirst(keyword, outDir, opts)` mirroring the video adapter — ranks candidates on-topic+resolution, downloads each in turn, returns first that succeeds (MediaAsset with localPath); imports `downloadMedia` dynamically to avoid cycle.
3. `search.ts`: free-image fallback branch now calls `freeImageAdapter.searchAndDownloadFirst(...)` (failover) instead of `searchFreeImages` + pick-one.
4. `downloader.ts`: stall default 30s → 90s; added `shouldRetry` to the `withRetry` call skipping permanent 4xx (`>=400 && <500 && !=429`).
5. `free-video/utils.ts`: `withRetry` gained optional `shouldRetry` option; callers break on non-retryable.

Typecheck: 0 errors after fixes.

## How to reproduce / verify
Run `scripts/verify-download-sources.ts` (template under this skill's `scripts/`).
It loads .env, calls each source's REAL fetcher, downloads 1 image + 1 video per source,
prints PASS/FAIL + bytes. Observed valid behavior post-fix:
  pexels(image) PASS 388KB; keyed-bulk(image) PASS 2.8MB; free-image PASS 16MB;
  searchImages PASS 584KB; pexels(video) PASS 31MB;
  free-video / fetchVisualsForScene(video): variable — flip PASS↔FAIL across runs.
The flip is LIVE throttling on free CC hosts, proven by:
  - `curl -I`/HEAD on the returned free-video `downloadUrl`s → HTTP 200 (Wikimedia .mpg, Archive .webm).
  - Those same .webm files downloaded successfully (4.6MB) on earlier passes.
  - Wikimedia API healthy: `curl "...commons.wikimedia.org/w/api.php?..."` → HTTP 200, 1s.

## Verification gotchas
- `tsx` does NOT auto-load `.env` — harness must `import { config } from 'dotenv'; config();`.
- AVS `fetchVisualsForScene` returns a single asset (not array). `ImageResult/Videoresult.downloadUrl`, `MediaAsset.url`, `downloadMedia` returns `{path}`.
- Unit suite "failures" were environmental: `ModuleNotFoundError: No module named 'fastapi'`
  (Python venv missing dep — speech backend), `# SKIP host unreachable` network skips,
  and the MSYS fork crash (`cygheap read copy failed`) — all unrelated to the download fix.
  `new-features.test.ts` passed 19/19 in isolation.
- AVS runtime re-flags already-committed files as "changed" — do NOT re-edit to clear;
  verify with `git status --porcelain` + `git diff HEAD` (empty = committed).
