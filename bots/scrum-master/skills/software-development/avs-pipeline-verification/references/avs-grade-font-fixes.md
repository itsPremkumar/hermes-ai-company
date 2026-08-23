# AVS Grade + Font Fixes (Wave 5, 2026-08-01)

Repro recipes + exact filter strings for the grade dead-signal fix (W5-1) and
the `colorbalance`/`format=gray` slowness pitfall (G32).

## W5-1: grade presets silently no-op + job-level grade not forwarded

### Symptom
A job with `"grade":"noir"` (or per-scene `[Grade: sunset]`) produced output
visually identical to `neutral` — no grayscale/warm/cyan shift. `avs-verify.sh`
passed (valid mp4), so the no-op was invisible to static gates.

### Root cause (two sub-defects)
1. `gradeFilter(kind)` in `src/agentic/ai/style-engine.ts` only handled
   `warm|cool|cinematic|vivid|neutral`; `noir|sunset|cyberpunk` hit `default`
   → harmless `eq=contrast=1.02:saturation=1.05`.
2. `computeStylePlan(res.plan, { preset, kinetic })` in `render.ts` never
   received `opts.grade`, so a job-level `grade` was ignored entirely (only
   per-scene `[Grade:]` tags reached the style plan, and only the 5 known
   grades).

### Fix
- Extend `export type GradeKind` and `const GRADES` with `noir|sunset|cyberpunk`.
- In `render.ts`, forward the job grade as a `gradeBias` (one entry per scene):
  ```ts
  const styleOpts: any = { preset: opts.preset ?? 'cinematic', kinetic: opts.kinetic };
  if (opts.grade) {
    const n = (res.plan.scenes ?? []).length || visuals.length;
    styleOpts.gradeBias = Array.from({ length: n }, () => opts.grade as any);
  }
  const stylePlan = computeStylePlan(res.plan, styleOpts);
  ```
- Add `grade?: string;` to the `renderAgenticSlideshow` opts interface and
  forward `grade: job.grade ?? meta.grade` from `agentic-modular.ts`.
- Implement the 3 grades (see G32 for strings — use `eq`+`hue`, NOT `colorbalance`).

### Empirical proof (vision unavailable)
Grayscale = R≈G≈B on a sampled frame. Use `frame_probe.py` luma or a rawvideo
R/G/B check: a noir scene shows R-G and R-B near 0; a neutral scene that was
supposed to be noir shows a normal color spread (proof the no-op happened).

## G32: `colorbalance` / `format=gray` pathological slowness on gyan.dev CPU build

### Symptom
A 3.7s scene with `[Grade: sunset]` (using `colorbalance`) burned 550 CPU-seconds
in a single ffmpeg and never completed. `format=gray` (noir) took 252+ CPU-sec/scene.
Both look like a hang; they are extreme slowness on this ffmpeg-static build.

### Fix — replacement filter strings (SIMD/YUV-native, fast)
```ts
case 'noir':      return 'hue=s=0,eq=contrast=1.35:brightness=-0.02';
case 'sunset':    return 'eq=contrast=1.05:saturation=1.3:gamma=0.95,hue=h=18:s=1.15';
case 'cyberpunk': return 'eq=contrast=1.15:saturation=1.4,hue=h=-22:s=1.25';
```
`hue=s=0` desaturates in YUV (no RGB→gray colorspace conversion). `hue=h=` rotates
hue for warm/cool tints. Both are cheap vs `colorbalance` (which mallocs heavily
and stalls) and `format=gray` (slow RGB→gray path).

### Standalone speed test (proves the fix is fast)
```bash
# fast path (hue=s=0)
ffmpeg -v error -i input/visuals/ai_city_night.jpg \
  -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,hue=s=0,eq=contrast=1.35:brightness=-0.02" \
  -t 8 -c:v libx264 -pix_fmt yuv420p -y /tmp/noir.mp4
# slow path (format=gray) — do NOT use
ffmpeg -v error -i input/visuals/ai_city_night.jpg \
  -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,format=gray,eq=contrast=1.35" \
  -t 8 -c:v libx264 -pix_fmt yuv420p -y /tmp/noir_slow.mp4
```
Both finish in seconds standalone, but in the full pipeline the slow path
compounds across scenes and stalls the box. Trust the standalone encode but
verify the FULL pipeline completes (poll `UserModeTime`, see below).

## Slow-vs-hang diagnosis (this box)
```bash
# sample 1
wmic process where "name='ffmpeg.exe'" get ProcessId,UserModeTime /format:list
# wait ~30s, sample 2 — if UserModeTime climbed, it's slow-but-progressing
```
- Climbing `UserModeTime` + growing output file = slow render, let it finish.
- Frozen/non-climbing value, OR node alive with NO `ffmpeg.exe` (G10) = true hang.
- Never conclude "hang" at the 60s `process(wait)` cap during a normal render.

## Do NOT use `-threads 1` as the G6 fix here
Adding `-threads 1` to `gpuExtra()` made encodes ~4-5 min/scene on the old AMD
APU and did NOT fix the `colorbalance` stall. The real driver was the heavy
filter. Remove `colorbalance`/`format=gray` first; default threads render fine
at ~690 MB free on this 6 GB box.
