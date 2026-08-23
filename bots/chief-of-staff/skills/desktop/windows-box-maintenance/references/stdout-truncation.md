# Process Output Truncation on Windows MSYS

## The 44-Line Buffer Problem

When running background processes via Hermes on Windows MSYS (git-bash), the visible output buffer only holds the most recent ~44 lines of stdout. This means:

- **Pipelines appear stuck** when they're actually 80% done
- **Later log messages** (completion, errors, gates) are never visible
- **You can't tell** if a process is progressing or hung from output alone

## Diagnosis

```bash
# 1. Check if the process is actually alive
tasklist //FI "PID eq <pid>" //NH
# or
ps -p <pid> -o pid,state,etime

# 2. Check workspace files for real progress
ls -la <workspace-dir>/<job>/  # see if render/ dir exists
find <workspace-dir>/<job> -type f | sort  # full inventory

# 3. Estimate processing time from input file sizes
stat -c%s <large-input-file>  # 80MB+ = 5-10 min processing
```

## Workaround

- **Check filesystem**, not stdout, for progress
- Phase table: `assets/*.mp4` only → downloading/verifying; `render/` dir → rendering started; `render/*.mp4` → complete
- Use `process(action='poll')` to confirm process is alive, then wait
