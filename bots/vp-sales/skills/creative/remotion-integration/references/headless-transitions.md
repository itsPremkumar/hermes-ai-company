# Headless Remotion transitions — verified recipe + traps

Companion to SKILL.md "Headless-GPU trap". Reproduction kit for the
`remotion-integration` skill's transition features under headless Chrome.

## Verified environment
- Remotion 4.0.487, Node 22, Chrome at `C:/Program Files/Google/Chrome/Application/chrome.exe`
- `CHROME_EXECUTABLE` exported; renders run fine for plain compositions.

## What works headless (no GPU)
- `slide({ direction: 'from-right' })` — pure CSS transform. Default-safe.
- A `<TransitionSeries>` of 2-3 scenes with `slide` transitions renders in
  ~30s (cached bundle) to ~3min (cold). Run **foreground, >=280s timeout**.

## What HANGS headless (no GPU)
- `crossZoom()`, `filmBurn()`, `linearBlur()` — WebGL canvas shaders.
- `wipe({ direction: 'from-right' })`, `dissolve()` — canvas polygon shaders.
- Symptom: `renderMedia` never returns; either a `delayRender` timeout at
  frame 0 OR a silent hang (process exits 1 with no stack when run under a
  background harness that clamps stdout). NOT a code bug in your composition —
  it's the missing GPU context.
- `chromiumOptions: { gl: 'swiftshader' }` does NOT reliably unblock them.

## Correct default mapping (autonomous path)
```ts
const safe = (t: string) => (allowShaderTransitions ? t : 'slide');
// crossZoom/filmBurn/linearBlur/wipe/dissolve -> 'slide' unless GPU present
```
Pass `allowShaderTransitions: true` only on a machine with a real GPU.

## Import rules (compile/runtime)
- Main entry `@remotion/transitions`: `crossZoom`, `dreamyZoom`, `filmBurn`,
  `linearBlur`, `TransitionSeries`, `linearTiming`, `springTiming` ONLY.
- Subpath: `import { slide } from '@remotion/transitions/slide'`,
  `import { wipe } from '@remotion/transitions/wipe'`,
  `import { dissolve } from '@remotion/transitions/dissolve'`, etc.
- `wipe` direction is `from-left|from-top|from-top-right|...|from-bottom-right`
  (NEVER `to-left`/`to-right` — throws `Unknown direction`).
- Presentation objects take a single options arg, no `durationInFrames`:
  `crossZoom({strength?})`, `filmBurn({seed?})`, `linearBlur({intensity?})`.
- Duration lives on the `<Transition>` element:
  `timing={linearTiming({ durationInFrames: 20 })}`.

## renderStill frame trap
Give the still `Composition` `durationInFrames={120}` (not 1) so
`renderStill({ frame: 30 })` is valid; otherwise throws
`Cannot use frame 30: Duration of composition is 1`.
