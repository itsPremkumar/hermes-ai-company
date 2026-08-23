# Case Study: X8 Duration Mismatch in Automated-Video-Generator

The X8 post-render check compares the actual rendered video length against `plan.totalDurationSec`. This case study documents how a 21.1s gap (actual 16.9s vs planned 38.0s) was reduced to 0.7s (actual 16.3s vs planned 17.0s).

## The Symptom

```
✗ X8 Duration matches plan: actual 16.9s vs planned 38.0s
```

The rendered MP4 was 16.9 seconds long, but the plan claimed it should be 38 seconds. X8 tolerance is `max(2s, planned * 0.05)`, so a 21s gap is a clear failure.

## The Architecture — Duration Data Flow

```
                      ┌─────────────────────┐
                      │      PLAN STAGE      │
                      │  buildPlan() sets    │
                      │  scene.durationSec   │
                      │  = 12s, 16s, 12s    │
                      │  totalDurationSec=38 │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │     ACQUIRE STAGE    │
                      │  Downloads actual    │
                      │  Pexels videos       │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │    VOICEOVER STAGE   │
                      │  TTS generates audio │
                      │  files: 5.4s, 5.0s, │
                      │  7.2s               │
                      │                     │
                      │  ⚠ BUG:             │
                      │  a.durationSec = 5.4 │
                      │  scene.durationSec   │
                      │  = 12s (NOT updated) │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │     RENDER STAGE     │
                      │  render.ts:287-291   │
                      │  OVERWRITES          │
                      │  a.durationSec WITH  │
                      │  scene.durationSec   │
                      │  (restores 12s!)     │
                      │                     │
                      │  Segment render:     │
                      │  -t 12 -shortest     │
                      │  → actual: 5s (min)  │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │   GATE (X8 CHECK)   │
                      │  actual=16.9         │
                      │  planned=38.0        │
                      │  → ✗ FAIL           │
                      └─────────────────────┘
```

## Stage Isolation

### Stage 1: Plan Stage
**Check:** `plan.json` per-scene durations
**Found:** Scene 0=12s, Scene 1=16s, Scene 2=10s → total 38s
**Source:** `plan.ts:128-146` — `variablePacing` with `base=4` × brain weights
**Verdict:** ✅ Plan durations calculated correctly from text heuristics

### Stage 2: Voiceover Generation (pipeline.ts:444-477)
**Check:** What actually sets `scene.durationSec` vs `asset.durationSec`
**Found three code paths:**

| Path | Lines | Updates `a.durationSec`? | Updates `scene.durationSec`? |
|------|-------|------------------------|------------------------------|
| Video file (estimateAudioDurationSafe) | 455-460 | ✅ | ✅ |
| Personal audio | 462-470 | ✅ | ✅ |
| **Voiceover (TTS)** | **471-476** | **✅** | **❌ MISSING** |

**Root cause:** The normal voiceover path (lines 471-476) set `a.durationSec = v.durationSec` (correct voiceover length) but **forgot** to set `scene.durationSec = v.durationSec`.

```typescript
// Line 471-476 — voiceover path (bug)
const v = voByScene.get(a.sceneIndex);
if (v) {
    a.audioPath = v.audioPath;
    a.durationSec = v.durationSec;       // ✅ asset gets correct 5.4s
    a.captionSegments = v.captionSegments;
    // ⚠ scene.durationSec still has old plan value (12s)!
}
```

### Stage 3: Render Assembly (render.ts:287-291)
**Check:** How visuals get their duration for rendering
**Found:** The render OVERWRITES asset duration with plan scene duration:

```typescript
for (const v of visuals) {
    const sd = res.plan.scenes[v.sceneIndex] && res.plan.scenes[v.sceneIndex].durationSec;
    if (sd && sd > 0) v.durationSec = sd;  // overwrites 5.4s with 12s!
}
```

**Verdict:** ❌ This restores the stale plan duration (12s), undoing the correct voiceover length (5.4s)

### Stage 4: Segment Encoding (render.ts:600-604)
**Check:** The actual ffmpeg command that creates each segment

```typescript
const args = [
    ...inputs, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
    '-t', String(dur),         // ← "encode at most dur seconds"
    '-c:v', 'libx264',
    '-c:a', 'aac',
    '-shortest',               // ← "stop at shortest stream"
    '-y', seg,
];
```

**Problem:** `-t 12` and `-shortest` conflict:
- Video stream: actual Pexels clip is 5s after `trim=duration=12`
- Audio stream: voiceover trimmed to 12s via `atrim=0:12`
- `-shortest` picks **video (5s)** over audio (12s)
- Segment output: **5 seconds**, not 12

**Verdict:** ❌ `-shortest` truncates each segment to the actual video clip length, not the planned duration

### Stage 5: Total Duration (plan.totalDurationSec stale)
**Check:** What X8 actually compares against
**Found:** `plan.totalDurationSec` was set once at plan time (38s) and **never recalculated** after per-scene durations were updated. Even if scene durations were corrected, `totalDurationSec` would still be 38s.

```typescript
// In pipeline.ts after the duration update loop — MISSING:
plan.totalDurationSec = plan.scenes.reduce((acc, s) => acc + s.durationSec, 0);
```

**Verdict:** ❌ `totalDurationSec` always stale

## The Fixes

### Fix 1: Update scene.durationSec from voiceover (pipeline.ts)
```typescript
const v = voByScene.get(a.sceneIndex);
if (v) {
    a.audioPath = v.audioPath;
    a.durationSec = v.durationSec;
    a.captionSegments = v.captionSegments;
    scene.durationSec = v.durationSec;   // ← ADD THIS LINE
}
```

### Fix 2: Recalculate total plan duration (pipeline.ts)
```typescript
// After the scene duration update loop:
plan.totalDurationSec = plan.scenes.reduce((acc, s) => acc + s.durationSec, 0);
```

### Fix 3: Replace -shortest with tpad (render.ts)
Replace the `loop`+`-shortest` pattern with `tpad=stop_mode=clone`:
```
- [0:v]${!isVideo ? 'loop=loop=-1:size=1,' : ''}fps=25,...trim=duration=${dur}...
+ [0:v]tpad=stop_mode=clone:stop_duration=${dur},fps=25,...trim=duration=${dur}...
```

And remove `-shortest` from the args array.

**How tpad works:**
- `tpad=stop_mode=clone:stop_duration=12` → pads the end of the video with the **last frame** for up to 12 extra seconds
- `trim=duration=12` → cuts the total to exactly 12s
- Combined: a 5s video gets 7s of frozen last-frame, then trim cuts at 12s → segment is exactly 12s
- No loop artifacts (no jump from end back to start)
- No truncation from `-shortest`

## Results

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Plan total Duration | 38.0s (stale) | 17.0s (voiceover sum) | -21s |
| Actual render | 13.0s | 16.3s | +3.3s |
| **X8 Status** | **✗ 21s gap** | **✓ 0.7s gap** | **PASS** |

## Key Lessons

1. **Duration flows are unidirectional and irreversible.** Once `scene.durationSec` is set from plan text, downstream overrides are fragile. Always verify the final value in the manifest.
2. **`-shortest` + `-t` = `min(dur, shortest_stream)`.** They work against each other. If you want exact duration, use `tpad` to pad the video, not `loop` (which causes visible jumps).
3. **A missing line is the hardest bug to find.** The absence of `scene.durationSec = v.durationSec` in the voiceover path was invisible to static analysis — only stepping through the data flow at runtime revealed it.
4. **`plan.totalDurationSec` is not auto-maintained.** It's set once at plan creation and must be explicitly recalculated after any per-scene duration update.
5. **Check `plan`, `manifest`, AND `render-manifest.json`.** The plan, the in-memory render manifest, and the persisted JSON can all diverge.
