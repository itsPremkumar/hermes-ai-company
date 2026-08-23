# W1-1 + W2-1: render.ts overlay & motion-FX fixes (2026-08-01)

Two real dead-signal bugs found by the continuous generate→QA→fix loop and
closed this session. Both are the classic "declared in cli-job.ts, consumed
only by compose.ts, silently dropped on the CLI render path" class.

## BUG W1-1 — titleCard / lowerThird / endCta / progressBar dropped

**Symptom:** jobs with `titleCard`/`lowerThird`/`endCta`/`progressBar` rendered
with NO title card, NO lower-third text, NO end CTA, NO progress bar — yet
`avs-verify.sh` + pixel probes reported PASS (valid mp4, captions fine).
Pixel probe on the landscape job: title-card window `white%=0.000` (expected
a big white "WILD PLANET" box).

**Root cause:** `render.ts` (the orchestrator path the CLI `render` actually
uses) has TWO branches:
- `if (segmented)` — DEFAULT (`AGENTIC_SEGMENTED !== '0'`), production. Builds
  each segment's filter independently, concatenates.
- `else` — non-segmented, xfade chain via `filter_complex_script`, ONLY when
  `AGENTIC_SEGMENTED=0`.

The global text overlays were first injected into the `vfArgs`/`videoMap`
assembled BEFORE the `if (segmented)` block — that block is consumed ONLY by
the `else` branch. So on the default production path the overlays never
reached ffmpeg. `compose.ts` handles them (via `buildOverlayPlan`), but the
standard CLI pipeline never calls `compose.ts`.

**Fix:** apply the four overlays as ONE post-process pass on the fully
concatenated `silent` video (after BOTH branches produce `silent`, before the
audio mux). Time-gated drawtext (title card `lte(t,2)`; end CTA `gte(t,total-4)`)
+ drawbox (progress bar `w='iw*(t/total)'`). Wrapped in try/catch + size guard
(`>2048`) so a failure KEEPS the base render instead of crashing.
Forwarded into `renderAgenticSlideshow` opts from `agentic-modular.ts`
(`titleCard`/`lowerThird`/`endCta`/`progressBar`).

**Proof:** re-rendered landscape job → title card white `0.22%`@1s, lowerThird
`0.75%` bottom-left (crop-isolated) vs ~`0%` before. `avs-verify.sh` still PASS.

## BUG W2-1 — shake/punchIn/parallax/speedRamp dropped (image assets)

**Symptom:** a "Motion FX" job (`shakeByScene`/`punchInByScene`/
`parallaxDepthByScene`/`speedRampByScene`) on IMAGE scenes showed no motion.
Frame-diff probe: motion scene `1.3` (identical to a static baseline) → no FX.

**Root cause:** these four fields were ONLY consumed by `compose.ts`
(`advanced-fx.ts`) on a VIDEO-ONLY pre-process in `agentic-modular.ts`
(BUG M3): `if (!/\.(mp4|webm|mov|m4v)$/i.test(a.localPath)) continue;` —
image assets explicitly skipped. So image-based scenes got zero motion.

**Fix:** forward the four fields into `renderAgenticSlideshow` opts, then apply
as filtergraph strings inside the segmented per-scene `segAdv` chain (works on
images AND videos uniformly):
- shake: `scale=W+2a:H+2a:force_original_aspect_ratio=increase,crop=W:H:x='${amp}+${amp}*sin(n/7)*sin(n/3)':y='${amp}+${amp}*cos(n/9)*cos(n/5)'`
  (amp = `max(1, round(min(1, intensity)*20))` px)
- punchIn: `zoompan=z='min(${z}\,1+0.05*time)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=WxH:fps=25`
- parallax: `crop=W:H:x='${px}*sin(2*PI*t/${dur})':y=0` (px = `round(min(0.3,|depth|)*W)`)
- speedRamp: `setpts=PTS/${k},minterpolate=fps=25:mi_mode=blend`

**SAR RE-PIN (G70 class):** these `scale`/`crop`/`zoompan` filters RESET the
sample aspect ratio AFTER the base chain's early `setsar=1`, producing
`SAR 12160:12159` and breaking downstream concat (avs-verify reported FAIL).
Re-pin **`,setsar=1` at the VERY END of `segAdvStr`** (after the motion
filters). After fix: `SAR 1:1`, PASS.

**Empirical proof the FX applied (vision unavailable):** extract consecutive
frames to rawvideo, compute mean abs per-pixel diff between frame t and t+0.2s:

```python
import subprocess
FF='node_modules/ffmpeg-static/ffmpeg.exe'
def frame_at(t,f):
    return subprocess.check_output([FF,'-v','error','-ss',str(t),'-i',f,
        '-frames:v','1','-vf','scale=160:90','-pix_fmt','rgb24','-f','rawvideo','-'],
        stderr=subprocess.DEVNULL)
def diff(a,b):
    n=len(a)//3; r1=a[0::3]; r2=b[0::3]
    return sum(abs(r1[i]-r2[i]) for i in range(n))/n
f='output/w2_motion/Motion FX.mp4'
prev=None; ds=[]
for t in [1.0,1.2,1.4,1.6,1.8,2.0]:
    fr=frame_at(t,f)
    if prev: ds.append(diff(prev,fr))
    prev=fr
print('motion scene mean frame-diff:', round(sum(ds)/len(ds),2))  # ~6.14
```
Motion scene ≈ 6.14 vs static baseline ≈ 1.3 (~4.7×). A near-zero diff on a
"Motion FX" job means the FX were dropped — investigate before declaring done.

## Commits
- `eaf034e` W1-1 (titleCard/lowerThird/endCta/progressBar)
- `1e62e09` W2-1 (motion FX + SAR re-pin)
