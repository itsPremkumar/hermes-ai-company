# ffmpeg luma content check — signalstats trap & rawvideo fix (2026-07-31)

## The bug: validator was dead code on this machine
`src/agentic/pipeline/asset-validators.ts` `checkImageHasContent()` originally ran
`-vf 'signalstats,metadata=print:key=lavfi.signalstats.YAVG:key=lavfi.signalstats.YSTD:data=1'`
and parsed `YSTD` from ffmpeg's log output. On the bundled ffmpeg **6.1.1
(gyan.dev essentials)** this fails TWICE:

1. `data=1` is NOT a valid option for the `metadata` filter in 6.1.1 →
   *"Error applying option 'data' to filter 'metadata': Option not found"* →
   the whole filtergraph fails → `execFileSync` **throws on every call**.
2. Even with `data=1` removed, this build's `signalstats` `metadata=print`
   emits only 29 keys (YMIN/YLOW/YAVG/YHIGH/YMAX/YDIF/SAT*/HUE*/BITDEPTH…) and
   **never prints `YSTD`** — the regex never matches.

Consequence: the `catch` path ran for EVERY image and returned
`{ok:true, stddev:8}` (stddev = the `minStddev` default), so
`isUniformPlaceholderImage()` (`acquire.ts:367,383`) never rejected any
placeholder. A solid swatch could sail through labeled "Source: openverse/pexels".
Symptom seen in the suite: `rejects a solid-color gradient placeholder` failed
with "got YSTD=8" — 8 was the catch default, NOT a measurement.

## The fix (build-independent, verified)
Decode one frame to a tiny grayscale rawvideo buffer and compute the luma
standard deviation in JS. No signalstats, no metadata parsing — works on any
ffmpeg build.

```bash
ffmpeg -hide_banner -i <img> -vf scale=64:64,format=gray -frames:v 1 \
       -f rawvideo -pix_fmt gray pipe:1
# → 4096 bytes, each = luma 0-255
```

```js
const out = execFileSync(ff, ['-hide_banner','-i',p,'-vf','scale=64:64,format=gray',
  '-frames:v','1','-f','rawvideo','-pix_fmt','gray','pipe:1'],
  { stdio:['ignore','pipe','ignore'], timeout:30000, maxBuffer:1e6 });
const n = out.length; let sum = 0;
for (let i=0;i<n;i++) sum += out[i];
const mean = sum/n; let v = 0;
for (let i=0;i<n;i++){ const d = out[i]-mean; v += d*d; }
const stddev = Math.sqrt(v/n) / 2;   // halved → signalstats' 0–~128 scale
```

Measured (2026-07-31): solid-color gradient `0x1e3a8a` → **0.12** (rejected),
`mandelbrot` → **21.9** (accepted). `MIN_CONTENT_STDDEV = 8` keeps its meaning
on the halved scale. Regression tests: `tests/agentic/pipeline/asset-validators.test.ts`
4/4 pass.

## When the signalstats form IS still used elsewhere
The `metadata=print` lines from signalstats go to **stderr** with a
`[Parsed_metadata_1 @ ...]` prefix on this build (not stdout) — if any code
reads them, capture stderr (or use `2>&1`) and note the 29-key limitation.

## Open observations from the 2026-07-31 test batch (UNRESOLVED — investigate next)
- `⚠ [DOWNLOAD] Failed to download https://videos.pexels.com/...mp4: ENOENT ...
  stat '<job>/assets/videos/scene_02/candidate_1.mp4'` — download reports
  success but the file stat fails; possible path/extension mismatch in
  `downloadMedia` (candidate path vs written filename).
- `⚠ Loop skipped: Loop failed (exit 4294967274)` — ffmpeg loop (exit -22
  EINVAL) on music looping; falls back to stock ccmixter gracefully, but the
  loop path is broken.
