# AVS aspect / 4K / intro-outro / J-cut / palette triage (2026-07-28)

Triage-only bug hunt (full report: `workspace/bug-hunt/findings_aspect.md`).
Core structural lesson: **AVS has TWO render paths that consume DIFFERENT job fields**:
- `src/agentic/operations/compose.ts` (`composeVideo`) — honors `aspect`/`orientation`/`platform`
  via `resolveOutputSize` (compose.ts:~1019), `exportAspects` via `resolveAspectSizes`
  (advanced-fx.ts:452, supports 4K=3840x2160), `paletteFilter`.
- `src/agentic/orchestrator/render.ts` (`renderAgenticSlideshow`, driven by
  `src/adapters/cli/agentic-modular.ts`) — has its OWN `resolveRenderDims` (render.ts:23),
  builds intro/outro cards + J-cut + segmented concat.
Any field verified in one path may be a silent no-op in the other. Audit BOTH.

## Verified WORKING (don't re-hunt)
- compose `{"aspect":"1:1"}` → 720x720; `exportAspects:["4K","1:1","9:16"]` from landscape
  → 3840x2160 / 1080x1080 / 720x1280 (all ffprobe-confirmed). 4K is an upscale of the base — by design.
- paletteFilter `cyberpunk` → real colorbalance/eq re-encode (pal_*.mp4 non-zero).
- Agentic CLI intro+outro cards: render + concat fine (vision-verified grid); `orientation: square`
  works via `(res.plan as any)?.orientation` fallback at render.ts:380.

## Open bugs found (triage, unfixed)
1. **jCutSec dropped in modular CLI render call** — `agentic-modular.ts:612-625` builds the
   `renderAgenticSlideshow` opts without `jCutSec` (it IS written to job-meta.json at :193).
   render.ts:644 then defaults defaultJCut=0 → global J-cut is a silent no-op; only per-scene
   `[JCut:]` tags work. MEDIUM.
2. **exportAspects/4K ignored in orchestrator path** — render.ts:210 hardcodes
   `exportMultiAspect(mp4, ['9:16','16:9','1:1'])`; `resolveAspectSizes` is only called from
   compose.ts:650. Agentic CLI jobs can NEVER emit 4K. MEDIUM.
3. **Unknown palette presets are SILENT no-ops** — `buildPaletteFilter` (compose.ts:212)
   default → `''`; call site skips with no warning. `sunset`/`noir` render untouched with zero
   diagnostics (verified). Vocab inconsistency: `noir` exists as a LUT (lut-loader.ts:47) and
   a genre grade, but not as a palette. LOW-MED.
4. **`res.workspace.jobId` undefined in modular CLI render** → `_intro_undefined.mp4`,
   `undefined_publish-manifest.json` etc (render.ts:382-383 naming). LOW.
5. Dead expr: render.ts:29 `aspect ?? (orientation ? undefined : undefined)` — lost `platform`
   fallback vs the compose.ts twin. INFO.

## Harness notes
- Fast empirical loop for compose-path knobs: `workspace/bug-hunt/compose-direct*.mjs`
  (calls composeVideo directly with 4 local test clips; seconds instead of the full
  plan→voice→visuals→render pipeline). Pitfall: `fs.rmSync(outDir,{recursive:true})` throws
  EBUSY on Windows if a prior ffmpeg still holds `base.mp4` — use a FRESH outDir per variant
  (sed-clone the driver to compose-out2) instead of fighting the lock.
- Full-pipeline harness: `workspace/bug-hunt/harness.mjs <job.json> <name>` (plan→voice→
  visuals→render, serializes Kokoro via lockfile, emits a 4-frame vision grid to
  `workspace/bug-hunt/grids/<name>.jpg`). Intro/outro card verification = vision_analyze the grid.
- Quick per-file ffprobe dims: `"$FP" -v quiet -show_entries stream=width,height -of csv=p=0 f.mp4`.
