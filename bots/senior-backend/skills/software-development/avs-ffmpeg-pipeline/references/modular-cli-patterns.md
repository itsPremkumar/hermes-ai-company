# Modular CLI Patterns (agentic-modular.ts / agentic-preview.ts)

## Dry-run mode (`--dry-run`)

Every stage (plan, visuals, voice, render) in `agentic-modular.ts` supports `--dry-run`.
When set, the stage prints what it *would* do and exits without writing files,
downloading assets, starting voice backends, or running ffmpeg.

**Pattern:**
- Check `cliArgs['dry-run']` early in each stage function (after loading plan.json
  but before any side-effect).
- Build a `DryRunDetail[]` array with the stage name and an array of info lines.
- Call `printDryRun(job, title, details)` which logs the report and `continue`s
  the job loop.
- The helper `printDryRun` is defined once at module scope — share across all stages.

**Per-stage dry-run output:**

| Stage    | Shows                                                              |
|----------|---------------------------------------------------------------------|
| plan     | Title, topic, voice, orientation, scene count, per-scene text/dur   |
| visuals  | Orientation, candidates-per-asset, per-scene keyword + kind + dur   |
| voice    | Default voice, target scene, per-scene voice label + cache status   |
| render   | Workspace path, scene count, orientation, caption mode, per-scene ✓ |

## Preview Thumbnails (`agentic-preview.ts`)

Standalone CLI at `src/adapters/cli/agentic-preview.ts` that generates a 5-frame
sprite sheet from a rendered job's MP4. Invoked via `npm run agentic:preview`.

**Flow:**
1. Read job JSON (`--file` or default `input/scripts/agentic-scripts.json`).
2. Filter by `--job <id>` if provided.
3. Read `plan.json` from workspace to get scene info + job metadata.
4. Find the rendered MP4 in `output/<jobId>/` (prefers title-based file).
5. Probe total frame count via ffprobe (`nb_read_packets`).
6. Compute `step = totalFrames / 5`.
7. Run ffmpeg: `-vf select='not(mod(n,step))',tile=5x1 -frames:v 1`.
8. Write sprite sheet to `output/<jobId>/preview/sprite.jpg`.

**Key implementation details:**
- Uses `execFileSync` (not spawn) — simple synchronous wrapper.
- Falls back gracefully when no plan.json / no MP4 / probe fails.
- Same `readJobJson` / `workspaceFor` / `readJson` helpers as agentic-modular.ts.
- Handles Windows paths via `path.join` (not shell interpolation).

## Adding new CLI subcommands to agentic-modular.ts

Template:
1. Add a `run<Subcommand>(cliArgs)` async function.
2. Register it in the `switch (subcommand)` block in `main()`.
3. Add to the help text in the `help` case.
4. Add an `npm run agentic:<subcommand>` script in package.json.
