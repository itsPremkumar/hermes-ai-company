# Segmented (resumable) render + per-path X8 duration fix

Concrete, proven recipe behind **P40** (AVG `src/agentic/orchestrate.ts`, gated by
`AGENTIC_SEGMENTED=1`). The default single-pass path is untouched and remains default.

## Why
A single-pass filter_complex render loses the whole timeline if ffmpeg dies at 95%.
Segmented rendering renders each clip independently (so a bad clip retries up to 3x)
then concatenates — checkpoint-style resilience.

## Per-clip segment render (the working filtergraph)
```ts
const isVideo = /\.(mp4|webm|mov|m4v)$/i.test(clip.file);
const doZoom  = clip.kind === 'scene' && !isVideo && opts.kenBurns !== false;
// NOTE: no comma inside zoompan under -filter_complex (P40) — use unbounded small zoom
const zoom = doZoom ? `,zoompan=z=zoom+0.0008:d=1:s=${W}x${H}` : '';
const vfChain =
  `[0:v]${!isVideo ? 'loop=loop=-1:size=1,' : ''}` +     // stills MUST loop before trim
  `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,` +
  `setsar=1,trim=duration=${dur},setpts=PTS-STARTPTS,settb=1/25${zoom}` +
  `${grade ? ',' + grade : ''},format=yuv420p,vignette=PI/5` +
  `${segCaptionArg.length ? ',' + segCaptionArg.join(',') : ''}` +   // drawtext loop (P18), NOT subtitles
  `${kin.length ? ',' + kin.join(',') : ''}[v]`;

const voPath = clip.kind === 'scene' ? res.voiceovers?.scenes[clip.idx]?.audioPath : undefined;
const hasVo  = !!voPath && fs.existsSync(voPath);
const inputs: string[] = ['-i', clip.file];
if (hasVo) inputs.push('-i', voPath);
else inputs.push('-f', 'lavfi', '-i', `anullsrc=channel_layout=mono:sample_rate=44100`); // every seg needs audio

const af = hasVo
  ? `[1:a]aresample=44100,atrim=0:${dur},asetpts=PTS-STARTPTS[a]`
  : `[1:a]atrim=0:${dur},asetpts=PTS-STARTPTS[a]`;

const args = [
  ...inputs,
  '-filter_complex', vfChain + ';' + af,
  '-map', '[v]', '-map', '[a]',          // LABEL outputs, never -map 0:v here (P40)
  '-t', String(dur), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25',
  '-c:a', 'aac', '-shortest', '-y', seg,
];
// retry args up to 3x ; throw if seg missing after retries
```

## Concat (stream-copy join)
```ts
const list = outDir + '/_concat_' + jobId + '.txt';
fs.writeFileSync(list, segFiles.map(f => `file '${f.replace(/\\/g, '/')}'`).join('\n'), 'utf8');
await new Promise<void>((res, rej) => {
  execFile(ffmpeg, ['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', silent],
    (e: any) => e ? rej(new Error('concat failed: ' + e)) : res());
});
// then pass2 (music duck + mux) runs unchanged on `silent`
```

## X8 expected duration — compute PER PATH (the real bug)
Default single-pass: `expectedDur = intro + scenes + outro - xf*(clips-1)`.
Segmented (no xfade): `expectedDur = intro + scenes + outro` (sum of clip durations).
Set `expectedDur` INSIDE each branch, then `verifyRenderedVideo(out, expectedDur)` once.
Before this fix the gate used the default formula for both → segmented flagged
"actual 18.4s vs planned 12.0s" (X8 fail) even though the video was correct.

## Failure signatures -> cause
| Symptom | Cause | Fix |
|---|---|---|
| `No option name near '1:s=720x1280'` | `\,` in zoompan split by `-vf` parser | drop the comma (P40) |
| `Error while opening encoder` / `vost#0:1 libx264` | `-map 0:v` after `[0:v]` consumed in graph | label `[v]`/`[a]` + `-map '[v]' '[a]'` (P40) |
| segment 0.04s, video ~2s | still image not looped before `trim` | `loop=loop=-1:size=1,` (P40) |
| concat aborts / desync | mixed video-only vs video+audio segments | give every seg an audio track (anullsrc) (P40) |
| X8 "too long" though correct | expected used default formula on segmented | per-path expectedDur (P40) |

## Verification
`AGENTIC_SEGMENTED=1 npx tsx bin/agentic-auto.ts --topic "..." --images --no-sfx --max-attempts 1`
-> assert `success: YES` and X7-X15 all pass. Also run the DEFAULT path (no flag) to confirm
no regression. Both must pass before committing.
