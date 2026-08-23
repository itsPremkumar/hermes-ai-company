# AVS Control-Surface Architecture — field-flow map

How a script-JSON option reaches the rendered video. Use this to add new
options or debug "parsed but doesn't affect output" bugs.

## Whole-video (top-level JSON) flow
```
agentic-scripts.json
  → AgenticCliJob (cli-job.ts)
  → buildPipelineRequest() (cli-job.ts: pure)
  → PipelineRequest (orchestrator/types.ts)
  → runAgenticPipeline() reads req.* into cfg / call sites (pipeline.ts)
```

## Per-scene inline `[Tag:]` flow (the long chain)
```
script string "[Tag: value] ..."
  → parseScript() (lib/script-parser.ts)
       • regex match + var assignment (parseScriptLocally)
       • .replace() strips tag from spoken text
       • Scene[] push sites (4×) carry the field
  → ScenePlan (agentic/types.ts)        [added field]
  → toScenePlans() (pipeline/plan.ts)    [maps Scene → ScenePlan]
  → computeStylePlan() (ai/style-engine.ts)
       • SceneStyle gets the field (per-scene override)
  → render.ts per-scene override loop    [copies ScenePlan → SceneStyle]
  → ffmpeg filter graph (render.ts)      [CONSUMES it per-scene]
```

## The 6 per-scene tags added (reference implementation)
Tags: `[CaptionTheme:]` `[Sfx:]` `[JCut:]` `[Vignette:]` `[Kinetic:]` `[MusicIntensity:]`

| Field | ScenePlan | style-engine | render consumption |
|-------|-----------|--------------|--------------------|
| captionTheme | types.ts | SceneStyle.captionTheme | resolveCaptionTheme per-scene in BOTH render paths (captionFile loop + segmented loop) |
| sfx | types.ts | SceneStyle.sfx | planSceneSfx() skips scene if sfx===false (sfx-selector.ts) |
| jCutSec | types.ts | SceneStyle.jCutSec | audio-delay loop reads stylePlan.scenes[visuals[i].sceneIndex].jCutSec |
| vignette | types.ts | SceneStyle.vignette | single global filter; if ANY scene sets vignette===false → disabled |
| kineticText | types.ts | SceneStyle.kineticText | computeStylePlan suppresses kinetic cues when kineticText===false |
| musicIntensity | types.ts | SceneStyle.musicIntensity | buildDuckExpression(duckForScene) maps calm/mid/energetic → duck depth |

## Gotcha: render reads globals from opts.*
The renderer computes `const theme = resolveCaptionTheme(opts.captionTheme)`
ONCE and applies to all scenes. To make it per-scene you MUST move the
resolution INSIDE the per-scene loop and read `stylePlan.scenes[i].captionTheme
?? opts.captionTheme`. Same for kinetic gate, vignette, jCutSec, musicIntensity.

## Top-level fields reachable from script JSON (verified working)
aiVerify, pruneWorkspaces, brain, dryRun, defaultVisual, agent
(mapped in buildPipelineRequest + read in runAgenticPipeline), plus the
37 pre-existing PipelineRequest fields and 13 inline [Tag:] types.

## `platform` → output aspect (added Wave I, 2026-07-24)
`platform` (`tiktok`/`youtube`/`instagram`/`reels`) was previously AI-style
only. It now flows: `AgenticCliJob.platform` → (read in `composeVideo`) →
`resolveOutputSize(job)` (pure exported fn in `compose.ts`) → output W×H.
Maps: tiktok/reels→9:16, instagram→1:1, youtube→16:9. Precedence:
explicit `aspect` > explicit `orientation` > `platform` default >
portrait. Unit test: `src/agentic/operations/compose-output-size.test.ts`
(12 cases). Note `platform` is NOT a PipelineRequest field that reaches
`compose.ts` via the pipeline graph — `composeVideo` reads `job.platform`
directly off the passed `ComposeInput.job` (`AgenticCliJob`).
