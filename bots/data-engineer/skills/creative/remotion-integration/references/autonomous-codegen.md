# Autonomous Hermes-controlled Remotion codegen (full capacity)

Verified in this repo (`C:\one\Automated-Video-Generator`, branch main). This is
the "Remotion used at full capacity" mode: the agent authors a NEW `.tsx` per
scene (not a preset), renders it, vision-verifies, self-fixes, and integrates
the clip into the main pipeline as a normal `[Visual:]` asset.

## Files (all under `src/agentic/media/`)
- `remotion-codegen.ts` — `authorRemotionComponent(spec)`, `assertSafeImports()`,
  `writeSceneProject(jobDir, spec, compId)`.
- `hermes-remotion-controller.ts` — `runRemotionController(scenes, opts)`,
  `extractMotionTags(script)`.
- `motion-resolver.ts` — `resolveMotion()` multi-library `[Motion: comp@lib]`.
- `motion-render.ts` — `renderMotionClip()` preset path.
- `REMOTION_AUTONOMOUS.md` — repo-local README for the subsystem.

## Authoring modes (remotion-codegen)
1. PROVIDED — `spec.code` (raw .tsx) used verbatim (agent wrote it).
2. GENERATED — `synthesize(spec)` emits a valid composition from
   `{kind,title,caption,data,labels,palette}`. Kinds: kinetic, infographic,
   hud, diagram, ui, map, particle, procedural, logo, timeline, spectrum,
   abstract. Add new kinds by extending the `switch` in `synthesize()`.
3. HELPERS — agent may also spawn reusable pieces into `<jobDir>/_lib/` and
   import them (allowlisted).

## Safety gate (assertSafeImports)
Generated `.tsx` may ONLY import: `remotion`, `react`, `@remotion/*`, `./`,
`../`. Blocks `fs`, `child_process`, `net`, `http`, etc. Reject with
`unsafe import blocked: "..."`. This is a hard gate, not a capability limit.

## Controller loop (runRemotionController)
```
for each MotionScene:
  for attempt in 0..maxRetries:
    spec = {...scene, code: attempt===0 ? scene.code : undefined}  // retry -> re-synth
    entry = writeSceneProject(jobDir, spec, compId)
    bundleLoc = await bundle(entry)                 // POSITIONAL entryPoint
    composition = await selectComposition({serveUrl, id:compId, inputProps:{}})
    composition.fps = fps; composition.width/height = ...   // fps NOT in select opts
    mp4 = renderMedia({composition, serveUrl, codec:'h264', outputLocation, concurrency:2})
    v = await verifyFrame(mp4, scene)               // ffprobe + optional vision
    if v.ok: return mp4
  return null  -> caller falls back to stock/user asset
copy verified mp4 -> input/visuals/<job>_s<n>.mp4
```
`extractMotionTags(script)` splits script by `\n` (one scene per line) and
matches `\[(GenMotion|Motion):\s*([^\]]+)\]` (case-insensitive). Returns
`{lineIndex: tagValue}`.

## Integration into main pipeline (zero compose changes)
The clip lands in `input/visuals/` and the scene tag becomes `[Visual: file]`.
The EXISTING visual-tag resolver then treats it like any user-supplied file.
Mixed final video = generated motion + downloaded/edited images + user video.

## What is NOT yet wired (documented honestly)
`runRemotionController` is built + unit-tested (6/6) + e2e-proven, but the
6-stage pipeline's tag parser / scene loop does NOT yet auto-invoke it. Today
it's driven by a manual e2e driver (`.mts` using dynamic `import()`). Next step:
hook `extractMotionTags` + `runRemotionController` into the planner → scene loop
and consume `Scene.visual.motion` in `compose.ts`.

## E2E recipe (verified working)
```bash
# needs Chrome: export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
# driver must use dynamic import (see tsx quirk) to load the controller
node --import tsx sample_genmotion_driver.mts
# -> writes input/visuals/sample_genmotion_s<N>.mp4 ; vision-check frames after
```
Verified result (later sample run, 5 `[GenMotion:]` scenes: diagram,
infographic, hud, timeline, spectrum) → **5/5 generated**, ffprobe-verified,
integrated to `input/visuals/`. 3 vision-checked: HUD (rings+sweep+SYS ONLINE),
timeline (4 milestone nodes alternating cyan/purple), spectrum (rainbow bars).

**Codegen template-literal GOTCHA (bit us, now fixed):** `synthesize()` builds
`.tsx` as a template string — EVERY dynamic value must be `${...}`-interpolated.
A bare `fill={i % 2 ? A : B}` is written verbatim into the output file and fails
at render with `i is not defined` (runtime scope bug; `assertSafeImports` won't
catch it). Fix: `fill={${i % 2 ? 'A' : 'B'}}` → emits `fill={A}`/`fill={B}`.
The retry loop must re-SYNTHESIZE with the fix, not re-render identical broken
code, or it loops on the same bug. (Timeline kind had exactly this; fixed.)

**Background-render error-swallowing:** `node --import tsx drv.mts > log 2>&1` in
a non-tty/background shell drops the Node stack (log shows only `stdin is not a
tty` + exit 1). Run e2e drivers FOREGROUND to see the real error.
