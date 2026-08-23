---
name: remotion-integration
description: >-
  Integrate, enhance, and debug Remotion-based video generation inside a
  codebase (e.g. an agentic text-to-video pipeline). Covers the LICENSE REALITY
  of Remotion templates, verified Remotion 4.x API gotchas (transitions/shapes/
  media-utils/render-pipeline signatures that differ from docs), the offline-safe
  verification workflow, CODE-ONLY motion-graphics composition recipes, and the
  autonomous Hermes-controlled codegen mode ([GenMotion:] → author new .tsx →
  render → verify → self-fix → integrate). Use whenever asked to "use Remotion
  more fully", "generate motion graphics from scratch", add transitions/captions/
  waveforms/intro cards, or vendor/clone template repos into a project.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Remotion Integration (license-safe, API-correct)

## When to use
- Adding Remotion features: scene transitions, caption styles, intro/outro
  cards, audio waveforms, kinetic text, motion graphics.
- Cloning / studying Remotion template repos to reuse ideas.
- Debugging Remotion 4.x compile errors around transitions/shapes.
- Building CODE-ONLY motion graphics (no external images/video/audio) or a
  standalone experimental Remotion sub-project → see
  `references/code-only-compositions.md` (scaffold pattern that reuses the parent
  node_modules, 8 proven composition recipes, render+verify workflow).

## Golden rule — LICENSE (verify before you clone)
The user ships commercially and demands **zero license issues**.

- ❌ **Official `remotion-dev/*` templates are NOT open-source.** Their
  `package.json` is `"private": true` + `"license": "UNLICENSED"`. Copying or
  vendoring them is a license violation AND breaches Remotion's own license
  clause (no copying/modifying Remotion code to relicense a derivative).
  → **Study patterns by reading only. Never `import` from a cloned template.**
- ✅ **MIT community repos are safe to reuse** (re-implement the technique as
  your own code; don't copy verbatim into main `src`).
- ⚠️ **Remotion core license:** Free for individuals / for-profit orgs ≤ 3
  employees / non-profits. Disallowed: selling or relicensing a Remotion
  derivative. A >3-employee company product needs a paid Company License.

### Verify a repo's license BEFORE cloning (don't trust the README)
```bash
# raw LICENSE file (branch main, then master)
lic=$(curl -s --max-time 20 "https://raw.githubusercontent.com/OWNER/REPO/main/LICENSE")
[ -z "$lic" ] && lic=$(curl -s --max-time 20 "https://raw.githubusercontent.com/OWNER/REPO/master/LICENSE")
echo "$lic" | grep -iE "MIT License|Apache|GPL|BSD|Mozilla|UNLICENSE" | head -1
# or package.json license field + GitHub API spdx
curl -s "https://api.github.com/repos/OWNER/REPO/license" | grep -oE '"spdx_id":[^,}]*'
```
If empty/unlicensed → **exclude** (unverified = unsafe for commercial).

### Confirmed MIT (commercially safe) repos — study + re-implement
`lifeprompt-team/remotion-scenes` (201 scenes), `degueba/onda` (transitions),
`ahgsql/remotion-subtitles` (caption styles), `ahgsql/remotion-animation`,
`stefanwittwer/remotion-animated`. (Verified via raw LICENSE fetch this session.)

## Verified Remotion 4.0.487 API (differs from docs — DO NOT guess)
See `references/remotion-4x-api.md` for full detail. The top traps:
- `@remotion/transitions`: built-in presentations from the **main entry**
  (`@remotion/transitions`) are ONLY `crossZoom`, `dreamyZoom`, `filmBurn`,
  `linearBlur`. The others (`slide`, `wipe`, `flip`, `dissolve`, `iris`, `swap`,
  `zoomBlur`, `ripple`, `clockWipe`, `bookFlip`, `zoomInOut`, `none`) are
  **subpath-only exports** — you MUST import them from their subpath, e.g.
  `import { slide } from '@remotion/transitions/slide'` and
  `import { wipe } from '@remotion/transitions/wipe'`. Importing `slide`/`wipe`
  from `@remotion/transitions` main throws `(0, esm_namespaceObject.slide) is
  not a function` at render. (Correction vs earlier notes that claimed these are
  "not prebuilt" — they exist, just not on the main entry.)
- Transition presentation signatures (verified against installed d.ts):
  `crossZoom({ strength? })`, `filmBurn({ seed? })`, `linearBlur({ intensity? })`
  — they take a **single options object, NO `durationInFrames`** (the duration
  lives on `<TransitionSeries.Transition timing={linearTiming({durationInFrames})}>`).
  `slide({ direction?: 'from-left'|'from-right'|'from-top'|'from-bottom' })`,
  `wipe({ direction?: 'from-left'|...|'from-bottom-right' })` — note the
  `WipeDirection` type is `from-*` (NOT `to-left`/`to-right`); `wipe({direction:'to-left'})` throws `Unknown direction "to-left"`.
- **Headless-GPU trap (HIGH impact, verified repeatedly this session):** the
  canvas/WebGL shader transitions — `crossZoom`, `filmBurn`, `linearBlur`, AND
  `wipe`, `dissolve` (these two also use canvas polygons) — **HANG under headless
  Chrome without a real GPU** (render never completes; `delayRender` timeout or
  silent hang). `slide` is pure CSS transform → headless-safe. DEFAULT every
  transition to `slide` in the autonomous/headless path; only enable the richer
  shader transitions when a GPU is present (e.g. `allowShaderTransitions: true`).
  `chromiumOptions: { gl: 'swiftshader' }` on `renderMedia`/`renderStill` does
  NOT reliably unblock them headless. A 3-scene `<TransitionSeries>` with 2
  transitions takes ~2-3 min to render headless — run it **foreground with a
  ≥280s timeout**; a 60s background-harness clamp will kill it and look like a
  code bug. Full reproduction kit: `references/headless-transitions.md`.
- `@remotion/shapes` `Circle` takes **`radius`** (not `size`).
- `@remotion/media-utils`: `getAudioData(src)` (async, can reject) →
  `visualizeAudio({audioData, frame, fps, numberOfSamples}): number[]`.
- **Programmatic render pipeline** (`@remotion/bundler` + `@remotion/renderer`):
  `bundle()` is POSITIONAL (`bundle(entryPoint)`), `selectComposition()` has NO
  `fps` key (set `composition.fps` after), and `probeAsset()` returns
  `durationSec` not `durationFrames`. Full pattern + gotchas in
  `references/remotion-4x-api.md` under "@remotion/bundler + @remotion/renderer".
- **Remotion as a generated visual source**: add a third `[Motion:]` visual
  source (multi-library `@library`) to an agentic pipeline — recipe +
  reference impl in `references/remotion-4x-api.md` under "Using Remotion as a
  generated visual source".

## Autonomous codegen mode (Hermes-controlled, FULL capacity)
When the user wants Remotion used at its **full capacity** (not just safe
presets), the agent **authors a brand-new `.tsx` per scene** instead of
re-implementing a template. Verified pattern in THIS repo (`src/agentic/media/`):
- `remotion-codegen.ts` → `authorRemotionComponent(spec)` synthesizes a valid
  composition from `{kind,title,data,labels,palette,code}`; `assertSafeImports()`
  blocks anything outside `remotion`/`react`/`@remotion/*`/local helpers;
  `writeSceneProject()` emits scene + Root + index into a per-job folder.
- `hermes-remotion-controller.ts` → `runRemotionController(scenes,opts)`:
  parse `[GenMotion:]`/`[Motion:]` tags → codegen → `bundle(entryPoint)` +
  `selectComposition({serveUrl,id,inputProps})` + `renderMedia()` → ffprobe
  verify → **self-fix retry loop** (rewrite `.tsx`, re-render) → **fallback to
  stock** → copy clip to `input/visuals/<job>_s<n>.mp4` and rewrite the scene
  tag to `[Visual: file]` (reuses the existing resolver — zero compose changes).
  See `references/autonomous-codegen.md` for the full recipe + what's NOT yet
  wired into the 6-stage pipeline.
- `remotion-verify.ts` → `verifyClip()` runs ffprobe (signal) AND, when a
  `visionCheck` callback is supplied, extracts a settled frame and confirms the
  subject matches the intended scene — this is the **vision-in-loop** gate that
  makes the self-fix loop enforce "verified visually", not just "rendered".
- `remotion-sequence.ts` → `renderSequence()` renders ALL scenes in ONE bundle
  with `<TransitionSeries>` transitions between them (headless-safe `slide`
  default; `allowShaderTransitions` for GPU); `renderStillClip()` uses
  `renderStill` to emit a generated **PNG** (cover/lower-third/thumbnail) into
  `input/visuals/`. This is the "Remotion should also generate images" path.
- Config (`AgenticConfig`): `autonomousMotion`, `motionMaxRetries`,
  `motionAutoDecide`, `motionLibrary` (`{name: folder}` for the
  `[Motion: comp@library]` multi-location syntax).
Trigger: "use Remotion fully", "generate motion graphics from scratch",
"agent writes the Remotion code", or a `[GenMotion: <free description>]` tag.
Full recipe + what's-not-yet-wired: `references/autonomous-codegen.md`.

## Mixed-source pipeline integration (proof-everything-works test)
The user's standing ask: "make ONE video that mixes downloaded Pexels
images/videos WITH Remotion-generated motion — verify it all works." This is
the end-to-end check that downloaded stock + autonomous motion compose into a
single correct timeline. Verified recipe (Pexels fetch + Remotion codegen +
ffmpeg concat, one frame vision-checked per segment): `references/mixed-source-pipeline.md`.
Key facts it captures: the `.env` `PEXELS_API_KEY` is live but drivers must call
`dotenv.config({path:'.env'})` themselves or the fetcher silently falls back to
Openverse with 0 results; `downloadMedia()` errors undefined on Pexels URLs so
download via Node 22 `fetch` instead; compose with ffmpeg (the controller isn't
auto-wired into `compose.ts` yet); verify by extracting one frame per segment
and vision-checking content + ORDER.

**tsx driver quirk (verified):** a top-level `import { x } from './foo.ts'` in
a NodeNext project can throw `does not provide an export named 'x'` when run via
`node --import tsx`. Use a **dynamic `import()`** in smoke/e2e drivers to load
the controller — static import works fine inside the app/test runner.

**Continuous-combination harness (reusable):** `scripts/batch_combo_harness.mts`
is a ready-to-run verifier for the "prove everything works" ask. It builds 5
orderings (video-led / Remotion-led / interleaved / Remotion-adjacent /
mixed-pairs) from 3 videos + 3 images + 3 Remotion clips, composes each to
`output/batch/round_<R>/`, extracts ONE frame per segment, and writes
`workspace/batch_report_<R>.txt` (R|combo|seg|tag|type|desc|frame=OK). Run it
with a different ROUND arg each time (e.g. `R1`, `R2`) — the seed varies the
shuffled orderings so every round yields DIFFERENT combinations. Re-run for N
rounds to continuously stress-test the full mixed-source workflow; vision-check
the Remotion segments separately.

**Background-render error-swallowing (verified):** launching an e2e driver as
`node --import tsx drv.mts > log 2>&1` in a non-tty/background shell DROPS the
Node stack trace (log shows only `stdin is not a tty` + exit 1). Run e2e/remotion
drivers **foreground** (or capture via `process.on('unhandledRejection')` +
explicit `console.error(e.stack)`) to see the real error. Headless Chrome render
itself is fine in background; only the Node stderr capture is unreliable there.

**Codegen `.tsx`-via-template-literal GOTCHA (verified, bit me):** when
`authorRemotionComponent()` builds a `.tsx` source as a template string, EVERY
dynamic value must be interpolated with `${...}`. A bare JSX expression like
`fill={i % 2 ? A : B}` is written verbatim into the output file and references an
**undefined variable at render time** → `i is not defined` / `A is not defined`.
Fix: interpolate the whole expression, e.g. `fill={${i % 2 ? 'A' : 'B'}}` (so it
emits `fill={A}` or `fill={B}`). Same trap for any `key={i}`, `x={i*420}`, etc.
The `assertSafeImports()` gate does NOT catch this (it's a runtime scope bug, not
an import). The **self-fix retry loop must re-SYNTHESIZE with the fix**, not just
re-render identical broken code — wire the retry to patch the generator, or it
loops forever on the same bug.

## Workflow (offline-safe)
1. Clone MIT study repos into an isolated folder (e.g. `remotion/_study/`) —
   **never into `src/`**, never imported by main code.
2. **Exclude the study folder from tsconfig** so broken `React` UMD imports in
   cloned repos don't break `tsc`:
   `"exclude": [..., "remotion/_study"]`.
3. Re-implement desired patterns as NEW components in the project's `remotion/`
   using only already-installed `@remotion/*` packages (zero new deps).
4. `npm run typecheck` must be clean.
5. **User mandate: do NOT push to GitHub until explicitly approved.** Verify
   locally only. Also: "use only the main project code — don't pull in
   unwanted template pieces." → re-implement, don't vendor.

## Visual verification (DO IT — Chrome is often already installed)
Do NOT assume the box is Chromium-less. **Look for Chrome first**, then render
for real. See `references/visual-verification.md` for the full recipe. Summary:
1. Probe common paths before giving up:
   `C:/Program Files/Google/Chrome/Application/chrome.exe`,
   `/c/Program Files (x86)/...`, `which google-chrome chromium`.
2. Export `CHROME_EXECUTABLE=<path>` (the pipeline's chrome-gate reads this).
3. **Render a short VIDEO via `npx remotion render <Comp> out.mp4 --props=... --frames=0-149`, NOT `remotion still`.** `renderStill` recopies the whole `public/` dir and often fails to serve an ad-hoc `staticFile()` image → scene renders **black** (missing image = hard crash; present-but-unserved = silent black). `renderMedia` (the production path) serves assets correctly.
4. Extract frames with ffmpeg-static (`-ss <t> -frames:v 1`) and vision-check.
5. **Extract SETTLED frames, not mid-animation.** A spring/kinetic title at
   frame 15 looks "fragmented/doubled" simply because later characters haven't
   sprung in yet. Pick a frame well after the entrance (e.g. 40+) before
   concluding there's a bug. Zoom-crop the caption region to judge subtle glow.
- Always report typecheck-clean vs visually-verified separately.

## renderStill + TransitionSeries pitfalls (verified this session)
- **`renderStill` frame-out-of-range:** `renderStill({ frame: N })` throws
  `Cannot use frame N: Duration of composition is 1, therefore the highest
  frame that can be rendered is 0` if the still `Composition` has
  `durationInFrames={1}`. Always give the still Composition a real duration
  (e.g. `durationInFrames={120}`) so `frame: 30` is valid.
- **One bundle for the whole sequence:** author a single `Root.tsx` that stacks
  all scenes inside `<TransitionSeries>` (each in a `<TransitionSeries.Sequence
  durationInFrames={...}>`, transitions in `<TransitionSeries.Transition
  presentation={...} timing={linearTiming({durationInFrames})} />` between them),
  then `bundle(entry)` + `renderMedia()` ONCE. This is far faster than re-bundling
  per scene and gives native Remotion transitions (the headline feature).
- **`delayRender` timeout vs silent hang:** a bad transition presentation (wrong
  import path or invalid direction) surfaces as a `delayRender` timeout error at
  frame 0; a GPU-less canvas-shader transition instead hangs silently (no throw).
  Distinguish by running foreground with a timeout and capturing the stack — see
  the "Background-render error-swallowing" note above.

## Rendering pitfalls found in the field (fix these)
- **Ghost / doubled caption:** rendering BOTH a static `SubtitleOverlay` AND
  `KaraokeCaptions`/styled captions stamps the text twice (faint duplicate
  under the main line). Make them **mutually exclusive** — karaoke/styled when
  word-timed cues exist, static overlay otherwise (`cond ? <Karaoke/> : <Overlay/>`).
- **Kinetic per-char text stretches edge-to-edge:** if the outer `AbsoluteFill`
  is the flex `row`, characters spread across the whole frame and decorative
  rings overlap them. Keep the outer node a pure centering container and put the
  characters in an INNER width-bounded (`maxWidth:'90%'`), wrapping, centered row.
- **Overlay title collides with card's own title:** when overlaying a kinetic
  title on an intro/outro card that already renders its title, add a `hideTitle`
  flag so the card skips its plain title (and hide its centered decorative ring).
- **"Neon" glow washed out:** a neon caption diluted by the brand accent reads
  as plain white. Use a FIXED electric-cyan halo (`text-shadow` stacked blurs)
  so the neon identity is unmistakable regardless of brand color.
- **Dead opt-in props:** don't leave a prop (e.g. `richTransitions`) + its
  import declared but never wired into rendering. Either wire it or remove it —
  KISS. Note: a bare `TransitionSeries` drops per-scene captions/kenBurns/kinetic
  the manual path carries, so wiring it naively regresses features.

## Verification limits (be honest)
- Remotion browser render needs Chromium. If Chrome truly isn't present, the
  chrome-gate falls back to ffmpeg (which does NOT exercise the Remotion `.tsx`)
  — but ALWAYS probe for Chrome first (see above); it's frequently installed.
- Always state typecheck-clean vs visually-verified separately.
