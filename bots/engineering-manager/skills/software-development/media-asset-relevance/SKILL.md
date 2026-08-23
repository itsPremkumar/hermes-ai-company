---
name: media-asset-relevance
description: Build and verify multi-provider free media (image/video) fetchers that return ON-TOPIC assets for a query. Use when a generative pipeline pulls wrong/off-topic stock media for a keyword ("lion" returns NASA space shots or museum art), or when designing/auditing an asset-download subsystem for AI video generation. Covers provider gating by query intent, word-boundary relevance filtering with off-topic compound exclusions, relevance-first (not resolution-first) ranking, and OFFLINE deterministic tests via provider monkeypatching.
---

# Media Asset Relevance — fixing "wrong image / wrong video" downloads

## When this applies
- A video/image generator fetches stock media by keyword and the output shows
  OFF-TOPIC assets (query "lion" → NASA "Lion nebula" space photo, MetMuseum
  "sea lion"/"Lion King" art, "stone lion" statue).
- You are building or auditing a fetcher that aggregates several free providers
  (Wikimedia, Internet Archive, NASA, MetMuseum, Openverse, Pexels, Pixabay…).
- A `searchBest`/ranking step picks by resolution and surfaces a high-res
  OFF-TOPIC image ahead of a real (lower-res) on-topic one.

## COVERS BOTH IMAGE AND VIDEO PATHS
The same three-part fix applies identically to images AND videos:
- **Image path**: `FreeImageAdapter` (`searchAll`/`searchBest`) + legacy
  `visual-fetcher.searchFreeImages`.
- **Video path**: `FreeVideoAdapter` (`searchAll`/`searchAndDownloadFirst`)
  + the legacy `visual-fetcher.fetchVisualsForScene` free-video fallback.
  The video providers (Wikimedia/Archive) search by the raw keyword string,
  so off-topic compounds ("lion king trailer", "lion dance", "sea lion") still
  surface and resolution-ranking still picks wrong content — apply the SAME
  `isOnTopic` filter + relevance-first ranking. Route the legacy fallback
  through `FreeVideoAdapter.searchAll` (which has the filter) instead of
  calling `wikiProvider.search`/`archiveProvider.search` directly (those have
  NO relevance gate).
- **Keep the `isOnTopic` helper IDENTICAL** across both adapters so behavior
  matches. Both must use the same off-topic-compound map and the same generic
  topic allowlist (`nature`, `city`, `background`, `texture`, `abstract`,
  plus `b roll`/`b-roll` for video).

## Root causes (in order of likelihood)
1. **Domain-specific providers queried for every keyword.** NASA = space,
   MetMuseum = art. They return off-topic results for everyday queries.
2. **No relevance filter.** Provider title/keywords not checked against the
   query, so "sea lion"/"lion king" pass through.
3. **Resolution-first ranking.** `sort by width*height` lets an off-topic
   high-res image win. Relevance must come first.

## The fix (3 parts)

### 1. Provider gate by query intent
Only query NASA when the keyword matches a space/astronomy regex
`/space|nasa|galaxy|nebula|star|planet|cosmo|astronom|moon|earth|satellite|telescope|comet|asteroid|universe|milky/`.
Only query MetMuseum for art/heritage regex
`/painting|sculpture|museum|artwork|portrait|renaissance|classical art|artifact|exhibit/`.
Wikimedia + Internet Archive are general photo libraries → always query.

### 2. Relevance filter (whole-word + off-topic compound exclusions)
Require the keyword token to appear as a **whole word** in the asset title
(use `\b` boundaries, NOT naive `.includes()` — naive include makes "lion"
match "stone lion"). Reject known off-topic compounds explicitly:
```ts
const offTopicCompounds: Record<string, RegExp> = {
  lion: /(stone\s+lion|sea\s+lion|lion\s+king|lioness|lion's|lions'\s|mountain\s+lion|city\s+lion)/,
  cat:  /(lion|tiger|bear|wildcat|cat\s+statue)/,
  dog:  /(hot\s+dog|dog\s+statue|sea\s+dog)/,
  bear: /(teddy\s+bear|grizzly)/,
};
```
Filter every candidate: drop if it matches an off-topic compound for its
query token; keep if a `\b<token>\b` match exists. Generic/scope topics
(`nature`, `city`, `background`, `texture`, `abstract`) accept anything.

### 3. Relevance-first ranking
```ts
sorted.sort((a, b) => {
  const aOn = isOnTopic(kw, a.title) ? 1 : 0;
  const bOn = isOnTopic(kw, b.title) ? 1 : 0;
  if (aOn !== bOn) return bOn - aOn;            // on-topic wins
  return (b.width * b.height) - (a.width * a.height); // then resolution
});
```

## Verification (must be OFFLINE + deterministic)
Do NOT rely on live API calls in CI — they are flaky and hide regressions.
Write `node:test` cases that **monkeypatch each provider's `search()`** with
fake results (mix on-topic + off-topic + the NASA/MET off-topic trap), then
assert: (a) off-topic providers excluded for the generic query, (b) off-topic
compounds filtered, (c) `searchBest` top hit is real on-topic. See
`templates/offline-relevance-test.ts`. Run with `npx tsx --test <file>`.
Also add a standalone proof script (e.g. `bin/verify-<topic>-relevance.ts`)
that runs the assertions and exits non-zero on failure.

## Pitfalls
- **Naive `.includes(token)`** matches "stone lion" → use `\b` whole-word.
- **Ranking by pixels only** → off-topic high-res wins → relevance-first.
- **Network tests in CI** → flaky/timeout. Guard with a `skipIfUnreachable`
  helper that `ctx.skip()`s AND throws (because `ctx.skip()` does not abort
  execution in Node 20/22) when the host is unreachable OR
  `process.env.CI === 'true'`.
- **Wikimedia upload servers 429 (rate-limit), not just 403.** A hand-rolled
  proof script using raw `axios.get` gets hammered with HTTP 429 (and 403) on
  rapid repeated downloads — worse when MULTIPLE sibling subagents share the
  same egress IP and all hit `upload.wikimedia.org` at once. Symptom: most image
  downloads fail 429 while the SAME titles are proven on-topic. Fixes:
  (a) send a `User-Agent` header on every GET; (b) backoff+retry on 429/403
  (`sleep(2500 * 2**attempt)`, ~3 tries); (c) throttle ~1.5–6s between requests;
  (d) **Internet Archive (archive.org) downloads are reliable and rarely 429** —
  prefer it when Wikimedia is saturated.
- **Prove relevance at the METADATA level even when downloads are 429-limited.**
  The filter is fully verifiable from `searchAll` returned *titles* alone (every
  returned title must be a whole-word real `<token>` and none may match an
  off-topic compound). If bytes can't land due to rate limits, the metadata scan
  still proves the filter works — report it as the primary acceptance gate,
  downloads as corroborating evidence.
- **`ffprobe-static` ships WITHOUT type declarations** → `import ffprobePath
  from 'ffprobe-static'` errors under strict `tsc`. Match the repo convention:
  `// @ts-ignore` on the line above the import (see
  `src/agentic/operations/probe.ts`).

## Live end-to-end download proof (complements the offline tests)
Offline monkeypatch tests catch regressions; a LIVE run proves the whole chain
`searchAll → download → validate` returns real on-topic media. Recipe in
`references/live-download-proof.md`:
1. `searchAll('lion',{count:10})` (images) / `searchAll('lion',{count:10,
   maxDuration:30})` (videos).
2. Dedup by `downloadUrl`; download each (axios + UA, 429 backoff, throttle).
3. Validate bytes: `ffprobe -v error -show_entries
   stream=codec_type,codec_name,width,height,duration` → assert `codec_type=
   video` + sane dimensions. Videos via the project's `freeVideoDownloader.
   downloadAll([r], dir)` (already resume/stall-guarded).
4. Rate each: `valid` (ffprobe passed) AND `isRealLion(title)` (whole-word, not
   off-topic compound). `offTopic === 0` is the gate.
This caught that the filter is correct but Wikimedia throttles the box — the
metadata scan was the proof, downloads corroboration.

## Project-specific notes (Automated-Video-Generator)
See `references/lion-relevance-bug.md` for the exact reproduction, the `.env`
Voicebox placeholder pitfall, and the commit-at-green operating cadence.
See `references/live-download-proof.md` for the live end-to-end download-proof
recipe and the lion-run findings (zero off-topic leakage; Wikimedia 429 throttle
under shared-IP sibling-agent load, Archive.org reliable).

## Project-specific notes (Automated-Video-Generator)
See `references/lion-relevance-bug.md` for the exact reproduction, the `.env`
Voicebox placeholder pitfall, and the commit-at-green operating cadence.
