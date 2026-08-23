# AVS optional/key-gated feature pattern (verified this session)

When adding an advanced capability to AVS, follow this shape so it stays
free/offline/no-key by default and never breaks a run.

## The three-layer gating contract
1. **OFF by default** — add a `false`-default flag to `AgenticConfig`
   (`src/agentic/config.ts`) AND `PipelineRequest` (`src/agentic/orchestrator/types.ts`),
   e.g. `optimizeHook?: boolean`, `seo?: boolean`, `aiThumbnail?: boolean`,
   `publishYouTube?: boolean`.
2. **Key-gated** — the actual network call lives behind an `isXEnabled()` that
   returns false unless an env key is set (`VIDEO_GEN_*` / `IMAGE_GEN_*` /
   `YOUTUBE_ACCESS_TOKEN`). No key ⇒ function returns `''` / `null`.
3. **Graceful fallback** — every happy path returns `''`/`null` on any failure
   (4xx, 5xx, timeout, exception); the caller falls back to the stock/offline
   path. Nothing throws out of the acquire/publish/render path.

## LLM-assisted features (hook, SEO)
- Heuristic always runs (offline, no key).
- If `useLlm && brain.modelEnabled`, call `brain.completeJSONTask<T>(system, prompt, schemaHint)`.
  **Do NOT call the standalone `completeJSON(o, system, prompt, schemaHint)` directly**
  from outside `brain.ts` — its first arg is a `BrainOptions`, not a string; it is
  private to the module. `completeJSONTask` is the public, budget+circuit-breaker
  guarded method on `AgentBrain`.
- On any LLM failure/parse error, fall back to the heuristic result silently.

## visualPreference union (extend in lockstep)
When adding a new visual kind, widen the union in ALL of these or typecheck breaks:
`ScenePlan.visualPreference` (types.ts), `AgenticConfig.preferVisual` + `PipelineRequest`
(orchestrator/types.ts), `ScenePreview.visualPreference` (operations/preview.ts),
the `acquire.ts` scene-fetch tuple + `effectiveKind` coercion + results-loop
`rawKind === 'gen' ? 'image' : ...` + `rawKind === 'video-gen' ? 'video' : ...`,
and `gateway.ts` re-acquire coercion (`vp === 'gen' ? 'image' : vp === 'video-gen' ? 'video' : vp`).

## Real YouTube upload (Feature 2)
`publishToYouTube(opts)` in `delivery/publish.ts`: resumable Data API v3 — POST init
to `.../videos?uploadType=resumable&part=snippet,status` (read `location` header), then
PUT the binary to that URL. Token precedence: `opts.accessToken` > `YOUTUBE_ACCESS_TOKEN`
env > `refreshYoutubeToken()` (uses `YOUTUBE_REFRESH_TOKEN`+`CLIENT_ID`+`SECRET`). Returns
`{uploaded, videoId?, reason?}`; never throws. Only runs when `publishYouTube` flag set.

## Test-file gotchas (tsx)
- `node --import tsx` compiles test files as **CJS** when it detects CJS — top-level
  `await import(...)` FAILS ("Top-level await not supported with cjs output"). Use
  **static `import * as x from '...'`** at the top, not dynamic `await import`.
- Relative import paths resolve from the test file's own dir: a test in `src/agentic/`
  importing `src/agentic/delivery/publish.ts` must use `'./delivery/publish.js'`, NOT
  `'../delivery/publish.js'` (that resolves to `src/delivery/`, which does not exist).
- Mock servers: `http.createServer(...).listen(0,'127.0.0.1', cb)` — read `port` from
  `srv.address().port` INSIDE the listen callback; setting `process.env.X_BASE_URL` before
  `listen` resolves to `''` because the URL isn't known yet. Await the `mockServer()` helper.
- For upload tests, stub `globalThis.fetch` to short-circuit the Data API endpoints, then
  restore it; assert on `result.uploaded`/`reason`, not network exceptions.

## Pre-existing test failures (this box, local ffmpeg.exe)
brand-audioless 180-183, M5 280, revise-restitch 124 fail because the local `ffmpeg.exe`
lacks `-c:a aac` / real-ffmpeg is slow (240s timeout test). PROVE a new failure is not a
regression by `git stash`-ing your edits and re-running the specific failing file — if it
fails identically on the unmodified tree, it is pre-existing. Pass-count deltas (not raw
failure counts) are the regression signal.
