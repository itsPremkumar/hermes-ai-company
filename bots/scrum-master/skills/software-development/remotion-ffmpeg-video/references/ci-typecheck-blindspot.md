# CI / typecheck blind spot + ffmpeg hardening (P40 / P41)

Concrete fixes for the Automated-Video-Generator class of project (Remotion + ffmpeg
agentic video pipelines). Captured from a session that turned a RED CI lint job green
and surfaced 8 hidden type errors.

## P41 — tsconfig `include` blind spot breaks CI lint

**Symptom:** `npm run lint` (ESLint) fails with ~87 errors, mostly
`Parsing error: "parserOptions.project" has been provided ... file was not
found in any of the provided project(s)`. The CI **lint job is RED**.

**Root cause:** `tsconfig.json` `include` was a hand-picked subset:
```
"include": ["src/agentic/*.ts","src/agentic/audio/**","src/infrastructure/**","src/lib/**","src/video-generator.ts","remotion/**"]
```
So `src/adapters/**` (HTTP server + MCP), `src/application/**`,
`src/services/**`, `src/views/**`, `src/middleware/**`, `src/cli.ts`,
`src/server.ts`, `src/mcp-server.ts`, and `src/agentic/plugins/**` were
**never typechecked**, and ESLint's `parserOptions.project: true` could not
resolve them → parse errors.

**Fix:** widen include to the whole tree:
```
"include": ["src/**/*.ts","remotion/**/*.ts"],
"exclude": ["node_modules","dist","dist-electron"]
```
After this, `tsc` compiles everything (surfacing real errors that were
hidden) and ESLint resolves all files → 0 errors, CI lint GREEN.

**Side effect:** hidden type errors appear. In this project, `advanced-transitions.ts`
had 8 real errors (plugin contract mismatches):
- `category` in `metadata` (not in `PluginMetadata`) → remove it
- `onPlan` used `scene.sceneIndex` but `PluginScene` field is `sceneNumber`
- every `PluginFilter` push was missing the required `metadata: Record<string,unknown>` field
- light-leak asset inferred as `any` (from `params.asset` any) → type as `string`

## P40 — sync ffmpeg blocks the event loop on a RAM-starved box

`execFileSync(ffmpeg, [...])` / `spawnSync(...)` **cannot be interrupted
mid-fork**. On a box with ~70-150MB free RAM, the spawn syscall can block
the entire Node process permanently (the JS `timeout` option never fires because
the thread is stuck in the syscall). This hangs the whole pipeline.

**Fix — async `runFfmpeg` helper (reuse everywhere ffmpeg is spawned):**
```ts
function runFfmpeg(args: string[], timeoutMs = 180000): Promise<number> {
  return new Promise((resolve) => {
    const { spawn } = require('child_process');
    const child = spawn(require('ffmpeg-static') as string, args, { stdio: 'ignore' });
    const t = setTimeout(() => { try { child.kill('SIGKILL'); } catch {/*noop*/} resolve(-1); }, timeoutMs);
    child.on('error', () => { clearTimeout(t); resolve(-1); });
    child.on('close', (code: number | null) => { clearTimeout(t); resolve(code ?? -1); });
  });
}
```
Convert every `execFileSync(ffmpeg, [...])` in the hot path (render,
thumbnail, frame extraction, contact sheet, audio mix, tone gen) to
`await runFfmpeg([...])`. A `code === 0` check replaces the old
try/catch-on-throw semantics.

## blackdetect debug pitfall (X10 false "false-positive")

**Do NOT** verify black frames with `ffmpeg -v error ... blackdetect`. The
`[blackdetect] black_start:...` lines print at **info** level and are
suppressed by `-v error`. Concluding "no black → gate is a false positive"
from a `-v error` run is a METHODOLOGICAL ERROR. The gate was correct.

Correct check: run `blackdetect` at default verbosity and read stderr, OR
probe frame luma directly with `signalstats` + `metadata=print` and compute
`YAVG`. Near-black fixtures have YAVG ~30 (below blackdetect pix_th=0.15 →
38.25 luma); bright content is 90+. A render failing X10 with bright real
content means a real code bug; failing with dark test fixtures means fix the
fixtures (regenerate with `lavfi color=c=blue@1`, etc.), not the gate.

## X7 size-floor calibration

`minSize = Math.max(50_000, Math.round(expectedDurationSec * 6_000))`.
- 20KB/s (old) over-penalised valid low-entropy clips (gradient cards
  compressed to ~9KB/s → 16s video failed at 320KB floor).
- 6KB/s + 50KB floor still catches empty/corrupt renders (<50KB) while
  letting gradient/placeholder content pass. Real photos (high entropy) are
  400KB+ and unaffected.
Pair with gradient placeholders (not flat `color=c=teal` fills — those
compress to <1KB and trip X7).

## Silent cached music (X12 trap)

`free-music` can cache a **silent** download (e.g. a 20-min mp3 that is
digitally silent: all samples at -91dB) as "valid". The render then has
no audio → X12 (loudness) correctly FAILS. This is NOT a gate bug — it's
missing silent-audio detection on cached downloads. Fix: probe cached music
with `volumedetect` and reject/regenerate if `max_volume < -60dB`. As a
pipeline fallback, mix a faint tone bed (`sine=frequency=200:duration=DUR`
at volume ~0.04) under the music so output is never dead-silent.
