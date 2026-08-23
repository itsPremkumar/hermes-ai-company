# Case Study: Automated-Video-Generator White Frames & Same-Video Bug

This case study documents a real debugging session of the `Automated-Video-Generator` project. The output showed all three scenes as the same blank/white video.

## The Symptom

- All three scenes in the output video showed white frames (RGB ~217,218,214)
- All three scenes appeared to use the SAME video asset
- Expected: three different dark-themed space videos

## Stage Isolation

### Stage 1: Plan
**Check:** `plan.json`  
**Found:** Scene keywords were correct ("solar system", "planets orbit", "saturn rings")  
**Verdict:** ✅ Plan stage OK

### Stage 2: Asset Fetch
**Check 1:** `agent.ts` hardcoded keywords  
**Found:** `agent.ts` lines 112-119 had hardcoded coffee keywords (`"espresso machine"`, `"barista cafe"`, `"latte art"`) regardless of topic  
**Fix:** Replaced with dynamic topic-derived keywords  
**Verdict:** ❌ Fix applied — but white frames persisted

**Check 2:** `fetchVisualsForScene` result index  
**Found:** Function always returned `videos[0]` — `resultIndex` parameter was never used  
**Fix:** Changed to `videos[Math.min(resultIndex, videos.length - 1)]`  
**Verdict:** ❌ Still same video (because of cache — see next)

**Check 3:** Cache key  
**Found:** Cache key was `query + type` — no `resultIndex` suffix. Scene 0 cached `videos[0]`, Scenes 1+2 hit the cache before resultIndex logic ran.  
**Fix:** Added `_r${resultIndex}` to cache key  
**Verdict:** ❌ Still same video (because of pool short-circuit — see next)

### Stage 3: Download
**Check:** `md5sum scene_*/candidate_*`  
**Found:** All three files had identical MD5 hashes  
**Verdict:** Confirmed same file — bug upstream

### Stage 4: Render
**Check 1:** Render manifest  
**Found:** All scenes had different `input` paths in `render-manifest.json`  
**Verdict:** ✅ Manifest correct — but if actual files are the same, render can't fix it

**Check 2:** Grade brightness values  
**Found:** `style-engine.ts` had `brightness=1.04`, `1.0`, `0.97` — all at or above the ffmpeg max of 1.0 (full white)  
**Fix:** Changed to small offsets: +0.05 warm, -0.04 cool, -0.03 cinematic  
**Verdict:** ❌ Fixed white frames — but scenes still had same video

### Stage 5: Pipeline fetchVisual
**Check:** The `fetchVisual` function in `pipeline.ts`  
**Found:** It checked the topic image pool FIRST. If the pool had ANY entries (one video fetched for the topic), it returned immediately — **bypassing the entire per-scene Pexels search with resultIndex**  
**Fix:** Reordered so the targeted ladder runs FIRST, pool is only a fallback  
**Verdict:** ✅ After this fix, all three scenes got DIFFERENT videos

## The Root Causes (3 separate bugs)

| # | Bug | File | Fix |
|---|-----|------|-----|
| 1 | Hardcoded coffee keywords | `agent.ts:112-119` | Dynamic topic-derived keywords |
| 2 | Grade brightness out of ffmpeg range | `style-engine.ts` | Valid [-1.0, 1.0] values |
| 3a | videos[0] always returned | `visual-fetcher.ts:1055` | resultIndex-based selection |
| 3b | Cache key too narrow | `visual-fetcher.ts:1035` | Add _r${resultIndex} suffix |
| 3c | Pool short-circuits Pexels search | `pipeline.ts:241-258` | Pool is fallback, not first check |

## Key Lessons

1. **Check the cache key first.** If it doesn't include distinguishing parameters, the cache gives the same result to everyone regardless of per-scene logic.
2. **Test fetch functions in isolation.** `npx tsx` directly caught the cache key bug that the full pipeline masked.
3. **The pool short-circuit is the hardest to spot.** A seemingly innocent "if pool has items, return immediately" bypasses all per-scene logic.
4. **ffmpeg silently clamps out-of-range parameters.** No error, no warning — just wrong output.
5. **Each fix reveals the next bug.** After fixing the cache key, the pool bug became visible. After fixing the pool, the render grade bug was visible.
