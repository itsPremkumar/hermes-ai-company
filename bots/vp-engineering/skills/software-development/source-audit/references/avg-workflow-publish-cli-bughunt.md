# AVG workflow / export / publish / CLI bug-hunt (verified)

Worked example of the NEW bug classes added to `source-audit` SKILL.md
(producer/consumer filename contract, bogus verification "expected" value,
guard-allowlist scope, cross-file path-literal divergence, resume config
staleness). All findings from a static bug-hunt of `src/agentic`,
`src/adapters/cli`, `src/lib`, `src/shared` — NO edits made, file:line + minimal fix only.

## Cross-file constant/path literal divergence (autopilot cache self-heal no-ops)
- `src/agentic/autopilot.ts:46` — `const VIDEO_CACHE = path.resolve(process.cwd(), 'agentic-pipeline/.video-cache.json')`.
- Real cache is `src/lib/visual-fetcher.ts:49` `const CACHE_FILE = resolveProjectPath('.video-cache.json')` → `<cwd>/.video-cache.json` (confirmed present at repo root; `agentic-pipeline/.video-cache.json` does not exist).
- All `fs.rmSync(VIDEO_CACHE)` in `diagnose` (lines 67, 80, 158, 212) hit a non-existent path → the "clear stale cache" self-heals silently never clear the real cache.
- Fix: `const VIDEO_CACHE = resolveProjectPath('.video-cache.json');` (or call `resetInMemoryCache()`).

## Filename/stem contract asymmetry (publish can't find render outputs)
- `src/agentic/publish.ts:70-81` `pickFileForAspect` looks for `${jobId}_16x9.mp4` / `${jobId}_1x1.mp4` / `${jobId}_9x16.mp4`.
  - ffmpeg render emits only `${jobId}.mp4` (`orchestrate.ts:1076`).
  - Remotion render emits `${jobId}_remotion_16x9.mp4` / `${jobId}_remotion_1x1.mp4` / `${jobId}_remotion.mp4` (`orchestrate.ts:2271, 2284-2288`).
  - Neither matches → every platform target falls back to the same `${jobId}.mp4` (wrong aspect for YouTube/Instagram).
- `src/agentic/publish.ts:83-92` `findSubtitles` looks for `${jobId}.srt`, but native caption file is `_captions_${jobId}.srt` (`orchestrate.ts:1195`) → native SRT never listed. (Localized sidecars `${jobId}.${lang}.srt` DO match — `localize.ts:80`.)
- Fix: publish must receive the actual rendered filenames (or match the `*_remotion_*` / `_captions_*` patterns) and the native SRT stem.

## Verification gate called with a bogus constant "expected" value (dispatch gate meaningless)
- `src/agentic/operations/dispatch.ts:69` — every op runs `verifyRenderedVideo(out, 1, { keywords: [] })`. With `expectedDurationSec = 1`: X8 "Duration matches plan" passes for any duration in (0, 3]s (tolerance `max(2, 0.05)`); X7 size floor collapses to `max(50000, 6*1000)=50KB` regardless of length. A broken trim/merge is reported as "gate pass".
- Fix: pass the op's real output duration (probe it) instead of literal `1`.

## Guard/allowlist scope narrower than callers' inputs (silent no-op cleanup)
- `src/adapters/cli/cli-runner.ts:130-132, 202-204, 254-256` calls `cleanupAssets(['public/videos', 'public/audio'])`.
- `src/lib/cleaner.ts:10-13` `canCleanupDirectory` only allows roots `tmp` and `public/jobs`. `public/videos` is a sibling of `public/jobs` (`relative = '../videos'`, `isPathWithin` false) → `continue`, nothing deleted.
- Fix: pass dirs the pipeline actually writes (per-job `public/jobs/<id>` / `tmp`), or add `public/videos`/`public/audio` to `allowedRoots`.

## Generated/templated shell script with mangled variable reference
- `src/agentic/publish.ts:136` — YouTube upload heredoc emits `-H "Authorization: Bearer $YOUTU...OKEN"` (mangled variable; should be `$YOUTUBE_ACCESS_TOKEN`). With `set -e` the script fails on first run and can never authenticate. NOTE: this `***` is a REAL source defect (a mistyped shell var inside a template string), NOT the display-mask-of-`Bearer` artifact the skill warns about — you can see the full literal is `$YOUTU...OKEN`, not `*Authorization: ***`.
- Fix: `-H "Authorization: Bearer $YOUTUBE_ACCESS_TOKEN"`.

## Resume config-metadata staleness (inverse of resumable-manifest staleness)
- `src/adapters/cli/batch-queue.ts:213` — `const manifest: BatchManifest = previous ?? emptyManifest(concurrency, maxRetries);`. On `--resume`, `manifest.concurrency`/`manifest.maxRetries` come from the OLD manifest; the live `options.concurrency`/`maxRetries` are ignored, so resuming with different knobs records the wrong values.
- Fix: after loading `previous`, overwrite `manifest.concurrency`/`manifest.maxRetries` with the resolved current options (keep only `jobs` from the old manifest).

## Cross-file type-cast drift (topic always = title) — minor
- `src/agentic/orchestrate.ts:1971` passes `cfg: res.plan as unknown as AgenticConfig`; `publish.ts:107` reads `(cfg).topic` but `Plan` has no `topic` → manifest `topic` always falls back to `title`. Use `req.topic` instead.

## `--only` silently ignored outside batch mode
- `src/adapters/cli/cli-runner.ts:49-57` parses `onlyIds` but it's only consumed inside `if (batch || resume)` (line 178). Normal single mode (loop at 191) processes ALL jobs. (Distinct from the existing filter-key-asymmetry pitfall — here the filter is parsed but never wired into the non-batch path at all.)
- Fix: in the single-job loop, skip jobs whose sanitized id is not in `onlyIds` when set.

## Verification method used (reproducible)
- Path-existence check: `node -e "const p=require('path');console.log(p.relative(p.join(process.cwd(),'public','jobs'), p.join(process.cwd(),'public','videos')))"` → `..\videos` proves `public/videos` is NOT under the allowed `public/jobs` root.
- Cache path diff: `sed -n '46p' src/agentic/autopilot.ts` vs `grep -n CACHE_FILE src/lib/visual-fetcher.ts`.
- Render output stems: `grep -n "out = \|_remotion\|_captions_" src/agentic/orchestrate.ts`.
- Duration gate constant: `grep -n "verifyRenderedVideo(out, 1" src/agentic/operations/dispatch.ts`.
