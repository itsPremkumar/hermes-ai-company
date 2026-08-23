# AgentBrain — free-model decision layer for the agentic video pipeline

Captured from the "agent makes every decision at advanced level" session. The
project constraint is **FREE + ONLINE-ALLOWED + VERIFIABLE** (user clarified:
"i need free okay ... i can use online tools and network ... but i need free").

## Architecture
`src/agentic/brain.ts` exposes `AgentBrain` with one method per decision point:
- B1 `writeScript(topic, title)` — narrative-arc script
- B2 `expandKeywords(sceneText, title, n)` — scene-specific search queries
- B5 `narrativeOrder(sceneTexts)` — full arc reorder (not just hook-word regex)
- B7 `deriveMusic(sceneTexts, title)` — music matched to emotional arc
- B10 `generateMetadata(title, scenes)` — SEO title/description/hashtags
- B3/B9 `visionVerify(filePath, keywords)` — image relevance / QA (vision model)

## Free model wiring (no paid keys)
- `OPENROUTER_API_KEY` + `OPENROUTER_MODEL` (default `meta-llama/llama-3.1-8b-instruct:free`)
- OR `OLLAMA_URL` + `OLLAMA_MODEL` (local, e.g. `llama3.1`)
- Vision: `OPENROUTER_VISION_MODEL` (default `google/gemini-2.0-flash-thinking-exp-1219:free`)

## CRITICAL pattern: heuristic fallback on EVERY method
The pipeline MUST never crash or hang on the model. Every `completeJSON()` call:
1. returns `null` if no key/URL configured, offline, rate-limited, or parse fails
2. the CALLER falls back to the existing `*Heuristic()` function when result is `null`

So: `const script = cfg.writeScript ? await cfg.writeScript(...) : writeScriptHeuristic(...)`.
With no key the pipeline produces the same deterministic output as before (offline-safe);
with a free key it upgrades to model-driven decisions. A live E2E with NO key proves
the fallback path still works and gates pass.

## JSON extraction is non-trivial
`extractJSON()` strips ``` fences, then scans for the first balanced `{`/`}` or `[`/`]`
(tracking string/escape state) — because models return prose around the JSON. Don't
`JSON.parse` the whole response; it usually fails.

## AbortController timeout
Every fetch gets `AbortController` + `setTimeout(..., timeoutMs ?? 20000)` so a slow
free endpoint can't hang the render budget (see P24 — offline runs already blow the
shell timeout; a hung model call is the same trap).

## Caveat for the verifier
The model CALL can't be E2E-verified without the user's free key, but the WIRING +
heuristic fallback IS verifiable (tsc + suite + a no-key render). Don't claim "AI
decisions active" unless you confirmed a key was present in the run env.
