# compose.ts audio-timing + low-RAM ffmpeg traps (from Waves A–F)

Reusable pitfalls from the agentic `compose` video campaign. Each cost a
full debug cycle; bake them in rather than re-discovering.

## 1. J-cut / audio-leads-picture — `amix` does NOT self-shift
`amix=inputs=N` starts EVERY input at `t=0`. You cannot make audio
lead picture by offsetting an `-i` in the filter — `amix` ignores
per-input timing.
**Fix:** offset the VIDEO input, not the audio. Add `-itsoffset <sec>`
to the `-i` that feeds the video stream so the picture starts *later* than
the voiceover → each scene's audio leads its cut (classic documentary J-cut).

```ts
const amixInputs = ['-i', withOverlays];
if (job.jCutSec && job.jCutSec > 0) amixInputs.push('-itsoffset', job.jCutSec.toFixed(2));
// ...then push voice/music/sfx inputs, build amix filter as normal
```
Same pattern for per-scene SFX: offset each sfx input by its cut time.
```ts
const at = cumStart[s.sceneIndex] ?? 0;           // cumStart = prefix-sum of scene durations
if (at > 0) amixInputs.push('-itsoffset', at.toFixed(2));
amixInputs.push('-i', s.localPath);
```
(Before this, `resolveSfx()` downloaded `sfxByScene`/`sfxOnCut` clips but
the mix pushed them ALL at t=0 — inaudible stack. `sfx=4` on a
3-scene job = 2 byScene + 2 onCut is the correct count.)

## 2. `isReadableVideo` must call ffprobe, NOT ffmpeg
A guard that checks "is this upstream FX intermediate a valid video?" is only
useful if it probes correctly. Calling the **ffmpeg** binary with
`-show_entries stream=codec_type` throws (`ffmpeg` rejects probe flags) →
the catch returns `false` → guard ALWAYS skips, masking both good and bad
inputs.
```ts
function ffprobeStaticPath(): string | undefined {
  try { const m = require('ffprobe-static') as { path?: string };
        return m?.path && fs.existsSync(m.path) ? m.path : undefined; }
  catch { return undefined; }
}
const o = execFileSync(ffprobeStaticPath(), ['-v','error','-show_entries','stream=codec_type','-of','csv=p=0', p], {stdio:['ignore','pipe','ignore'], timeout:15000}).toString();
return /video/.test(o);
```
Also fail-fast on empty: `if (!p || !fs.existsSync(p) || fs.statSync(p).size === 0) return false;`

## 3. Comma inside ONE filter string = filterchain splitter
`gradeFilter('cinematic')` returning `'curves=preset=strong_contrast,eq=saturation=0.92'`
is FATAL when the caller does `filters.join(',')` (as `applySceneFx` does):
the comma splits it into `curves=preset=strong_contrast` (invalid preset, no
`eq`) chained to `eq=saturation=0.92`. Result: corrupt `grade_*.mp4`
("moov atom not found"), which then poisons every downstream stage.
**A comma inside a single filter value is ALWAYS a filterchain separator
in ffmpeg `-vf`/`-filter_complex`.**
Fix options, in order of preference:
- Return ONE valid filter: `'eq=contrast=1.15:saturation=1.05'`.
- Or return SEPARATE array entries and join with comma (each entry is
  one complete filter). Never embed `,` inside a single entry.
(Same root as the `paletteFilter` bug class: `colorbalance=...,eq=...` →
split. The fix there was RAM-safe re-encode, but the comma rule is the
root. Rule 2 of the embedded ffmpeg pitfalls: `enable='gte(t,1)*lte(t,4)'`
also splits on its comma unless escaped as `\,` via an `escExpr()` helper.)

## 4. x264 OOM on the ~800MB-RAM box
Re-encoding a large frame through `libx264` with default threads can hit
`x264 [error]: malloc of size N failed` → "Error while opening encoder"
→ empty output file → "Nothing was written into output file".
This is silent until you capture `e.stderr`. Fix for ANY ffmpeg
re-encode stage on this machine:
```ts
execFileSync(ff(), ['-y','-i',out,'-filter_complex',`[0:v]${pal}[v]`,'-map','[v]',
  '-c:v','libx264','-preset','veryfast',
  '-pix_fmt','yuv420p','-threads','1',   // ← RAM-safe
  pf], {stdio:['ignore','ignore','pipe'], timeout:60000});
```
`-threads 1` cuts encoder RAM dramatically; `-pix_fmt yuv420p` avoids
GRAY8/misaligned planes. Apply to: palette re-encode, per-scene grade
re-encode, any `libx264` pass that runs concurrently with network fetch.

## Why these matter together
The J-cut + sfx-timing (1) are the HIGH-CONTROL features; the other
three (2,3,4) are the SILENT-CORRUPTION traps that make a feature
look "done" (exit 0, file exists) but produce a broken/empty artifact.
Rule of thumb from the campaign: a compose feature is only verified when
`ffprobe final.mp4` shows the expected `width×height` AND 2 streams
(video+aac) AND a `vision_analyze` of a frame confirms the visual
(grade tint / burned text / timing) — never on exit code alone.
