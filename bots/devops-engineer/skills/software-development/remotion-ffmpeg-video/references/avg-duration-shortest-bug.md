# Duration Mismatch: `-shortest` vs `-t` in Segmented Rendering

## Symptom
Post-render check **X8 fails**: `actual 16.9s vs planned 38.0s` (or similar).
The rendered video is much shorter than the plan predicted, even though all assets are real video content.

## Root Cause
In `src/agentic/orchestrator/render.ts` (segmented mode, ~line 601-603), each scene segment is rendered with **both** `-t <dur>` and `-shortest`:

```
-t String(dur)    → "encode at most this much output"
-shortest         → "stop when the shortest stream ends"
```

These work as an **AND** — ffmpeg stops at the **earliest** of the two conditions:

| Input Stream | Planned Duration | Actual Source | `-shortest` wins if… |
|-------------|-----------------|---------------|---------------------|
| Video (Pexels clip) | `trim=duration=12s` | Actual clip = 5s | **Video is shorter** → output = 5s |
| Audio (voiceover) | `atrim=0:12s` | Padded to 12s | |

**Result:** Even though the plan says 12s, the segment is only 5s because the video source ran out of frames. `trim=duration=12` on a 5-second video does NOT add frames — it only caps at 12s. The remaining 7s are gone.

All 3 segments concatenated → sum of actual video lengths (~17s) ≠ sum of planned durations (~38s).

## The Two Competing Systems
1. **Plan duration** (plan.ts): Calculates per-scene durations from text length via `base=4 * brain_weight`. Typical output: 12+16+12 = 40s.
2. **Render duration** (render.ts, segmented mode): Each scene is an independent ffmpeg call. Video `trim=duration=D` + audio `atrim=0:D` + **both** `-t D` and `-shortest` → output = `min(D, shortest_input_stream)`.

## Fix Options (ordered by quality)

### Option A (Best): Remove `-shortest`, loop short videos
In the segment filter chain for VIDEO sources:
- BEFORE: `fps=25,scale=...,trim=duration=${dur}`
- AFTER: `loop=loop=-1:size=999999,trim=duration=${dur}`
The `loop=-1` makes the video infinite, then `trim` cuts at `dur`.
**Downside:** Visible loop boundaries on short clips.

### Option B (Visual quality): Remove `-shortest`, use `tpad`
Instead of `-shortest`, add `tpad=stop_mode=clone:stop_duration=R` to freeze the last frame for the remainder.
**Downside:** Need to know the source video duration to compute `R`.

### Option C (Accuracy): Update plan AFTER acquire
After `acquireAssets` downloads each asset, update:
```typescript
plan.scenes[i].durationSec = Math.max(voiceoverDuration, actualVideoDuration);
```
Then the plan reflects reality and X8 passes naturally.
**Downside:** Requires voiceover to be generated before acquire is complete (currently voiceover = third stage).

## Code Location
- `src/agentic/orchestrator/render.ts` lines 600-603 (segmented mode flag combo)
- `src/agentic/pipeline/gate.ts` lines 208-214 (X8 check with `±2s or 5%` tolerance)
- `src/agentic/pipeline/plan.ts` lines 128-146 (plan duration calculation)

## Affected Runs
All runs using `--backend agent` with Pexels as primary video provider. Pexels videos average 5-15s, while plans expect 12-16s per scene. Every video-first scene with a short clip will trigger this mismatch.
