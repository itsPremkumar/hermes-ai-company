# MSYS path trap + the junction that corrupts the repo

## Symptom (this session, cost a debugging cycle)
`write_file` to `/c/one/prems-jarvis-hermes/...` "succeeds" but later `python -m
pytest` reports `collected 0 items`, and `import jarvis` fails with `No module
named 'jarvis'` even though `ls` shows the files. Worse: the working copy can
silently lose `.git` AND `jarvis/__init__.py`, so the repo is broken and `git`
commands error.

## Root cause
On this Windows box `C:\one` is a **junction** to `C:\c\one`. MSYS bash, the
write_file tool, and Python each resolve `/c/one` slightly differently, producing
a split-brain where files exist but are invisible/importable from the path you
think you're using. The junction copy also became corrupted (missing `.git` +
package init), which is fatal — not just confusing.

## Fix / canonical rule (use this, not the junction)
1. **Never keep the live project under a junction** (`C:\one` or `C:\c\one`).
2. **Clone to a plain, non-junction path** and treat it as canonical:
   `C:\Users\PREM KUMAR\prems-jarvis-hermes`
3. Authoritative path probe (use this as source of truth):
   ```python
   python -c "import jarvis.cli, os; print(os.path.abspath(jarvis.cli.__file__))"
   ```
4. If the local copy EVER looks corrupted (missing `.git` / `jarvis/__init__.py`),
   **re-clone from GitHub `itsPremkumar/prems-jarvis-hermes`** — do NOT debug the
   junction copy.
5. Always set PYTHONPATH to the canonical path before any `python -m` call:
   `PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes python -m pytest -q`

## Why this matters for orchestrators
SQLite `jarvis_state.db`, cron workdir, `delegate_task` context paths, and the
Task Scheduler `.cmd` scripts must ALL use the SAME canonical, non-junction path.
Mixing `C:\one` / `C:\c\one` across write tool / terminal / cron causes "file not
found" and "0 tests" mysteries and, worse, silent repo corruption. Pick
`C:\Users\PREM KUMAR\prems-jarvis-hermes` and use it everywhere.
