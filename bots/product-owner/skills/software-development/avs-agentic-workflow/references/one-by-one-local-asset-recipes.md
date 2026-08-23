# One-by-one local-asset AVS recipes (verified 2026-07-27)

Reusable driver patterns for the agent-driven, one-asset-at-a-time AVS workflow when every
visual is pre-supplied. Run from repo root `C:\one\Automated-Video-Generator`. ffmpeg-static is
at `./node_modules/ffmpeg-static/ffmpeg.exe` (NOT on PATH).

## Stage sequence (all-local job)
```bash
npx tsx src/adapters/cli/agentic-modular.ts plan    --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts voice   --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts visuals --no-acquire --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts render  --file input/scripts/<job>.json
```
Avoid the monolithic `pipeline` (TRAP 1 hang) and avoid hand-writing the manifest — the
`--no-acquire` flag synthesizes `render-manifest.json` from `plan.json` localAssets.

## Recipe: download ONE stock asset + verify it alone
`tmp_agent_run/dl_one_video.mts`:
```ts
import 'dotenv/config';
import * as fs from 'fs';
import mod from '../src/lib/visual-fetcher/search.ts';
const { searchVideos } = (mod as any).searchVideos ? (mod as any) : (mod as any).default ?? mod;
const q = process.argv[2] ?? 'programming code screen developer';
const out = process.argv[3] ?? 'input/visuals/asset.mp4';
const vids = await searchVideos(q, 1, 1, 'landscape'); // limit=1 → ONE
if (!vids?.length) { console.log('NO RESULTS'); process.exit(1); }
const r = await fetch(vids[0].url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
fs.writeFileSync(out, Buffer.from(await r.arrayBuffer()));
// verify: ffprobe (resolution/duration) + vision_analyze on an extracted frame
```
Then `ffmpeg -i <out>` for the signal gate + extract one frame `ffmpeg -ss 2 -i <out> -frames:v 1 f.png`
and `vision_analyze(f.png, "does this show <subject>?")`.

## Recipe: agent-authored Remotion clip, render ONE + verify
`tmp_agent_run/gen_clip.mts`:
```ts
import mod from '../src/agentic/media/hermes-remotion-controller.ts';
const { runRemotionController } = (mod as any).runRemotionController ?? (mod as any).default ?? mod;
const code = `...valid Remotion TSX (AbsoluteFill/Text/spring/useCurrentFrame)...`;
const res = await runRemotionController(
  [{ index: 0, text: 'Title', kind: 'logo', code, durationInFrames: 180 }],
  { jobId: 'myjob', maxRetries: 2, fps: 30, width: 1920, height: 1080, allowFallback: false },
);
// res[0].status === 'generated' → integratedPath is input/visuals/<jobId>_s0.mp4
```
Valid `kind` values: `kinetic|infographic|hud|diagram|ui|map|particle|procedural|logo|timeline|spectrum|abstract`.

## Recipe: verify final render (the honest gate)
```bash
FF=./node_modules/ffmpeg-static/ffmpeg.exe
$FF -i output/<id>/<title>.mp4                       # Duration + Stream (expect 1280x720, h264, aac)
for t in 3 11 19 27 35 43 51; do
  $FF -y -i output/<id>/<title>.mp4 -ss $t -frames:v 1 -vf scale=960:-1 tmp_agent_run/f_$t.jpg
done
# stitch + vision_analyze: confirm scene order, burned captions, NO stock leak, 16:9
```
**vision_analyze gotcha:** large PNGs (e.g. 4096×2160) time out — downscale with
`-vf scale=1280:-1` before analyzing.

## Script authoring rule (parser behavior)
- 1 line = 1 scene by default; the parser sentence-splits on `.?!` (so multi-clause em-dash
  lines like *"Meet AVS — … — MIT licensed."* would explode into many scenes).
- A line carrying a `[Visual: file]` tag is kept WHOLE as one scene (B1 fix, 2026-07-27) — so
  bind your local asset on the same line as the narration.
- `localAsset` is only set if the file already exists in `input/visuals/` when the parser runs.
