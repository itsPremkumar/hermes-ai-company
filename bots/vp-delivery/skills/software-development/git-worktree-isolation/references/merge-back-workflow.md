# Merge-Back Workflow — Worktree Branch → Main

Complete, verified workflow for merging a worktree branch back into `main`, based on a production-hardening merge that brought 13 commits + uncommitted fixes across 7+ files with zero regressions.

## 1. Pre-merge audit

Before attempting the merge, inventory every worktree:

```bash
git worktree list
```

Identify which worktrees have work that isn't in `main`:

```bash
# Check each worktree's branch for commits not in main
git log main..<branch> --oneline
git log main..<branch> --since="24 hours ago"  --oneline
```

Also check for **uncommitted changes** inside each worktree:

```bash
cd /path/to/worktree
git status --short
```

## 2. Commit all uncommitted worktree changes

Before merging, every uncommitted change in the worktree must be committed to its branch:

```bash
cd /path/to/worktree
git add -A
git commit -m "<scope>: <description of all uncommitted changes>"
```

Remove any obvious artifacts first (empty files, debug output, etc.):

```bash
rm -f '$null'  # Windows/PowerShell artifact
```

## 3. Dry-run merge (from main worktree)

Switch to the main repo and attempt a dry-run merge:

```bash
cd /path/to/main-repo
git merge --no-commit --no-ff <branch>
```

- `--no-commit` prevents the merge from finalizing — you inspect first
- `--no-ff` forces a merge commit even when fast-forward is possible (keeps history clear)
- If it says "Automatic merge failed; fix conflicts and then commit the result" → handle conflicts

Check which files were auto-merged cleanly:

```bash
git diff --cached --stat
```

List conflicted files:

```bash
git diff --name-only --diff-filter=U
```

## 4. Resolve conflicts

For each conflicted file, read it and analyze both versions:

```bash
# Read the file to see conflict markers
cat path/to/conflicted/file.ts

# View each side
git show HEAD:path/to/file.ts  # main's version
git show <branch>:path/to/file.ts  # branch's version
```

Resolution strategy — prefer the **more complete** version:
- The branch version typically has the more recent fixes
- Add **both** sets of changes where they're additive, not contradictory
- Use the branch version when it's strictly a superset (more assertions, better fix)
- When HEAD already has the fix but in a different form, compare and merge the intent

For escaping issues in test files (JS backslash hell), use Python to fix the raw file bytes rather than fighting shell escaping:

```python
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# Fix the line directly
lines[77] = "    assert.ok(!withSpeech!.includes('\\\\,'), 'commas must stay raw for ffmpeg');\n"
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
```

After resolving, stage the fixed file:

```bash
git add path/to/resolved/file.ts
```

## 5. Commit the merge

Once ALL conflicts are resolved and ALL files are staged (check with `git status --porcelain` — should show no unmerged files):

```bash
git commit -m "Merge branch '<branch>' into main

<Concise summary of what the branch brought in>
...
"
```

The commit message should list the major feature groups brought in by the merge, not every individual commit.

## 6. Verify the merge

### Typecheck
```bash
npm run typecheck  # or: npx tsc -p tsconfig.json --noEmit
```

### Test the conflicted file(s) specifically
```bash
node --import tsx --test --test-timeout=240000 --experimental-test-module-mocks path/to/conflicted/file.test.ts
```

All tests in the previously-conflicted file must pass — this proves the conflict resolution didn't break logic.

## 7. Clean up stale worktrees

After merging, prune worktrees whose directories have been deleted:

```bash
git worktree prune
```

This removes stale entries from `.git/worktrees/`. Verify:

```bash
git worktree list
# Should only show worktrees whose directories still exist
```

## 8. Push

```bash
git push origin main
```

Verify push succeeded:

```bash
git log --oneline main -1     # Should be the merge commit
git status --short            # Should be clean
```

## 9. Post-push: check main worktree is still on `main`

After pushing, background processes (auto-merge bots, scheduled jobs, dependabot) may have
switched the main worktree to another branch without you knowing. Verify:

```bash
git branch --show-current     # Should print 'main'
```

If it shows something else (e.g. `dependabot/npm_and_yarn/...`), switch back:

```bash
git checkout main
```

Then confirm up-to-date:

```bash
git log --oneline main -1
```

## 10. Documentation audit (post-merge)

After a worktree merge, the `docs/` folder may be stale — features the branch added or changed
are now in `main`, but the written documentation still describes the old state. Run a
documentation audit:

```bash
# 1. What changed recently?
git log --oneline main --since="24 hours ago" | head -20

# 2. Inventory the docs that reference changed areas
ls docs/*.md

# 3. For each doc, cross-reference against the actual codebase:
#    - New CLI flags → check bin/agentic-run.ts and src/adapters/cli/
#    - New env vars → check .env.example and src/constants/config.ts
#    - New source files → check if FILE_STRUCTURE.md lists them
#    - Changed defaults → check src/lib/*.ts for default values
#    - Vendored dependencies: check if said "external" dep is actually
#      in-repo (e.g. `src/speech/` for Voicebox) — update docs accordingly
#    - Test count / test commands → check package.json scripts

# 4. Key docs to always audit after a code-change burst:
#    CHANGELOG.md        — add unreleased entries
#    cli-reference.md    — sync all npm scripts + flags
#    ENVIRONMENT.md      — add/update env vars
#    usage.md / QUICKSTART.md — update primary workflow examples
#    configuration.md   — update config options table
#    FILE_STRUCTURE.md   — add new directories/files
#    TESTING.md          — update test counts, commands
#    troubleshooting.md  — add new common issues
#    Any provider-specific docs (VOICEBOX_*, VOICE_CLONING_*) — verify
#      vendored vs external dependency descriptions match reality
```
