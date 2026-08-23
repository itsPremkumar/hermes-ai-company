---
name: media-pipeline-debugging
description: "Stage-isolation debugging for multi-stage generation pipelines (video, image, audio). Isolate defects by checking each stage independently before fixing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, pipeline, video, media, generation, rendering]
    related_skills: [systematic-debugging, verify-codebase]
---

# Media Pipeline Debugging

## Overview

Automated generation pipelines (video, image, audio) have multiple stages where defects compound. A white frame in the final video could come from: wrong keywords, bad API results, stale cache, wrong asset selection, or broken render filters.

**Core principle:** Isolate each stage independently. Check what each stage actually produced before fixing anything.

## Stage Isolation Technique

### Typical Stages

```
Plan → Fetch → Cache → Download → Assemble → Render
```

For each stage:
- What data **entered** this stage?
- What data **exited** this stage?
- Is the exit data correct?
- If yes → bug is upstream or downstream.
- If no → this stage has the defect.

### What to Check Per Stage

| Stage | Evidence | How to Verify |
|-------|----------|---------------|
| Plan | `plan.json` | Are `searchKeywords` relevant to the topic? |
| Fetch | API response via test script | Does `resultIndex` select different results? |
| Cache | Cache key content | Does the key include all distinguishing params? |
| Download | `md5sum` scene files | Different hashes = different files. Same = bug. |
| Render | `render-manifest.json` | Does each scene reference a different input? |
| Frame | `ffmpeg` frame extraction + `blackdetect` | `RGB(217,218,214)` ≈ white. `RGB(24,23,22)` ≈ content. Use `blackdetect=d=0.3:pix_th=0.15` to find black segments. See `rendered-media-qa` for the `blackframe` vs `blackdetect` trap. |

## Common Pipeline Defects

### 1. Hardcoded Search Keywords
A stage substitutes the user's topic with fixed terms (e.g. "espresso machine" for any topic).
- **Check:** `agent.ts` or planning stage for hardcoded keyword arrays.
- **Fix:** Derive keywords from the topic/title dynamically.

### 2. Index Ignored
The fetch function always returns `results[0]` regardless of `resultIndex`.
- **Check:** The return statement in the fetch function.
- **Fix:** `results[Math.min(resultIndex, results.length - 1)]`.

### 3. Cache Key Too Narrow
The cache key is only `query + type`, so Scene 0 caches `results[0]` and Scenes 1+2 hit the cache before any per-scene logic runs.
- **Check:** The cache key construction.
- **Fix:** Include `_r${resultIndex}` in the cache key.

### 4. Pool Short-Circuit
A pre-fetched topic pool returns immediately from `fetchVisual`, bypassing the per-scene search entirely.
- **Check:** The fetch function's first check — does it return pool results?
- **Fix:** Move pool fallback AFTER the per-scene search ladder.

### 5. ffmpeg Parameter Out of Range
The `eq` filter's `brightness` accepts [-1.0, 1.0] (0=no change). Values ≥1.0 silently clamp to full white.
- **Check:** Style/grade presets for brightness values.
- **Fix:** Use small offsets (±0.03–0.05).

### 6. tsx Cache Staleness
Node.js tsx caches compiled JS. Source edits won't take effect until cache is cleared.
- **Fix:** `rm -rf /tmp/tsx-* ~/.cache/tsx` before re-running.

### 9. Duration "Impossible" Mismatch = Bad Measurement, Not Bad Command
A concat of two 2s clips reporting 5s is almost always a **measurement** bug, not an
ffmpeg bug. Seen in this project: `estimateAudioDurationSafe` used `Math.ceil(4.04)`
→ `5`, which then broke every downstream duration comparison. The ffmpeg command was
correct (verified by `ffmpeg -i out.mp4` → `Duration: 00:00:04.04`; same filter on
clean 2s clips → 4.04s).

**Debug rule:** when a duration looks wrong, probe with `ffmpeg -i <file>` (parse
`Duration:`) as the source of truth BEFORE assuming the ffmpeg command is wrong.
ffprobe is NOT bundled with `ffmpeg-static` — use `ffmpeg -i`, not `ffprobe`.
Full recipe + concat-filter gotchas: `references/ffmpeg-duration-measurement.md`.

**Also:** when measuring freshly-written files, `estimateAudioDurationSafe` style
helpers can mis-read; prefer the direct `ffmpeg -i` parse, and never `Math.ceil` a
duration that feeds comparisons.

### 8. Black Frames in Render Output — Source vs Pipeline Origin

Black frames in the final render can come from three different stages. **Isolate which stage first** using the table below:

| Origin | Symptom | Evidence | Fix |
|--------|---------|----------|-----|
| **Source video** | Black at the START of a scene (fade-in) | `blackdetect` on the downloaded asset shows leading black | Call `trimBlackFrames()` after download (see `rendered-media-qa` for the filter trap) |
| **Render gap** | Black BETWEEN scenes (at scene boundaries) | `blackdetect` on the final MP4 shows black at concat junctions | Fix crossfade/transition overlap logic |
| **Missing/truncated asset** | Entire scene is black | Segment filesize much smaller than siblings (e.g. 158KB vs 769KB) | Check `render-manifest.json` for the asset's `localPath` |

**Quick triage command:**
```bash
# Check source videos for leading black
for s in scene_01 scene_02 scene_03; do
  ffmpeg -i "assets/videos/$s/candidate_1.mp4" -t 5 \
    -filter:v "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep black
done

# Check final render for any black segments
ffmpeg -i "render/job_xxx.mp4" \
  -filter:v "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep black
```



### 7. Duration Mismatch (X8 Gate) — Plan vs Render Mismatch

The rendered video length doesn't match the plan's `totalDurationSec`. This is the most common post-render gate failure.

**Checklist for X8 debugging:**

1. **Verify plan total:** `plan.totalDurationSec` vs sum of `plan.scenes[].durationSec`
   - If they differ → `totalDurationSec` went stale after scene durations were updated

2. **Check manifest durations:** In `res.manifest.assets`, what is each asset's `durationSec`?
   - If still matching plan (12s) instead of voiceover (5.4s) → scene durations weren't propagated to assets, or render.ts:287-291 overwrote them

3. **Inspect segment render args:** Look for `-shortest` and `-t` in the same ffmpeg command
   - `-shortest` + `-t dur` = `min(dur, shortest_stream)` — the EARLIER of the two limits wins
   - If video clips are shorter than `dur`, `-shortest` truncates the segment to the video length

4. **Fix chain:**
   - Ensure `scene.durationSec` is updated from voiceover/actual asset duration
   - Recalculate `plan.totalDurationSec` after updates
   - Replace `-shortest` with `tpad=stop_mode=clone:stop_duration=N` in segment renders
   - `tpad` pads short videos with the last frame, no loop artifacts, no truncation

**Related case study:** `references/duration-mismatch-x8-case-study.md` (full walkthrough of a 21s → 0.7s gap fix)

**Full bug-hunt case log** (8 empirically-found defects + per-video QA one-liners + node:test gotchas): `references/avs-production-hardening-bug-hunt.md`

### 10. Silent Infinite Hang = stream.destroy() Without an Error
A pipeline that goes silent for 30+ minutes (log file mtime frozen, process alive)
is usually an **unsettled promise**, not a slow operation. Seen here: a download
stall guard called `response.data.destroy(); writer.destroy()` with NO argument —
`destroy()` without an error emits only `'close'` (never `'error'`/`'finish'`),
so the `await new Promise(...)` around the stream never settled and acquire hung
forever.
- **Detect:** compare log mtime vs now (`ls -la --time-style=+%H:%M log; date`).
  Silent >10min with a live pid = hung promise, not slow network.
- **Fix:** always `destroy(new Error(...))`, AND add a `'close'` handler that
  rejects if neither finish nor error settled first (belt-and-braces).
- **Sibling check:** any stream-promise wrapper in the codebase with a bare
  `destroy()` in a timer/guard has the same bug — fix the class.

### 11. Frozen "Still" = Kind/Extension Mismatch
`freezedetect=n=0.001:d=2` finding a multi-second freeze on an image scene that
should have Ken Burns motion → check the asset's real extension. Fallback
providers can return a VIDEO (.webm) for an image request; downstream treats it
as a still (first frame only, no zoompan). Fix: reclassify candidate kind by
actual downloaded extension, with a warning.

### 12. Overlapping/Garbled Burned Text at Scene Boundaries
Two captions composited on top of each other = per-scene drawtext `enable`
windows using `gte(t,start)*lte(t,end)` — at a boundary `end === next start` so
BOTH are enabled on the same frames. Windows must be half-open:
`gte(t,start)*lt(t,end)`. Only frame extraction + vision review catches this;
blackdetect/freezedetect/exit codes all pass. Add a source-grep regression test
so `lte()` can't sneak back into dynamic windows.

### 13. Stopword Search Keywords
Topic "The turtle who learned to fly" → visual searches for `"the"` /
`"the close up"` (12s timeouts, junk hits). Any heuristic that picks topic nouns
by word length alone will lead with articles/pronouns. Filter a stopword set
before building search angles; regression-test that no `[Visual:]` tag is
stopword-led and the content noun survives.

### 14. Test Process Won't Exit After All Tests Pass
node:test reports every subtest ok but the process lingers until --test-timeout
kills it (shows as `cancelled 1` on the FILE, pass counts fine). Diagnose with a
preload probe:
```js
// probe-handles.mjs  (node --import tsx --import ./probe-handles.mjs <test>)
setTimeout(() => {
  console.log('ACTIVE:', process._getActiveHandles().map(h=>h.constructor.name));
}, 15000).unref();
```
Usual culprits (all seen in one session): ffprobe/child spawned with
`stdio:['pipe',...]` — the open stdin pipe keeps the child alive (use
`['ignore','pipe','ignore']` + `child.unref()` + tree-kill on timeout); guard
leftover `ChildProcess` in the handle list names the spawn site to fix.

### 15. Infinite Retry

A retry filter that classifies **all AxiosErrors** as transient will retry
downloads that can never succeed — because axios wraps non-retryable errors
(file-too-large, 401/403, bad URL) as AxiosErrors too.

**Signal:** `[retry] download:candidate_1.mp4: attempt 1 failed (maxContentLength size of 157286400 exceeded); retrying in 1017ms` — repeats until pipeline timeout.

**Root cause:** `e.name === 'AxiosError'` catch-all in the retry filter (see
`download.ts:isDownloadRetryable`). Axios throws AxiosError for both transient
(429, 5xx) and permanent (maxContentLength, 404) failures.

**Fix:** Add a non-retryable message/status guard BEFORE the name catch-all:
```typescript
if (typeof e.message === 'string' && /maxContentLength|too large|size exceeded/i.test(e.message)) return false;
```
Full walkthrough: `references/retry-filter-axios-pitfall.md`.

### 16. Windows Process Termination Must Be Synchronous for Port Reuse

On Windows, `spawn('taskkill', ...)` returns before the process tree is fully
dead. The next `ensureBackend()` finds the port still bound and the backend
fails silently (`waiting for backend...` → stuck).

**Fix:** Use `execSync` instead of `spawn` so kill completes before return:
```typescript
require('child_process').execSync(`taskkill /T /F /PID ${pid}`, { stdio: 'ignore' });
```
On Linux/macOS, `SIGKILL` is synchronous by nature; this is Windows-specific.

## Concrete Workflow

```bash
# 1. Check the plan
cat workspace/jobs/<job>/plan.json | jq '.scenes[].searchKeywords'

# 2. Test the fetch function in isolation
npx tsx -e "
const { fetchVisualsForScene } = require('./src/lib/visual-fetcher.ts');
// ... test with different resultIndex values
"

# 3. Check downloaded files
md5sum workspace/jobs/<job>/assets/videos/scene_*/candidate_*

# 4. Check frame content
ffmpeg -ss 1.0 -i output.mp4 -vframes 1 -f rawvideo -pix_fmt rgb24 - | python3 -c "
import sys; d=sys.stdin.buffer.read(); t=len(d)//3
print(f'RGB({sum(d[0::3])/t:.0f},{sum(d[1::3])/t:.0f},{sum(d[2::3])/t:.0f})')
"

# 5. Clear caches after edits
rm -rf /tmp/tsx-* ~/.cache/tsx workspace/cache/
