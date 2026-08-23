# AVS compose.ts — verified ffmpeg filter table & probe snippets

All strings below are KNOWN-GOOD (tested via node `execFileSync` array args
in `compose.ts` / `compose-scene-fx.ts`). Copy verbatim.

## gradeFilter() — inline `[Grade: X]`
Single filter string, NO comma inside (caller does `filters.join(',')`,
comma = chain separator → splits a comma'd string into two broken tokens).
| value        | string                                              |
|--------------|----------------------------------------------------|
| warm         | `eq=gamma_r=1.12:gamma_b=0.90:saturation=1.10` |
| cool         | `eq=gamma_b=1.12:gamma_r=0.92:saturation=1.05` |
| cinematic   | `eq=contrast=1.15:saturation=1.05`  (was `curves=preset=strong_contrast,eq=…` → BROKEN) |
| vivid        | `eq=saturation=1.40:contrast=1.10` |
| sepia        | `sepia=0.8`                          |
| bw / mono / grayscale | `format=gray`                    |
| vintage      | `curves=vintage:saturation=1.20`       |
| neutral / unknown | `undefined` (no-op)                |

## buildPaletteFilter() — job.paletteFilter
Whole graph wrapped as `[0:v]${pal}[v]` → `-filter_complex`.
A comma INSIDE is fine here (it is the whole graph, chained).
| value    | string                                                              |
|----------|--------------------------------------------------------------------|
| warm     | `colortemperature=6500,eq=saturation=1.15:gamma=0.95`         |
| cool     | `colortemperature=9500,eq=saturation=1.05:gamma_b=1.08`       |
| blue     | `colorbalance=bs=0.12:rs=-0.06:gs=-0.03,eq=saturation=1.20` |
| teal     | `colorbalance=bs=0.14:gs=0.05:rs=-0.10,eq=saturation=1.25` |
| cinematic| `eq=contrast=1.15:saturation=1.05,colortemperature=7000` |
| cyberpunk| `curves=matrix=0.9 0 0 0 1.1 0 0 0 1.3,eq=saturation=1.3:contrast=1.1` |
| vintage  | `curves=vintage:saturation=1.2,eq=contrast=1.05`         |

## isReadableVideo() — guard helper
MUST use **ffprobe-static**, NOT ffmpeg-static:
```ts
function ffprobeStaticPath(): string | undefined {
  try { const m = require('ffprobe-static') as { path?: string };
        return m?.path && fs.existsSync(m.path) ? m.path : undefined;
  } catch { return undefined; }
}
const o = execFileSync(ffprobeStaticPath()!,
  ['-v','error','-show_entries','stream=codec_type','-of','csv=p=0', p],
  { stdio:['ignore','pipe','ignore'], timeout:15000 }).toString();
return /video/.test(o);
```

## J-cut audio-mix (job.jCutSec > 0)
Shift VIDEO timeline forward so audio leads picture:
```ts
if (job.jCutSec && job.jCutSec > 0)
  amixInputs.push('-itsoffset', job.jCutSec.toFixed(2));
// …but DON'T copy the shifted stream:
const vcodec = (job.jCutSec && job.jCutSec>0)
  ? ['-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-threads','1']
  : ['-c:v','copy'];
// args: [...amixInputs, '-filter_complex', amix, '-map','0:v','-map','[a]', ...vcodec, '-c:a','aac','-shortest', finalVideo]
```

## SFX timing (sfxByScene / sfxOnCut)
`resolveSfx()` returns `{sceneIndex, localPath}[]`. In the mix loop, push
`-itsoffset cumStart[s.sceneIndex]` BEFORE each `-i s.localPath`
so each SFX fires at its cut (not stacked at t=0).

## Node-spawn test snippet (verifies a filtergraph WITHOUT the MSYS terminal glitch)
```js
const { execFileSync } = require('child_process');
const ff = require('ffmpeg-static');
const out = execFileSync(ff,
  ['-y','-v','error','-i','IN.mp4',
   '-filter_complex','[0:v]colorbalance=bs=0.14:gs=0.05:rs=-0.10,eq=saturation=1.25[v]',
   '-map','[v]','-c:v','libx264','-preset','veryfast', 'OUT.mp4'],
  { stdio:['ignore','ignore','pipe'], timeout:60000 });
```
If `OUT.mp4` is 0 bytes → `x264 [error]: malloc of size N failed` = OOM →
add `-threads 1 -pix_fmt yuv420p`.
