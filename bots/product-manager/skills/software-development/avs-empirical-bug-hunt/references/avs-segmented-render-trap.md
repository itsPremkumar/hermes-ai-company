# G30 — Segmented vs non-segmented render branch (`render.ts` internal two-path trap)

## The trap
`renderAgenticSlideshow()` in `src/agentic/orchestrator/render.ts` has TWO code
paths that both produce a concatenated `silent` video:

1. `if (segmented)` — the **DEFAULT** (runs unless `AGENTIC_SEGMENTED=0`). It loops
   over every clip (intro / scenes / outro), builds a **per-segment** filter graph
   (caption / kinetic / emoji / per-scene advanced FX + grade), encodes each to
   `_seg_*.mp4`, then concatenates with `-fflags +genpts -f concat -c copy` into
   `silent`. It does **NOT** reference the global `vfArgs` / `videoMap` accumulated
   before the branch.
2. `else` (non-segmented) — assembles ONE big `filter_complex` from `vfArgs` /
   `videoMap` (captions, kinetic, vignette) and encodes directly.

**Consequence:** any global overlay (title card, lower-third, end CTA, progress bar)
you append to `vfArgs` / `videoMap` BEFORE the `if (segmented)` block is consumed
ONLY by branch 2. On the default production path it is **silently dropped** — the
video renders with no title card / lower-third and frame probes show 0% text
pixels, with **NO ffmpeg error**.

## Root cause this session (BUG W1-1)
`titleCard` / `lowerThird` / `endCta` / `progressBar` were declared in `cli-job.ts`,
forwarded through `buildPipelineRequest` → `PipelineRequest` (`types.ts`), and
forwarded again into `renderAgenticSlideshow` opts in `agentic-modular.ts` — but
`render.ts` never burned them (only `compose.ts`'s `buildOverlayPlan` did). So the
standard CLI `render` silently dropped all four.

## The fix (verified pattern)
1. Forward the four fields job → opts in `agentic-modular.ts` (mirror `intro` / `outro`).
2. Add them to the `render.ts` opts interface.
3. **Apply them as a SINGLE post-process pass on `silent`**, AFTER both branches
   produce it and BEFORE the music mux:
   - compute `totalDur = introDur + Σ scene durations + outroDur`
   - build a `string[]` of `drawtext` / `drawbox` filters (time-gated with
     `enable='lte(t\,N)'` / `enable='gte(t\,N)'` for title card / end CTA; lower-third
     spans the whole video; progress bar is a `drawbox` with `w='iw*(t/totalDur)'`)
   - re-encode: `ffmpeg -i silent -vf <joined> -c:v libx264 -pix_fmt yuv420p -c:a copy -y _av_ol_<job>.mp4`
   - guard: require success + size > 2048 bytes, else keep base `silent`; wrap in
     try/catch so a bad filter never kills the render.
   This guarantees overlays survive BOTH branches and span the whole timeline correctly.

## How to confirm a fix like this empirically (no vision model)
- Pixel-probe frames via Python + ffmpeg rawvideo (see `scripts/frame_probe.py`):
  - title card at t≈1s should show white/bright text pixels (white% > 1).
  - lower-third at any t>1s should show text pixels.
  - a `[Filter: bw]` scene → per-channel means R≈G≈B (maxdiff < 8).
  - a `[Filter: sepia]` scene → R − B > 5 (warm tint).
- Run `bash scripts/avs-verify.sh <final.mp4> "C:/.../verify"` for the
  black/freeze/volume/SAR/stddev gate.

## Don't repeat this mistake
When adding ANY global (whole-timeline) overlay to `render.ts`, never inject it into
the pre-`if(segmented)` `vfArgs` / `videoMap` — it only affects the non-segmented
branch. Burn it post-concat on `silent`, or per-segment only if it is genuinely
per-scene.

## Trap 2 — per-scene motion FX dropped for IMAGES (BUG W2-1, 2026-08-01)
`shakeByScene` / `punchInByScene` / `parallaxDepthByScene` / `speedRampByScene` were
only consumed by `compose.ts` (`advanced-fx.ts`). The `agentic-modular.ts` M3
pre-process calls those appliers but **`continue`s on non-video assets**
(`if (!/\.(mp4|webm|mov|m4v)$/i.test(a.localPath)) continue`), so image-based CLI
jobs get ZERO motion. Frame-diff probe: ~1.3 (same as a static scene).

**Fix:** forward the four fields into `renderAgenticSlideshow` opts, and inside the
segmented loop add them to `segAdv` (the per-scene filter chain, ~line 863) inside
`if (clip.kind === 'scene')` — so they apply to images AND videos uniformly:
- shake: `scale=${W+a*2}:${H+a*2}:force_original_aspect_ratio=increase,crop=${W}:${H}:x='${a}+${a}*sin(n/7)*sin(n/3)':y='${a}+${a}*cos(n/9)*cos(n/5)'` (a=1..20px)
- punchIn: `zoompan=z='min(${z}\\,1+0.05*time)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${W}x${H}:fps=25`
- parallax: `crop=${W}:${H}:x='${px}*sin(2*PI*t/${dur})':y=0`
- speedRamp: `setpts=PTS/${k},minterpolate=fps=25:mi_mode=blend`
Proof: frame-diff 6.14 vs 1.3 static baseline (~4.7× more motion).

**SAR regression (G70):** those filters reset SAR after the base chain's `setsar=1`
→ `SAR 12160:12159`, which breaks the concat-copy join (avs-verify reports FAIL).
Re-pin at the end of the segment chain:
```ts
const segAdvStr = segAdv.length ? ',' + segAdv.join(',') + ',setsar=1' : '';
```

## Trap 3 — multilingual captions = tofu for non-CJK (BUG W3-1, 2026-08-01)
`pickFontArg` in `render.ts` only special-cased CJK (msyh.ttc / NotoSansCJK). Hindi
(Devanagari), Tamil, Arabic, etc. render as **boxes on Arial** — no error, just tofu.
Fix: detect Indic/Arabic codepoint ranges and fall back to a capable font, mirroring
the CJK branch:
```ts
const INDIC_ARABIC_RE = /[…\u0600-\u06FF \u0900-\u097F \u0980-\u09FF \u0B00-\u0B7F \u0B80-\u0BFF …]/;
const SCRIPT_FONT = process.platform === 'win32'
  ? 'C:/Windows/Fonts/Nirmala.ttf' : '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf';
// in pickFontArg: else if (INDIC_ARABIC_RE.test(text) && fs.existsSync(SCRIPT_FONT)) return `fontfile='${SCRIPT_FONT}'`;
```
Proven: standalone `ffmpeg drawtext fontfile=Nirmala.ttf text='सूर्य'` → 214 real
glyph pixels (not tofu). **General rule:** any new script block needs its own font
fallback added to `pickFontArg`, or it tofus. Include the G30 post-concat overlay,
segAdv motion, and font-fallback checks in the "is this field a dead signal on the
CLI path?" audit.
