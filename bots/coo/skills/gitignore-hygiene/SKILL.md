---
name: gitignore-hygiene
description: Tracked junk re-dirties git? Add rule + git rm --cached.
category: devops
---

# .gitignore Hygiene (mixed-language repos)

## When to use
- User points at git status / VS Code Source Control showing `M` or `??` entries for `__pycache__/*.pyc`, `dist/`, `node_modules/`, `*.log`, venv, or other generated artifacts that *should* be ignored.
- Adding ignore rules to an existing repo that already has those files committed.
- Auditing a repo where generated/regenerable files are tracked.

## The core pitfall (most important lesson)
**Adding a rule to `.gitignore` does NOT retroactively stop git from tracking files it already follows.**
If `foo.pyc` was committed earlier, it stays tracked and keeps showing as `Modified` every time the interpreter rewrites it — even after you add `__pycache__/` to `.gitignore`. The ignore file only prevents *new, untracked* files from being added.

Fix requires TWO moves:
1. Add the ignore rule (so future files are excluded).
2. **Untrack** the already-committed files with `git rm --cached -r` (files stay on disk; only the index entry is removed).

## Workflow
1. **Audit what's already tracked** (the junk you need to untrack):
   ```bash
   git ls-files | grep -iE "__pycache__|\.pyc$|\.pyo$|dist/|node_modules/|\.venv/|venv/|\.log$"
   ```
   Save the list, e.g. `git ls-files | grep -iE "\.pyc$" > /tmp/junk.txt`.

2. **Add the ignore rules** to the right `.gitignore`. Prefer the repo-root one for cross-cutting artifacts; add a subdir `.gitignore` only when the rule is package-local (e.g. a vendored backend's own ignore already exists — check with `find . -name .gitignore` first; don't duplicate).

3. **Untrack the already-committed junk** (cached only — files are NOT deleted from disk):
   ```bash
   git rm --cached -r --quiet $(cat /tmp/junk.txt)
   ```
   After this, `git status` shows `D` (staged deletions) for those entries — that is the intended cleanup. They are no longer on-disk-tracked.

4. **Verify** (see below). If a new compile still shows as dirty, the rule doesn't match — fix the pattern.

## Verification — git IS the verifier (not npm/tsc)
A `.gitignore` change is NOT covered by `npm run test`, `tsc`, `eslint`, or any source linter. Those test code, not ignore rules. The authoritative verifier is git itself:
```bash
# 1) rule actually matches the path
git check-ignore -v src/speech/__pycache__/main.cpython-311.pyc
#    -> prints "<file>:<line>:<rule>\t<path>"  => rule is active

# 2) nothing of that kind is still tracked
git ls-files | grep -c '\.pyc$'        # want: 0

# 3) simulate a NEW dirty file to prove future regen won't re-dirty the tree
touch src/speech/__pycache__/_probe_test.cpython-311.pyc
git status --short | grep -c "__pycache__/_probe"   # want: 0
rm -f src/speech/__pycache__/_probe_test.cpython-311.pyc

# 4) git still parses the ignore file without error
git status --porcelain >/dev/null && echo "git OK"
```
Note: `git status` will still list the staged `D` deletions — those are expected. Filter with `grep -vE "^D"` to confirm no *live* (untracked/modified) dirt remains: `git status --short | grep "__pycache__" | grep -vE "^D"` must be empty.

## Mixed Node/TS + Python ignore template
For a repo with both a TS app and a vendored Python backend (the AVS case), a root-level Python block is needed IN ADDITION to existing Node/TS rules. See `references/mixed-node-python-gitignore.md` for a known-good block to append.

## Pitfalls
- **Forgetting `git rm --cached`** → the file keeps re-appearing as `M` forever. Fix is the untrack step, not more ignore rules.
- **Using `git rm` (no `--cached`)** → deletes the file from disk. Always use `--cached` for ignore cleanup.
- **Subdir `.gitignore` already exists** → don't re-add the same rule at root; `git check-ignore -v` will tell you which file/line matched. Honor the existing one.
- **`.bak` / runtime JSON under input/** → if the project intentionally tracks sample configs but generates per-run variants, ignore only the generated variants (e.g. `*.bak`, `*-backup.json`), not the canonical `input-scripts.json`. Check git history before ignoring.
- **Thinking `npm test` "verifies" the change** → it does not. Git is the only verifier for ignore rules.
