# Running pytest on this Windows host (PREM KUMAR / MSYS git-bash)

Captured from a real session where foreground `python`/`pytest` invocations silently
produced NO stdout and reported exit 0, hiding failures for many iterations.

## The two traps

1. **Unquoted paths with spaces break the command.**
   The user home dir is `C:/Users/PREM KUMAR/` (space in "PREM KUMAR").
   `env -u PYTHONPATH C:/Users/PREM KUMAR/AppData/.../python.exe -m pytest ...`
   bash splits at the space: runs `C:/Users/PREM` (fails with a syntax error about
   the rest of the path looking like Python code). ALWAYS quote the interpreter path:
   `"C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe"`

2. **Foreground stdout from `python.exe` is silently lost in this terminal.**
   `python -c "print('x')"` and `python -m pytest ... -q` return empty output AND
   exit 0 even when tests fail. Redirecting with `> file` also produced no file.
   The reliable path is **background mode** — it captures the process buffer:
   ```
   terminal(background=true, command='cd "C:/Users/PREM KUMAR/samm" && env -u PYTHONPATH "C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe" -m pytest tests/ -q 2>&1', notify_on_complete=true)
   process(action='wait', session_id=..., timeout=60)
   ```
   The output comes back in the `output` field (with `bash: no job control in this shell`
   as a harmless first line).

## Gotchas seen
- The `Python312` interpreter at that path actually reports `3.11.15` — version label is
  unreliable; just use the path that exists.
- A `pytest` on PATH (`which pytest`) resolved to the hermes venv, not the project venv.
  Prefer the explicit interpreter path above for project tests.
- The task's literal command `env -u PYTHONPATH ... -m pytest tests/ -q` is correct once
  the path is QUOTED. Without quotes it fails as in trap 1.
- `grep -c` / `grep -aoE` piped after pytest in the same background command can hang or
  lose output. Run ONE pytest invocation, capture to the process buffer, then inspect.
- `search_files` with a `path` containing `samm/samm` (nested same-name dirs) failed with
  "system cannot find the path"; use `terminal` `grep -rn` instead for those paths.

## Recipe that worked (final)
```
cd "C:/Users/PREM KUMAR/samm"
env -u PYTHONPATH "C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe" -m pytest tests/ -q --cache-clear
```
Run it via `terminal(background=true, notify_on_complete=true)`, then `process(wait)`.
Add `--cache-clear` when a prior cached run might be stale (e.g. after fixing a bug that
earlier failures were masking).

## Reading the summary
`-q` prints a single line like `55 passed, 1 skipped` plus a progress line
`...........s............` (`.`=pass, `s`=skip, `F`=fail, `E`=error). When forwarding to the
user, report the EXACT pass/skip/fail/error counts.
