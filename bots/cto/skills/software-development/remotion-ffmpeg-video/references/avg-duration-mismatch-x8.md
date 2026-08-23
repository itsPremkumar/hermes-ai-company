# AVG: X8 Duration Mismatch — Debugging & Fix

## The Symptom
Post-render gate X8 fails: `actual Ns vs planned Ms` where `|N-M| > max(2, M*0.05)`.

## Data Flow — Where Durations Live

```
Plan (plan.ts)
  scenes[].durationSec     ← calculated from text via base*weight (e.g. 12s)
  totalDurationSec          ← sum of scenes[].durationSec

Render Manifest (render-manifest.json)
  assets[].durationSec     ← set from plan OR from voiceover duration

Render (render.ts, segmented mode)
  visuals ← manifest.assets (kind !== 'music')
  v.durationSec is set from plan.scenes[idx].durationSec (lines 287-291)
  expectedDur = sum(visuals[].durationSec)

Segment ffmpeg cmd (segmented mode, line 600-603):
  -t <dur>                 ← cap output at dur seconds
  -shortest                ← stop when SHORTEST stream ends
```

## Root Cause Checklist (in order of probability)

### 1. `scene.durationSec` stale after voiceover update
In `pipeline.ts`, the voiceover path (line 471-476) sets `a.durationSec = v.durationSec` but
MISSED setting `scene.durationSec = v.durationSec`. Then render.ts lines 287-291
OVERWRITES the correct `a.durationSec` with the stale `scene.durationSec`.

**Fix:** Add `scene.durationSec = v.durationSec` in the voiceover path.
**Also:** Recalculate `plan.totalDurationSec` after all per-scene updates.

### 2. `-shortest` truncates short video clips
`-shortest` + `-t dur` together: ffmpeg stops at the SHORTEST input stream.
If video is 5s but audio is trimmed to 12s, output = 5s (not 12s).

**Fix:** Replace `-shortest` with `tpad=stop_mode=clone:stop_duration=${dur}` in the
video filter chain, BEFORE `trim`. The `tpad` pads with cloned last frame so there
are always enough video frames for `trim` to reach `dur`.

### 3. `totalDurationSec` not recalculated
After any per-scene duration update, `plan.totalDurationSec` must be recalculated:
```typescript
plan.totalDurationSec = plan.scenes.reduce((acc, s) => acc + s.durationSec, 0);
```
The X8 check uses `totalDurationSec` as `expectedDurationSec`.

### 4. Non-segmented mode (single pass with xfade)
In the non-segmented (single-ffmpeg-call) path, `-t <totalSec>` is used
without `-shortest`. If any scene video is shorter than the trim duration,
the single-pass mode may encode garbage/black for the remainder.

## X8 Gate Check (gate.ts)
```typescript
// line 208
const durOk = dur > 0 && Math.abs(dur - expectedDurationSec) <= Math.max(2, expectedDurationSec * 0.05);
// Tolerance: ±2s or 5%, whichever is larger
```

## Diagnostic Commands
```bash
# Check actual render duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.mp4

# Check what plan says
cat workspace/jobs/job_XXX/plan.json | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));d.scenes.forEach((s,i)=>console.log('Scene',i,':',s.durationSec,'s'));console.log('Total:',d.totalDurationSec,'s')"

# Check asset durations from manifest
cat workspace/jobs/job_XXX/render-manifest.json | node -e "const m=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));m.assets.filter(a=>a.kind!=='music').forEach((a,i)=>console.log('Asset',i,':',a.durationSec,'s'))"

# Verify tpad works
ffmpeg -f lavfi -i testsrc=duration=1:size=640x360:rate=25 -vf "tpad=stop_mode=clone:stop_duration=2,trim=duration=3,setpts=PTS-STARTPTS" -f null -
```

## Key Files
- `src/agentic/orchestrator/pipeline.ts` lines 451-478 — duration updates after voiceover
- `src/agentic/orchestrator/render.ts` lines 287-291 — plan-to-visual duration copy
- `src/agentic/orchestrator/render.ts` lines 536-603 — segmented render + tpad/-shortest
- `src/agentic/pipeline/plan.ts` lines 128-146 — plan duration calculation
- `src/agentic/pipeline/gate.ts` lines 208-214 — X8 check
