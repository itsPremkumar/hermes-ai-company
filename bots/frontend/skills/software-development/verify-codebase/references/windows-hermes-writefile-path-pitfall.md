# Windows + Hermes `write_file` path-translation pitfall

## Symptom
`write_file` reports `bytes_written` + `resolved_path: C:\Users\PREM KUMAR\...`
**but the file lands in the wrong place** — off by one directory level, or under a
stray prefix. Observed case:

- Intended: `C:\Users\PREM KUMAR\samm\tests\test_webui.py`
- Actual:   `C:\Users\PREM KUMAR\samm\samm\tests\test_webui.py`   (one dir too deep)
- Linter error also shows the path mangled with a doubled drive prefix:
  `C:\c\Users\PREM KUMAR\samm\samm\webui\app.js` (the `C:\c\...` is a
  git-bash/MSYS `$PWD` ↔ Windows-path translation artifact, not the real on-disk path).

So the file WAS written, just not where the caller expected. `ls`/glob on the intended
path then reports "file not found" and the test/import that depends on it silently does
nothing → the whole suite can time out or skip unexpectedly.

## Root cause
When the `path` argument is a Windows absolute path on this git-bash/Python312 host,
the `write_file` resolver can mis-translate the MSYS path into the Windows path,
duplicating a directory component (e.g. `samm/samm/`) or pre-pending a stray `C:\c\`.
The resolved path printed back is already wrong, so the write succeeds *against the
wrong target*.

## How to catch it (do this AFTER every write_file on this host)
1. Confirm the intended file exists where you expect:
   ```bash
   find . -name "test_webui.py"      # or whatever the target basename is
   ls -la tests/                     # the intended directory
   ```
2. If `find` reports the file under an unexpected path (e.g. `samm/tests/` instead of
   `tests/`), move it:
   ```bash
   mkdir -p tests
   cp samm/tests/test_webui.py tests/test_webui.py
   rm samm/tests/test_webui.py
   ```
3. Re-run the verification command that depends on the file's location.

## Why this matters for verification
A misplaced test file is the *worst* kind of silent failure: `pytest tests/` collects
a different (or empty) set, the suite may appear to pass on a stale cache, or hang on a
collection/import that never resolves. Always `find . -name <basename>` after creating
files via `write_file` on this box — never trust the printed `resolved_path` alone.

## Related
- `verify-codebase` Step 6 "Re-verify file persistence AFTER the build" covers the
  *vanish/revert* race (different bug: file disappears after a heavy run). This doc is
  the *wrong-directory* variant: file exists but not where you asked. Both fall under
  "confirm on disk with `find`/`ls`, don't trust the tool's echo."
