# AVG — Image Diversity, Legacy Porting & Repo Verification Gotchas

Concrete recipes from the session that finished per-scene visual diversity + ported
3 legacy features (local assets, default-visual, scene-edit API) into the agentic system.

## 1. Per-scene image diversity — the recurring bug class

Symptom: every scene renders the SAME photo, OR a non-topic photo (e.g. a "walking"
video shows a coffee photo). This happened repeatedly; root causes, in order found:

### Cause A — fetchVisualsForScene returns the FIRST keyword's top result for all scenes
`fetchVisualsForScene(keywords)` loops individualQueries and returns the FIRST keyword
with results. Every scene's keyword list started with the topic noun ("coffee") → all
scenes returned Pexels' same #1 photo.
**Fix:** `getImagePool()` in `orchestrate.ts` pre-fetches ONE pool of ~12 photos for the
cleaned topic noun, then assigns scene `i` → `pool[i % pool.length]`. Guarantees distinct
real photos. (Verified: coffee video → 3 distinct photos `27860686`/`31711944`/`38466981`.)

### Cause B — topic noun too weak / polluted
"5 fascinating facts about coffee" → if you don't strip stopwords+numbers, the search query
is the whole phrase and Pexels returns nothing useful / collapses.
**Fix:** `topicNoun = topic.split(/\s+/).filter(w => !/\d/.test(w) && !STOPWORDS.has(w.toLowerCase())).join(' ')`
with `STOPWORDS = {a,an,the,of,about,for,on,to,in,5,fascinating,facts,benefits,how,what,why,from,...}`.
Result: "5 fascinating facts about coffee" → "coffee". Same extraction feeds the pool.

### Cause C — cache-poisoning (off-topic photo served to a different topic)
The last-resort fallback query in the fetch ladder was hardcoded `'coffee'`. When Pexels
returned nothing for a real topic (e.g. "walking" → Pexels genuinely returns EMPTY for
"walking"/"person walking"/"walking outdoors"), the ladder fell to `fetchVisualsForScene(['coffee'])`
→ `.video-cache.json` hit → coffee photo served to the walking video.
**Fix:** last-resort ladder entry uses the topic noun, not "coffee":
`ladder.push([topicNoun || 'coffee', 'nature', 'city', 'technology'].slice(0, 1))`.
Now a missing image falls back to a bright card, never an off-topic cached photo.

### Cause D — dead hosts (Flickr/Openverse 502) pass the usable filter
Flickr URLs 502 on download. If they reach the render, the scene is black/broken.
**Fix:** reject dead hosts in the usable filter: `DEAD_HOSTS = /flickr\.com|staticflickr\.com|live\.staticflickr/i;`
drop any pool pick matching it. Also `OPENVERSE_ENABLED=false` for offline runs.

### Cause E — bright placeholder was navy → falsely flagged black by X10
`makePlaceholder` painted navy (luma ~14.6) which falls under blackdetect `pix_th=0.15`
→ X10 false-fail.
**Fix:** placeholder is now BRIGHT (luma > 60) and is written INTO the scene dir on download
failure (not just /tmp) so the render finds a real frame, never a black gap.

### Diagnostic order when "all scenes same / wrong photo"
1. `cat .video-cache.json` (repo root) — look for cross-topic entries (e.g. `image:coffee:portrait` being served to a non-coffee run). rm -f it and re-render to rule out staleness.
2. `curl -s "https://api.pexels.com/v1/search?query=<topicNoun>&per_page=3" -H "Authorization: <PEXELS_API_KEY>" | head` — confirm Pexels actually returns results for the noun. Empty → the pool will be empty → bright-card fallback (expected, not a bug).
3. Check `candidates.json` `source` field per scene: `local-asset` (user file), `pexels` (pool), or placeholder. Wrong topic + `pexels` → Cause C/B. Same `pexels` id across scenes → Cause A.

## 2. Porting a legacy feature into the agentic system (P1 pattern)

Legacy system (`src/video-generator.ts` + `src/lib/*` + `src/infrastructure/pipeline/scene-editor.ts`)
has features the 2-day agentic system lacked. Port by REUSING already-tested `src/lib/*`
code — do not rewrite. Concretely done this session:

- **Local asset reuse (P1a):** add `localAssets?: string[]` to `AgenticConfig` +
  `PipelineRequest`; distribute round-robin into `ScenePlan.localAsset` in `runAgenticPipeline`;
  in `acquire.ts`, if `scene.localAsset` set and `inputAssetPath(scene.localAsset)` exists,
  `copyFileSync` into the scene dir and `continue` (skip stock fetch). Source tag = `local-asset`,
  url = `local://<file>`. Reuses `inputAssetPath` from `src/lib/path-safety.ts`.
- **Default-visual fallback (P1b):** add `defaultVisual?: string`; in the `download` wrapper
  (orchestrate.ts), on final failure call `useDefaultVisual()` which copies
  `inputAssetPath(req.defaultVisual)` into the dir before the bright card. Mirrors legacy
  `default.mp4` behavior.
- **Scene-edit API (P1c):** new `src/agentic/scene-edit.ts` with `reorderScenes`/`deleteScene`/
  `updateScene`/`insertScene` operating on a **persisted `plan.json`** in the workspace
  (write it via `writeJson(workspace, 'plan.json', plan)` right after `acquireAssets`).
  Renumbers `sceneNumber` + recomputes `totalDurationSec`. This is what lets a NEW agent edit a
  video without re-running the pipeline. Modeled on legacy `scene-editor.ts` but uses the
  agentic workspace files.

CLI wiring: add `--local-assets "a.jpg,b.mp4"` + `--default-visual "default.jpg"` to
`bin/agentic-auto.ts`; thread them through `autopilot.ts` request spread
(`localAssets: req.localAssets ?? cfg.localAssets`).

**Gap-analysis→port discipline:** produce a feature-comparison table (legacy vs
agentic-ffmpeg vs agentic-Remotion), mark each GAP DONE/PENDING, prioritize P1 (reuse tested
code, high ROI) before P2 (needs online TTS/vision). Keep legacy `input/input-scripts.json`
workflow UNTOUCHED (user rule). Save the analysis as `agentic-pipeline/GAP_ANALYSIS.md`.

## 3. Repo verification gotchas (AVG)

### Lint: `bin/*.ts` reports a PARSING ERROR — it is NOT a code defect
`npx eslint bin/agentic-auto.ts` → `error Parsing error: "parserOptions.project" has been
provided ... bin/agentic-auto.ts was not found in any of the provided project(s)`.
This fires because `bin/**` is NOT in `tsconfig.json`'s `include`, so eslint's TS parser
can't resolve the file's project. It is a pre-existing config artifact, independent of your
edits. **Do not "fix" it or count it as a failure.** Verify the real program instead:
`npx eslint src/agentic/*.ts` → expect 0 errors (90 pre-existing style warnings: eqeqeq,
no-require-imports, etc. — author style, ignore).

### Verification commands (current, this session)
- Typecheck: `npx tsc -p tsconfig.json --noEmit` → EXIT 0 (strict whole project).
- Tests: `npx tsx --test "src/**/*.test.ts"` → **201 tests / 200 pass / 1 skip / 0 fail**
  (18 suites) as of the P1 commit `627dcc4`. Changed-area quick check:
  `npx tsx --test "src/agentic/scene-edit.test.ts" "src/agentic/agentic.test.ts"`.
- Live E2E (local assets): `npx tsx bin/agentic-auto.ts --topic "..." --local-assets "a.jpg,b.jpg" --no-sfx --max-attempts 1` → inspect `candidates.json`: expect `source:"local-asset"`, `url:"local://a.jpg"` etc., and all X7–X15 gates PASS.
- Visual verify: extract frames + `blackdetect` (same check as X10):
  `FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")`;
  `"$FFMPEG" -i render/<job>.mp4 -vf "blackdetect=d=0.3:pix_th=0.15" -f null -` → no `black_start` output.
- Lint program: `npx eslint src/agentic/*.ts` → 0 errors (warnings OK).

### Note on "unverified" system flags
The desktop harness may flag "unverified" after edits. Re-run `tsc --noEmit` + the targeted
`tsx --test` slice and report the concrete pass counts — that IS the fresh evidence. The
single eslint error on `bin/*.ts` does not invalidate the run.
