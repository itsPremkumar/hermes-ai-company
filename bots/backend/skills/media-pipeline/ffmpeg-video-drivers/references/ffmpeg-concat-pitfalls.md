# ffmpeg concat / build pitfalls — exact errors + fixes

All from a real one-by-one AVS build (ffmpeg 6.1.1 static, Windows MSYS).

## P1 — concat demuxer doubles the path
List file at `input/visuals/build_list.txt` containing:
```
file 'input/visuals/build_scene_1.mp4'
```
Command: `ffmpeg -y -f concat -safe 0 -i input/visuals/build_list.txt -c copy out.mp4`
Error:
```
[concat @ ...] Impossible to open 'input/visuals/input/visuals/build_scene_1.mp4'
[in#0] Error opening input: No such file or directory
```
Cause: concat demuxer resolves each `file` entry RELATIVE TO THE LIST FILE'S
DIRECTORY (`input/visuals/`), so the absolute-ish entry is appended again.
Fix: list bare filenames (relative to the list dir):
```
file 'build_scene_1.mp4'
file 'build_scene_2.mp4'
...
```
Also works: absolute Windows paths with forward slashes, e.g. `file 'C:/one/.../build_scene_1.mp4'`.

## P2 — `-vf` on the wrong input
Command (broken): `ffmpeg -y -i pic.mp4 -t 4 -vf "scale=..." -i aud.wav -map 0:v -map 1:a -c:v libx264 out.mp4`
Error:
```
Option vf (set video filters) cannot be applied to input url ...aud.wav --
you are trying to apply an input option to an output file or vice versa.
```
Fix: move `-vf` to the output side, after `-map`:
`... -map 0:v -map 1:a -vf "scale=..." -c:v libx264 out.mp4`

## P3 — `-loop` ordering
Command (broken): `ffmpeg -y -loop 1 -i img.png -t 4 ...`
Error: `Option loop not found.`
Fix: `-loop 1 -framerate 30 -i img.png -t 4` (`-framerate` BEFORE `-i`).

## P4 — tall screenshot → thin strip
Input `s2.png` = 1350×18825 (full-page). With
`scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2`
the result is an unreadable vertical strip (vision confirmed).
Fix: detect tall (`h > w*1.3`) and scroll-pan:
`scale=1920:-2,crop=1920:1080:0:'min((ih-oh)*t/4,ih-oh)'`
(vision confirmed full-width readable Tools page after fix).

## P5 — concat needs uniform params
`[0:v][1:v]...concat=n=6:v=1:a=1` failed with:
```
[fc#0] Stream specifier ':v' in filtergraph description ... matches no streams.
Error initializing complex filters: Invalid argument
```
Cause: inputs had mixed fps (29.97 vs 30) / color ranges (bt709 vs bt470bg).
Fix: normalize every scene at build time:
`-r 30 -s 1920x1080 -pix_fmt yuv420p -c:v libx264 -c:a aac -ar 44100 -ac 1`
Then the demuxer `-c copy` concat works.

## tsx driver import error
Static: `import { generateVoiceovers } from './src/lib/voice-generator.ts'`
Error: `does not provide an export named 'generateVoiceovers'` (export DOES exist).
Fix: `const { generateVoiceovers } = await import('./src/lib/voice-generator.ts');`
The repo itself uses `await import(...)` for these modules everywhere.
