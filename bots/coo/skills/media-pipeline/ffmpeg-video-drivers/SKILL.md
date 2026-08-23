---
name: ffmpeg-video-drivers
description: ffmpeg driver pitfalls and tsx one-by-one build pattern.
alwaysApply: false
---

# ffmpeg Video Drivers (one-by-one pipeline builds)

Use this skill whenever you must **build or verify a video from individual assets**
(downloaded clips, Remotion renders, screenshots, images, voice, music) using
`ffmpeg-static` + a small `node --import tsx *.mts` driver — i.e. the AVS
"agentic video" workflow and any mixed-media assembly.

## Core discipline (the AVS one-by-one rule)
Build and verify **one asset at a time**. For each unit: make it → save →
`ffprobe`/frame-extract → `vision_analyze` one frame → **only then** move on.
If a unit fails the visual bar, **reject and regenerate it with an explicit richer
prompt** (proven: a bare Remotion `hud` kind rendered only faint corner text;
regenerating with a detailed prompt + `palette` produced the real HUD). Do NOT
bulk-generate and verify after.

## ffmpeg pitfalls (all hit and fixed in a real run)

### P1 — concat demuxer doubles the path
The concat demuxer resolves list entries **relative to the list file's own
directory**. If the list lives in `input/visuals/` and you write
`file 'input/visuals/build_scene_1.mp4'`, ffmpeg reads
`input/visuals/input/visuals/build_scene_1.mp4` → "No such file or directory".
**Fix: write bare filenames** `file 'build_scene_1.mp4'` (relative to the list).
Repro + fix in `references/ffmpeg-concat-pitfalls.md`.

### P2 — `-vf` lands on the wrong input
When building `pic + audio → out` with `['-i','pic', ..., '-i','aud', '-map','0:v','-map','1:a', '-vf', <filter>, ...]`,
a `-vf` placed *before* the second `-i` attaches to the audio input →
`Option vf cannot be applied to input url ...wav`. **Fix: put `-vf` AFTER `-map`
(output side).** See references file.

### P3 — `-loop` ordering on this static build
`-loop 1 -i img` errors with `Option loop not found`. **Fix: `-loop 1 -framerate 30 -i img -t 4`.**
(`-framerate` before `-i`, not `-r` after.)

### P4 — tall full-page screenshot → thin strip
`scale=1920:1080:force_original_aspect_ratio=decrease,pad=...` on a 1350×18825
full-page screenshot yields an unreadable vertical strip. **Fix: detect tall
(`h > w*1.3`) and scroll-pan instead:**
`scale=1920:-2,crop=1920:1080:0:'min((ih-oh)*t/4,ih-oh)'`.

### P5 — concat needs uniform params
`concat=n=6:v=1:a=1` fails with `Stream specifier ':v' matches no streams` when
inputs differ (e.g. 29.97fps vs 30fps, bt709 vs bt470bg). **Fix: normalize every
scene to identical params** when building: `-r 30 -s 1920x1080 -pix_fmt yuv420p
-c:v libx264 -c:a aac -ar 44100 -ac 1`.

## tsx driver pattern (AVS-specific)
A standalone `*.mts` driver that imports project modules (e.g.
`src/lib/voice-generator.ts`, `src/lib/free-music.ts`) MUST use **dynamic import**:
`const { generateVoiceovers } = await import('./src/lib/voice-generator.ts');`
A static `import { X } from './src/lib/voice-generator.ts'` throws
`does not provide an export named 'X'` even though the export exists (the repo
itself uses `await import(...)` everywhere for these). Use top-level `await` in
the driver (not a `main().catch()` wrapper) — the `main()`-call form can exit 0
with no output under `node --import tsx` in a non-TTY shell.

Run drivers with: `node --import tsx driver.mts </dev/null` (the `< /dev/null`
avoids a `stdin is not a tty` exit-1 in non-interactive shells).

## Verification loop (always-available, no Ollama needed)
The project's built-in `verifyMedia(img, kw, {vision})` routes vision to a local
Ollama (`moondream:latest` @ `localhost:11434`); with Ollama down it returns
`verdict=undefined` and `{vision:{enabled:false}}` does NOT disable it. So:
1. `ffprobe` (resolution/aspect/duration) via offline `verifyMedia` — always works.
2. extract ONE frame: `ffmpeg -y -ss <t> -i in.mp4 -frames:v 1 /tmp/f.png`
3. `vision_analyze(/tmp/f.png, "Does this show X? Any black/corrupt?")` — the
   agent's own vision tool, always available, and what actually proves quality.

## Music + narration mux
`ffmpeg -i video.mp4 -i music.mp3 -filter_complex "[1:a]volume=0.25[bg];[0:a][bg]amix=inputs=2:duration=longest:dropout_transition=0[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -shortest out.mp4`
Use `duration=longest` (not `first`) so music carries the full clip; `volume=0.25`
ducks the bed under voiceover.

## Support files
- `references/ffmpeg-concat-pitfalls.md` — exact error transcripts + fixed command lines for P1–P5.
- `templates/assemble_driver.mts` — known-good top-level-await driver that builds 6 normalized scenes (image/video/tall-screenshot aware) and concats via the demuxer with bare filenames.
