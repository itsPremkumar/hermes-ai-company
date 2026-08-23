# ClawHub skill: create → verify → publish workflow

Proven end-to-end across 3 skills this session (json-tools, md-linter, file-watcher).

## Workflow

```
1. Create SKILL.md + tool.py in clawhub-skills/<slug>/
2. Smoke-test each subcommand
3. Write ad-hoc verification script → run → clean up
4. clawhub publish
5. clawhub inspect <slug> to confirm live
```

## Why verify before publish

`clawhub publish` snapshots the current folder. A broken tool ships as a broken
published skill. The verification script catches:
- Import errors (runtimes, missing stdlib modules)
- argparse mistakes (name clashes, wrong dest)
- Exit-code convention violations (CI tools must exit non-zero on findings)

## Verification script pattern

Write to an OS-safe temp path, run it, then delete it. The system may enforce
this pattern on edited code — best to do it proactively.

Two proven sub-patterns:

### Pattern A: mkdtemp + run_cmd (for tools with file I/O)

```python
#!/usr/bin/env python3
"""Ad-hoc verification for <skill-slug>."""
import os, sys, json, tempfile, shutil

TMP = tempfile.mkdtemp(prefix="hermes-verify-")
errors = 0

def ok(msg): print(f"  PASS  {msg}")
def fail(msg):
    global errors
    print(f"  FAIL  {msg}")
    errors += 1

def run_cmd(mod, cmd, args, expect_exit=None):
    """Call cmd_* on module, handling SystemExit.
    expect_exit: accept this exit code (e.g. 1 for lint tools on finding)."""
    try:
        getattr(mod, f"cmd_{cmd}")(type("A", (), args)())
        ok(f"{cmd} returned normally")
    except SystemExit as e:
        if e.code == 0 or e.code == expect_exit:
            ok(f"{cmd} exit({e.code})")
        else:
            fail(f"{cmd} exit({e.code})")
    except Exception as e:
        fail(f"{cmd} raised {type(e).__name__}: {e}")

# ── import and test ──
sys.path.insert(0, os.path.join(BASE, "my-skill"))
import my_tool as mt

# Create test fixtures
test_file = os.path.join(TMP, "input.txt")
with open(test_file, "w") as f: f.write("test data\n")

# Run each subcommand
run_cmd(mt, "check", {"paths": [test_file], "verbose": False}, expect_exit=1)
run_cmd(mt, "format", {"path": test_file, "write": False})
# ... more commands ...

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(errors)
```

Run it, then delete it:
```bash
python "C:\Users\PREM KUMAR\AppData\Local\Temp\hermes-verify-*.py"
rm -f "C:\Users\PREM KUMAR\AppData\Local\Temp\hermes-verify-*.py"
```

### Pattern B: stdout capture via StringIO (for tools that print output)

Use when the tool's subcommands print to stdout and you want to assert on
actual output rather than just exit codes. Also useful when testing inline
helper functions (`_strip_html`, `_extract_text`, etc.) that aren't subcommands.

```python
#!/usr/bin/env python3
"""Ad-hoc verification for <slug> — stdout capture variant."""
import sys, os, io, importlib, argparse

BASE = r"C:\one\paperclip-company\clawhub-skills"
passed = 0; failed = 0

def check(label, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1; print(f"  ✓ {label}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1; print(f"  ✗ {label}" + (f" — {detail}" if detail else ""))

sys.path.insert(0, os.path.join(BASE, "my-skill"))
mod = importlib.import_module("my_tool")
importlib.reload(mod)   # clear any prior import state

check("cmd_scan exists", hasattr(mod, "cmd_scan"))
check("cmd_format exists", hasattr(mod, "cmd_format"))

# Capture stdout for a printing command
buf = io.StringIO()
sys.stdout = buf
try:
    mod.cmd_scan(argparse.Namespace(paths=["input.txt"], verbose=False))
    output = buf.getvalue()
    check("scan produces output", "Scanned" in output or "result" in output)
except Exception as e:
    check("scan produces output", False, str(e))
sys.stdout = sys.__stdout__

# Test a helper function
stripped = mod._strip_html("<p>Hello</p>")
check("_strip_html basic", "Hello" in stripped)

total = passed + failed
print(f"Result: {passed}/{total} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
```

Key techniques:
- `importlib.reload()` clears cached state when testing multiple skills in sequence
- `io.StringIO` + `sys.stdout` swap captures print output without spawning a subprocess
- `argparse.Namespace(...)` constructs fake args without going through the CLI parser
- `hasattr()` checks that named functions actually exist before calling them
- Source-inspection checks (`"def cmd_scan" in open(mod.__file__).read()`) prove the
  function was defined in source even if the module-side dispatch differs from what
  `hasattr` finds at runtime

## Directory structure

```
clawhub-skills/<slug>/
├── SKILL.md                # frontmatter + rich body
├── <tool>.py               # the executable
├── examples/               # (optional) example files
└── tests/                  # (optional) test fixtures
```

## Why the rich body pattern

ClawHub skills are browsed from the registry UI and from `clawhub inspect`.
A SKILL.md with Install/Commands/Usage/Features/Examples/Why/Support sections
is self-contained — the user never needs to scroll past the file to understand
what it does. See `templates/clawhub-skill-SKILL.md` for the copy-modify template.
