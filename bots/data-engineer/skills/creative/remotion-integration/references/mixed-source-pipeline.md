# Mixed-source pipeline integration (the "does everything work" test)

Verified this session: prove the WHOLE pipeline by composing ONE final video
from **three different source types on one timeline** — a downloaded Pexels
video, a downloaded Pexels image, and a Remotion-generated motion clip. This is
the end-to-end integration check for the autonomous Remotion system.

## 1) Acquire real downloaded assets (Pexels)
The project has a live `PEXELS_API_KEY` in `.env`. Use the project's own
fetcher — but you MUST load `.env` yourself in a driver, because only
`src/mcp-server.ts` calls `dotenv.config()`; a bare `node --import tsx` driver
sees `process.env.PEXELS_API_KEY === undefined` and the fetcher silently
falls back to "no API key -> Openverse" (and returns 0 results).

```ts
import * as dotenv from 'dotenv';
dotenv.config({ path: path.resolve('.env') });   // <-- required in drivers
const { searchImages, searchVideos } = await import('./src/lib/visual-fetcher/index.ts');
const imgs = await searchImages('city skyline night', 3, 1, 'landscape');
const vids = await searchVideos('technology abstract', 3, 1, 'landscape');
// MediaAsset.url is a DIRECT downloadable Pexels URL, e.g.
//   https://images.pexels.com/photos/.../pexels-photo-....jpeg
//   https://videos.pexels.com/video-files/.../..._1920_1080_30fps.mp4
```

**Download gotcha (verified):** the project's `downloadMedia(url, dir, name)`
FAILED with an undefined `error` on these Pexels URLs (the wrapper's error
field wasn't populated). Don't debug it — download directly with Node 22's
built-in `fetch` (no extra deps):
```ts
const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
const buf = Buffer.from(await res.arrayBuffer());
fs.writeFileSync(outPath, buf);   // works for both images.pexels.com and videos.pexels.com
```
Drop the files into `input/visuals/` (the same dir the Remotion controller
integrates its clips into).

## 2) Generate the Remotion motion clip
```ts
const { runRemotionController } = await import('./src/agentic/media/hermes-remotion-controller.ts');
const res = await runRemotionController(
  [{ index: 0, text: 'AI Powered', kind: 'hud', palette: ['#0a0a14','#7c3aed','#22d3ee'], durationInFrames: 120 }],
  { jobId: 'mix_remotion', maxRetries: 4, fps: 30 },
);
// -> input/visuals/mix_remotion_s0.mp4
```
Driver MUST use dynamic `import()` (NodeNext static import throws `does not
provide an export named` under `node --import tsx`).

## 3) Compose into one mixed timeline (ffmpeg, AVS-contained)
The autonomous controller is NOT auto-invoked by the 6-stage `compose.ts` yet
(see autonomous-codegen.md), so build the mixed video with ffmpeg (the same
media tool `compose.ts` itself uses). Goal: all segments 1920x1080 @ 30fps.
```bash
FF=./node_modules/ffmpeg-static/ffmpeg.exe
# Pexels video: trim + scale+pad to 1920x1080@30
$FF -y -i input/visuals/pexels_tech.mp4 -t 5 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 -c:v libx264 -pix_fmt yuv420p -an _v.mp4
# Pexels image -> 4s ken-burns (zoompan) clip
$FF -y -loop 1 -i input/visuals/pexels_city.jpg -t 4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.0008,1.2)':d=120:s=1920x1080:fps=30" -r 30 -c:v libx264 -pix_fmt yuv420p _i.mp4
# Remotion clip is already 1920x1080@30
# concat (use -safe 0; list paths can be Windows - write with forward slashes)
printf "file '%s'\nfile '%s'\nfile '%s'\n" "$(cygpath -u _v.mp4)" ... > _list.txt   # OR just hardcode forward-slash paths
$FF -y -f concat -safe 0 -i _list.txt -c copy output/mixed_pipeline_demo.mp4
```
ESM drivers: use `import { spawn } from 'child_process'` - `require()` is NOT
defined in `.mts`, and `spawn(FF, [args])` with an args ARRAY (not a string)
avoids MSYS quoting issues.

## 4) Verify the mixed video (the point of the test)
- `ffprobe` the final: expect `1920x1080`, one video stream, sane duration.
- Extract ONE frame per segment (Pexels video ~1s, image ~6s, Remotion ~10s)
  and `vision_analyze` EACH - confirm correct content AND correct order. This
  is the proof the mixture rendered the right asset in the right slot.
- Verified result this session: seg1 = Pexels wireframe tech clip, seg2 =
  London Canary Wharf night skyline, seg3 = Remotion HUD radar `SYS.ONLINE`.
  All three vision-confirmed, in order. Final `output/mixed_pipeline_demo.mp4`
  (5.48 MB) delivered to `Downloads/`.

## Notes
- `.mts` drivers are SCRATCH - never treat `system changed paths` for them as
  real source edits; the flag is stale noise. Clean them up (rm) before the
  final verification commit so only implementation files are staged.
- Keep the downloaded assets in `input/visuals/` for reuse; they're real Pexels
  media, not generated.
