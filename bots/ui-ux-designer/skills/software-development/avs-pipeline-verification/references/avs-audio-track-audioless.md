# AVS single-task audio utilities — audio-less gap (BUG A5 + A6)

Date: 2026-07-28. Extends the recurring `[N:a]` audio-less crash class
(documented in `avs-audio-less-audit.md`) into the **single-task audio
callables** that the earlier edit.ts/render.ts passes did NOT cover:

- `src/agentic/operations/audio-track.ts` — `addMusic()`, `addAudioTrack()`
- `src/lib/audio-processor.ts` — `applyAutoDucking()`

These are the functions the CLI exposes as "add music / add voiceover to a
video" single tasks. They were unguarded against two distinct audio-less
failure modes.

## BUG A5 — `applyAutoDucking` throws on an audio-less video

`addMusic(file, query)` calls `applyAutoDucking(musicPath, [file], ...)`.
`applyAutoDucking` did `[0:a]concat` over the voice paths to build a combined
voice track. When `file` (the video) is **audio-less**, `[0:a]` matches no
stream → the concat fails silently → `temp_combined_voice.mp3` is **never
created** → the ducking step then tries to open that missing file and THROWS:

```
[in#1] Error opening input: No such file or directory
Error opening input file ...\temp_combined_voice.mp3
```

In `addMusic` this is caught (`.catch(() => musicPath)`) so it degrades to a
non-ducked music mux — but the ducking path itself is broken, and `applyAutoDucking`
is also called directly elsewhere. **Fix:** add a local `hasAudioStream(file)`
helper (ffprobe `codec_type==='audio'`) and filter voice paths to audio-bearing
ones. If **none** have audio, return `musicPath` unchanged (nothing to duck).
If some do, concat only those.

```ts
const audibleVoicePaths = voicePaths.filter((p) => hasAudioStream(p));
if (audibleVoicePaths.length === 0) return musicPath; // no ducking needed
// ...concat only audibleVoicePaths, then sidechain-compress as before
```

## BUG A6 — `addAudioTrack` returns `ok:true` while dropping audio (silent lie)

`addAudioTrack(file, audioFile)` does `[1:a]volume=${audioVolume}[a]` +
`-map 0:v -map [a]`. With a **silent / audio-less** `audioFile` (e.g.
`aevalsrc=0`), ffmpeg exits 0 but the `[1:a]` mapping produces no real audio
and the output is a **video-only file** — yet the function returns
`{ ok: true }`. The caller believes audio was added; it was silently lost.

**Fix:** after a successful mux, validate the OUTPUT actually contains an
audio stream via ffprobe. If not, return `ok:false` with a clear detail:

```ts
if (!audioStreamPresent(output))
  return { ok: false, output: undefined,
           detail: `audio track missing in output (source ${audioFile} produced no usable audio)`,
           usedMusic: false };
```

Add `audioStreamPresent(file)` helper (require `ffprobe-static`, probe
`codec_type`).

## Empirical test recipe (reuse in `*-audioless.test.ts`)

```ts
import { execFileSync } from 'child_process';
const ffmpeg: string = require('ffmpeg-static');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'avs-audioless-'));

function audioLessVideo(name: string, dur = 3): string {
  const p = path.join(TMP, name);
  execFileSync(ffmpeg, ['-f','lavfi','-i',`color=c=blue:s=320x180:d=${dur}:r=25`,
    '-c:v','libx264','-pix_fmt','yuv420p','-t',String(dur),'-y',p], { stdio: 'ignore' });
  return p;
}
function realAudio(name: string, dur = 3): string {       // NOTE: .wav + pcm_s16le
  const p = path.join(TMP, name.replace(/\.[^.]+$/, '.wav'));
  execFileSync(ffmpeg, ['-f','lavfi','-i',`sine=frequency=440:duration=${dur}`,
    '-c:a','pcm_s16le','-t',String(dur),'-y',p], { stdio: 'ignore' });
  return p;
}
function probeHasAudio(f: string): boolean {
  const out = execFileSync(require('ffprobe-static').path,
    ['-v','quiet','-show_entries','stream=codec_type','-of','csv=p=0',f]).toString();
  return out.split('\n').includes('audio');
}
```

Assertions:
- A5: `applyAutoDucking(music, [audioLessVideo])` returns the music path (no throw).
- A5: `applyAutoDucking(music, [realAudio])` produces a ducked file with audio.
- A6: `addAudioTrack(audioLessVideo, realAudio)` → `ok === true` AND `probeHasAudio(output) === true`.
- A6: `addAudioTrack(audioLessVideo, silentAudio)` → `ok === false` (the silent
  lie is gone; it no longer reports ok:true for a dropped track).

## Hard-won gotcha — lavfi `aac` encoder fails in this fixture context

The first test draft used `-f lavfi -i sine=... -c:a aac` to make the "real
audio" fixture. That **fails** with a cryptic `Command failed: ffmpeg ... -c:a aac`
under the gyan.dev build when sourced from lavfi. **Use `-c:a pcm_s16le` and a
`.wav` extension** for fixtures — universally accepted, no encoder surprise.
This cost a full failed test run before the fix.

## Status
Code fix + empirical test written in worktree `audit/audio-track-audioless`
(worktree path `../worktree-audio-fix`). Test 1 (A5 audio-less → returns music,
no throw) confirmed PASSING before the session ended. Tests 2–4 were still
failing on **test-fixture ffmpeg encoding issues** (the `.wav` fix above resolves
them) — NOT on the source-fix logic. Re-run after applying the `.wav` fixture fix
to reach 4/4, then commit+merge per the standard worktree discipline.
