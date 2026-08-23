# ffmpeg / ffprobe post-render + source verification recipes (AVG)

Concrete, copy-paste recipes behind `src/agentic/video-analyzer.ts` and
`src/agentic/asset-checks.ts`. All deterministic, offline, no AI keys.

## 1. Black / freeze frame detection (X10 / X11)
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
# black frames longer than 0.3s
"$FFMPEG" -i clip.mp4 -filter:v "blackdetect=d=0.3:pic_th=0.10:pix_th=0.15" -f null -
# frozen (near-identical) frames longer than 0.5s
"$FFMPEG" -i clip.mp4 -filter:v "freezedetect=n=0.003:d=0.5" -f null -
```
Stats print to **STDERR** (parse both stdout+stderr). A `testsrc` clip has black
borders -> blackdetect CORRECTLY fires (so a synthetic test clip is expected to fail X10).

## 2. Audio loudness + clipping (X12 / X13)
```bash
"$FFMPEG" -i clip.mp4 -filter:a volumedetect -f null - 2>&1 | grep -E "max_volume|mean_volume"
# good clip:  max_volume: -17.7 dB   mean_volume: -21.1 dB
# broken:     max_volume: -999.0 dB  (volumedetect never ran -> fix: use -filter:a, see P17)
```
Pass rule: `-60 dB < peak <= 0 dB` and `peak < -1.0 dB` (no clipping).

## 3. Dimensions + codec (X14 / X15) -- prefer ffprobe
```bash
PROBE=$(node -e "const m=require('ffprobe-static');console.log(typeof m==='string'?m:m.path)")
"$PROBE" -v error -show_entries stream=width,height,codec_name,pix_fmt,color_range \
  -of default=noprint_wrappers=1 clip.mp4
# width=720  height=1280  codec_name=h264
```
Fallback when ffprobe absent: parse `ffmpeg -i` STDERR for `(\d+)x(\d+)` + `Video:\s*(\w+)`.
NOTE: `ffprobe-static` exports `{path}`, NOT a string -- read `.path` (P15).

## 4. Source-asset checks (I4 / I5 / V4 / V5 / V6 / I7)
`probeAsset(filePath)` -> `{width,height,durationSec,aspect,codec}`.
`checkSourceAsset(filePath, {kind,minWidth,targetAspect,sceneNeedSec})` returns
`SourceCheckResult[]` (id I4/I5/V4/V5/V6 + pass/detail).
`findDuplicates(paths[])` -> groups sharing a `sha256` of their first 256KB (I7).

## 5. Offline unit-test pattern (no network, no real render)
Generate a fixture with ffmpeg, then assert:
```ts
import { execFileSync } from 'child_process';
const ffmpeg: string = require('ffmpeg-static');
execFileSync(ffmpeg, ['-y','-f','lavfi','-i','testsrc=size=720x1280:rate=25:duration=4',
  '-f','lavfi','-i','sine=frequency=440:duration=4','-c:v','libx264','-c:a','aac','-shortest', clip], {stdio:'ignore'});
// testsrc has black borders -> expect X10 to FAIL (correct), all other X pass.
```
For a genuinely clean clip: this ffmpeg build rejects `mandelbrot=size=`/`s=...` forms;
`testsrc=size=WxH:rate=R:duration=D` works. To assert "all X pass", generate a NON-black
moving clip (e.g. overlay a moving box on testsrc) or accept X10 as the expected failure on testsrc.
