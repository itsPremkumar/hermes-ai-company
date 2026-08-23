# Empirical verification recipe (AVS)

All checks use local `ffmpeg-static` / `ffprobe-static` (no Chrome, no network).

## Reusable harness
`workspace/bug-hunt/harness.mjs <job.json> <name>` runs plan → voice →
visuals --no-acquire → render → writes a 2x2 vision grid to
`workspace/bug-hunt/grids/<name>.jpg`. Job contract: bare JSON array with a
`script` field using `[Scene: x] text [Visual: bare.mp4]` lines, optional
`[Transition: ...]` / `[Filter: ...]` tags, and job-level FX fields
(orientation, shakeByScene, speedRampByScene, punchInByScene,
parallaxDepthByScene, emojiByScene, jCutSec, exportAspects, backgroundMusic,
duckDepth, voiceVolume, paletteFilter, captionTheme, kenBurns). Reusable clips
`workspace/bug-hunt/assets/{a,b,c,d}.mp4` are copied into `input/visuals/` by the
harness.

## Frame grid (vision_analyze input)
```bash
FF=./node_modules/ffmpeg-static/ffmpeg.exe
mkdir -p workspace/bug-hunt/grids
# 4 evenly-spaced frames -> 2x2 grid
$FF -y -i "output/<name>/<Title>.mp4" \
  -vf "select='not(mod(n\,$(($(frames-1))))),scale=640:-2' -vsync vfr" \
  -frames:v 4 workspace/bug-hunt/grids/<name>_%03d.png
# (or stitch with hstack/vstack as in the bug-hunt scripts)
```
Then `vision_analyze(image_url=grids/<name>.jpg, question=...)`.

## Per-scene zoom / motion check (proves an FX actually changed output)
Extract frames at scene boundaries and compare:
```bash
for t in 0.2 3.0 4.0 6.3; do
  $FF -y -ss $t -i V -vframes 1 f_$t.png   # -ss AFTER -i = real frame
done
```
Stitch 2x2 and vision-ask "is the right frame more zoomed than the left?".

## ffprobe duration / audio-sync
```bash
FP=./node_modules/ffprobe-static/ffprobe.exe
$FP -v error -show_entries format=duration -of csv=p=0 V.mp4
# audio vs video diff should be < 0.5s
$FP -v error -show_entries stream=codec_type -of csv=p=0 V.mp4   # has audio?
```

## Audio RMS (is music/voice actually audible, not silent?)
```bash
$FF -y -i V.mp4 -af volumedetect -f null - 2>&1 | grep -iE "mean_volume|max_volume"
# mean_volume around -25 .. -30 dB = audible; -91 = silent (bug)
```

## Motion-FX regression probe
`npx tsx workspace/bug-hunt/motion/probe.mts` — emits per-FX output dims +
duration (e.g. numeric ramp 1.5 → 5.32 s from 8 s source; confirms not a no-op).

## Info / gotchas
- Windows `ffmpeg-static` path: `./node_modules/ffmpeg-static/ffmpeg.exe`
- `vision_analyze` needs a REAL file or file:// URL (not a bare Windows path).
- A render that logs an xfade-fallback warning every time = the chained-xfade
  bug signature (fixed); absence of that warning post-fix = good signal.
