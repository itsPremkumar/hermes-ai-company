# Remotion 4.0.487 — verified API facts (from node_modules .d.ts)

These are REAL signatures in the installed `@remotion/*` packages. Common
online docs/tutorials assume different names — trust these.

## @remotion/transitions
- Prebuilt presentations (the ONLY ones exported):
  `crossZoom`, `dreamyZoom`, `filmBurn`, `linearBlur`.
  `fade`/`slide`/`wipe`/`flip` are NOT shipped — build them yourself.
- Exports: `TransitionSeries`, `linearTiming`, `springTiming`,
  `useTransitionProgress`, `makeHtmlInCanvasPresentation`,
  type `TransitionPresentation`, `TransitionPresentationComponentProps`,
  `TransitionTiming`.
- `TransitionSeries` is `FC & { Sequence, Transition, Overlay }`.
  - `TransitionSeries.Sequence` props = `{ durationInFrames, offset?, className?, ...LayoutBasedProps, name?, showInTimeline?, freeze? }` + children. **NO `presentation` prop.**
  - `TransitionSeries.Transition` props = `{ timing: TransitionTiming; presentation?: TransitionPresentation }`.
- `TransitionPresentation<P>` = `{ component: LooseComponentType<TransitionPresentationComponentProps<P>>; props: P }`.
- `TransitionPresentationComponentProps<P>` includes:
  `presentationProgress: number; children; presentationDirection;
   passedProps: P; presentationDurationInFrames; onElementImage; onUnmount;
   bothEnteringAndExiting`.
  -> a custom presentation reads `presentationProgress`, NOT `useTransitionProgress()`.
- `useTransitionProgress()` returns `TransitionState = { entering, exiting, isInTransitionSeries }` (no `progress`).

### Correct custom-transition structure
```tsx
const Fade: React.FC<TransitionPresentationComponentProps<{}>> =
  ({ presentationProgress, children }) =>
    <AbsoluteFill style={{ opacity: presentationProgress }}>{children}</AbsoluteFill>;

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={D}>{...}</TransitionSeries.Sequence>
  <TransitionSeries.Transition
     presentation={{ component: Fade, props: {} }}
     timing={linearTiming({ durationInFrames: 24 })} />
  <TransitionSeries.Sequence durationInFrames={D}>{...}</TransitionSeries.Sequence>
</TransitionSeries>
```

## @remotion/shapes
- Components: `Arrow, Callout, Circle, Ellipse, Heart, Pie, Polygon, Rect,
  Spark, Star, Triangle` (+ `make*` utils).
- `Circle` props = `MakeCircleProps & AllShapesProps`; `MakeCircleProps = { radius: number }`.
  -> use `<Circle radius={...} />`, NOT `size`.
- `Rect` takes `{ width, height, color, radius }`.
- `AllShapesProps` adds SVG path styling, `effects`, `pixelDensity`, etc.

## @remotion/media-utils (waveform + audio-reactive)
- `getAudioData(src: string, options?): Promise<MediaUtilsAudioData>` — async,
  CAN reject (decode failure / odd format). Wrap in try/catch; render nothing on fail.
- `visualizeAudio({ audioData, frame, fps, numberOfSamples }): number[]` — bar heights.
- Also: `VisualizeAudio` (component), `getWaveformPortion`, `visualizeAudioWaveform`.
- **IMPORT PITFALL (TS2305 hit this session):** `getAudioData` /
  `visualizeAudio` are exported from **`@remotion/media-utils`**, NOT from the
  `remotion` package. Importing them from `'remotion'` is a **TS2305** ("has no
  exported member"). Correct:
  ```ts
  import { getAudioData, visualizeAudio } from '@remotion/media-utils';
  // (type MediaUtilsAudioData also from '@remotion/media-utils')
  ```
- `getAudioData` needs a URL, not a bare relative path: wrap the asset in
  `staticFile(audioPath)` (the existing `remotion/VoiceoverWaveform.tsx` is the
  verified reference impl). `numberOfSamples` MUST be a power of two (round up).
- If no audio file is supplied, drive bars procedurally (layered `sin`) so the
  composition always renders — never block the scene on missing audio.

## @remotion/captions
- `createTikTokStyleCaptions({ captions: [{text,startMs,endMs}], combineTokensWithinMilliseconds })` ->
  `{ pages: [{ text, startMs, tokens: [{text, fromMs, toMs}], durationMs }] }`.
  Active page = page where `nowMs in [startMs, startMs+durationMs)`.

## @remotion/bundler + @remotion/renderer (render pipeline) — VERIFIED 4.0.487
The real programmatic render path (what AVS `src/render.ts` and
`src/agentic/orchestrator/remotion.ts` use). This is the pattern for adding a
*generated* motion-graphic scene/clip, not just a still.

```ts
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';

const serveUrl = await bundle(entryPoint);          // POSITIONAL, not an object
const composition = await selectComposition({
  serveUrl, id: 'MyComp', inputProps,               // NO `fps` key here
});
composition.width = 1920; composition.height = 1080; composition.fps = 30;
await renderMedia({ composition, serveUrl, codec: 'h264',
                    outputLocation, inputProps, concurrency: 2 });
```

GOTCHAS (TS errors hit + fixed this session — do NOT guess):
- `bundle()` takes the entry path **positionally**: `bundle(entryPoint)`.
  Passing `bundle({ entryPoint, webpackCacheDisabled })` is a **TS2345**
  (real signature is `(entryPoint, onProgress?, options?)`).
- `selectComposition()` options object has **NO `fps` field**. Setting `fps`
  is a **TS2353** ("Object literal may only specify known properties, 'fps'").
  Set fps on the returned `composition` instead: `composition.fps = 30`.
- The `AssetProbe` returned by `asset-checks.ts → probeAsset()` uses
  `durationSec` (seconds), **NOT** `durationFrames`. Checking
  `probe.durationFrames` is a **TS2339**. Use `probe.durationSec > 0.1`.
- `composition.durationInFrames` IS valid (set by `selectComposition`).
- Compositions are **data-driven**: pass content via `inputProps`
  (`getInputProps()` / `defaultProps`); don't hardcode data in the component
  if the planner/caller should inject it.

SMOKE-TESTING a render module under `node --import tsx`:
- Prefer **dynamic** `await import('./src/agentic/operations/motion-render.js')`
  over a top-level static `import { x } from './file.ts'`. The static form
  occasionally throws "does not provide an export named 'x'" under tsx's
  NodeNext resolution; dynamic import resolves correctly and surfaces real
  runtime errors in a try/catch.

## Using Remotion as a generated visual source (multi-library pattern)
When the agentic pipeline can pick a motion graphic instead of stock/user
footage, model it as a **third visual source** alongside `[Visual: keyword]`
(stock) and `localAssets`/`videoClips` (user files). Additive + backward-compat.
- Tag syntax: `[Motion: CompositionId]` or advanced `[Motion: Id@library]`.
- `library` maps to a folder via config (`motionLibrary: { name: "rel/folder" }`),
  default `creation` → `remotion-creation/`. Resolve `<folder>/index.ts`,
  `bundle()` it, `selectComposition(id)`, `renderMedia()` to
  `workspace/<job>/motion/...` (AVS containment — never system TEMP).
- Verify the output with the existing offline `probeAsset()` gate (same bar as
  downloaded assets); on failure fall back to stock/user asset.
- Reference implementation (this repo, committed): `src/agentic/media/motion-resolver.ts`
  + `src/agentic/operations/motion-render.ts` + `motion-resolver.test.ts`.

## Offline render reality
- Remotion browser render requires Chromium. Offline box -> chrome-gate fails
  fast -> ffmpeg fallback (does NOT run the `.tsx`). So the `.tsx` is only
  typecheck-verified offline; visual verification needs Chrome present.
