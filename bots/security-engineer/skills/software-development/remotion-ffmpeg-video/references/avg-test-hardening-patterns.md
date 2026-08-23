# AVG test-hardening patterns (session 2026-07-18)

Two reusable techniques for adding real test coverage to the Automated-Video-
Generator agentic pipeline WITHOUT a full render (no ffmpeg/network needed).

## 1) Unit-test PURE exported helpers from a 2000-line render engine
File `src/agentic/orchestrate.ts` is ~2170 lines and was only indirectly tested
(through render.test.ts / integration.test.ts / agentic.test.ts). Do NOT try to
test the whole module. Instead: grep for `export function` / `export async function`
inside it, then import THOSE directly in a focused `*.pure.test.ts`.

Verified-good pure helpers already extracted + tested this session:
- `sourceFromUrl(url)` — maps image host -> source name (pexels/pixabay/...).
- `buildDuckExpression(visuals, full, duck)` — builds the ffmpeg `between(t,a,b)*gt(...)`
  audio-duck term; accumulates offsets across scenes. Assert the structure
  (starts with `full-(full-duck)*gt(`, contains `between(t\,X.XXX\,Y.YYY)`).
- `chunkCues(segs)` — caption chunking: merges sub-100ms / <3-char micro-segments
  into the PREVIOUS segment (a leading micro-segment at index 0 is NOT merged —
  that is by design, test the documented direction), enforces 500ms min, splits
  >8-word segments at the midpoint.

Pattern: `src/agentic/orchestrate.pure.test.ts` imports
`{ buildDuckExpression, chunkCues, sourceFromUrl } from './orchestrate.js'`.
Note the `.js` extension (tsx/NodeNext). Loading the module pulls its whole graph
but runs fine under tsx.

## 2) Gate lock-down: test the pure safety function directly
`src/agentic/gate.ts` `runFinalGate(plan, candidates, decisions, manifest, opts)`
is a pure sync function. Build fixtures with the real `AssetCandidate` /
`AssetDecision` / `Plan` / `RenderManifest` types (use the `assetId()` helper from
`types.ts`). Assert each X-check fails correctly:
- X2 missing scene visual (approved set != all scene indices)
- X3 unresolved decision (a candidate with no decision entry)
- X4 + overall pass=false when manifest is null
- X5 runtime > platform cap (default shorts=60s; honor `maxRuntimeSec` override)
- X6 approved asset with empty `license`
- X1 drift >10% when manifest durations diverge

Pattern: `src/agentic/gate.test.ts` (9 tests).

## 3) Bounded concurrency without a new dependency
`acquireAssets` fanned out every scene via `Promise.all(sceneFetches)` — a 20-scene
plan = 20 simultaneous API calls. Replaced with a zero-dep helper:

```ts
export async function mapWithConcurrencyLimit<T>(tasks: (() => Promise<T>)[], limit: number): Promise<T[]> {
  const out: T[] = new Array(tasks.length);
  let cursor = 0;
  async function worker() {
    while (cursor < tasks.length) { const idx = cursor++; out[idx] = await tasks[idx](); }
  }
  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, () => worker()));
  return out;
}
```
Test it: order preserved under varied latency, peak concurrency <= limit AND
actually saturates (peak === limit), empty input -> [], per-task error propagates
(do NOT swallow). Pattern: `src/agentic/acquire.test.ts` (5 tests).

Trap: when converting `sceneFetches` from `Promise<T>[]` to `(() => Promise<T>)[]`,
declare the array ONCE before the for-loop; pushing inside the loop after a
per-iteration `const sceneFetches = []` discards each iteration (the bug that
cost 6 typecheck rounds this session).

## 4) brain.ts heap guard (RAM-constrained box)
`visionVerify` did `readFileSync(filePath).toString('base64')` with no size cap.
Add `statSync` + a `maxImageBytes` option (default 8MB); return `null` (callers
already fall back to the signal gate) when over cap. Protects the heap on a 6GB box.

## CI gotcha: prettier is a SEPARATE gate from lint
`npm run lint` green != CI green. CI also runs `npm run format:check`. Before
pushing any TS change: run `npm run format` then `npm run format:check`. Local
lint 0 + format clean is the real pre-push gate.
