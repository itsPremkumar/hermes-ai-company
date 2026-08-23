# AVS visual defects caught only by frame inspection

Typecheck + 36 unit tests + ffprobe dimension checks all PASSED while the videos
were visually broken. These were found by extracting frames and calling
`vision_analyze`. Capture them so they are not "re-fixed" blindly and so the
visual gate is never skipped.

## Defect 1 — orientation ignored (landscape/square → portrait)
- **Symptom (vision):** a job declared `orientation: landscape` rendered a portrait
  frame (tall, letterboxed); `square` rendered as portrait too.
- **Root cause:** `src/adapters/cli/agentic-cli.ts` called `renderAgenticSlideshow`
  WITHOUT passing `orientation`/`dimensions`. `render.ts` defaults `W=720,H=1280`
  (portrait) when `opts.dimensions` is undefined. The orientation was parsed into the
  plan but never reached the renderer.
- **Fix:** build `ORIENT_DIMS = {portrait:{720,1280}, landscape:{1280,720},
  square:{1080,1080}}` in the CLI and pass `dimensions: ORIENT_DIMS[orient]` into the
  render opts. Verified: landscape `1280,720`, square `1080,1080`, portrait `720,1280`,
  and all `_16x9`/`_1x1`/`_9x16` variants correct.
- **Commit:** `058c1a7`.

## Defect 2 — watermark black-box on every video
- **Symptom (vision):** a solid dark/grey square in the bottom-right corner of every
  frame.
- **Root cause:** `render.ts` Pass-3 logo overlay ran whenever `logoPath` existed
  (`input/visuals/logo-automation.png`). That file is `rgb24` (NO alpha) with an opaque
  black background, so overlaying it stamped a black box. It also ran even when `brand`
  was not set.
- **Fix:** (a) gate the overlay on `opts.brand` (opt-in, matches the documented control
  surface); (b) skip when the logo has no alpha channel (`ffprobe` pix_fmt regex
  `/rgba|argb|ya8|ya16|graya|ga|:a$|a@/`). Also widened `RenderOpts.brand` to
  `{watermark?, accent?}`.
- **Commit:** `058c1a7`. Note: a transparent PNG logo WILL now composite correctly.

## Defect 3 — untranslated multilingual burned captions
- **Symptom (vision):** `language: hi-IN` (or ta/fr/de) job — audio tagged Hindi but the
  burned caption was English (`"Voiceover scene one in hi-IN."`). Only the SRT *sidecar*
  was localized, not the on-screen caption.
- **Root cause:** burned caption text always came from `voiceoverText` (English);
  `render.ts` had no `captionText` concept. `pipeline.ts` localized only SRT/VTT.
- **Fix:** (a) `types.ts` added optional `ScenePlan.captionText`; (b) `render.ts` burned
  paths prefer `captionText ?? voiceoverText` (2 sites: scText at ~L485, kinetic raw at
  ~L614); (c) `pipeline.ts` after `applyProEdits`, when `targetLang !== 'english'` and
  `brain` present, `translateScenes(sceneTexts, lang, brain)` and stash into
  `captionText`; guarded (no model configured → English fallback, no regression); (d)
  new `src/agentic/media/translate.ts` reuses `AgentBrain.completeJSON<T>(system, prompt,
  schemaHint)` (the sanctioned zero-cost LLM path) — `completeJSON` is the PUBLIC method
  on `AgentBrain` (class is `AgentBrain`, NOT `Brain` — that name is wrong and breaks
  typecheck).
- **Status at session end:** implemented, typecheck clean, 36/36 unit tests pass, NOT
  yet committed. Re-run multilingual jobs and vision-check that captions match the voice
  language once a free model is configured (offline → stays English gracefully).

## Isolation trick: fixture artifact vs real bug
The `persp_*.png` fixtures bake label text (e.g. "AERIAL VIEW") into the image. A vision
report of "caption overlaps the AERIAL VIEW text" is the FIXTURE, not a code bug. To
prove it: render one job with a clean no-text source (`persp_clean.png` = plain gradient
SVG via sharp), vision-check the frame. If no job-title/prompt text leaks, the pipeline
is correct. This session used exactly that to disprove a false "title leak" report.

## Hard rule
A combinatorial batch is NOT verified until frames have been looked at with
`vision_analyze` — typecheck + unit + ffprobe are necessary but NOT sufficient.
