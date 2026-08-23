# One-by-one agent-driven video build (AVS showcase, 2026-07-27)

Proven end-to-end run: 8 scenes (3 agent-authored Remotion, 4 Pexels stock, 1 GitHub
screenshot) → Kokoro voice → hand-written manifest → 52s 16:9 render, all frames
vision-verified, delivered to Downloads. Zero use of the batch pipeline.

## Driver scripts (put in `tmp_agent_run/`, run with `npx tsx`)

### 1. One Remotion scene from hand-authored TSX
```ts
import mod from '../src/agentic/media/hermes-remotion-controller.ts';
const { runRemotionController } = (mod as any).runRemotionController ? (mod as any) : (mod as any).default ?? mod;

const code = `
import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
export const Scene0: React.FC = () => { /* component named Scene<index>! */ };
`;
const res = await runRemotionController(
  [{ index: 0, text: 'AVS title reveal', kind: 'logo', code, durationInFrames: 180 }],
  { jobId: 'avs_showcase', maxRetries: 2, fps: 30, width: 1920, height: 1080, allowFallback: false },
);
// status:'generated' → file at input/visuals/<jobId>_s<index>.mp4
```
Notes:
- Component export MUST be named `Scene<index>` (controller uses compId `Scene${index}`).
- kind must be from MotionKind union (`logo`, `infographic`, …) — `'intro'` fails typecheck.
- ~1080p h264 output; 6s = 180 frames @30fps. First-attempt success for plain
  AbsoluteFill + spring/interpolate compositions; keep to Arial/inline styles.

### 2. One stock video (limit=1)
```ts
import 'dotenv/config';
import * as fs from 'fs';
import mod from '../src/lib/visual-fetcher/search.ts';
const { searchVideos } = (mod as any).searchVideos ? (mod as any) : (mod as any).default ?? mod;
const vids = await searchVideos(process.argv[2], 1, 1, 'landscape');
const r = await fetch(vids[0].url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
fs.writeFileSync(process.argv[3], Buffer.from(await r.arrayBuffer()));
```
Then per asset: ffprobe (`D=$($FF -i f.mp4 2>&1); echo "$D" | grep -E 'Duration|Video'`),
extract ONE frame `-ss 2 -frames:v 1 -vf scale=1280:-1 out.jpg` (scale mandatory —
vision_analyze times out on 4K PNGs), vision-check, only then next asset.

### 3. One music track
```ts
import mod from '../src/lib/free-music.ts';
const m = (mod as any).default ?? mod;
const res = await m.resolveFreeBackgroundMusic('upbeat electronic technology background',
  { intensity: 'mid', durationSec: 62 });
// res.localPath → workspace/cache/free-music/processed/<id>_processed.mp3 (real 60s mp3)
```

## GitHub-page screenshot → 16:9 still
browser_navigate + browser_vision → tall PNG (e.g. 1247×17013). Crop the header band:
`ffmpeg -i raw.png -vf "crop=1247:701:0:60,scale=1920:1080:flags=lanczos" out.png`
(701 = 1247*9/16; offset 60 skips the GH nav bar). Vision-verify repo name/stars legible.

## Stage sequence for an all-local-assets job (CURRENT — 2026-07-27 B1/B2/B3)
```bash
npx tsx src/adapters/cli/agentic-modular.ts plan    --file input/scripts/<job>.json
# ✅ sentence-split (B1) + scene-order (B3) are handled automatically now:
#    a [Visual: file] line = exactly ONE scene; local-asset jobs keep author order.
#    Verify: `node -e "const p=require('./workspace/jobs/<id>/plan.json'); console.log(p.scenes.length)"`
npx tsx src/adapters/cli/agentic-modular.ts voice   --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts visuals --no-acquire --file input/scripts/<job>.json
#    --no-acquire synthesizes render-manifest.json from plan.json localAssets + resolves BGM.
#    NO network acquire, NO hand-written manifest, NO plan.json reorder.
npx tsx src/adapters/cli/agentic-modular.ts render  --file input/scripts/<job>.json
```
If you ever need to re-bind a SINGLE scene to a different local file on a `render` re-run
(rare), edit `render-manifest.json`'s `assets[]` entry (`kind` image|video, 0-based
`sceneIndex`, absolute `localPath`) — `render` reads that, not `plan.json`. This is the
only remaining manual-manifest case; fresh builds use `--no-acquire`.

> OBSOLETE (kept for archaeology only): the pre-2026-07-27 path required a `plan.json`
> reorder one-liner + a hand-written `render-manifest.json`. That is GONE — do not
> reproduce it. The old template asserted `sceneIndex` 0-based with image→Ken-Burns; those
> facts still hold for the `render-manifest.json` shape if you must edit it by hand.

## Final whole-timeline verification (cheap)
```bash
V="output/<id>/<title>.mp4"
for t in 2 10 18 26 34 42 50; do $FF -y -i "$V" -ss $t -frames:v 1 -vf scale=960:-1 f_t$t.jpg; done
$FF -y -i f_t2.jpg -i f_t10.jpg ... -filter_complex "[0][1]...xstack=inputs=7:layout=..." grid.jpg
# ONE vision_analyze on grid.jpg: per-frame content, captions legible, no stock leaks/black frames
```
Caveat: expected-vs-actual frame offsets in the vision verdict are usually timestamp drift
(a scene boundary near the sample time), not a missing scene — re-sample 2-3 frames inside
the suspect window before concluding a scene is absent (this run: "missing AI-dots scene"
was found intact at t=20-24s).

## Render facts from this run
- Base render is 1280×720 @25fps even for landscape jobs (job resolution, not 1080p) —
  8 scenes ≈ 52s, ~5.5 MB.
- render stage prints publish-manifest/archive/review-thread lines — informational, not blockers.
- Deliverable copy: `cp output/<id>/*.mp4 "/c/Users/PREM KUMAR/Downloads/"` (user expects this).
- MSYS gotcha: `$(...)$?`-style chains can eat exit codes; a stray `$null` file appears if a
  PowerShell-ism (`2>$null`) sneaks into a bash command — delete it.
