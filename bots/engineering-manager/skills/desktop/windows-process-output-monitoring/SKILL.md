---
name: windows-process-output-monitoring
description: Diagnose and work around Windows MSYS background process stdout truncation. When process output buffers show only ~44 lines and the pipeline appears stuck, check the filesystem instead.
---

# Windows Process Output Monitoring

## Problem

On Windows MSYS (git-bash), Hermes background process stdout is truncated at ~44 lines in the process buffer. A pipeline that appears stuck is often still running — its later output simply doesn't fit in the visible ring buffer.

## Identifying the Problem

Signs of stdout truncation:
- Process status shows "running" but output hasn't changed in minutes
- Only the first ~44 lines of output are visible (plugin registry, plan phase, network selections)
- Later phases (voiceover, gate, rendering, archive) never appear
- Process PID is still alive but no visible progress

## Solution: Filesystem Inspection

Always check the workspace/filesystem to determine the real pipeline phase:

```bash
# Find the newest working directory
JOB=$(ls -t <workspace-dir>/ | head -1)
find "<workspace-dir>/$JOB" -type f | sort
```

### Phase Detection Table

| Files Present | Phase |
|--------------|-------|
| `assets/videos/scene_*/candidate_*.mp4` only | Downloading or verifying |
| `plan.json` + `candidates.json` | Plan ready, candidates analysed |
| `voiceover/` tracks appearing | Voiceover generation in progress |
| `render/` directory appears | Rendering started |
| `render/<output>.mp4` exists | Render complete |
| `archive/`, `output/` directories | Post-processing complete |

### Estimate Wait Time from File Sizes

```bash
for i in 1 2 3; do
  f="<workspace-dir>/$JOB/assets/videos/scene_0${i}/candidate_1.mp4"
  s=$(stat -c%s "$f" 2>/dev/null || echo 0)
  echo "Scene $i: $((s/1024/1024)) MB"
done
# 20MB+ per file = 2-5 min processing
# 80MB+ (4K) = 5-10+ min processing
```

### Verify Process is Actually Alive

```bash
# Windows (tasklist)
tasklist //V 2>/dev/null | grep -i "ffmpeg\|node\|tsx"

# MSYS/bash
ps aux | grep -i "ffmpeg\|tsx\|node" | grep -v grep

# Check specific PID
ps -p <pid> -o pid,state,etime
```

## Why This Happens

The Hermes background process buffer on Windows MSYS uses a fixed-size ring buffer (~44 lines of output). The pipeline writes output sequentially from start to finish. Early output (plugin registrations, plan phase, network selection messages) fills the initial lines. Later phases' output is written but doesn't fit in the visible window — the process IS still making progress.

## Prevention

- Add periodic progress markers (file writes, log files) to long-running pipelines
- For agentic pipelines, check workspace directory for file-level progress
- Use `process(action='poll')` to check live status but verify with filesystem
- **Best fix (AVS prod-hardening session): redirect to a log file, not a pipe.**
  A background command ending in `| tail -40` shows NOTHING until exit (pipe
  buffering) — 20 minutes of blindness on a long render. Instead run
  `cmd > /tmp/run.log 2>&1` in the background process and monitor with
  `tail -15 /tmp/run.log` from separate terminal calls. Full history, live,
  and immune to the ring buffer entirely.
