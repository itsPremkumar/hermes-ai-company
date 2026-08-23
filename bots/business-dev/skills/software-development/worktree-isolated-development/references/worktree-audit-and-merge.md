# Worktree Audit & Merge-Back Workflow

When worktrees accumulate — especially from parallel development sessions or
abandoned branches — some may hold **uncommitted changes** and/or **uncommitted
commits** that were never merged back to `main`. This reference covers the
systematic discovery and consolidation workflow.

## When to use

- User says "check if worktrees have uncommitted code not in main"
- You find stale/prunable worktrees from `git worktree list`
- A worktree was created for a branch but never merged back
- Before cleaning up old worktrees to reclaim disk space

## Phase 1 — Discover all worktrees

```bash
cd /c/one/<project>
git worktree list
```

Output shows every worktree with its path, current HEAD commit, and branch.
Lines with `prunable` indicate the worktree directory was deleted but git
hasn't cleaned up the reference yet.

```text
C:/one/Project              781fc2d [main]
C:/one/Project-feature       e9a16a2 [feat/my-feature] prunable
C:/one/Project-hardening     a8586c1 [qa/hardening]
```

## Phase 2 — Check each worktree for uncommitted changes

```bash
cd <worktree-path>
git status --short
```

Three possible states:
- **Clean** — no output (no action needed)
- **Modified/staged** — `M` prefix files (need committing)
- **Untracked** — `??` prefix files (new files to review)

### Common remediation

```bash
# Stage and commit all pending work
cd <worktree-path>
git add -A
git commit -m "fix: description of pending changes"
```

Remove any obvious artifacts (e.g. empty `$null` files, temp logs) before
committing:

```bash
rm -f '$null' 'temp*.log'
```

## Phase 3 — Check for unmerged commits

A worktree's branch may have commits that exist locally but were never merged
into `main`. Check BOTH directions:

```bash
# From main repo:
git log main..<branch-name> --oneline          # commits on branch NOT in main
git log <branch-name>..main --oneline --since="24 hours ago"  # how far main has moved ahead
```

The key question: **how far behind is main?** Check the merge-base:

```bash
git merge-base main <branch-name>
git log -1 --format="%h %s (%ar)" $(git merge-base main <branch-name>)
```

If the merge-base is recent (hours/days), the merge is likely clean. If it's
days/weeks old, expect conflicts.

## Phase 4 — Dry-run the merge

From the **main worktree** (never merge from a secondary worktree):

```bash
cd /c/one/<project>  # main worktree
git merge --no-commit --no-ff <branch-name> 2>&1
```

This simulates the merge without committing. Check for:

- **Auto-merging** files — expected for parallel changes
- **CONFLICT** — needs manual resolution in specific files
- **Abort** on failure: `git merge --abort` if you need to start over

### Conflict resolution approach

1. Read the conflicted file (look for `<<<<<<< HEAD` / `=======` / `>>>>>>> branch`)
2. Determine which side's change to keep (or combine both)
3. The qa/production-hardening branch often has the **more comprehensive** fix
   because it was written after main's version and incorporates additional
   assertions or edge cases discovered during testing
4. Edit with `patch` tool, then `git add` the resolved file
5. Complete the merge: `git commit`

## Phase 5 — Verify the merged code

After the merge commit:

```bash
# Confirm commits are reachable from main
git merge-base --is-ancestor <branch-name> main && echo "YES — all merged" || echo "STILL MISSING"

# Run typecheck
npm run typecheck

# Run the affected test files
node --import tsx --test --test-timeout=240000 tests/path/to/resolved.test.ts
```

## Phase 6 — Clean up stale worktrees

```bash
# Prune deleted worktree references
git worktree prune

# Verify only active worktrees remain
git worktree list
```

The output should now show only the main worktree and any actively-used
secondary worktrees. Pruned ones are removed from the list.

## Phase 7 — Handle Worktree-Only Files (merge + copy pattern)

Some worktrees hold **files that do not exist on the main worktree at all**
(e.g. production-readiness docs, release notes, new test files). When these are
committed on the branch but need to reach `main`:

```bash
# Option A — merge (recommended for many files)
git merge <branch-name>

# Option B — cherry-pick (for a single commit's files)
git fetch . <branch-name>
git cherry-pick <commit-hash>

# Option C — manual copy (for uncommitted/new files in an orphan worktree)
# If the worktree directory was deleted but git still knows the branch:
git checkout <branch-name> -- path/to/new-file.ts  # overwrites local path
```

## Pitfalls

- **Main worktree may not be on `main`** — always check `git branch` first.
  If the main worktree checked out a different branch (e.g. a dependabot
  auto-branch), `git checkout main` before merging.
- **Dependabot / auto-branch interference** — a CI/dependabot process may
  switch the main worktree to a dependency branch between the time you push
  and the time you verify. If `git worktree list` shows the main repo on
  a non-`main` branch after a push, simply `git checkout main` and re-push.
- **`git merge-base --is-ancestor` can lie** — it only checks ancestry, not
  content. After a merge that produced conflicts, run actual tests/typecheck
  to validate the resolved content is correct.
- **Don't merge from inside a secondary worktree** — the merge lands in that
  worktree's HEAD, not in `main`. Always `cd` to the main worktree directory.
- **The `patch` tool may double-escape backslashes** in TS string literals
  when resolving merge conflicts. After patching a conflict that involves
  `\\,` (escaped comma) or similar escape sequences, verify the actual file
  content with `read_file` and fix any over-escaped sequences.

## Real-world example: qa/production-hardening merge

In one session, the `qa/production-hardening` worktree had:
- **12 commits** not in `main` (process leak fixes, download guards, CLI validation)
- **3 modified files** (human-readable labels, content gate, honest source labeling)
- **4 untracked files** (asset-validators.ts, test file, release notes, `$null` artifact)
- The merge-base was ~24h old; main had moved ahead significantly

**Workflow applied:**
1. `rm '$null' && git add -A && git commit` — committed pending changes
2. `git merge --no-commit --no-ff qa/production-hardening` — found 1 conflict
3. Resolved `enhancement.test.ts` (took branch's version with extra assertions)
4. `git commit` — commit message documented all brought-in fixes
5. `npm run typecheck && node --import tsx --test tests/file.test.ts` — verified
6. `git push origin main`
7. `git worktree prune` — cleaned stale references
