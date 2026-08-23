# X8 duration bug: intro dropped / video truncated — isolation recipe

Two distinct failure modes collapse a planned ~17.5s woven intro→scenes→outro
video to a shorter actual render, both flagged by X8 (`actual vs planned`):

| Actual | Cause | Fix |
|--------|-------|-----|
| ~8s | `concat` (intro→scene0, sceneN→outro) missing `fps=25` after `settb=1/25` | append `,fps=25` to the concat output |
| ~13.8s | `-shortest` on the mux truncates 17.5s video to the ~14s audio (voiceovers only, no music) | `[aout]apad[aout]` + remove `-shortest` |
| ~13.8-15s | `expectedDur` computed with wrong `xfadeOverlap` (didn't subtract both intro+outro cuts) | `xfadeTransitions = (clips-1) - (intro?1:0) - (outro?1:0)` |

## Standalone isolation test (no TTS/music, seconds not minutes)
Write a `.js` that runs the EXACT video filtergraph on the real asset files from
a workspace and `ffprobe`s the result. This separates "filter bug" from "mux bug"
without a full E2E render.

```js
const { execFileSync } = require('child_process');
const ffmpeg = require('ffmpeg-static');
const ff = require('ffprobe-static').path;
const ws = process.argv[2];
const base = `agentic-pipeline/workspaces/${ws}/render`;
const a = `agentic-pipeline/workspaces/${ws}/assets/videos`;
const jpg = (n) => `${a}/scene_0${n}/candidate_1.jpg`;
const intro = `${base}/_intro_${ws}.mp4`;
const outro = `${base}/_outro_${ws}.mp4`;
const dur = (p) => execFileSync(ff, ['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1',p]).toString().trim();
const fc =
`[0:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,trim=duration=3,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[v0];`+
`[1:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,trim=duration=5,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[v1];`+
`[2:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,trim=duration=5,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[v2];`+
`[3:v]fps=25,trim=duration=2.5,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[vintro];`+
`[4:v]fps=25,trim=duration=3,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[voutro];`+
`[vintro][v0]concat=n=2:v=1:a=0,settb=1/25,fps=25[vx1];`+
`[vx1][v1]xfade=transition=fade:duration=0.5:offset=5[vx2];`+
`[vx2][v2]xfade=transition=fade:duration=0.5:offset=9.5[vx3];`+
`[vx3][voutro]concat=n=2:v=1:a=0,settb=1/25,fps=25[vout]`;
const out = `${base}/_t_full.mp4`;
try { execFileSync(ffmpeg, ['-loop','1','-i',jpg(1),'-loop','1','-i',jpg(2),'-loop','1','-i',jpg(3),'-i',intro,'-i',outro,'-filter_complex',fc,'-map','[vout]','-c:v','libx264','-pix_fmt','yuv420p','-r','25','-y',out], {stdio:'ignore'}); console.log('FULL cut chain dur:', dur(out)); } catch(e){ console.log('FULL ERR', e.message); }
```

Run: `node test_filter.js <jobId>`. Expect `17.52` (matches planned 17.5s).
- If it reports ~8s → `fps=25` missing on a `concat` output.
- If it reports the planned value but the PIPELINE still truncates → the bug is
  in the mux args (`-shortest`), not the filtergraph.

## Key lesson
When an X8 mismatch appears, ALWAYS isolate the filtergraph standalone first.
A full E2E render also exercises TTS (25s fallback ×3 offline) + free-music network
calls, which multiply the debugging time 10× and mask the real cause.
