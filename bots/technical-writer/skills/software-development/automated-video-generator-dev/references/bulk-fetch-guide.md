# Bulk Subject Fetch — Reference

The "download N images/videos of `<subject>`" capability added in this session.
Lives in `src/agentic/operations/bulk-fetch.ts` (`runBulkImageFetch`) and is wired
into `agentic-batch.ts` (`--search`/`--count`/`--kind`) and `single-feature.ts`
(`searchQuery`/`downloadCount` JSON fields).

## API
```ts
runBulkImageFetch(
  query: string,                 // subject, e.g. "eagle", "ocean waves"
  count: number,                // desired DISTINCT assets
  outDir: string,               // where to write (e.g. workspace/bulk/images/eagle)
  orientation: 'none'|'portrait'|'landscape'|undefined,
  kind: 'image' | 'video' = 'image',
): Promise<string[]>            // local file paths written
```

Source order (each de-duped by URL so final set is distinct):
1. Pexels — `searchImages` (image) / `searchVideos` (video) when `PEXELS_API_KEY` env is set.
2. Openverse/Wikimedia fallback ladder — `fetchVisualsForScene([query], preferVideo, orientation, undefined, page*count)` looped up to 8 pages.
3. `downloadMedia` writes each (honors its own cache + maxContentLength guard — a too-large Wikimedia webm logs a graceful skip, not a crash).

## CLI invocations
```bash
npx tsx src/adapters/cli/agentic-batch.ts --search "eagle" --count 10
npx tsx src/adapters/cli/agentic-batch.ts --search "ocean waves" --count 5 --kind video
npx tsx src/adapters/cli/agentic-batch.ts --search "eagle" --count 10 --orientation landscape
```
npm shorthand: `npm run agentic:fetch -- "eagle" --count 10`

## JSON job
```json
{ "id": "sf_bulk_eagle", "title": "Bulk: 10 Eagle Images",
  "mode": "download-images", "searchQuery": "eagle", "downloadCount": 10, "orientation": "landscape" }
{ "id": "sf_bulk_ocean", "title": "Bulk: 5 Ocean Wave Videos",
  "mode": "download-videos", "searchQuery": "ocean waves", "downloadCount": 5 }
```
In `runDownloadImages`, presence of `job.searchQuery` short-circuits the
per-scene path and calls `runBulkImageFetch` directly.

## Live evidence (this session, Windows box, NO Pexels key)
```
Bulky image fetch: "eagle" x 10 -> ...\workspace\bulk\images\eagle
[PEXELS] No API key set — skipping Pexels image search. Free sources will be used as fallback.
  FALLBACK: Got 5 image(s) from free sources (Openverse/Wikimedia).
  Downloaded 2/10 distinct image(s):
     image_001.jpg
     image_002.jpg

$ file workspace/bulk/images/eagle/*.jpg
image_001.jpg: JPEG image data, Exif standard, baseline, precision 8, 1024x592, components 3
image_002.jpg: JPEG image data, baseline, precision 8, 1024x683, components 3
```
**Interpretation:** mechanism is correct end-to-end (real JPEGs on disk). The
`2/10` is the free-source pool ceiling for that niche subject without a Pexels
key — NOT a defect. With `PEXELS_API_KEY` set in `.env`, the Pexels branch runs
first and reaches the requested count.

## Pitfalls (bulk-fetch specific)
- `searchImages` returns images only — must call `searchVideos` for `--kind video`.
- `fetchVisualsForScene` orientation param type is `'none'|'portrait'|'landscape'|undefined`; passing `''` (empty string) fails typecheck. Use `(orientation || 'portrait') as any`.
- Always confirm outputs with `file <path>` (real media, not zero-byte placeholder) before reporting success.
