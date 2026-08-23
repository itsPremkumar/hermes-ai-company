---
name: hermes-cron-script-ops
description: >
  Author and debug Hermes `no_agent` cron SCRIPT jobs (the `script:` field on a
  cron job, not the LLM-driven prompt path). Covers the execution-sandbox
  quirks that make naive script jobs silently fail or perpetually report
  "error": there is NO /bin/bash in the cron sandbox (so .sh wrappers die with
  execvpe(/bin/bash) failed), `.py` scripts run under the Hermes venv Python,
  and ANY non-zero exit is flagged `error` even when the job genuinely ran and
  produced output. Use when you (a) create or edit a cron job with `no_agent:
  true` + `script:`, (b) see a script cron job stuck in `error` with
  "Script not found" or "exited with code 1", or (c) must verify a fleet-touching
  cron script is safe before promoting it from dry-run. Load this whenever a
  user asks why a Hermes cron script job is failing/erroring.
---

# Hermes cron `no_agent` script jobs — authoring & debugging

Hermes cron jobs come in two flavors:
1. **LLM-driven** (default): the prompt is run by the agent each tick.
2. **`no_agent: true` + `script:`**: the scheduler executes a script file
   (`.sh` or `.py`) and delivers its stdout verbatim. **This is the flavor with
   sharp edges** — it runs in a stripped sandbox, not your interactive terminal.

## Trigger / when to load
- Creating or editing any cron job that sets `no_agent: true` and `script:`.
- A script cron job shows `last_status: "error"` with
  `execution_error: "Script not found: ..."` or `Script exited with code 1`.
- You need to verify a cron script actually runs in the scheduler (not just in
  your terminal) — e.g. a fleet DevOps/verify loop.
- Investigating "this cron job never runs / always errors but works when I run
  it by hand."

## The three sandbox gotchas (root causes)

### Gotcha 1 — NO bash in the scheduler sandbox
Your interactive terminal has `bash` (git-bash/MSYS), but the `no_agent` worker
does NOT. A `.sh` script fails immediately:
```
WSL (9 - Relay) ERROR: CreateProcessCommon:818: execvpe(/bin/bash) failed: No such file or directory
```
**Fix:** make the entrypoint a **`.py` file**. The `no_agent` runner executes
`.py` via the Hermes venv Python, which IS present in the sandbox. Keep any
shell-only logic inside Python (`subprocess`, `shutil`, `os`).

### Gotcha 2 — script path resolution
`script: "devops_loop_daily.py"` resolves under
`C:\Users\<user>\AppData\Local\hermes\scripts\`. A `script:` value pointing at a
file that does not exist yields `Script not found: <full path>`. Always verify
the file is actually written there (use `write_file` or check the dir).

### Gotcha 3 — ANY non-zero exit == "error"
If your script exits `1` for a *legitimate* reason (e.g. a verification engine
that returns 1 when some repos fail), the job is flagged `error` FOREVER, even
though it ran fine and wrote its report. **The scheduler cannot tell
"job failed" from "job ran and found problems."**
**Fix:** the wrapper should report success (exit 0) when the run *completed and
produced its output artifact*, reserving exit 1/2 for genuine crashes (missing
engine, no report written). The real pass/fail data belongs in the artifact
(report file / JSON), not the exit code.

## Authoring checklist
1. Entrypoint = `.py`, lives in `~/AppData/Local/hermes/scripts/`.
2. Use `sys.executable` to spawn the real engine so it inherits the venv.
3. Wrap risky work in `try/except` → return 1 only on real crash.
4. After the engine runs, check the output artifact exists; return 0 if yes.
5. Prefer `--dry` / read-only first; gate any git-commit/push/docker behind an
   explicit flag you flip only after reviewing one report.
6. Point the cron job's `script:` at the `.py` filename (no path).

## Verify it actually runs (do not trust "it works in my terminal")
```text
cronjob action=run job_id=<ID>
```
Inspect the returned `execution_success`, `last_status`, and `execution_error`.
This executes in the REAL sandbox, so it surfaces Gotcha 1/2/3 immediately.

## Known-good wrapper pattern
See `templates/noagent_wrapper.py` for a copy-paste, dry-run-safe wrapper that
(1) runs a Python engine via `sys.executable`, (2) returns 1 only on genuine
crash, (3) returns 0 when the daily report was written.

## Real debugging transcript (worked example)
`references/cron-noagent-gotchas.md` walks the actual incident where
`devops-loop-daily` errored every run: missing `.sh` → created `.py` → bash
sandbox error → switched script field → exit-1-still-error → hardened wrapper
to return 0 on artifact-present. Use it as the reproduction recipe.

## Pitfalls
- Don't assume `bash`/shell utilities (`curl`, `grep`) exist in the sandbox —
  shell out from Python or use Python stdlib.
- Don't let the engine's "found failures" exit code leak to the scheduler.
- Don't enable auto-commit/push on a fleet cron job until you've reviewed one
  dry-run report — the blast radius (git push to many remotes) is large.
- The interactive terminal and the cron sandbox are DIFFERENT environments;
  always confirm via `cronjob action=run`, never just by local execution.
