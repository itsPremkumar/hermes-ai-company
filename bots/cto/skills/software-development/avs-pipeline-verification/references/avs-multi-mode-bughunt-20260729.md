# Multi-Mode Bug Hunt — 2026-07-29

## Context

Systematically exercised **all available agentic generation modes** of the
Automated-Video-Generator pipeline to expose cross-cutting bugs. Each mode
exercises a different code path (fetcher, TTS, render, export, edit, config
proof). The bug cluster spanned 3 files across 2 entry points.

## Multi-Mode Exercise Order

| Step | Mode | What it tests | Time | Result |
|------|------|---------------|------|--------|
| 1 | `plan` | Script parser, scene splitting | 2s | ✅ |
| 2 | `download-images` | Pexels fetcher, visual cache | 15s | ✅ |
| 3 | `download-videos` | Video search/download path | 20s | ✅ |
| 4 | `download-music` | Music search engine | 10s | ✅ |
| 5 | `download-sfx` | SFX resolution (none configured) | 2s | ✅ (0 fetched) |
| 6 | `generate-voice-edgetts` | Edge TTS voice generation | 10s | ✅ |
| 7 | `compose` | Advanced pipeline (full compose) | 25s/ea | ✅ (all 3 orientations) |
| 8 | GIF/poster/contact-sheet | ffmpeg export transcodes | 5s/ea | ✅ |
| 9 | `apply-advanced` | Config proof / palette signals | 2s | ✅ |
| 10 | `edit` | Scene editor + re-render | 120s | ❌ **3 bugs found** |

## Bugs Found

### Bug 1 — `_av_undefined.mp4` (Critical)
**File:** `src/adapters/cli/agentic-modular.ts`
**Symptom:** `ENOENT: no such file or directory, rename '...render\_av_undefined.mp4'`
**Root cause:** Edit command passed `workspace: { root: ws.root, assetsDir: ws.assetsDir }`
without a `jobId` property. `renderAgenticSlideshow()` needed `res.workspace.jobId` to
build temp filenames — without it, the path became `_av_undefined.mp4`.
**Fix:** Added `jobId: id` to the workspace object.

### Bug 2 — ENOENT on rename (Critical)
**File:** `src/agentic/orchestrator/render.ts`
**Symptom:** `ENOENT: no such file or directory, rename '...render\_av_xxx.mp4' -> 'output/.../scene_1_edit.mp4'`
**Root cause:** `fs.renameSync(silent, out)` where `out` paths target `output/<id>/` which
doesn't exist until a full pipeline run. No `mkdirSync` before the rename.
**Fix:** Added `fs.mkdirSync(path.dirname(out), { recursive: true })` at the top of
`renderAgenticSlideshow()`.

### Bug 3 — Hyphen vs underscore workspace ID mismatch (Critical)
**File:** `src/adapters/cli/agentic-modular.ts` (10 sites)
**Symptom:** Edit command looked for workspace `multi-test-landscape` (hyphen) while
batch pipeline created `multi_test_landscape` (underscore).
**Root cause:** `agentic-batch.ts` normalizes IDs to lowercase underscores via
`.replace(/[^a-z0-9]+/g, '_')`. `agentic-modular.ts` used the raw job ID unchanged.
**Fix:** Created `src/shared/identifiers.ts` with shared `normalizeJobId()` function
matching batch conventions. Applied to all 10 call sites in `agentic-modular.ts` and
3 in `agentic-batch.ts`.

## New Features Added Alongside Fixes

| Feature | Files | Description |
|---------|-------|-------------|
| Shared ID normalization | `src/shared/identifiers.ts` | Cross-entry-point consistent job IDs |
| Workspace temp cleanup | `src/adapters/cli/agentic-clean.ts` + npm script `agentic:clean` | Deletes stale `_av_*.mp4`, `_seg_*`, `_concat_*` older than 1h |
| Subtitle SRT/VTT export | `src/agentic/orchestrator/render.ts` | SRT + VTT alongside final MP4 from `captionSegments` |
| Chapter markers | `src/agentic/orchestrator/render.ts` | ffmpeg chapter metadata from scene titles |
| Verbose ffmpeg flag | `src/agentic/orchestrator/render.ts` | `opts.verbose` prints full ffmpeg command to stderr |
| End-to-end test | `tests/agentic/e2e/pipeline.test.ts` | 2 tests: plan→render→ffprobe verify |
| Gitignore hygiene | `.gitignore` | Render intermediates, probe scripts |

## Verification

- TypeScript typecheck: `tsc --noEmit` → 0 errors
- Full test suite: 724/732 pass, 0 fail, 0 cancelled
- E2E test (isolated): 2/2 pass
- `agentic-clean` command: ✅ works (scans 20 jobs, nothing to clean)

## Commit
`a809179` — "feat: shared normalizeJobId, subtitle/cc export, chapter markers, verbose ffmpeg, agentic-clean, e2e test" (8 files, +500/−26 lines)
