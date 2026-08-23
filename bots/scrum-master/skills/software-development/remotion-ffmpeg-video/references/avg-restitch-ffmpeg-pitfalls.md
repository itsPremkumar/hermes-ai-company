# restitch / concat-stitch ffmpeg pitfalls (AVG editor ops)

Concrete, verified failure modes from dogfooding `restitchMaster` (edit-in-place
scene swap into a rendered master) across 6 varied orientations. Each was a
real crash the unit tests (portrait+audio only) DID NOT catch.

## P1 - hardcoded scale breaks non-portrait masters
**Symptom:** `restitch` works on 720x1280 portrait but crashes on landscape /
square / 1080p with `Error initializing complex filters: Invalid argument`
or a dimension-mismatch.
**Root cause:** the new-scene clip was force-scaled to `scale=720:1280`, but
`partA` (trimmed from the master) kept the master's native resolution. The
concat filter requires identical WxH on every input.
**Fix:** probe the master's native resolution with ffprobe and scale BOTH
`partA` and `norm` to it:
```ts
const info = await probeVideo(masterMp4);   // {width,height,codec,fps,hasAudio}
const W = info.width, H = info.height, FPS = info.fps || 25;
const scaleVf = `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p`;
// apply scaleVf to partA, partB, AND norm (with ,fps=${FPS} on norm)
```

## P2 - silent (no-audio) master crashes the concat filter
**Symptom:** video-only master -> `Stream specifier ':a' in filtergraph ...
matches no streams`.
**Root cause:** the concat filter graph `[0:v][0:a]...` references an audio
stream that doesn't exist.
**Fix:** make it audio-aware. When `masterInfo.hasAudio === false`, feed each
part a FINITE silent track and map by the doubled index:
```ts
// inputs: for each part p -> ['-i', p, '-f','lavfi','-i', `anullsrc=channel_layout=mono:sample_rate=44100:duration=${sceneDur}`]
// filter: parts.map((_,i) => `[${2*i}:v][${2*i+1}:a]`).join('') + `concat=n=${n}:v=1:a=1[v][a]`
// ALSO append '-shortest' to the output args, or the endless anullsrc hangs ffmpeg.
```
Note the index math: with interleaved `-i p -f lavfi -i anullsrc`, part i's
video is `2*i`, audio is `2*i+1`. A wrong offset (e.g. `[n+i]`) is the silent
failure that still errors.

## P3 - estimateAudioDurationSafe Math.ceil poisoning duration comparisons
**Symptom:** a 4.04s clip reads as 5s; assertions expecting ~4s fail;
restitch outputs correctly but the *test* (or any duration gate) sees 5.
**Root cause:** `return Math.ceil(d)` on the ffprobe `format=duration`.
**Fix:** return the precise float `return d;` - round only at display. Affects
every downstream duration comparison (caption timing, render gates, restitch
length checks).

## P4 - ffprobe line-position parsing is fragile (CRLF / missing fields)
**Symptom:** `probeVideo` returned `{width:720, height:720, codec:"1280"}`
for a 720x1280 clip - height and codec_name were misaligned.
**Root cause:** parsing `-of default=nw=1:nk=1` output by array position after
`split(/\r?\n/)`; CRLF / field-count drift silently shifts columns.
**Fix:** request `-of json` and read by key:
```ts
const s = JSON.parse(out).streams?.[0] || {};
const [nf, df] = String(s.r_frame_rate || '25/1').split('/').map(Number);
return { width: Number(s.width)||720, height: Number(s.height)||1280,
         codec: s.codec_name||'h264', fps:(nf&&df?nf/df:25)||25, hasAudio };
```

## P5 - revise full-scope render writes to a non-existent dir
**Symptom:** `revise --auto` -> `Error opening output .../output/<id>_r1/...mp4:
No such file or directory`.
**Root cause:** the `runAgenticPipeline` render path in `reviseJob` never
`mkdirSync`s `output/<id>_rN/`; only `renderRevisionFromCache` did.
**Fix:** `fs.mkdirSync(path.join(process.cwd(),'output',revisionJobId), {recursive:true})`
before `renderAgenticSlideshow`.

## P6 - revise --auto hangs on jobs without a cached render
**Symptom:** `revise --auto` blocks for minutes (network) on synthetic jobs.
**Root cause:** `runAgenticPipeline` is called even when no
`render-manifest.json` exists, so it fetches real media over the network
instead of using the cached-workspace fast path.
**Recommendation:** prefer `renderRevisionFromCache` (scope-aware, offline)
and only fall back to full pipeline when no cache exists.

## Dogfood harness recipe (reusable)
To catch P1-P4, build a varied matrix and exercise each editor op:
- 6 variants: portrait_4s_audio, landscape_6s_audio, square_3s_audio,
  portrait_2s_noa (no audio), landscape_10s_audio, portrait_1s_audio.
- Build each as 3 concatenated sub-clips -> master + plan.json
  (`scenes:[{durationSec},{durationSec},{durationSec}]`).
- Register as real workspace jobs (`workspace/jobs/<id>/plan.json` +
  `output/<id>/<title>.mp4`) and drive `reorder`/`critique`/`revise` via the
  CLI; drive `restitch` at module level across all orientations.
- Assert: reorder renumbers; critique flags black-gaps/silent-audio/square;
  restitch output ~= plan total (4.04s for 2s+2s) and OOR scene fails safe.
