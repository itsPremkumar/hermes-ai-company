# Remotion 4.0.487 — verified API surface (against installed .d.ts)

The web docs describe a newer/different API. For THIS project (4.0.487), trust
`node_modules/@remotion/*/dist/**/*.d.ts`. Verify a package's exact exports with:
`node -e "const p=require('@remotion/PKG/package.json'); console.log(p.types)"`
then read that `.d.ts`.

## @remotion/transitions
- Prebuilt presentations ONLY: `crossZoom`, `dreamyZoom`, `filmBurn`, `linearBlur`.
- NO `fade`/`slide`/`wipe` named exports — build custom ones.
- Exports: `TransitionSeries`, `linearTiming`, `springTiming`, `useTransitionProgress`, `makeHtmlInCanvasPresentation`, `TransitionPresentation` type.
- `TransitionSeries.Sequence` props: `{ children, durationInFrames, offset?, className?, ...LayoutBasedProps }`. **NO `presentation`.**
- Transition between two sequences:
  ```
  <TransitionSeries>
    <TransitionSeries.Sequence durationInFrames={N}>...</TransitionSeries.Sequence>
    <TransitionSeries.Transition presentation={pres} timing={timing} />
    <TransitionSeries.Sequence durationInFrames={N}>...</TransitionSeries.Sequence>
  </TransitionSeries>
  ```
- `useTransitionProgress()` → `{ entering:number; exiting:number; isInTransitionSeries:boolean }` (NOT `progress`).
- A custom presentation component gets `presentationProgress` from its OWN props
  (`TransitionPresentationComponentProps`), e.g.
  `({ presentationProgress, children }) => <AbsoluteFill style={{opacity:presentationProgress}}>{children}</AbsoluteFill>`.
- `TransitionPresentation<{}> = { component, props }` — NO `timing` field.
- `timingFor` returns `linearTiming({durationInFrames:24})` or
  `springTiming({config:{damping:200}, durationInFrames:30})`.

## @remotion/motion-blur
- `CameraMotionBlur`: `{ children: ReactNode; samples?: number }` — drop-in OK.
- `Trail`: `{ layers, lagInFrames, trailOpacity, children }` — NOT drop-in (needs
  explicit layer config). Don't wrap arbitrary children in `Trail`.

## @remotion/shapes
- Components: `Arrow, Callout, Circle, Ellipse, Heart, Pie, Polygon, Rect, Spark, Star, Triangle`
  + `make*` path generators.
- `Circle` takes `radius` (NOT `size`). `Star`/`MakeStarProps` = `{ points, innerRadius, outerRadius, edgeRoundness? }`.
- Shape components use a fixed viewBox — awkward to position. PREFER
  `makeStar({points, innerRadius, outerRadius, edgeRoundness})` / `makeCircle({radius})`
  / `makePolygon({points, radius})` → returns `{ path: string, ... }`, then render
  `<svg viewBox="0 0 SIZE SIZE"><path d={path} .../></svg>` with full CSS control.
- `AllShapesProps` extends `React.SVGProps<SVGPathElement>` (minus width/height/d/hidden/name),
  so `fill`, `stroke`, `strokeWidth`, `opacity`, `style` are valid.

## @remotion/paths
- `interpolatePath(value: number, firstPath: string, secondPath: string) => string`
  (value 0→1). Also: `parsePath`, `getPointAtLength`, `getLength`, `normalizePath`, etc.
- For morph transitions, hardcode two valid `d` path strings (circle + star) and
  interpolate between them.

## @remotion/media-utils
- `getAudioData(src: string) => Promise<MediaUtilsAudioData>` (async, can fail offline).
- `visualizeAudio({ audioData, frame, fps, numberOfSamples }): number[]` (heights).
- Pattern: lazy `useEffect` + `useState` for audioData, render NOTHING on failure
  (graceful — never crash the composition).
