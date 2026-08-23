# AVG: real media probing (duration + dimensions) via ffprobe-static

## The bug class
Single-task media ops (silence-removal, scene-detect/trim, auto-reframe,
brand-kit) need the clip's **duration** (and often **dimensions**) to build
filters. A naive implementation reads these from ffmpeg `stderr` hints:

- `silence.ts` parsed `DURATION:n` from the silencedetect log — but **real
  ffmpeg output does NOT emit that sentinel**. Fallback was `duration || 1e9`
  -> `spokenSpans` clamped to 1e9 -> the keep-filter kept the ENTIRE clip ->
  **silence removal was a silent no-op in production**.
- `scene.ts` did `duration = opts.duration ?? parseDurationHint(log) ?? 0` ->
  no hint -> `0` -> `buildChapters(cuts, 0)` filtered all bounds to `<= 0` ->
  **chapters/trim returned empty in production**.
- `reframe.ts` / `brand.ts` parsed `\d+x\d+` from ffmpeg `-f null` stderr —
  works by luck but is fragile (matches unrelated numbers).

## The fix (reusable pattern)
Create one injectable probe module using the already-present `ffprobe-static`
dep. ffprobe emits clean JSON; parse it. Make the runner injectable so unit
tests pass a fake `MediaInfo` (no binary spawn).

```ts
// probe.ts
// ffprobe-static ships no types
// @ts-ignore
import ffprobeStatic from 'ffprobe-static';

export interface MediaInfo { duration: number; width: number; height: number; }
export type ProbeRunner = (file: string) => Promise<MediaInfo>;

export function parseProbe(out: string): MediaInfo {
  let data: any = null;
  try { data = JSON.parse(out); } catch { return { duration: 0, width: 0, height: 0 }; }
  const dur = parseFloat(data?.format?.duration ?? '0') || 0;
  let width = 0, height = 0;
  for (const s of data?.streams ?? []) {
    if ((s.width && s.height) && (s.codec_type === 'video' || !width)) {
      width = parseInt(s.width, 10) || width;
      height = parseInt(s.height, 10) || height;
    }
  }
  return { duration: dur, width, height };
}

const defaultRunner: ProbeRunner = (file) => new Promise((resolve) => {
  const { spawn } = require('child_process');
  const bin = (ffprobeStatic as unknown as { path: string }).path;
  const child = spawn(bin, ['-v','error','-show_entries','format=duration',
    '-show_entries','stream=width,height','-of','json', file],
    { stdio: ['ignore','pipe','pipe'] });
  let out = '';
  child.stdout.on('data', d => (out += d.toString()));
  child.stderr.on('data', d => (out += d.toString()));
  child.on('close', code => resolve(code === 0 ? parseProbe(out)
    : { duration: 0, width: 0, height: 0 }));
});

export async function probeMedia(file: string, runner: ProbeRunner = defaultRunner) {
  return runner(file);
}
```

Each op: `const probe = opts.probe ?? probeMedia; const info = await probe(file);`
then use `info.duration` / `info.width`. Tests inject `{ duration, width, height }`
directly. NOTE: the op's `fs.existsSync(file)` guard runs BEFORE the probe — unit
tests must write a real temp file (even 1 byte) so the guard passes and the mock
runner/probe take over.

## Proof the bug was fixed (test assertions)
- `removeSilence` with a real 12.5s duration + a 1s silent span must report
  `removed 1 silent span` (was `removed 0` under the 1e9 fallback).
- `detectScenes(mode:'chapters')` with duration 12.5 + cuts at 3.2/7.8 must yield
  3 chapters (0-3.2, 3.2-7.8, 7.8-12.5) — was 0 chapters under the `0` fallback.
- `computeCropBox(1920,1080,'9:16')` -> box ratio ≈ 0.5625 (9:16).

## General lesson
For ANY op that needs media metadata, **probe with ffprobe, never parse ffmpeg
stderr hints** (they're format/version dependent and often absent). Keep the
probe injectable for tests. This is the "don't trust the log, measure the file"
rule for media pipelines.
