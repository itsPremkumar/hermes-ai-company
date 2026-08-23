# Cross-Entry-Point Shape Consistency (2026-07-29)

Three new bug classes found while running ALL 18 single-feature modes
across landscape/portrait/square orientations.

## Bug Class A: Workspace ID normalization asymmetry

**Symptoms to recognize:**
- `npm run agentic:modular edit --scene 1 --visual "sunrise"` runs without
  errors but the changes never appear in the output video.
- The edit re-downloads visuals but then says "no plan.json found" or renders
  nothing — the workspace it searched doesn't exist.
- `compose` output from `agentic-batch.ts` works but `edit` from
  `agentic-modular.ts` can't find it.

**Root cause:** Two CLI entry points normalize job IDs differently:
- `agentic-batch.ts`: `id.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 64)`
- `agentic-modular.ts` (BEFORE fix): raw `job.id || 'job_<ts>'` — no normalization

So a job with `"id": "multi-test-landscape"` creates workspace
`workspace/jobs/multi_test_landscape` via the batch pipeline but `edit`
looks in `workspace/jobs/multi-test-landscape` (different dir — doesn't
exist) → silent no-op.

**Fix:** Define ONE `normalizeId()` function and use it at EVERY ID
generation site. In agentic-modular.ts there were 10 sites — all needed
changing. The function:
```ts
function normalizeId(raw: string): string {
    return raw.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 64);
}
```

**Prevention:** Grep for EVERY `const id = job.id || ...` across ALL
entry-point files (`agentic-modular.ts`, `agentic-batch.ts`,
`agentic-cli.ts`, `cli-runner.ts`, `batch-queue.ts`). Every one must
normalize the same way. A grep that returns different patterns = a
pending bug.

## Bug Class B: Incomplete workspace shape passed to render

**Symptoms to recognize:**
- Edit command log shows `_av_undefined.mp4` in the error message when
  trying to rename the rendered file.
- The rename comes from `renderAgenticSlideshow` trying to build a temp
  filename from `res.workspace.jobId` but `jobId` is `undefined`.

**Root cause:** The edit command built a mock `workspace` object with
only `{ root, assetsDir }` but `renderAgenticSlideshow` expects at
minimum `{ root, jobId }` (uses `jobId` to construct temp filenames
like `_av_<jobId>.mp4`, `_seg_<jobId>_*.mp4`, `_intro_<jobId>.mp4`,
`_concat_<jobId>.txt`).

**Fix:** Add `jobId: id` to every synthetic workspace object before
passing it to any function that calls `renderAgenticSlideshow` or
accesses `ws.jobId`.

**API contract to know:** The `renderAgenticSlideshow` function at
`src/agentic/orchestrator/render.ts:397` accesses `res.workspace.jobId`
directly. It also uses `res.workspace.root + '/render'` as the temp
output dir. Every caller must provide BOTH fields.

## Bug Class C: Missing destination directory in render output

**Symptoms to recognize:**
- `ENOENT: no such file or directory, rename '...render\\_av_<job>.mp4'
  -> '...output\\<job>\\scene_1_edit.mp4'`
- Every other part of the render succeeds — the file is produced at the
  temp location but fails to be moved to the final destination.

**Root cause:** `renderAgenticSlideshow` (render.ts:992) does
`fs.renameSync(silent, out)` where `out` is `opts.outPath`. In edit
mode `opts.outPath` points to `output/<jobId>/scene_1_edit.mp4` but
the `output/<jobId>/` directory doesn't exist (only created by a full
pipeline run). `renameSync` does NOT create parent directories.

**Fix:** Before rename, ensure the destination directory exists:
```ts
try { fs.mkdirSync(path.dirname(out), { recursive: true }); } catch { /* ignore */ }
```

**Broader pattern:** Any function that accepts an arbitrary `outPath`
must ensure the parent directory exists. Same applies to
`fs.copyFileSync`, `fs.writeFileSync` with a path in a non-standard
location.

## Multi-mode verification pattern

This session tested ALL 18 single-feature modes successfully across
3 orientations (landscape, portrait, square):

| Mode | What it exercises |
|------|-------------------|
| `plan` | Script parsing, scene building, orientation |
| `download-images` | Pexels/Openverse image search, download |
| `download-videos` | Pexels video search, download |
| `download-music` | Free-music resolution, bundling |
| `download-sfx` | SFX config parsing (zero results = expected) |
| `generate-voice-edgetts` | Voice backend, scene voiceover |
| `generate-voice-voicebox` | Voicebox/Kokoro engine |
| `compose` | Full pipeline: visuals → voice → music → render |
| GIF export (palettegen+use) | `render-gif` mode, palette generation |
| Poster export (frame extract) | `render-poster` mode |
| Contact sheet (tile montage) | `render-contact-sheet` mode |
| `apply-advanced` | Config proof — all control-surface signals |
| `rerender` | Cache-reuse from prior compose |
| `clone-voice` | Voice cloning from reference clip |
| `download-url` | Direct-URL download |
| `edit` | Per-scene visual/voice/color edits + re-render |

For a full combinatorial run, use `agentic-batch.ts --mode <mode>` with
a multi-job input file. Each mode operates independently from the same
`agentic-scripts.json` config.
