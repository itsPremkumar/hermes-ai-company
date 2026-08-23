# Worktree Code Audit — Finding & Merging Uncommitted Work

Check every git worktree for code that exists on a branch but has NOT been
merged into `main` — whether committed or uncommitted. This prevents work
from being lost in abandoned worktrees.

## When to Use

- User asks "check worktrees for uncommitted code"
- User has many worktrees and wants to ensure nothing is lost
- Before cleaning up stale worktrees
- As part of a broader codebase audit

## Workflow

### Step 1 — List all worktrees

```bash
git worktree list
```

Output shows each worktree's path, HEAD commit, and branch:

```
C:/repo/main                 abc1234 [main]
C:/repo/feature-branch       def5678 [feat/feature] prunable
```

Note: `prunable` means the worktree directory no longer exists on disk but git
still has a reference to it.

### Step 2 — Find pruned/stale worktrees

Try to cd into each worktree path. If the directory doesn't exist, the worktree
was deleted externally but git still tracks it:

```bash
ls -d /c/one/<worktree-path> 2>&1
```

Any that fail with "No such file or directory" are stale.

### Step 3 — Check each existing worktree for uncommitted changes

```bash
cd /c/one/<worktree-path> && git status --porcelain
```

Interpretation:
- Empty output = clean (no uncommitted changes)
- ` M <file>` = modified but not staged
- `?? <file>` = untracked new file
- `A  <file>` = staged but not committed

Also check for staged-but-uncommitted changes:
```bash
git diff --cached --stat
```

### Step 4 — Check for commits not in main

For each worktree branch, find commits that exist on the branch but NOT on
main:

```bash
# From the main repo
cd /path/to/main

# Local branches
git log main..<branch-name> --oneline

# Remote tracking branches
git log main..origin/<branch-name> --oneline
```

If a branch has unique commits, check when they were authored:
```bash
git log main..<branch-name> --oneline --since="24 hours ago"
```

### Step 5 — Understand the divergence point

Find when the branch forked from main:

```bash
git merge-base main <branch-name>
git log -1 --format="%h %s (%ai)" $(git merge-base main <branch-name>)
```

This tells you how far behind main the branch is. If the merge-base is old,
the branch may have many merge conflicts to resolve.

### Step 6 — Merge strategy

**Option A — Direct merge (simplest):**
```bash
cd /path/to/main
git merge --no-commit --no-ff <branch-name>
```

Check for conflicts:
```bash
git diff --name-only --diff-filter=U
```

Resolve any conflicts, then:
```bash
git add <resolved-files>
git commit -m "Merge branch '<branch-name>' into main"
```

**Option B — Rebase + merge (cleaner history):**
```bash
cd /path/to/worktree
git fetch origin
git rebase origin/main
# Resolve conflicts during rebase
git checkout main
git merge <branch-name>
```

### Step 7 — Handle uncommitted changes in the worktree

Before merging, either:
1. Stash them: `git stash` (merge first, then pop)
2. Commit them on the branch first: `git add -A && git commit -m "..."`

For new files in a worktree that should be committed before merge:
```bash
cd /path/to/worktree
git add -A
git commit -m "feature: <description of work>"
```

### Step 8 — Clean up after merge

```bash
# Prune stale worktree references
git worktree prune

# Optionally remove the merged worktree
git worktree remove /path/to/worktree --force
git worktree prune

# Push merged main
git push origin main
```

### Step 9 — Verify merge completeness

```bash
# Confirm branch commits are now reachable from main
git merge-base --is-ancestor <branch-name> main && echo "YES — all merged" || echo "NO — still missing"

# Check no remaining commits ahead
git log main..<branch-name> --oneline
```

Confirm the key new files exist in main:
```bash
# Check files that were unique to the worktree
test -f path/to/new-file.ts && echo "EXISTS" || echo "MISSING"
```

### Step 10 — Validate the merged code

Run typecheck and tests on main:

```bash
npm run typecheck
node --import tsx --test --test-timeout=240000 --test-concurrency=2 --experimental-test-module-mocks "path/to/conflicted-test.test.ts"
```

## Pitfalls

- **The `cd` to a worktree may fail due to MSYS path translation.** When
  `git worktree list` shows `C:/one/proj-worktree`, use exactly that path
  in `cd`. If it fails, try `C:/c/one/proj-worktree` (the MSYS translation
  adds an extra `/c`).
- **Don't trust `git log main..<branch>` from inside the worktree** — the
  worktree may not have `main` checked out locally. Run the comparison from
  the main repo's directory.
- **A worktree directory that no longer exists but shows `prunable`** doesn't
  lose the branch commits — they're still in the git object store. The branch
  can be checked out in the main repo. But the uncommitted work IS lost when
  the directory is deleted.
- **Always verify key files exist in main after merge** — auto-merge may
  silently skip new files if they conflict with existing ones.
- **The `patch` tool may double-escape backslashes** in string content when
  editing files. After patching, verify with `read_file`.
