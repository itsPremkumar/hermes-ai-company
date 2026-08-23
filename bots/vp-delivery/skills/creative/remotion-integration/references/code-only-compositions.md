# Code-only Remotion (no external images/video/audio)

Remotion can generate a huge range of videos from PURE CODE — SVG, CSS, Canvas,
React, gradients, math. No stock media needed. Verified end-to-end this session
(8 compositions rendered to real MP4 + vision-checked, all clean).

## Standalone sub-project pattern (reuse parent node_modules — zero install)

When the ask is "experiment with Remotion in a NEW folder" (not touch the main
pipeline), scaffold a self-contained sub-project that borrows the parent's
already-installed `remotion` + `react`:

```
remotion-creation/
  package.json        # {"type":"module", scripts: studio/render/list via `remotion ... index.ts`}
  tsconfig.json       # OWN config — see below
  remotion.config.ts  # Config.setVideoImageFormat('jpeg'); setConcurrency(2); setChromiumOpenGlRenderer('angle')
  index.ts            # registerRoot(RemotionRoot)
  Root.tsx            # <Composition id=.. component=.. durationInFrames fps width height /> x N
  lib/theme.ts        # shared THEME + seeded(i) deterministic RNG + lerp
  compositions/*.tsx  # one component per video
  out/*.mp4           # renders
```

- **Sub-project tsconfig** must differ from the AVS root (root uses NodeNext +
  `jsx:react`). For a bundler-served Remotion folder use:
  `"module":"ESNext","moduleResolution":"Bundler","jsx":"react-jsx","noEmit":true,"types":["react","node"]`.
- **Exclude the new folder from the ROOT tsconfig** (add to its `exclude`) so
  `npm run typecheck` at root stays green and the two configs don't fight. Then
  typecheck the sub-project separately: `cd remotion-creation && npx tsc -p tsconfig.json --noEmit`.
- No `npm install` needed — Remotion CLI resolves `remotion`/`@remotion/*`/`react`
  up the tree from the parent `node_modules`.

## Render + verify (Chrome present on this Win box)

```bash
cd remotion-creation
export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
npx remotion compositions index.ts                       # list (first run bundles ~1-2 min — background it)
npx remotion render index.ts <Id> out/<Id>.mp4 --codec=h264
```

- **First `compositions`/`render` call bundles everything (~1-2 min) → run it in
  the BACKGROUND with notify; foreground 60s cap will time out.** Subsequent
  renders reuse the cached bundle and are fast (batch all remaining in one bg loop).
- `chrome-headless-shell` is auto-installed under `node_modules/.remotion/`;
  `npx remotion browser ensure` confirms/downloads it.
- Visual-verify each: `ffmpeg-static -y -ss <t> -frames:v 1 out/_f.png` on a
  SETTLED frame (t ≈ 3s), then vision_analyze. All 8 came back clean first try.

## Proven composition recipes (1920x1080, 30fps) — all asset-free

| Composition | Core technique |
|---|---|
| Kinetic typography | per-word `spring({frame-delay})` + `interpolate` for y/scale; gradient last word via `background-clip:text` |
| Bar chart infographic | `spring` height + count-up `Math.round(interpolate(grow,[0,1],[0,value]))` |
| Confetti particles | N particles positioned by `seeded(i)`; y = `(frame*speed + seed) % (H+100)`; rotate per frame |
| Neural network | build node grid from layer sizes; pulse dot travels edge via `interpolate(phase,[0,1],[ax,bx])`, phase=`(frame*k+seed)%1` |
| HUD radar | rotating `<g transform="rotate(sweep cx cy)">` sweep wedge; blips glow when `|sweep-angle|<60°` |
| Aurora loop | SEAMLESS: map `frame/durationInFrames → 2π`; blurred radial-gradient blobs orbit on sin/cos of that t; `mixBlendMode:'screen'` |
| Terminal typing | typewriter by char budget = `frame*CPS`, slice each line; blinking cursor `floor(frame/15)%2` |
| Spectrum visualizer | procedural (NO audio file): bar len = layered `sin(frame*k + i)`; `hsl((i/N)*360+frame)` rainbow |
| Pie chart | SVG `<path fill="..."/>` arc per slice: `a1 = angle + frac*2π*grow`; legend count-up `interpolate(grow,[0,1],[0,value])` |
| Logo reveal | rotating gradient ring (`rotate(frame*k)`) + spring scale on inner square + `spring` letter slide-in + tagline fade |
| Audio-reactive (REAL audio) | `@remotion/media-utils`: `getAudioData(staticFile(path))`→`visualizeAudio({audioData,frame,fps,numberOfSamples:powerOfTwo})`; fallback to procedural bars if decode fails |
| Lower-third | bottom-left card: `spring` slide-in bar + `interpolate` name slide; faux radial-gradient backdrop as "video" |
| Timeline / roadmap | horizontal line + `spring` nodes Q1–Q4; `interpolate(progress,[0,1],[x0,x1])` progress stroke; glow circles |
| Loading spinner | SVG ring with `strokeDasharray` arc + `rotate(frame*k)`; blinking `_` cursor |

Determinism matters: use a seeded RNG (`Math.sin(i*127.1+43.7)*43758.5453` frac),
never `Math.random()`, or particles flicker between frames.

## Integrating standalone compositions INTO the main AVS pipeline

The whole pipeline runs one flow: **`bundle(entryPoint)` → `selectComposition({serveUrl,id,inputProps})` → `renderMedia({composition,serveUrl,outputLocation,inputProps})`**. Verified call sites:
- `src/render.ts:202` — bundles `remotion/index.ts`, selects `SingleScene` per scene.
- `src/agentic/orchestrator/remotion.ts:154` — bundles `remotion/index.ts`, loops aspect ratios, selects `AgenticVideo`.

So the hook point for any new composition is just its **`id` in `remotion/Root.tsx`**. Integration paths, least → most invasive:
1. **CLI generator (`agentic:motion`)** — mirror `agentic:image`/`agentic:editor`: call `bundle()`+`renderMedia()` for a chosen id with `inputProps`. Zero pipeline coupling; agent renders a clip then feeds it to the editor/concat. START HERE.
2. **Data-driven via `inputProps`** — convert hardcoded data (WORDS/DATA/LINES) to `getInputProps()`/`defaultProps` so the planner passes script-derived content (real stats, headline words, build-log lines).
3. **Intro/outro/transition cards** — render `KineticTypography`/`ConfettiParticles` as standalone clips, ffmpeg-concat onto the main video (how the showreel was built).
4. **Animated scene background / B-roll** — add scene `visual.type:'motion'` alongside `'image'|'video'`; `SingleSceneVideo`/`AgenticVideo` render that composition as the bg layer, voiceover+captions on top.
5. **Overlay layer** (lower-thirds/HUD/spectrum) — render with transparent bg (prores/vp8 alpha or png sequence), composite via ffmpeg `overlay` or a Remotion `<Sequence>`.
6. **Merge into `remotion/Root.tsx`** — move components in, register `<Composition>`s → instantly renderable by existing bundle/select calls (tightest coupling).
7. **MCP tool** — add `motion_render` to `src/mcp-server.ts` (alongside `agentic_*`) so external agents drive the engine.
8. **Programmatic import** — same node_modules: `import {bundle}` and point `entryPoint` at the sub-folder's `index.ts`; keeps experiment isolated but callable.

## What code-only CANNOT do (needs external AI/assets)
Photorealistic humans, real photos, live-action, realistic 3D characters,
original music, human voice. Remotion generates/animates/composes/renders — it
does not invent photoreal media. For audio-reactive visuals from a REAL track,
use `@remotion/media-utils` (`getAudioData`+`visualizeAudio`); the math-driven
spectrum above needs no audio at all.
