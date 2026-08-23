# AVS batch-run campaign 2026-07-31 — external kill, isolation, and two CLOSED bugs

Session task: generate 9 different test videos (3 topics × 3 variants) via the
wave-scheduled batch, fix every error found. Result: 9/9 rendered, 0 failed,
`Batch Summary: 9/9 completed`, `EXIT=0`. Full suite 742 pass / 0 fail.

## The 9-job test matrix (proven shape)

`input/scripts/agentic-scripts.json` — 9 jobs, 3 topics × 3 variants, spanning
both orientations and 3 video types:

| # | Topic | Orientation | videoType |
|---|-------|------------|-----------|
| 1-3 | why do bees make honey v1..v3 | portrait | product |
| 4-6 | 5 easy ways to reduce plastic waste v1..v3 | landscape | facts |
| 7-9 | the science of rainbows explained v1..v3 | portrait | tutorial |

Back up the original scripts file before overwriting (`cp ... .bak`).

## Run #1 — died with external-kill signature (diagnosis chain)

Command: `npx tsx src/adapters/cli/agentic-batch.ts --parallel 1 > /tmp/avs-batch-run.log 2>&1`

Observed:
1. `⚠ [DOWNLOAD] Failed to download <pexels-uhd-url>: ENOENT: no such file or
   directory, stat '...\workspace\jobs\gen_ignr7o\assets\videos\scene_02\candidate_1.mp4'`
2. The `.part` file was GROWING (12.8MB → 13.6MB per 20s) — an active download.
3. The retry recovered: `candidate_1.mp4` = 15.4MB, valid 4s UHD (ffprobe-verified).
4. Then the process died: log mtime 14:52:22, last line `EXIT=1`, **no stack
   trace, no `❌ Fatal`, no `📊 Wave N/9 complete`, no Batch Summary**.
5. Windows Application/System event logs showed NO crash entries in the window.

Conclusion: external taskkill, NOT a crash. Two independent defects:

### Defect A — download.ts:178-181 ENOENT race (CLOSED)
`src/lib/visual-fetcher/download.ts`: after `streamToFile` resolves,
`if (fs.existsSync(partPath)) fs.renameSync(...)` then `statSync(outputPath)`
threw raw ENOENT when a CONCURRENT session's `pruneWorkspaces()` deleted the
`.part` between stream-write completion and the rename check. The retry
(pipeline download wrapper, 3 attempts) recovered the file, but the raw error
was misleading.

Fix (download.ts): before rename, `if (fs.existsSync(outputPath))
fs.rmSync(outputPath, { force: true })` (Windows rename-over-existing = EPERM);
when `.part` is gone AND no output exists, throw a CLEAN retryable error:
`download produced no file for ${filename}: .part file vanished after stream
completed (concurrent cleanup?)`.

### Defect B — cleanupRam() self-kill (CLOSED, see G26 in SKILL.md)
`wave-scheduler.ts` cleanupRam taskkilled any process >500MB not named
hermes/electron — including the batch's own node/tsx process during a UHD
download + ffmpeg children. Fixed with own-process-tree exclusion (parent-PID
walk via wmic).

## Run #2 — the isolation recipe that worked (9/9)

```bash
AGENTIC_WORKSPACES_ROOT="C:/one/Automated-Video-Generator/workspace/batch-isolated" \
AGENTIC_KEEP_WORKSPACES=25 \
npx tsx src/adapters/cli/agentic-batch.ts --parallel 1 > /tmp/avs-batch-run2.log 2>&1
echo "EXIT=$?" >> /tmp/avs-batch-run2.log
```

- Wave pacing: each wave = 1 job (--parallel 1), ~8-10 min/wave (UHD
  downloads dominate). 9 waves ≈ 90-100 min total.
- Monitor: `grep -a "Wave [0-9]/9 complete" /tmp/avs-batch-run2.log` +
  `find output -name "final.mp4" -newermt <start> | wc -l` + `ps -ef | grep
  agentic-batch`. RAM dips to ~200MB free mid-download then recovers —
  don't panic-kill at low RAM; the batch's own cleanup now skips its tree.
- Concurrent legacy session (`npx tsx src/cli.ts`, another Hermes session
  running hermes_sample_local / dog_* jobs) was ACTIVE during run #2 — the
  isolated workspace root made it harmless. That's the point of the fix.
- Per-wave output line: `✅ <title> → C:\...\output\gen_<id>\_compose\final.mp4`
  and `📊 Wave N/9 complete: 1✅ 0❌`.

## End-of-batch verification (empirical, per memory rules)

1. `Batch Summary: 9/9 completed, 0 failed` + `EXIT=0` in the log.
2. For every `output/gen_*/_compose/final.mp4`:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,avg_frame_rate -show_entries format=duration,size -of default=nw=1 "$f"
   ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1 "$f"
   ```
   Expected: h264 + aac, 25fps, portrait 720×1280 or landscape 1280×720,
   duration ≈ 16-21s, non-trivial size (2-5MB).
3. Quality spot-check (no placeholders / no black frames):
   ```bash
   ffmpeg -v error -i final.mp4 -vf "blackdetect=d=0.5:pix_th=0.10" -f null - 2>&1 | grep -c black_start   # expect 0
   ffmpeg -i final.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"                 # speech: mean ≈ -18 to -22 dB
   ```
4. Copy finals to a campaign dir: `output/campaign-testing-9videos/video_N.mp4`
   (workspace/jobs is transient — campaign copies are the durable artifact).

## Harness exit-code trap (cost a misread)
The Hermes background-process notice reported "completed normally (exit code
0)" for run #1 — but the log's own `EXIT=1` line and mtime told the truth.
The bash wrapper exits 0 because the trailing `echo "EXIT=$?"` succeeds.
ALWAYS trust the log's `EXIT=` line + last-write time over the harness
completion notice.
