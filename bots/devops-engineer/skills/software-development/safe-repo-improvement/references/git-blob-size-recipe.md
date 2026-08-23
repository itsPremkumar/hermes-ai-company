# Decide if a git history rewrite (force-push / BFG / filter-repo) is worth it

Use when a "large file is bloating the repo" accusation surfaces. Rewrite is
DESTRUCTIVE to the shared repo — only do it if the blobs are actually large.

## Step 1 — is it tracked on the working branch / default branch?
```bash
# currently tracked in tree?
git ls-files | grep -E '\.mcp-jobs\.json$'

# on origin/main tree?
git ls-tree -r --name-only origin/main | grep -qx 'PATH'

# default branch name
git remote show origin | grep 'HEAD branch'
```

## Step 2 — which refs actually contain it?
```bash
for b in $(git for-each-ref --format='%(refname)' refs/heads refs/remotes); do
  if git ls-tree -r --name-only "$b" 2>/dev/null | grep -qx 'PATH'; then
    echo "ON: $b"; fi
done
```

## Step 3 — is each commit an ancestor of main (reachable = actually bloat)?
```bash
for h in $(git log --all --format='%H' -- PATH); do
  git merge-base --is-ancestor "$h" origin/main 2>/dev/null \
    && echo "REACHABLE: $h" || echo "dead-history: $h"
done
```

## Step 4 — measure the real blob sizes (the only number that matters)
```bash
for h in $(git log --all --format='%H' -- PATH); do
  blob=$(git rev-parse "$h:PATH" 2>/dev/null)
  [ -n "$blob" ] && echo "$h -> $(git cat-file -s "$blob") bytes"
done
# live working-copy size:
du -h PATH
```

## Decision rule
- Live file already gitignored AND total historical blobs < ~1 MB → **do NOT rewrite.**
  Skip it, say why. (Real case: "14 MB" guess was 16 KB live + ~15 KB history.)
- Blobs are MB-scale AND the file is on main's reachable history → rewrite is justified
  (BFG `--strip-blobs-bigger-than 1M` or git filter-repo), then force-push + notify
  collaborators. Still needs explicit user confirmation — it's destructive.

## Always also check
- Does the file still exist in `.git` pack and inflate clone size? `du -sh .git`.
- Is it in `runtimeManagedRoots` / `.gitignore`? If ignored but in history, the
  worst case is historical bloat only — see rule above.
