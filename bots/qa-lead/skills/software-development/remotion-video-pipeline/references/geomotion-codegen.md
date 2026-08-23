# GenMotion Autonomous Remotion Codegen

The GenMotion sub-system is the **autonomous Remotion code generator** in AVS.
It gives the agent full capacity to write, render, verify, and self-fix any
Remotion composition from a natural-language description — no preset templates,
no capability caps.

## Three Remotion Mechanisms

| Mechanism | Tag/Flag | What happens | Best for |
|-----------|----------|-------------|----------|
| **Autonomous codegen** | `[GenMotion: description]` | Agent writes a brand-new `.tsx` from scratch, renders it, vision-verifies, self-fixes (up to 5 retries), integrates into `input/visuals/` | Unique per-scene graphics (infographics, HUD, diagrams, abstract loops) |
| **Pre-built library** | `[Motion: comp]` or `[Motion: comp@library]` | Selects existing composition from `remotion-creation/` (or named library folder), passes data-driven props | Reusable templates (BarChart, NeuralNetwork, TerminalTyping) |
| **Full pipeline render** | `--renderer remotion` | Entire video rendered via `remotion/AgenticVideo.tsx` (A1-A11 features) instead of ffmpeg | Cinematic output with transitions, grading, karaoke, kinetic text |

## Autonomous Codegen Architecture

```
User script: [GenMotion: animated neural network with colored layers]

         ↓
1. **hermes-remotion-controller.ts**
   - Parses `[GenMotion:]` tags from the script via `extractMotionTags()`
   - Creates `MotionScene` objects with index, text, kind, palette, data
   - Calls `generateOneScene()` per scene

         ↓
2. **remotion-codegen.ts** — The "brain's pen"
   - `authorRemotionComponent(spec)` → returns complete `.tsx` string
   - Two modes:
     • PROVIDED: `spec.code` is used verbatim (agent hand-wrote it)
     • GENERATED: `synthesize(spec)` auto-creates from kind + text + palette + data
   - `assertSafeImports(src)` — safety gate (only `remotion`/`react`/`@remotion/*`/local)
   - `writeSceneProject(jobDir, spec, compId)` — writes `.tsx` + `Root.tsx` + `index.ts`
   - `cleanSceneProject(jobDir)` — clears old bundle artifacts before retry

         ↓
3. **@remotion/bundler bundle()** → bundles the .tsx entry
   **@remotion/renderer renderMedia()** → renders to MP4

         ↓
4. **remotion-verify.ts** — two-layer verification
   - `signal` gate: ffprobe checks dimensions + duration
   - `vision` check: extracts a settled frame (`-i file -ss 1.0`) + pluggable callback
   - `verifyClip()` returns `{ok, signal, vision?, note}`

         ↓
5. **Self-fix loop** (up to `maxRetries` = 5)
   - On failure: passes `variant: attempt` so `synthesize()` produces DIFFERENT code
   - `cleanSceneProject()` clears old bundle cache before re-bundling
   - Never varies for the same inputs without variant — this was FIXED

         ↓
6. **Integration**
   - Moves verified MP4 to `input/visuals/<job>_s<n>.mp4`
   - Script tag rewritten from `[GenMotion:]` to `[Visual: file]`
   - Controller returns `SceneResult[]` with status per scene
```

## 12 Synthesizer Kinds (remotion-codegen.ts)

Each produces a valid, self-contained `.tsx` composition:

| Kind | Description | Key features |
|------|-------------|-------------|
| `kinetic` | Typography scale-in with spring | Text with glow shadow, scale+opacity animate |
| `infographic` | Bar chart with labels | Animated bars (spring per bar), gradient fill |
| `hud` | Sci-fi radar sweep | Concentric circles + rotating scan line |
| `diagram` | Flow/block diagram | Numbered blocks connected by arrows, spring-in |
| `ui` | App mockup | Browser window with title bar + content cards |
| `map` | Route path animation | Dashed-line reveal + moving dot along path |
| `particle` | Varied particle system | Multi-seed color, wobble, per-frame movement |
| `procedural` | Geometric art | Rotating rects with time-varying position/color |
| `logo` | Brand reveal | Gradient circle + text with spring scale |
| `timeline` | Roadmap/steps | Connected nodes on a horizontal line |
| `spectrum` | Audio visualizer | Multi-frequency oscillator bars with hue cycling |
| `abstract` | Default gradient blobs | Blob background with screen blend, radial gradient |

**Retry diversity:** The `variant` parameter (0-5) changes particle seeds,
spectrum phases, and procedural offsets so each retry produces different output.
Without this, failures repeated identically.

## Key Files

| File | Purpose |
|------|---------|
| `src/agentic/media/remotion-codegen.ts` | Code author + synthesizer (508 lines) |
| `src/agentic/media/hermes-remotion-controller.ts` | Orchestrator loop (187 lines) |
| `src/agentic/media/remotion-verify.ts` | Frame verification (64 lines) |
| `src/agentic/operations/motion-render.ts` | Data-driven `[Motion:]` renderer (106 lines) |
| `src/agentic/media/motion-resolver.ts` | `[Motion:]` tag resolution (91 lines) |
| `src/agentic/orchestrator/remotion.ts` | Full pipeline `renderAgenticWithRemotion()` (198 lines) |
| `remotion-creation/` | 16 pre-built library compositions |
| `remotion/AgenticVideo.tsx` | Full pipeline composition (A1-A11) |

## remotion-creation Library (16 compositions)

```
remotion-creation/compositions/
├── KineticTypography.tsx       — Text scale-in with spring
├── BarChartInfographic.tsx    — Animated bar chart
├── ConfettiParticles.tsx      — Particle burst
├── NeuralNetwork.tsx          — Colored node network
├── HudRadar.tsx               — Sci-fi radar sweep
├── AuroraLoop.tsx             — Colorful aurora
├── TerminalTyping.tsx         — Typewriter effect
├── SpectrumVisualizer.tsx     — Frequency bars
├── PieChart.tsx               — Animated pie chart
├── LogoReveal.tsx             — Brand reveal with gradient
├── AudioReactiveSpectrum.tsx  — Audio-reactive bars
├── LowerThird.tsx             — Lower-third title
├── TimelineRoadmap.tsx        — Milestone timeline
├── LoadingSpinner.tsx         — Minimal spinner
├── FlowDiagram.tsx (2026-07-29) — Animated step diagram
└── AppUI.tsx (2026-07-29)     — App mockup interface
```

Use via `[Motion: FlowDiagram]` or `[Motion: AppUI@creation]`.

## Known Patterns & Pitfalls

1. **Retry without variant is pointless.** The `synthesize()` function is
   deterministic — identical inputs produce identical output. Always pass
   `variant: attempt` on retry (FIXED 2026-07-29).

2. **Clean before retry.** Remotion's `bundle()` caches aggressively. Call
   `cleanSceneProject(jobDir)` before re-bundling on retry to avoid serving
   stale bundles.

3. **Comma-inside-filter is a separator.** The `synthesize()` output template
   literals must avoid commas in inline style values — `{ color: '#7c3aed' }`
   is fine, but `fontFamily: 'system-ui, sans-serif'` would need escaping.

4. **`extractFrame` seek order.** Always use `-i file -ss N` (INPUT seek, `-ss`
   AFTER `-i`). The opposite (`-ss N -i file`) returns 0-byte on odd-keyframe
   streams and looks like a corrupt file.

5. **`require.resolve('ffmpeg-static')` may be a `.cmd` wrapper on Windows.**
   Use try/catch fallback to bare `'ffmpeg'` (FIXED 2026-07-29).

6. **ffmpeg dimension padding.** Some codecs round to even values — the probe
   check allows `Math.abs(dim - expected) <= 8` (FIXED 2026-07-29), not strict
   `===`.

7. **Operator precedence gotcha.** `p.durationSec ?? 0 > 0.05` parses as
   `p.durationSec ?? (0 > 0.05)` → `false` for missing duration. Always
   use `(p.durationSec ?? 0) > 0.05` (FIXED 2026-07-29).
