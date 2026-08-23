# Visual QA: combinatorial render + frame inspection (the loop that caught the orientation + watermark bugs)

This is the exact pattern used in the July 2026 AVS sweep that found two
real defects (orientation-ignored → landscape rendered portrait; opaque-logo
watermark → black box in corner) which `ffprobe`/codec gates missed entirely.

## Why this matters
`ffprobe` reports width/height/duration/codec correctly EVEN WHEN the aspect is
wrong or a black box is stamped in the corner. Automated gates pass. Only a
human-vision pass on extracted frames catches it. So: render MANY combinations,
extract frames, `vision_analyze` them, fix, re-render, re-verify.

## The loop

### 1. Generate distinct, inspectable test assets
Don't rely on network/free-source footage for visual QA — it's non-deterministic.
Generate labeled placeholder images with `sharp` (project already has `sharp`):
```ts
import sharpDefault from 'sharp';
const sharp = sharpDefault as unknown as (b: Buffer) => any;
// SVG gradient + bold label text -> PNG, one per "perspective"
sharp(Buffer.from(svg)).png().toFile(`input/visuals/persp_aerial.png`);
```
Make each image a different color + a big text label ("AERIAL VIEW", "CLOSE-UP",
"WIDE SHOT", …) so a mis-rendered frame is obvious (wrong image, or watermark
box, or wrong aspect).

### 2. Build a combinatorial batch
Cover the cross-product: orientation (portrait/landscape/square) × captions
(burned/karaoke/none) × music (on/off) × several voices, plus one all-tags job
and one `dryRun` control-surface job. ~40–50 jobs is enough to hit every enum
without taking hours. Reference JSON shape: `input/scripts/agentic-scripts.json`
is an array of `{ id, title, script, orientation, voice, captions, backgroundMusic,
localAssets:[...], ... }`. Inline tags go INSIDE `script` text:
`[Visual: persp_aerial.png] [Grade: warm] [Transition: fade] [KenBurns: on]
[CaptionTheme: neon] [Kinetic: on] [JCut: 0.3] [Vignette: on] [Sfx: off]
[MusicIntensity: energetic]`.

### 3. Render in background (voice fallback is slow)
```bash
npx tsx src/adapters/cli/agentic-cli.ts > workspace/tmp/matrix.log 2>&1
# notify_on_complete=true; then poll grep -c "Output:" / DONE_RC
```
Voice stage falls back: speech-backend (torch) fails fast → Edge-TTS → Windows
offline speech. Each job ~30–60s. With ~45 jobs expect ~40 min.

### 4. Extract frames (read paths from a file, NOT $() — spaces break it)
```ts
// extract-frames.ts: read workspace/tmp/mp4list.txt (one mp4 per line)
import { execFileSync } from 'child_process';
const ffmpeg = require('ffmpeg-static');
const ffprobe = require('ffprobe-static').path;
// probe duration, extract 2 frames at 25%/75%
execFileSync(ffmpeg, ['-y','-ss',String(t),'-i',mp4,'-frames:v','1',
  '-vf','scale=480:-1', out], { stdio:'ignore' });
```

### 5. vision_analyze each frame — ask the RIGHT questions
For orientation: "Is the image WIDE (wider than tall, filling frame edge-to-edge,
no big black bars)?" / "Is it a SQUARE?" / "Is it tall PORTRAIT?"
For watermark: "Is there a grey/dark square artifact in the bottom-right corner?
(should be NONE)" and for brand-on: "Do you see the logo, NOT a black box?"
For captions: "Is the burned caption fully inside the frame and legible? Any
duplicate/ghost text? Any raw ffmpeg filter code (fontcolor=, enable=between)
showing as text?"

### 6. Fix + re-verify (one render+vision round per fix)
- Orientation bug: pass `dimensions` from orientation in the CLI render opts.
- Watermark bug: gate on `opts.brand` AND skip when logo `pix_fmt` lacks alpha.
After fixing, re-render ONLY the affected jobs and re-run the vision pass; the
artifact must be gone.

## Gotchas observed this sweep
- `sharp` is a CJS default export — `import sharp from 'sharp'` (not `import * as`).
- `vision_analyze` needs a real local file path; extract frames to
  `workspace/tmp/frames/` first.
- The grey-square "watermark" looked like a UI artifact to vision but was the
  opaque `logo-automation.png` (rgb24, black bg) overlaid at bottom-right.
- `landscape` job producing `720x1280`: ffprobe said "valid video" — only the
  vision frame + the dimension check against the REQUESTED orientation exposed it.
