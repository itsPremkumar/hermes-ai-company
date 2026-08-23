# AVS Audit Pitfall: stale-snapshot recommendations vs. current code

## Lesson (from 2026-08-02 session)

When asked to "analyze / improve the video generator," do NOT emit a long
list of concrete fixes from memory or from a docs/SCAN-*.md snapshot alone.
This repo is refactored heavily between sessions — a scan written weeks ago
describes a `cli-job.ts:186 clearProjectState()`, `ffmpeg-correlation.ts`
circuit-breaker, `composeScenes()` batching, etc. that **no longer exist** in
the working tree.

### What actually happened
Proposed 12 improvements. After reading the real current source, 5 were already
implemented in the present codebase:
- **compose batching (P0#1)** — already single-pass via `singlePassPlan` inside `composeVideo()`; per-scene spawns only fire in rare mixed-codec+no-transition paths (correct behavior).
- **voice-cache re-probe (P2#2)** — `voice-generator.ts` `fromFile()` short-circuits on cache hit (line ~411); cached WAVs are NOT re-ffprobed via subprocess. No edit needed.
- **audio ducking (P1#2)** — already in `render.ts` ~line 1175: `buildDuckExpression` drives `volume=eval=frame:volume='...'` duck of music under speech, with per-scene `[MusicIntensity:]` overrides.
- **state-clear at session start (P0#2)** — already architecturally resolved: pipeline scopes `workspaceRoot: ./workspace/jobs/${jobId}` per run; `jobId = req.jobId ?? job_${Date.now()}` fresh dir each run, stale scenes cannot bleed across runs.
- **provider-health CLI (P1#3)** — was a half-finished WIP in the working tree (untracked `lib/visual-fetcher/provider-health.ts` + `agentic-modular.ts`/`search.ts` modified-but-uncommitted). Completed + wired it, did not invent it.

Two "improvements" were genuine NEW value and were pushed:
- **P1#4 `detectDuplicateScenes()`** in `compose.ts` — non-fatal WARN when two scenes share an identical source asset; O(n) 256KB-hash; never blocks render.
- **P2#3 / P2#1** in `pipeline.ts` — `POOL_FETCH_TIMEOUT_MS` 20s→12s; last-ditch image pool fallback races candidates via `Promise.any` (first hit wins).

## Rule to follow on this repo
1. Read the ACTUAL current source for every file you intend to change BEFORE
   writing the audit. Grep for the symbol/function the old notes reference
   (`grep -rn "clearProjectState" src/` returned nothing — signal it was
   removed/renamed).
2. Treat `docs/SCAN-*.md` and memory snippets as HYPOTHESES, not facts.
3. If a proposed fix's target symbol doesn't exist, search for the real
   equivalent (`fetchVisualsForScene` moved to `lib/visual-fetcher/search.ts`).
4. Before claiming "X is missing/broken," confirm with a grep + a read of the
   real call site. The codebase is more mature than its audit docs.

## Verified signatures (2026-08-02, do not re-derive blindly)
- `withTimeout(p: Promise<T>, ms: number, label: string)` — in
  `src/agentic/orchestrator/ffmpeg.ts` (NOT `shared/http`). Order is
  (promise, timeoutMs, label). Passing (promise, label, ms) is a TS error.
- `fetchVisualsForScene(keywords: string[], preferVideo: boolean, orientation, _outputDir?, resultIndex=0)`
  — in `src/lib/visual-fetcher/search.ts`. Takes a KEYWORD ARRAY, not a string.
- `composeVideo(input: ComposeInput)` — entry point in `compose.ts` (there is
  NO `composeScenes`/`composeMany` at top level; those are internal helpers).
- Provider-health tracker lives at `src/lib/visual-fetcher/provider-health.ts`
  (`getProviderHealth()`, `recordProviderFailure()`). The CLI command wrapper is
  `src/adapters/cli/provider-health.ts` (`runProviderHealthCommand`).
- Plan stage is `src/agentic/pipeline/plan.ts` (NOT `plan.tsx`). Assets are NOT
  downloaded at plan time, so "thumbnail extraction during plan" does not fit —
  it belongs in the visuals stage.

## Test/verify commands (authoritative)
- `npm run typecheck` (tsc --noEmit) — MUST be clean before any push.
- `npm run lint` — 0 errors required; 2426 pre-existing warnings are NOT yours.
- `npm test` = vitest; the canonical AVS master gate is the `verify-avs-master`
  runner (empirical: RAS lint + dead-imports + unit suites + MVP slice).
- Tests use `node:test` + `node:assert/strict`. Example:
  `tests/agentic/operations/caption-window.test.ts`.

## See also (other AVS pitfalls captured this cycle)
- **Write-path secret redaction trap** — editing any file with
  `Authorization`/`Bearer`/`_TOKEN`/`secret`/`apiKey` can silently corrupt the
  string at write time (`$YOUTUBE_ACCESS_TOKEN` -> `$YOUTU...OKEN`); the same
  trap stalled the parallel session for 25+ messages. Verify with hex bytes,
  fix with a raw Python byte write. -> `references/write-path-token-redaction.md`
- **CLI acquireDeps wiring footgun** — job-JSON feature flags must be set in
  BOTH `pipeline.ts` and the CLI's separate `acquireDeps` literal (~line 400 in
  `agentic-modular.ts`), or the CLI silently drops them. ->
  `references/cli-acquiredeps-wiring.md`
