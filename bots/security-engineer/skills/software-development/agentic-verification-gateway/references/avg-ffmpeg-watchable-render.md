# AVG — Watchable ffmpeg render: the filtergraph traps that ate a session

The agentic AVG render was upgraded from a silent slideshow to a **watchable** video:
per-scene voiceover (TTS or tone fallback) + **burned captions** + **crossfade transitions**
+ **Ken Burns zoom** + **ducked background music**. All via `ffmpeg-static` (no Remotion/Chrome).

Every one of these traps produced a real `ffmpeg failed: Error initializing complex filters: Invalid argument`
during live runs. Documented so the next session starts already knowing the fix.

## 1. `subtitles` filter rejects absolute Windows paths
The SRT path is passed inside `-filter_complex`. ffmpeg's `subtitles=` option treats a drive colon
(`C:`) as an option separator and fails with:
`Unable to parse option value '...' as image size`.

- `subtitles=C:/one/.../x.srt` → FAIL
- `subtitles=C\:/one/.../x.srt` (escaped colon) → FAIL
- `subtitles=relative/path/x.srt` (written next to cwd) → **OK**

Fix: write `_captions_<job>.srt` under a path relative to `process.cwd()` and pass that relative
string. (Verified empirically: only relative paths worked on this Windows box.)

## 2. Filtergraph is NOT a shell — quotes are literal, commas in expressions escape
Inside `-filter_complex '...'` the content is a filtergraph, not a shell command. Wrapping a value
in `'...'` makes the `'` chars part of the value → "Invalid argument".

WRONG:  `zoompan=z='min(zoom+0.0005,1.04)':d=1:s=720x1280`
RIGHT:  `zoompan=z=min(zoom+0.0008\,1.04):d=1:s=720x1280`
                                           ^^^ escape the comma with backslash

For `force_style='FontSize=28,...'`: the `&` chars are fine unescaped; keep the whole value unquoted
or the quotes become literal. If a style value contains `:` it must be escaped as `\:`.

## 3. Audio input stream indices are offset by the video inputs
Inputs order matters. If you pass N stills first (`-loop 1 -i img0 … -i imgN-1`) then append K
voiceover files (`-i a0 …`), the audio streams are `[N:a]`, `[N+1:a]`, … NOT `[0:a]`.

WRONG:  `[0:a][1:a][2:a]concat=n=3:v=0:a=1[aout]` → "Stream specifier ':a' matches no streams"
RIGHT:  `const base = visuals.length; [${base}:a][${base+1}:a]…concat=n=K:v=0:a=1[aout]`

## 4. Two-pass render (still required, new shape)
PASS 1 — build the chained video AND concatenate voiceover audio in ONE filtergraph:
```
[0:v]...xfade...[vout]; [vout]subtitles=rel/x.srt[vcap]; [N:a][N+1:a]concat=n=K:v=0:a=1[aout]
-map [vcap] -map [aout] -c:v libx264 -c:a aac -shortest → voiced.mp4
```
PASS 2 — duck music under voiceover:
```
-i voiced.mp4 -i music.mp3
-filter_complex "[1:a]volume=0.18[a];[0:a][a]amix=inputs=2:duration=shortest[aout]"
-map 0:v -map [aout] -c:v copy -c:a aac -shortest → final.mp4
```

## 5. xfade offset math
For scene durations d0..dK-1 and crossfade `xf`, the i-th xfade (i≥1):
`offset = sum(d0..d(i-1)) - xf*i`   (cumulative duration minus total overlap).
Wrong cumulative → "Invalid argument" or a video shorter than expected.

## 6. TTS absence must not block the job
`generateVoiceovers()` throws "Too many voice generation failures" when Edge-TTS/SAPI is missing.
Wrap it; on failure synthesize a quiet per-scene sine `.wav` and use a sentence-length caption
fallback, set `voiceoverDriven=false`. The video stays watchable. (This box has no Edge-TTS, so
the verified runs used the tone fallback — the code path is identical, only the audio source differs.)

## Reusable probe recipe (verify ffmpeg filter syntax BEFORE baking it into code)
Write a tiny `bin/subtest.ts` that builds a 1s test image + a 1-cue SRT, then loops candidate
`-vf` strings and prints OK/FAIL. This isolates filtergraph bugs in seconds instead of full runs:
```ts
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const ffmpeg: string = require('ffmpeg-static');
const { execFileSync } = require('child_process');
const os = require('os'), fs = require('fs');
const dir = 'agentic-pipeline/workspaces/_subtest';
fs.mkdirSync(dir, { recursive: true });
execFileSync(ffmpeg, ['-f','lavfi','-i','color=c=blue:s=720x1280:d=1','-frames:v','1','-y',dir+'/img.png'], {stdio:'ignore'});
fs.writeFileSync(dir+'/t.srt', '1\n00:00:00,000 --> 00:00:02,000\nHi\n');
for (const vf of ['subtitles=agentic-pipeline/workspaces/_subtest/t.srt' /* , ... */]) {
  try { execFileSync(ffmpeg, ['-loop','1','-i',dir+'/img.png','-vf',vf,'-t','1','-y',dir+'/o.mp4'], {stdio:'ignore'}); console.log('OK', vf); }
  catch { console.log('FAIL', vf); }
}
```
(This probe is how #1 was confirmed: absolute paths FAIL, relative paths OK.)
