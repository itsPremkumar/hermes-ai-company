---
name: workspace-pipeline-maintenance
description: Maintain disk space, monitor background process progress, and troubleshoot common failures (ENOSPC, download limits, stuck verification) for batch video-generation pipelines running on Windows.
---

# Workspace Pipeline Maintenance

Recurring housekeeping for batch video-generation pipelines (e.g. Automated-Video-Generator). Background processes accumulate GBs of intermediate files, stdout buffers are shallow, and common failures (ENOSPC, 150MB download limit, stuck verification) are non-fatal traps.

## Triggers

- Pipeline job fails with `ENOSPC: no space left on device`
- Background process won't progress past "verification" or "rendering"
- Workspace jobs directory is 10GB+
- User asks to "clean up" or "free space"

## First: Check Disk Space

```bash
df -h /c/
```

- **<1GB free** → CRITICAL: delete old jobs immediately
- **<1.5GB free** → WARN: avoid libx264 encoding (use h264_mf instead); kill
  Chrome and non-essential processes before rendering
- **<5GB free** → WARN: clean before starting a new run
- **5GB+ free** → OK

## RAM Discipline — Avoid System Destabilization

This Windows box has ~6 GB RAM, often <1.2 GB free. Heavy video operations
(4K downloads, libx264 encoding, concurrent ffmpeg processes) can exhaust RAM
and make the entire system sluggish or freeze — user reported system instability
when ffmpeg's x64 encoder repeatedly hit malloc failures.

**Before starting any video pipeline run:**

1. Check free RAM: `wmic OS get FreePhysicalMemory /value` — <1.5 GB = risky
2. Kill non-essential processes (Chrome, Brave, WhatsApp, SearchHost) via
   `taskkill /PID X /F` — Chrome alone can use 500+ MB across processes
3. Switch to `h264_mf` (Windows MediaFoundation hardware encoder) when RAM is
   tight — it uses <100 MB extra vs libx264's 500+ MB at 720p
4. Set `outputQuality: "medium"` in job scripts (not "high") to reduce encode
   memory pressure
5. Avoid downloading 4K Pexels videos (3840×2160) — they're 17-150 MB each and
   trigger malloc failures in ffmpeg-static. Use local `input/visuals/` fallbacks
   or keyword-targeted searches that return 720p-1080p results
6. Process **one video at a time** — do not queue multiple renders sequentially
   without intermediate cleanup
7. Clean temp files between jobs: delete `workspace/jobs/<job>/_render/` (temp
   segments), `workspace/cache/`, and downloaded `assets/videos/` directories

**Signs of destabilization:**
- ffmpeg exits with `x264 [error]: malloc of size N failed`
- `Failed to inject frame into filter network: Cannot allocate memory`
- Hermes session gets interrupted (orphan recovery messages)
- System UI feels sluggish or mouse hangs briefly
- Windows reports <400 MB free

**Recovery:**
- Immediately kill all ffmpeg processes: `taskkill /F /IM ffmpeg.exe`
- Run `rm -rf workspace/jobs/*/_render_temp* workspace/cache/`
- Reboot if system remains sluggish after cleanup

```bash
# Remove all jobs older than the current session (by prefix pattern)
rm -rf workspace/jobs/job_178461*/ workspace/jobs/job_178462*/
# Or by age (30+ minutes)
find workspace/jobs/ -mindepth 1 -maxdepth 1 -type d -mmin +30 -exec rm -rf {} +
```

Each job directory is 100-500MB. Accumulated across many runs, easily 26GB+.

## Monitor Background Process Progress

**Problem**: Background process stdout only shows ~44 lines via `process(wait)` — the buffer doesn't flush, making it appear stuck.

**Solution**: Check workspace filesystem directly — each phase creates predictable artifacts:

| Phase | Files Created | How to Check |
|-------|--------------|--------------|
| Plan | `plan.json` | `ls workspace/jobs/<job>/plan.json` |
| Download | `assets/videos/scene_*/candidate_*.mp4` | `find workspace/jobs/<job>/assets -type f` |
| Verify | `verification/*.json` | `ls workspace/jobs/<job>/verification/` |
| Voiceover | `audio/*.wav`, `audio/subtitles.srt` | `ls workspace/jobs/<job>/audio/` |
| Gate | `approval-manifest.json` | `ls workspace/jobs/<job>/approval-manifest.json` |
| Render | `render/<job>.mp4` | `ls workspace/jobs/<job>/render/` |
| Archive | `archive/archive-manifest.json` | `ls workspace/jobs/<job>/archive/` |

Use `process(action='log', session_id='...', limit=200)` to get the FULL stdout buffer, not just the preview.

## Troubleshoot Common Failures

### ENOSPC (no space left on device)

**Symptom**: Pipeline fails mid-render with `ENOSPC: no space left on device, write`.

**Fix**: Clean old jobs (above). Also check temp dirs:
```bash
df -h /c/
rm -rf /tmp/remotion-* /tmp/chromium-*
```

### High quality render stuck on download

**Symptom**: Pipeline shows `⚠ [DOWNLOAD] Failed to download https://...: maxContentLength size of 157286400 exceeded` and progress stops.

**Root cause**: Pexels returns 4K (3840x2160) video files >150MB. The pipeline's downloader has a 150MB cap to protect memory/disk.

**What happens**: The pipeline retries with a different candidate. If all candidates are 4K, it stalls. The process is NOT dead — it's waiting for Pexels to return a smaller video.

**Workaround**: Cancel and use a different topic that typically yields non-4K content. Or let it run — if Pexels has a smaller version, it'll eventually pick one up.

### Verification of 4K videos is very slow

**Symptom**: Pipeline stuck on "verification" for 5-10+ minutes.

**Root cause**: The `blackdetect` and `freezedetect` ffmpeg filters decode every frame of the source video. 4K (3840x2160) at 30fps = 8M pixels × 900+ frames per scene.

**Fix**: Be patient — it's not stuck, just slow. The pipeline recovers automatically once verification completes.

### Remotion Chrome connection timeout

**Symptom**: `Timed out after 25000 ms while trying to connect to the browser!`

**Root cause**: `@remotion/renderer`'s `ensureBrowser()` can't connect to Chrome/Chromium on this Windows host even with `CHROME_EXECUTABLE` set.

**Workaround**: Use `--renderer ffmpeg` instead of `--renderer remotion`.

## Reference Files

- `scripts/check-disk-space.sh` — quick disk check before batch runs
- `scripts/process-monitor.sh` — tail workspace files to gauge pipeline progress
