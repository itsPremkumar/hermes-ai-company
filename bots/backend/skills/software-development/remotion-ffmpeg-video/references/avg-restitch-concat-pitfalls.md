# AVG: restitch / in-place splice — concat-filter & ffprobe pitfalls

Context: built `restitch.ts` (edit-in-place: swap a regenerated scene clip into
the ALREADY-rendered master at the correct timeline offset, no full re-render).
Driven it against a VARIED matrix (portrait/landscape/square, with/without
audio, 1s–10s) and hit 4 distinct bugs. Unit tests only used portrait+audio
inputs, so they missed all 4. Lessons below are durable for ANY in-place
ffmpeg splice/edit op in this repo.

## Pitfall 1 — hardcoding 720:1280 breaks every non-portrait master
The original restitch scaled `partA` via `-t cutAt -r 25` (master-native res)
but `norm` (the new scene) via `scale=720:1280`. On a landscape/square/1080p
master the concat filter fails with `Error reinitializing filters!` /
`Failed to inject frame into filter network: Invalid argument` — a dimension
mismatch (partA stayed 1280x720, norm was forced to 720x1280).
FIX: probe the MASTER resolution and scale BOTH spliced parts to it.
```ts
const info = await probeVideo(masterMp4);          // {width,height,fps,hasAudio}
const scaleVf = `scale=${info.width}:${info.height}:force_original_aspect_ratio=decrease,pad=${info.width}:${info.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p`;
// apply scaleVf to partA, norm, AND partB (same W/H/FPS = concat-safe)
```
Reuse `probeVideo` from `src/agentic/orchestrator/ffmpeg.ts` (it returns
`{width,height,codec,fps,hasAudio}`).

## Pitfall 2 — silent/audio-less master: concat `[i:a]` matches nothing
When the master has NO audio stream (e.g. a `-an` render), the concat FILTER
`[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]` aborts:
`Stream specifier ':a' in filtergraph ... matches no streams`.
FIX: make it audio-aware. If `probeVideo(master).hasAudio === false`, feed each
part a silent track and renumber audio inputs:
```ts
const inputs = masterInfo.hasAudio
  ? parts.flatMap(p => ['-i', p])
  : parts.flatMap(p => ['-i', p, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100']);
const filter = parts.map((_, i) =>
  masterInfo.hasAudio ? `[${i}:v][${i}:a]` : `[${i}:v][${n + i}:a]`).join('') +
  `concat=n=${n}:v=1:a=1[v][a]`;
```
(Output stays silent — correct for a silent source — instead of crashing.)

## Pitfall 3 — `estimateAudioDurationSafe` used `Math.ceil` (off-by-one)
`Math.ceil(4.04)` → `5`, so any duration comparison / assertion on a spliced
output read 5s for a real 4.04s clip. REMOVED the ceil; returns the precise
float. This is a shared util — fixing it also fixed caption-timing / gate math
that depended on it.

## Pitfall 4 — `probeVideo` parser misalignment (line-position parse)
First `probeVideo` impl parsed ffprobe `-of default=nw=1:nk=1` output by LINE
POSITION: `const [w,h,codec,fps] = out.trim().split('\n')`. On Windows `\r\n`
and ffprobe key ordering this returned `width:720, height:720, codec:"1280"`
(garbage) — which silently fed the wrong scale and broke the no-audio case.
FIX: parse `ffprobe -of json` and read by KEY:
```ts
const s = JSON.parse(out).streams[0];
return { width: Number(s.width), height: Number(s.height), codec: s.codec_name,
         fps: nf/df, hasAudio };
```

## Pitfall 5 — `reviseJob` (full scope) rendered to a missing dir
`revise.ts` wrote `output/<id>_r<round>/<title>.mp4` without `fs.mkdirSync`,
so ffmpeg failed `Error opening output ... No such file or directory`.
FIX: `fs.mkdirSync(outDir, { recursive: true })` before `renderAgenticSlideshow`
on BOTH render paths (the scope-aware cached path already had it; the full
pipeline path did not).

## Dogfood method that caught all 4 (use it for every new editor op)
Unit tests with a single portrait+audio fixture hide resolution/audio edge
cases. Build a VARIED matrix and exercise the op on every variant:
- portrait (720x1280), landscape (1280x720 / 1920x1080), square (1080x1080)
- with audio AND `-an` (no audio)
- short (1s, ~0.33s scenes) and long (10s)
Build each as a 3-scene master (concat 3 sub-clips) + a `plan.json` with
per-scene `durationSec`, then call the op directly (module import) and assert
on the REAL output duration via `estimateAudioDurationSafe`. Also drive the
real CLI (`reorder`/`critique`/`revise`) by registering jobs in
`workspace/jobs/<id>/plan.json` + `output/<id>/<title>.mp4` + a `jobs.json`
pointed at with `--file`.
- `reorder` across all orientations: works (renumbers 3,2,1→1,2,3, even 0.33s scenes).
- `critique` correctly flags: black-gap (2.96s on a concat-built square master),
  silent audio (`peak -999dB` sentinel, no crash), square aspect.
- `restitch` edge: out-of-range scene N returns `ok:false` (fail-safe).

## Gotcha observed (not a crash) — worth a follow-up
`revise --auto` on a job with NO cached `render-manifest.json` calls
`runAgenticPipeline`, which FETCHES REAL MEDIA OVER THE NETWORK and HANGS on a
disconnected/synthetic job. The scope-aware cached path
(`renderRevisionFromCache`) is the fast offline path but only triggers when a
cache exists. RECOMMENDATION: make `revise --auto` prefer the cached-render
fast path and only fall back to full pipeline when no cache is present.
