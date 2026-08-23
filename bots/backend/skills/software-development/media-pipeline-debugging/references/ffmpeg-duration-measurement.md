# ffmpeg Duration Measurement — Pitfalls & Authoritative Probe

When a concat/splice/trim produces an "impossible" duration (e.g. two 2s clips
concatenating to 5s), suspect the **measurement**, not the ffmpeg command.

## Symptom
- `estimateAudioDurationSafe(out)` returns 5 for a file that is actually 4.04s.
- A duration comparison / assertion fails by ~1s even though the ffmpeg command
  is provably correct (verified by `ffmpeg -i out.mp4` → `Duration: 00:00:04.04`).
- The same concat FILTER on two clean 2s clips yields 4.04s in isolation.

## Root causes seen
1. **`Math.ceil` in the duration helper.** `parseFloat` then `Math.ceil(4.04)` → `5`.
   Ceiling also throws off every downstream gate/timing comparison. Fix: return the
   precise float; round only at display.
2. **ffprobe `format=duration` reading a stale/metadata `duration` tag** rather than
   the computed container duration (e.g. a tag inherited from a source master).
3. **Keyframe padding on `-c copy` concat** makes a 2s+2s master 5s. Always
   re-encode the concat (`-c:v libx264 -c:a aac`) or use the concat *filter*; the
   demuxer with `-c copy` is unreliable for duration.

## Authoritative probe (use this, not a helper, when debugging)
```bash
# ffmpeg -i prints "Duration:" — this is the source of truth for what ffmpeg wrote.
ffmpeg -i out.mp4 2>&1 | grep -E "Duration|Stream"
```
Node/tsx:
```ts
import { execFileSync } from 'child_process';
const probe = (p: string): string => {
  try { const r: any = execFileSync(ffmpeg, ['-i', p], { stdio: ['ignore','ignore','pipe'] }); return String(r.stderr); }
  catch (e: any) { return String(e.stderr || ''); }
};
const m = probe(out).match(/Duration:\s*(\d+:\d+:\d+\.\d+)/);
```
> NOTE: ffprobe is NOT bundled with `ffmpeg-static` (spawnSync `ffprobe.exe` → ENOENT).
> Use `ffmpeg -i` parse above; do not call `require('ffmpeg-static').replace('ffmpeg.exe','ffprobe.exe')`.

## Concat filter (bulletproof splice)
```bash
ffmpeg -y -i partA.mp4 -i partB.mp4 \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k out.mp4
```
- Works correctly on equal-length clips (2s+2s → 4.04s).
- Make every part use the SAME `-r 25 -ar 44100` and an explicit `-t <dur>` output
  option, or the filter pads one stream to align the other and the duration balloons.
- Prefer this over the concat *demuxer* + `-c copy` (keyframe padding → wrong length).

## Gotcha: tsx double-loads test files
`node --test` + tsx can execute a test file twice on the same temp dir, producing
stale-file races. Use a unique output filename per run and delete it first:
```ts
const out = path.join(dir, `restitched_${Date.now()}_${Math.floor(Math.random()*1e6)}.mp4`);
try { fs.rmSync(out, { force: true }); } catch {}
```
