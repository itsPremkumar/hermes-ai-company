# Combined-feature bug hunt (2026-07-28) — COMBO-A/B/C triage

Jobs: `workspace/bug-hunt/combo_{a,b,c}.json` rendered via
`node workspace/bug-hunt/harness.mjs <job.json> <outName>` (plan→voice→visuals--no-acquire→render,
Kokoro serialized via `.voice.lock`). Grids at `workspace/bug-hunt/grids/combo_{a,b,c}.jpg`.
Findings: `workspace/bug-hunt/findings_combo.md`.

## Confirmed REAL bugs (all still open at session end — triage only)

### 1. `exportAspects: ['4K']` → ZERO exports, silent (HIGH)
- `src/agentic/media/export.ts:22-28`: `Aspect` type + `ASPECT_DIMS` have NO `'4K'` key.
- `:73` `const { w, h } = ASPECT_DIMS[a]` — destructure of `undefined` THROWS, and it is
  OUTSIDE the per-aspect try/catch at :79 → whole `exportMultiAspect` aborts.
- Swallowed by `render.ts:214` `try { ... } catch { /* optional */ }` → no log line at all.
- Perverse effect: `['4K']` yields FEWER exports than omitting exportAspects (which
  gives the default 9:16/16:9/1:1 trio). The "BUG A2" fix comments (agentic-modular.ts:670,
  render.ts:211) forward the value but the DIMS table was never extended. The correct 4K
  mapper exists unused in `advanced-fx.ts:483` (`resolveAspectSizes`).

### 2. `paletteFilter` ignored on the modular render path (HIGH)
- `agentic-modular.ts:657-678` renderAgenticSlideshow opts forward jCutSec/exportAspects/
  emojiByScene… but never `paletteFilter`; `orchestrator/render.ts` has ZERO references
  to it (grep = 0). Noir/etc. implemented only in `compose.ts:224/306` (composeVideo path).
- Same TWO-RENDER-PATH trap as `avs-aspect-palette-triage.md` — verify knobs in BOTH paths.
- Proof: COMBO-A noir job rendered fully-saturated SMPTE bars (vision-confirmed).

### 3. `[Filter: x]` tag: unparsed AND leaks into TTS + burned captions (HIGH)
- `src/lib/script-parser.ts` has no `[Filter:]` matcher at all → `scene.filter` never set
  (plan.json shows `filter: null`) even though consumption code EXISTS
  (`render.ts:507-509,758` keyed on `sp.filter` — bw/vintage/sepia).
- Worse: `[Filter:...]` missing from both the `allOtherTags` regex (:174) and the
  `cleanText` strip-list (:267-286) → the literal tag is SPOKEN by TTS and shown in
  burned captions on screen. Double-check any new tag is in BOTH lists.

### 4. `[Transition:]` regex silently drops extended vocabulary (MEDIUM)
- `script-parser.ts:230`: `/(fade|slide|zoomblur|cut)/` only. glitch/whippan/morphcut/
  lightleak → `undefined` → default crossfade, tag stripped, no warning. Style-engine's
  `xfadeName` supports far more names; parser is the bottleneck.

## Verification techniques that paid off
- **Letterbox false-alarm:** a portrait canvas + landscape asset gives big black areas;
  a downscaled 2x2 grid frame reads as "pure black" to vision. Before filing a
  black-frame bug: `blackdetect=d=0.1:pix_th=0.10` over the whole file (0 hits = fine)
  + extract the exact timestamp full-res and re-vision it. COMBO-A's "black frame"
  was letterboxing.
- **A/V sync check:** ffprobe `format=duration` vs per-stream durations; Δ ≤ 0.15s
  trailing pad is normal.
- Confirmed WORKING (don't re-hunt): modular-CLI motion FX (shake/punchIn/speedRamp/
  parallax per scene, logged as `motion FX applied to scene N`), emojiByScene 🔥 visible,
  jCutSec accepted, kenBurns+captions combo, default aspect exports.

## tsx one-liner pitfall
`npx tsx -e "import {...} from './src/...'"` fails MODULE_NOT_FOUND; write a throwaway
`.mts` file with a RELATIVE path from its location and run `npx tsx file.mts` instead.
Note the exported names in export.ts's compiled surface may not match what you expect —
read the file first.
