# Provider & Repo Quirks — Parallel Media Downloader

## Pexels (keyed, free)
- Base: `https://api.pexels.com`
- Images: `GET /v1/search?query=<topic>&per_page=N&page=1` → `data.photos[]` each with `id, alt, photographer, url, src.large2x|large|original`.
- Videos: `GET /videos/search?query=<topic>&per_page=N&page=1` → `data.videos[]`, each with `video_files[]` (filter `file_type` includes `mp4`, sort by `width` desc for best quality), `user.name`, `duration`, `image` (poster).
- Auth: header `Authorization: <KEY>` (no `Bearer`).
- **QUIRK**: invalid/missing key → HTTP **200** with `{"photos":[],"error":undefined}` (empty, no error field). A placeholder key like `your_pexels_api_key_here` yields 0 results. So:
  - Gate behind `pexelsKeyPresent()` that rejects empty AND the known placeholder string.
  - To verify a key works, parse the JSON body and count `photos`/`videos`, not just the status code.

## Wikimedia Commons (keyless, image+video)
- Image provider: `WikimediaImageProvider`. Video provider: `WikimediaProvider`.
- Best image `downloadUrl` is usually `https://upload.wikimedia.org/.../..._<width>px.jpg`; pick a sane width (e.g. 1280) to avoid 50MB downloads.
- **429s aggressively under burst** → bounded concurrency (4–5) + retry/backoff honoring `Retry-After`. The relevance-filtered candidate pool from OTHER hosts (Archive.org, Pexels) is the failover that saves the run.
- **⚠ 403/429 fix**: set `User-Agent` header to a real browser string on the HTTP client. Requests with custom/generic UAs (`Automated-Video-Generator/1.0`, `node.js`, `curl/*`) return 403 (forbidden) or 429 (rate limit) from Wikimedia CDNs. Use:
  ```ts
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Referer': 'https://www.google.com/',
  }
  ````

## Internet Archive (keyless, image: `ArchiveOrgImageProvider`, video: `ArchiveOrgProvider`)
- Image search: `advancedsearch.php?q=<kw> AND mediatype:image`, then fetch `/metadata/<id>` per doc, filter `files` by image extension, build `https://archive.org/download/<id>/<file>`.
- Can be SLOW (sequential metadata fan-out) → keep a per-search timeout (60s) so it can't hang the job.

## NASA / MetMuseum (keyless, images)
- `NasaImageProvider`, `MetMuseumImageProvider`. OFF-TOPIC for most queries (NASA→space, Met→art). **Gate them to space/art topics only**; querying them for every keyword is the root cause of the "lion → Lion nebula" bug.

## Automated-Video-Generator repo (Structural facts)
- Free media adapters: `src/lib/free-image/adapter.ts` (`FreeImageAdapter.searchAll`, `static isOnTopic`), `src/lib/free-video/adapter.ts` (`FreeVideoAdapter.searchAll`, `static isOnTopic`). `isOnTopic` is whole-word + compound-exclusion + brand/non-Latin blocklist.
- Core parallel engine built this session: `src/lib/media-downloader.ts` — `downloadTopicMedia(topic, {images, videos, concurrency, timeoutMs, offlineFallback, verifyVisual})`; `searchAllImagePlatforms` / `searchAllVideoPlatforms`; `downloadOneAsset` (per-asset retry + `Promise.race` timeout); `generateOfflineVisual` (ffmpeg CC0 backstop via `tools/asset-creator/src/index.js`).
- Keyed platform module: `src/lib/pexels.ts` (`searchPexelsImages`, `searchPexelsVideos`, `pexelsKeyPresent`).
- CLI demo: `bin/agentic-download.ts` (`"<topic>" --images N --videos N --concurrency N --timeout-ms MS --verify-visual`). Loads `.env` via `dotenv.config`.
- `LlmBridge` (`src/agentic/bridge.ts`): only `completeJSON(system, prompt, schemaHint)`, **no `generate`** → use `completeJSON` for any vision/classification call.
- `.env` is gitignored — safe to store API keys there (never commit keys). Format: `PEXELS_API_KEY=<realkey>`.
- Known PRE-EXISTING CI debt (not regressions): 36 `mock.module` test failures in `src/adapters/**` (tsx transpile gap) + 2 `no-control-regex` errors in `src/lib/errors.ts`. `npm run lint` exits 1 on those but they are unrelated to media downloads.

## Auto-generated ambient audio fallback (zero-network)
When external music providers (open-lofi, internet-archive) fail or are unavailable, generate a gentle pink-noise ambient drone via ffmpeg instead of leaving the video without background audio. This is always the last resort provider in the chain.

```ts
// ffmpeg args for ambient pink noise:
const args = [
  '-f', 'lavfi',
  '-i', `anoisesrc=color=pink:duration=${durationSeconds}`,
  '-af', 'volume=0.08,lowpass=f=800',
  '-ac', '1',
  '-ar', '44100',
  '-y', destPath,
];
```

**QUIRK**: `anoisesrc` does NOT accept `volume` as a source parameter — you MUST apply it as a separate `-af 'volume=N'` filter. Putting `volume=-28dB` inside the lavfi source string causes ffmpeg error "Option not found".

## Verification recipe (offline, fast, no hang)
```ts
// in a node:test, monkeypatch on the PROTOTYPE so the search fns (which build
// their own adapter instances) use fakes:
const wik = await import('./free-image/providers/wikimedia.js');
const orig = wik.WikimediaImageProvider.prototype.search;
wik.WikimediaImageProvider.prototype.search = async () => fakeImg(['Lion in savanna'],'wiki');
// ... assert results; then restore:
wik.WikimediaImageProvider.prototype.search = orig;
```
- For `downloadOneAsset` never-throws: use `url: 'data:image/png;base64,xxx'` (fails instantly, no DNS hang).
- Do NOT call `asset-creator`/ffmpeg inside unit tests — it hangs the tsx harness. Verify the offline CC0 backstop by running the real CLI e2e.
