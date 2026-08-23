---
name: parallel-media-downloader
description: Build a production-ready, fault-tolerant PARALLEL multi-platform media (image+video) downloader that isolates each source, filters off-topic results, downloads with bounded concurrency + candidate failover, and falls back to locally-generated CC0 placeholders when offline/rate-limited. Use for "download N images/videos about <topic>", "make downloading parallel and robust", "one platform failing shouldn't break the rest", "offline fallback for media", or integrating a keyed provider (Pexels/Pixabay) alongside keyless ones (Wikimedia, Internet Archive).
---

# Parallel Fault-Tolerant Media Downloader

## When to use
- "Download N images/videos about <topic>" where TOPIC RELEVANCE matters (no NASA space shots for "lion", no brand/commercial collisions like Japanese "LION" detergent commercials).
- "Make downloading parallel and robust" / "if one source fails the rest must still work".
- "What if offline / rate-limited?" → need a CC0 local backstop so the job always completes.
- Integrating a keyed provider (Pexels/Pixabay/Openverse) next to keyless ones.

## Provider priority ladder (Pexels → Pixabay → Free)
**Pexels is the RECOMMENDED primary provider** for both images and videos. Free sources (Openverse, Wikimedia, Internet Archive) are fallbacks only — slower, more prone to 429, and often return off-topic content. When Pexels API key is present:
- Log a prominent `★ PEXELS is the RECOMMENDED primary` banner once per run.
- Always try Pexels FIRST. Log `★ [PEXELS] Selected candidate #N` on success.
- If Pexels returns empty, log `⚠ [PEXELS] No results — trying fallback sources…`.
- Only fall through to Pixabay (2nd tier) → free sources (last resort) if Pexels fails.

```ts
// Canonical priority ladder in fetchVisualsForScene:
if (hasPexelsKey) {
  const pexelsResults = await searchPexels(query, ...);
  if (pexelsResults.length > 0) {
    console.log('  ★ [PEXELS] Selected candidate #N for "' + q + '"');
    return pexelsResults[pickIndex];
  }
  console.log('  ⚠ [PEXELS] No results — trying fallback sources…');
}
// 2nd tier: Pixabay (if key set)
// 3rd tier / last resort: Free sources (Wikimedia, Openverse, Internet Archive)
```

## Architecture (the reusable pattern)
1. **Search ALL platforms in parallel, each ISOLATED.** `Promise.allSettled` over per-platform search fns. A throwing provider yields `[]`, never crashes the batch. Add a per-search timeout (e.g. 60s) so a slow provider (Archive.org) can't hang the job.
2. **Pexels-first priority** (see ladder above). Log prominently which provider originates each asset so audits are traceable.
3. **Shared relevance filter** applied to EVERY platform's results BEFORE download. Reject off-topic by:
   - whole-word match on the query (avoid `lion` matching `stone lion` / `sea lion` / `lion king` / `lioness`);
   - brand/commercial token blocklist (`cm|commercial|detergent|shampoo|brand|広告|商品|公式`…);
   - non-Latin title rejection when the query is Latin (non-Latin char ratio > ~0.3) — this is what blocks Japanese "LION" detergent TV commercials.
4. **Download with bounded concurrency** (`mapWithConcurrencyLimit`, default 4–5) so you don't trigger 429s. De-dup candidates by URL.
5. **Candidate failover**: if the top result 429s, try the NEXT on-topic candidate (different source = different host = often not throttled). Collect `good` first, then re-attempt `need*2` extras from the pool.
6. **Per-asset timeout** (video ~90s via `Promise.race`) + **overall job timeout** (e.g. 180s) so the caller NEVER hangs. On timeout, return whatever was collected.
7. **Offline CC0 backstop**: if online yields < requested, generate local placeholder assets with ffmpeg (e.g. a `tools/asset-creator` KenBurns clip / background image). Mark each result `mode: 'offline'` vs `'online'` so reports distinguish real downloads from placeholders. Zero network, zero keys.
8. **Per-file error isolation**: `downloadOneAsset` catches EVERYTHING and returns `{ok:false, reason}` — NEVER throws. Image path: retry/backoff honoring `Retry-After` on 429/5xx (3 tries, 2s·2ⁿ). Video path: route through a hardened download manager with resume + stall guard.

## Concrete shape (TypeScript, condensed)
```ts
export async function searchAllImagePlatforms(topic, n=6) {
  const tasks = [ freeImageAdapter.searchAll(topic,{count:n})
                    .then(s => s.flatMap(x => x.results.map(r => ({source:x.source,title:r.title,url:r.downloadUrl,kind:'image'})))) ];
  if (pexelsKeyPresent()) tasks.push(searchPexelsImages(topic,n).then(imgs => imgs.map(r=>({source:'pexels',title:r.title,url:r.downloadUrl,kind:'image'}))));
  const settled = await Promise.allSettled(tasks);          // isolation
  return settled.flatMap(s => s.status==='fulfilled' ? s.value : []);
}
// download: mapWithConcurrencyLimit(pool.map(h=>()=>downloadOneAsset(h,dir)), concurrency)
// failover: if good.length<want, re-attempt need*2 next candidates
// offline backstop: for i in good.length..want: push generateOfflineVisual(...)
```

## Verification (prove it works — do NOT just announce)
- **Offline unit tests** (node:test, NO network, NO ffmpeg): monkeypatch each provider's `prototype.search` to return fake on-topic / off-topic / throwing results; assert (a) a throwing provider → `[]`, (b) off-topic dropped, (c) `downloadOneAsset` returns `ok:false` on a bad URL instead of throwing. See pitfall about ffmpeg-in-tests.
- **E2E proof**: run the real CLI once; inspect the output dir for actual files + a per-asset `source` report + confirm off-topic count = 0.
- **Live key check**: for a keyed provider, hit the API once (curl/node) and inspect the PARSED body, not just HTTP status (Pexels returns 200 + empty for a bad key — see quirks).

## Pitfalls
- **Pexels returns HTTP 200 with `photos: []` for an invalid key** (no 401 / error body). Detect placeholder keys explicitly (`key === 'your_pexels_api_key_here'` → skip) and gate keyed providers behind a `keyPresent()` check. Always parse the response body to confirm real results.
- **`tsx --test` does NOT support `mock.module`** → old adapter tests fail with "mock.module is not a function". These are PRE-EXISTING repo debt, not your regression. Run with `node --import tsx --test --experimental-test-module-mocks`; even then a real `fs`-mock-reset bug ("Cannot mock 'fs'. The module is already mocked") may remain in legacy adapter tests — fix separately, out of scope.
- **`search_files` (Hermes tool) errors "os error 3" on some repo `src` paths** → use terminal `grep -rn` instead.
- **ffmpeg / child-process work inside `node:test` HANGS the tsx harness** (event loop stays alive → run times out). Keep unit tests pure/logic-only; verify the offline CC0 backstop via the real CLI e2e run, NOT a unit test. (Also: tests that do real network can hang on 429/DNS — always monkeypatch providers on their prototype.)
- **`LlmBridge` (Automated-Video-Generator) exposes `completeJSON`, NOT `generate`** → `bridge.generate(...)` is a TS2339. Use `completeJSON(system, prompt, schemaHint)`.
- **Relevance ranking must be relevance-first, not resolution-first** — otherwise a high-res off-topic result outranks an on-topic one.
- **NASA / MetMuseum are off-topic for most queries** — gate them to only space/art topics; querying them for every keyword is what caused the original "lion → NASA nebula" bug.

## Reference files
- `references/provider-quirks.md` — Pexels endpoint shape + behavior, Wikimedia/Archive 429 + Retry-After, and project-specific gotchas for the Automated-Video-Generator repo.
