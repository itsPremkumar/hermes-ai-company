---
name: media-fetch-relevance-guard
description: Build and verify query→asset relevance gates for keyword-based image/video/stock fetch pipelines (free APIs like Wikimedia / Internet Archive / NASA / MetMuseum / Openverse / Pexels / Pixabay, or any searchAll-style media provider). Use when a download subsystem returns off-topic media ("wrong image/video changed the generated content"), when adding/auditing a media-search provider, or when a searchAll aggregator queries multiple providers per keyword. Covers provider-domain gating, whole-word + compound-exclusion + brand/commercial + non-Latin filtering, relevance-first (not resolution-first) ranking, an offline monkeypatch test pattern, and a TS brace-depth diagnostic for safe edits.
---

# Media Fetch Relevance Guard

## When to use
- User reports "download gave the wrong image/video" / "wrong asset changed the video content".
- A `searchAll` / `searchImages` aggregator queries multiple providers for EVERY keyword.
- Adding a new free media provider (Wikimedia, Internet Archive, NASA, MetMuseum, Openverse, Pexels, Pixabay).
- Auditing relevance of any keyword→media pipeline before/after a video-generation run.

## Root-cause pattern (the bug this fixes)
A query like `"lion"` returns off-topic assets because of THREE independent defects that usually coexist:

1. **Provider over-querying** — the aggregator queries DOMAIN-SPECIFIC providers (NASA = space, MetMuseum = art) for *every* keyword. `"lion"` → "Lion nebula" space photos + "sea lion" / "Lion King" art.
2. **Resolution-first ranking** — `searchBest` / `searchAndDownloadFirst` ranks by pixel count, so a high-res OFF-TOPIC asset beats a lower-res REAL asset.
3. **No relevance gate** — result titles are never checked against the query; compound nouns ("stone lion", "lion king", "sea lion") pass straight through.

## The fix (apply ALL of these)
1. **Provider-domain gating**: only query NASA for space/astronomy keywords; only query MetMuseum for art/museum keywords. General libraries (Wikimedia, Internet Archive) are always queried. This is the single biggest lever — it stops the off-topic provider from ever being queried.
2. **Relevance filter `isOnTopic(keyword, title)`** that REJECTS:
   - Off-topic compound nouns via a per-token `Record<token, RegExp>` (e.g. `lion: /(stone\s+lion|sea\s+lion|lion\s+king|lioness|...)/`).
   - **Brand / commercial tokens**: `/\b(cm|commercial|advert|detergent|shampoo|soap|brand|mylink|ナテラ|広告|商品|公式)\b|ライオン/` — catches "LION" the detergent brand's Japanese TV commercials, which a whole-word match on "lion" still leaks.
   - **Non-Latin titles for Latin queries**: if the query is `/^[\x00-\x7F]+$/` and the title's non-Latin-char ratio `> 0.3`, reject. Kills foreign brand/media clips that aren't the requested English topic.
   - Accepts a title ONLY if it contains the query token as a WHOLE WORD (`\b` boundary), never as a substring.
3. **Relevance-first ranking**: in `searchBest`, sort by `onTopic ? 1 : 0` DESC, THEN by resolution. Never resolution alone.
4. **Apply the filter in every path**: the aggregator (`searchAll`), the ranking (`searchBest` / `searchAndDownloadFirst`), AND any legacy fallback that calls `provider.search()` directly. A legacy `fetchVisualsForScene`-style function often bypasses the adapter and calls providers directly — re-route it through `adapter.searchAll()`.

## Pitfalls (learned the hard way)
- **Naive whole-word match is NOT enough.** "lion" matched the Japanese brand "ライオン" and the English "Lion MyLink startup animation" — both off-topic. You MUST add brand/commercial + non-Latin guards. Verify with a REAL download, not just unit tests on Latin titles.
- **The first fix is usually incomplete — do a REAL end-to-end download.** Pass 1 (compound exclusions) caught "lion king"/"sea lion". Pass 2 (after a real `searchAll` + download + filename inspection) caught the Japanese brand commercials. Off-topic assets only show up at runtime/download, not in metadata-only reasoning.
- **Legacy fallback paths bypass the adapter.** Route them through `adapter.searchAll()` or the filter is silently skipped.
- **Editing nested TS try/for loops breaks braces.** Flattening `for (const p of [a,b]) { try {} catch {} }` into a single `try {}` leaves the outer braces misaligned; `tsc` then reports `'catch' expected` / `'try' expected` far from the real spot. Use `scripts/brace-depth.cjs` to find the exact line where depth first goes negative.
- **Tooling note (Windows/MSYS):** `search_files` can fail with `os error 3` (path not found) on absolute repo paths like `C:/one/.../src/lib/...` even though the file exists. Fall back to `terminal` + `grep -n "pattern" path` — it works reliably.

## Offline test pattern (CI-safe, no network)
Monkeypatch providers so relevance tests run deterministically in CI. See `references/offline-test-pattern.md`. Skeleton:
```ts
const adapter = new FreeVideoAdapter() as any;
adapter.archive = { name: 'archive', search: async () => fakeVideos(['ライオン ナテラ ...', 'Lion MyLink ...', 'LION detergent commercial']) };
adapter.wiki = { name: 'wikimedia', search: async () => fakeVideos(['Male lion resting in savanna']) };
const all = await adapter.searchAll('lion', { count: 10 });
const titles = all.flatMap((s) => s.results.map((r) => r.title));
assert.ok(!titles.some((t) => /ライオン|ナテラ|mylink|detergent/i.test(t)), 'brand clips filtered');
```
For ANY test that DOES hit the network, wrap with `skipIfUnreachable(host, t)` (returns early when the host is down) and additionally skip all such tests when `process.env.CI === 'true'` so CI never flakes on network.

## Verification gate (before claiming done)
- `typecheck` 0, lint 0.
- Offline relevance tests PASS (new + existing).
- REAL end-to-end download: ≥N valid on-topic assets, ZERO off-topic — check filenames + titles + ffprobe/file validity. Report the source breakdown and explicitly confirm no off-topic asset slipped through.

## References
- `references/relevance-filter-recipe.md` — copy-paste `isOnTopic` (image + video) and provider-gating (`shouldQuery`) implementations.
- `references/offline-test-pattern.md` — monkeypatch test skeleton + `skipIfUnreachable` guard.
- `scripts/brace-depth.cjs` — brace-depth diagnostic for verifying TS edits.
