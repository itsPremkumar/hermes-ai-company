# Remotion v4 gotchas — evidence-backed

Discovered and verified against Remotion 4.0.487 (`node_modules/@remotion/*`) during a
composition bug audit. Keep these durable framework facts here; they are NOT
session-transient.

## 1. useCurrentFrame() inside <Sequence> is already localized
File: `node_modules/remotion/dist/cjs/use-current-frame.js`
```js
const frame = useTimelinePosition();
const context = useContext(SequenceContext);
const contextOffset = context ? context.cumulatedFrom + context.relativeFrom : 0;
return frame - contextOffset;
```
So inside `<Sequence from={N}>`, `useCurrentFrame()` ∈ [0, duration). Subtracting
`from` again (e.g. `local = frame - from`) yields negative values for the first N
frames → `interpolate` clamps to 0 → `opacity = Math.min(fadeIn,fadeOut)` = 0.
Scene renders invisible; crossfade/fade-out timing never fires. Fix: `local = frame`.

## 2. CameraMotionBlur multiplies children
File: `node_modules/@remotion/motion-blur/dist/cjs/CameraMotionBlur.js`
```js
return <AbsoluteFill ...>{new Array(actualSamples).fill(true).map((_, i) => (
  <AbsoluteFill ...><Freeze frame={currentFrame - sampleFrameOffset + 1}>{children}</Freeze></AbsoluteFill>
))}</AbsoluteFill>;
```
Default `samples=10`. Any `<Audio>`/media inside is instantiated N times (louder +
phasing). Keep per-scene audio OUTSIDE the blur wrapper; `CameraMotionBlur` should
only wrap purely-visual moving layers.

## 3. getAudioData is browser-only + fetch-based
File: `node_modules/@remotion/media-utils/dist/get-audio-data.js`
```js
if (typeof document === 'undefined') throw new Error('getAudioData() is only available in the browser.');
const response = await fetchWithCorsCatch(src, options?.requestInit);
```
Needs a served URL; pass `staticFile(audioPath)`, not a bare relative path like
`agentic-assets/<jobId>/s0_audio.mp3`. Wrap in try/catch and `render(null)` on
failure so headless renders degrade instead of looping the waveform indefinitely.

## 4. makeArrow() default path overshoots a small viewBox
File: `node_modules/@remotion/shapes/dist/utils/make-arrow.d.ts`
Defaults: length 300, headWidth 185, headLength 120, shaftWidth 80, direction 'right'.
Contrast `makeStar`/`makeCircle`/`makePolygon`, which center at (size/2, size/2) and
return `width = height = 2*radius`. The arrow is NOT centered → it is clipped /
invisible inside a `viewBox="0 0 ${size} ${size}"` (size default 120). Center the
arrow path or size the viewBox to its bounds before rendering as an accent.

## 5. createTikTokStyleCaptions input is lenient
File: `node_modules/@remotion/captions/dist/caption.d.ts` + `create-tiktok-style-captions.js`
`Caption = { text, startMs, endMs, timestampMs: number | null, confidence: number | null }`.
Input `{text, startMs, endMs}` works; the `as any` cast in callers is harmless, not a bug.
Tokens come back as `{ text, fromMs, toMs }` and pages as
`{ text, startMs, tokens, durationMs }` (durationMs is Infinity for the last page until
`add()` runs). Active-line lookup: `nowMs >= startMs && nowMs < startMs + (durationMs ?? Infinity)`.

## 6. Comments can lie about error boundaries
`SubtitleOverlay` genuinely wraps `<SubtitleInternal>` in a `SubtitleErrorBoundary`.
`KaraokeCaptions` has a comment "Wrapped in an error boundary so a caption failure
never aborts the render" but renders `<KaraokeInner {...props}/>` with NO boundary.
Any throw inside (bad caption shape, token map) crashes the whole composition.

## Reproduce the verification (run from repo root)
```bash
find node_modules/@remotion/shapes/dist -name "*.d.ts" | head
cat node_modules/remotion/dist/cjs/use-current-frame.js
cat node_modules/@remotion/motion-blur/dist/cjs/CameraMotionBlur.js
cat node_modules/@remotion/media-utils/dist/get-audio-data.js
cat node_modules/@remotion/captions/dist/create-tiktok-style-captions.d.ts
```
