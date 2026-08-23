# AVG static bug-hunt — CLI / Classic / Batch / Export / Publish

Worked example of the three "read-only, code-path-verified" defect classes from
`source-audit` SKILL.md, found on the Automated-Video-Generator (AVG) repo
(`C:/one/Automated-Video-Generator`). Method: baseline tests + typecheck green,
read every in-scope file, confirm each suspect by exact code-path trace (no
network/keys needed). No source edited.

Baseline at audit time:
- `src/agentic/export.test.ts` + `config.test.ts` + `autopilot.test.ts` → 22/22 pass
- `src/adapters/cli/cli-runner.test.ts` + `batch-queue.test.ts` → 8/8 pass
- `tsc -p tsconfig.json --noEmit` clean in the audited area.

## BUG 1 — `--only` filter never matches (filter-key normalization asymmetry)
- `src/adapters/cli/cli-runner.ts:50-55` (and `batch-queue.ts:207` uses the same `onlyIds`).
- Symptom: `--only "Home Workout"` silently skips the job.
- Root cause: `onlyIds` is parsed from raw argv (`"Home Workout"`), but job ids are
  `sanitizeFilename(job.id || job.title)` → lowercase + non-alphanumerics→`_` (`"home_workout"`).
  `batch-queue.ts` matches `onlyIds.has(input.id)` where `input.id` is the sanitized id.
- Fix: sanitize the filter values the same way (define `sanitizeFilename` before `parseArgs`):
  ```ts
  const onlyIds = onlyRaw
    ? onlyRaw.split(',').map((s) => sanitizeFilename(s.trim())).filter(Boolean)
    : undefined;
  ```

## BUG 2 — publish manifest `topic` always `undefined` (cross-file type-cast drift)
- Call site `src/agentic/orchestrate.ts:1929` → `src/agentic/publish.ts:105`.
- Symptom: every `publish-manifest.json` has `topic: undefined`.
- Root cause: `writePublishManifest` is called with `cfg: res.plan as unknown as AgenticConfig`.
  `Plan` (`src/agentic/types.ts:34`) has NO `topic` field (only `jobId, title, orientation,
  voice, musicQuery, scenes, totalDurationSec`), yet `buildPublishManifest` sets `topic: cfg.topic`.
- Fix (either): in `buildPublishManifest` use `topic: cfg.topic ?? cfg.title ?? ''`; or at the
  call site pass `topic: res.plan.title` into the `cfg` object instead of relying on the cast.

## BUG 3 — resumable manifest loses in-run progress (resumable-manifest staleness)
- `src/adapters/cli/batch-queue.ts:232, 265, 288`.
- Symptom: on a mid-batch crash, `--resume` re-runs already-completed jobs.
- Root cause: workers call `writeManifest(manifestPath, manifest)` at start (L232) and end
  (L265) of each job, but `manifest.jobs` is only assigned from the live `entries` map at L288
  *after* all workers finish. During the run `manifest.jobs` still holds the previous/empty
  array, so the on-disk manifest never reflects completed/failed jobs until the very end.
- Fix: before each `writeManifest` inside the worker, refresh the array:
  ```ts
  manifest.jobs = [...entries.values()].sort((a, b) => a.index - b.index);
  writeManifest(manifestPath, manifest);
  ```

## Confirmed NOT bugs (checked and cleared)
- `configToRequest` (`src/agentic/config.ts:489`) — dead code (defined once, never called). Not a live bug.
- `exportMultiAspect` dimension math (`export.ts:25-99`) — correct; exported filenames
  (`<jobId>_9x16.mp4`, etc.) exactly match what `publish.ts:72-74` looks for.
- autopilot render-soften self-heal (`autopilot.ts:125-222`) — bounded by `maxAttempts`; the
  env fix is honored on later attempts and cleared per-run; stops when `diagnose` returns no fixes.
- Segment-path `createRenderReadyJob` is synchronous, so the un-awaited call at `cli-runner.ts:154/236` is fine.
