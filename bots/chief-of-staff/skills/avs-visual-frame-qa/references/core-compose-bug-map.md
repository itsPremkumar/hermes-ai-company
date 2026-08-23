# Core render+compose bug map (triage 2026-07-28)

Confirmed bugs in the AVS core render/compose path (full evidence in
`workspace/bug-hunt/findings_core.md` in the repo). Useful when fixing or
re-testing these files:

- **compose.ts:746-775 `crossfadeSlideshow`** — xfade graph invalid three ways:
  operands swapped (`[i:v][i-1:v]`), chain never consumes `[v_{i-1}]`, segments
  comma-joined + dangling `format=yuv420p` after a labeled pad. Every
  transition (fade/slide/glitch/whippan/morphcut/lightleak) silently falls back
  to hard-cut concat. Correct form: `[0:v][1:v]xfade=...,format=yuv420p[v1]`
  then `[v1][2:v]xfade=...[v2]`, chains joined with `;`.
- **agentic-modular.ts:592** — the CLI `render` stage calls
  `renderAgenticSlideshow` (orchestrator/render.ts), NOT `composeVideo`. So
  shakeByScene / speedRampByScene / punchInByScene / parallaxDepthByScene /
  paletteFilter are silent no-ops in the standard plan→voice→visuals→render
  pipeline. composeVideo is reached only via single-feature.ts / wave-scheduler.ts.
- **compose.ts:558-623 audio mix** — when voiceVolume/duck ≠ 1 the graph becomes
  `[1:a]volume=0.50[va][2:a]amix=...` → "Trailing garbage" → silent video shipped.
  Labeled outputs `[va]/[ma]` are never fed into amix; chains need `;` separators.
- **visual-fx.ts:85-86** — `vintage` uses nonexistent `saturation` filter (needs
  `eq=saturation=`), `sepia` filter doesn't exist in ffmpeg-static 6.1.1 gyan
  essentials at all (needs colorchannelmixer matrix).
- **advanced-fx.ts:239 particles** — filtergraph ends in `[ov]` but no `-map "[ov]"`
  → unconnected output → always fails.
- **advanced-fx.ts:56 eqByScene** — `anequalizer=c0 f=1000:g=3:...` invalid;
  per-channel params must be one quoted space-separated string, `n` isn't an option.
- **compose.ts:709/625** — relative outDir writes cwd-relative paths into
  slideshow_list.txt but concat demuxer resolves entries relative to the LIST
  FILE dir → ENOENT → base.mp4 missing → unguarded `copyFileSync` at 625 crashes
  composeVideo. Always pass absolute outDir; testing composeVideo directly with
  relative outDir reproduces the crash.
- **advanced-fx.ts:35 isReadableVideo** — size>0 only (compose.ts:189 has the
  real ffprobe version); corrupt intermediates propagate.
- Render artifacts named `undefined_*` (`res.workspace.jobId` undefined in some
  render.ts sub-paths); `outputName` job field ignored (title used instead).

## Direct composeVideo driver (bypasses CLI wiring)
compose.ts has no named ESM exports under tsx — import default:
```js
import mod from '../../src/agentic/operations/compose.ts';
const { composeVideo } = mod;
await composeVideo({ job, sceneVisuals, sceneAudio: [], outDir: path.resolve(...),
  inputDir: 'input/visuals', scenes: [...] });
```
Run with `npx tsx`. Use absolute outDir (see crash above).

## Harness notes (workspace/bug-hunt/harness.mjs)
- First run may blow the 240s stage timeout while voice warms up — just rerun;
  voice results are cached.
- Harness looks for `output/<dir>/<outName>.mp4` but render names the file by
  job TITLE → "NO OUTPUT MP4" even on success. Grid manually from the titled mp4.
- ffprobe-static path: `node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe`
  (NOT `node_modules/ffprobe-static/ffprobe.exe`).
