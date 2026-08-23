# Asset-Diversity Debugging: Same Video Across All Scenes

When every scene in a multi-scene video uses the **identical source file**, it's
usually a pipeline short-circuit or cache-key collision, NOT a Pexels search issue.

## Quick Diagnosis

```bash
# Check if all scenes share the same asset
md5sum workspace/jobs/*/assets/videos/scene_*/candidate_1.mp4
```

If all MD5s match, continue below. If they differ, diversity is working — look elsewhere.

## Three-Layer Bug Pattern (encountered together in one production pipeline)

### Layer 1 — Per-scene `resultIndex` never used

The fetch function declares `resultIndex: number = 0` but ALWAYS returns
`videos[0]` from the API response:

```typescript
// BROKEN — ignores resultIndex
if (videos.length > 0) {
    return videos[0]; // same video for EVERY scene
}

// FIXED — picks a result per scene
const pickIndex = Math.min(resultIndex, videos.length - 1);
return videos[pickIndex];
```

Apply to ALL provider paths: Pexels video, Pixabay video, free video sources,
and the image fallback path.

### Layer 2 — Cache key does not include `resultIndex`

The cache key is built only from the search query + orientation + type. When
Scene 0 fetches with `resultIndex=0` and caches `videos[0]`, Scene 1's fetch
with `resultIndex=1` hits the same cache key and returns `videos[0]` **before
the result-index logic can run**.

```
// BROKEN — same cache key for every scene
const cacheKey = buildCacheKey(query, orientation, type);

// FIXED — per-scene cache key
const cacheKey = `${buildCacheKey(query, orientation, type)}_r${resultIndex}`;
```

### Layer 3 — Pool short-circuits the per-scene search

The pipeline's `deps.fetchVisual` checks a **shared topic image pool** FIRST.
If the pool has ANY entries (built from a single topic-noun search), it returns
immediately — **bypassing the entire ladder search with resultIndex**.

```
// BROKEN — pool checked before per-scene search
const pool = await getImagePool();
if (pool.length > 0) {
    return pool[sceneIndex % pool.length]; // always pool[0] when pool has 1 entry
}

// FIXED — per-scene search runs FIRST, pool is a fallback
// (move pool fallback AFTER the ladder search)
```

## Debugging Workflow

### 1. Confirm the symptom
```bash
# All scene assets same?
md5sum assets/videos/scene_*/candidate_1.mp4

# Same file size?
stat --format="%n: %s bytes" assets/videos/scene_*/candidate_1.mp4
```

### 2. Check the cache
The asset cache lives at `workspace/cache/<sha256(url)><ext>`. List it:
```bash
ls -la workspace/cache/
```

Each unique SHA256 file = one unique URL downloaded. If only 1-2 files exist,
the API returned few unique results or the cache key collision is active.

### 3. Check the pool short-circuit
Add a log line at the pool return point and re-run a single scene:
```bash
npx tsx bin/agentic-run.ts --topic "..." --title "..." ...
```

Look for the log output — does it say "fetchVisual" (goes through ladder) or
is there no log at all (hit the pool early-return)?

### 4. Isolate the fetch function
Write a small test harness that calls `fetchVisualsForScene` directly with
the same parameters each scene would use:
```typescript
for (let i = 0; i < 3; i++) {
    const r = await fetchVisualsForScene(keywords, true, 'portrait', undefined, i);
    console.log(`scene ${i} -> URL: ${r?.url}`);
}
```
If this shows different URLs but the pipeline produces the same file, the
pool short-circuit is the culprit (Layer 3).

## Prevention Checklist

- [ ] Every fetch function that accepts `resultIndex` actually USES it with
      `Math.min(resultIndex, results.length - 1)` on every return path
- [ ] Cache keys include `resultIndex` (or scene index) so different scenes
      can cache different results
- [ ] Pool/flags checked ONLY as a LAST RESORT fallback, not before the
      per-scene targeted search
- [ ] No API fetcher returns at most 1 result when more are available
      (`per_page` parameter set high enough)
