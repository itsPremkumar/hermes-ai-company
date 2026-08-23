# Known-good Python block for a mixed Node/TS + Python repo

Append to the repo-root `.gitignore` (in addition to whatever Node/TS rules already exist).
Verified working in Automated-Video-Generator (Node/TS app + vendored `src/speech/` Python backend + `tools/computer-agent` Python).

```gitignore
# Python (bytecode, caches, virtualenvs) — regenerable, machine-specific
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

Notes from the AVS case:
- The repo already had `venv/`, `src/data/`, `*.db`, `voicebox.db` ignored at root — but NO `__pycache__`/`*.pyc` rules, so 140 `.pyc` files stayed tracked and re-dirtied VS Code Source Control on every Python recompile.
- `src/speech/.gitignore` ALREADY ignored `__pycache__/`, but the files were committed before that ignore existed, so they remained tracked until `git rm --cached -r`.
- `tools/computer-agent/src/__pycache__/` was tracked and NOT covered by any rule — the root-level block above fixed it.
- After adding the rule, run:
  `git ls-files | grep -iE "__pycache__|\.pyc$" > /tmp/junk.txt && git rm --cached -r --quiet $(cat /tmp/junk.txt)`
- Verify: `git ls-files | grep -c '\.pyc$'` must print `0`; `git check-ignore -v <any .pyc path>` must print the matching rule line.
- Do NOT use plain `git rm` (deletes from disk) — always `--cached`.
