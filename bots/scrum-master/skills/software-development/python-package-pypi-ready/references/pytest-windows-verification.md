# Proving a pytest suite is green under Windows / MSYS (git-bash)

## The problem
Under git-bash, `pytest` emits its final summary line (`59 passed, 1 skipped in 34s`)
using `\r` carriage returns. When you pipe or redirect (`pytest 2>&1 | grep passed`),
that line gets overwritten and `grep` finds nothing — even on a fully green run. You
see the dot-progress bar (`....s....`) but no count. Naive `grep "passed"` fails.

## The dependable probe (in-process, prints rc)
Run pytest from inside Python so the return code is the source of truth. rc=0 ⇒ all
pass; rc!=0 ⇒ failures/errors. Works regardless of `\r` terminal weirdness.

```bash
PY312="/c/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe"
cd "/c/Users/PREM KUMAR/samm"
env -u PYTHONPATH "$PY312" - <<'PY'
import sys, pytest
rc = pytest.main(["tests/", "-q", "--no-header", "-p", "no:cacheprovider"])
print("PYTEST_RC=", rc)
sys.exit(0)
PY
echo "shell exit=$?"
```

## Fallback: read the dot bar
The progress line is `N` dots (passed) + letters per outcome:
- `.` = passed
- `s` = skipped
- `F` = failed
- `E` = error

`............................s...............................` = 59 passed, 1 skipped.

## Stripping `\r` (flaky, secondary)
`pytest ... 2>&1 | tr -d '\r' | grep -iE "passed|skipped"` sometimes surfaces the
line but the progress bar can still eat it. Prefer the in-process probe above.

## Interpreter gotcha (environment, not a bug)
The default `python` on PATH may not have the project's native deps (`sqlite_vec`,
etc.). Locate the interpreter that has them installed (e.g. `Python312/python.exe`)
and run verification with that. Use `env -u PYTHONPATH` so the local `samm/` package
is imported from the cwd, not a stale installed copy.

## One-liner verification trio for a PyPI-readiness task
```bash
# 1) pyproject parses
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('pyproject OK')"
# 2) entrypoint importable
env -u PYTHONPATH "$PY312" -c "import samm.cli; print('main =', hasattr(samm.cli,'main'))"
# 3) suite green (use the in-process probe block above)
```
