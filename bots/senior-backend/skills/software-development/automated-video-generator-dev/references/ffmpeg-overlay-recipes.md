# ffmpeg overlay/FX recipes — verified working forms (AVS compose.ts)

These were found the hard way during the advanced-signal bake-in. Copy-paste
verified against `ffmpeg-static` (no system ffmpeg) on Windows. Run via
`execFileSync(ff, ['-y','-i',base,'-vf', vf.join(','), out])` — array args, no shell.

## 1. Text escape helpers (CORRECT — the old `esc` was buggy)

```ts
// CORRECT (use these). Old version did `.replace(/:/g,'\\\\:')` which produced
// `\\:` and ffmpeg mishandled it. New version produces a single backslash.
function esc(t: string): string {
  return t.replace(/\\/g, '\\\\').replace(/:/g, '\\:').replace(/'/g, "'\\''");
}
// Escape a comma/colon INSIDE an enable expression so `-vf` doesn't split it:
function escExpr(t: string): string {
  return t.replace(/,/g, '\\,').replace(/:/g, '\\:');
}
```

## 2. Title / lower-third / CTA drawtext (multi-word text is fine IF escaped)

```
drawtext=fontfile='C\:\\Windows\\Fonts\\arialbd.ttf':text='Blue World':fontcolor=white:fontsize=36:x=10:y=H-th-40:box=1:boxcolor=black@0.4:boxborderw=6:enable='gte(t\,1)*lte(t\,4)'
```
- `fontfile` backslashes escaped as `\:`.
- `text` with spaces wrapped in `'...'`; apostrophes inside escaped by `esc()`.
- `enable='gte(t\,1)*lte(t\,4)'` — **comma escaped as `\,`** (RULE 1).
- `y=H-th-40` is fine in drawtext (H = input height there).

## 3. Animated progress bar (VERIFIED working)

```
drawbox=x=0:y=ih-8:w='min(iw,iw*(t/9))':h=8:color=white@0.9:t=fill
```
- `ih`/`iw` NOT `H`/`W` (RULE 2 — drawbox rejects H/W).
- width expr in SINGLE quotes; via argv the quotes reach ffmpeg intact.
- do NOT use `enable=lte(t,9)` — comma splits filterchain AND `min()` clamps at t>=dur.
- set `dur` = clip length (e.g. `fxVisuals.length * 3` s).

## 4. Stabilize = TWO PASS (vidstab)

```
# pass 1 — detect
ff -i in.mp4 -vf "vidstabdetect=shakiness=5:result=transforms.trf" -f null -
# pass 2 — transform (reads transforms.trf)
ff -i in.mp4 -vf "vidstabtransform=input=transforms.trf:smoothing=30" out.mp4
```
Running both in ONE `-vf` yields an empty/broken clip.

## 5. Slideshow from still images (avoid 0.04s single-frame)

```
ff -loop 1 -i img.jpg -t 3 -vf "scale=W:H,format=yuv420p" -c:v libx264 scene_0.mp4
# then concat the per-scene mp4s with -c copy
```

## 6. Audio mix (single vs multi input)

- 1 audio input: `[0:a]acopy[a]` (anullsrc is a SOURCE, not a filter).
- >=2 inputs: `amix=inputs=N:duration=longest`.
- Only push audio inputs that exist AND `size > 0` (empty input → silent failure).

## 7. Bold font = bold FONT FILE, never `fontweight`

`fontweight=700` → "Option 'fontweight' not found". Map weight>=600 to the
bold file: `arial`->`arialbd.ttf`, `georgia`->`georgiab.ttf`, etc. Helper
`resolveFontFile(family, weight)` in compose.ts.

## 8. Color: CSS names raw, hex with 0x

`fontcolor=white` OK ; `fontcolor=0xwhite` FAIL ; `fontcolor=0xffffff` OK.
