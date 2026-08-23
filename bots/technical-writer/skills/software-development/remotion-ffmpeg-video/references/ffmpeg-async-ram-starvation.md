# ffmpeg/ffprobe on a RAM-starved box — async pattern + traps

Project: Automated-Video-Generator (AVG) on a Windows laptop with ~70–150 MB free
RAM. The dominant production bug class here is **synchronous ffmpeg/ffprobe
spawns that permanently block the Node event loop**.

## The core rule
NEVER use `execFileSync` / `spawnSync` for ffmpeg/ffprobe in the hot path.
Under RAM starvation the `fork()` syscall can fail with EAGAIN and the JS
`timeout` option CANNOT fire because the thread is blocked mid-fork — the
process hangs forever (only a hard SIGKILL recovers it, and you can't SIGKILL a
spawnSync because you're inside it).

Convert EVERY ffmpeg/ffprobe call to **async `spawn` + hard timeout + SIGKILL**:

```ts
function runFfmpeg(args: string[], timeoutMs = 120000): Promise<number> {
  return new Promise((resolve) => {
    const { spawn } = require('child_process');
    const child = spawn(ffmpegBin(), args, { stdio: ['ignore', 'pipe', 'pipe'] });
    const t = setTimeout(() => { try { child.kill('SIGKILL'); } catch {} resolve(-1); }, timeoutMs);
    child.on('error', () => { clearTimeout(t); resolve(-1); });
    child.on('close', (code: number | null) => { clearTimeout(t); resolve(code ?? -1); });
  });
}
```

For commands that must return text (blackdetect, volumedetect, ffprobe), capture
BOTH `stdout` and `stderr`, and resolve on **both stream `end` events**, not on
`close` alone (see trap #3).

Files in AVG already converted this way: visual-fetcher, music-verifier,
asset-checks, media-verifier, video-analyzer (`runCli`), gate, export.ts,
tts.ts, bin/normal-gen.ts. Still sync (lower priority, off hot path):
src/lib/audio-processor.ts, src/lib/voice-engine.ts — convert if they ever run
during a render.

## Trap #1 — `ffmpeg -v error` hides blackdetect output
`blackdetect` prints at INFO level, not ERROR. If you probe with
`ffmpeg -v error -i file -vf blackdetect ... -f null -`, the blackdetect lines
are SUPPRESSED and you'll falsely conclude "no black". This caused a
multi-session misdiagnosis where a real X10 black-frame defect was wrongly
called a "gate false positive". Always run blackdetect at DEFAULT verbosity and
grep the full combined stdout+stderr.

## Trap #2 — `ffmpeg-static` v6 type drift
`require('ffmpeg-static')` (and `(await import('ffmpeg-static')).default`) is
now typed as `{ path: string }`, NOT `string`. Passing it to `execFile`/`spawn`
as the binary errors with "spawn ... ENOTDIR" or a TS type error. Extract
`.path`: `const ffmpeg: string = require('ffmpeg-static').path;` (or
`as any`). This broke 21 type errors across `src/agentic/plugins/*` because
`orchestrate.ts` imports `./plugins/index.js` (plugins are INTEGRATED, not
orphaned — a tsconfig `exclude` of them does NOT work while `include:["src/**/*"]`
matches them via the import). Fix the type errors; do not exclude the dir.

## Trap #3 — `runCli` must await stream `end`, not `close`
On a slow/starved box, `child.on('close')` can fire before stdout/stderr flush,
so `out + err` is PARTIAL/garbled and regex matching mis-parses it (e.g. a
`black_duration` line read as real black). Correct pattern:

```ts
let out = '', err = '', outEnd = false, errEnd = false;
const finish = () => { if (outEnd && errEnd) resolve(out + '\n' + err); };
child.stdout?.on('data', d => out += d.toString());
child.stderr?.on('data', d => err += d.toString());
child.stdout?.on('end', () => { outEnd = true; finish(); });
child.stderr?.on('end', () => { errEnd = true; finish(); });
child.on('close', () => { if (outEnd && errEnd) finish(); else setTimeout(finish, 50); });
```

## X7 size-gate calibration
`verifyRenderedVideo` X7 floor should be **duration-scaled but conservative**:
`minSize = max(50_000, expectedDurationSec * 6_000)`. A 20KB/s factor
over-penalises valid low-entropy content (gradient placeholder cards, simple
scenes) — they compress to ~9KB/s and wrongly fail. 6KB/s still catches
empty/corrupt renders (<50KB). Real photo outputs are 400KB+ so the agentic path
is unaffected.

## Verifying "is the video black?" correctly
1. Run `ffmpeg -i file -vf blackdetect=d=0.3:pix_th=0.15 -f null -` at DEFAULT
   verbosity; grep `black_start`. No `black_start` = clean.
2. Use `signalstats,metadata=print:key=lavfi.signalstats.YAVG` to measure average
   luma; a value < ~38 (0.15*255) is below the blackdetect threshold and will be
   flagged as black — fix the SOURCE asset (near-black test fixture), not the gate.
3. The gate (`detectBlackFrames`) is correct; a mismatch between your manual probe
   and the gate almost always means your manual probe used `-v error` (trap #1) or
   measured the wrong file.
