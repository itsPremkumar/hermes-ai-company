# Reconcile Playbook (expanded decision flow)

Each flagged repo from `scripts/sync_audit.sh` gets one of these treatments. The
order matters: do the cheap/safe cleanups (scratch copies) and the clearly-correct
pushes (real project work) first, then handle the dangerous divergence last.

## Step A — Real project: uncommitted source/docs or unpushed commit
Goal: get genuine work onto GitHub without pushing junk.

```bash
cd /path/to/real-repo
# stage real files explicitly; DO NOT `git add .`
git add src/foo.ts docs/SPEC.md
# exclude .bak / -backup / -preN junk; optionally gitignore them
printf '\n# local backup copies\ninput/*.json.bak-*\n' >> .gitignore
git add .gitignore
git commit -m "feat: real change summary"
git push origin <branch>
```
Never `git add .` on a repo a running cron writes to (e.g. `revenue/moltbook/*.json`).

## Step B — Diverged fork (ahead !=0 AND behind !=0, or master vs main)
DANGER: do not force-push, do not blind-merge. Preserve the local-new work on a
new branch so nothing is destroyed and GitHub opens a PR automatically.

```bash
cd /path/to/diverged-repo
# 1. find files genuinely new vs origin/main
for f in $(git diff --name-only HEAD); do
  if git cat-file -e origin/main:"$f" 2>/dev/null; then
    echo "exists on main: $f"
  else
    echo "NEW (preserve): $f"
  fi
done
# 2. park the new work on its own branch
git checkout -b prem-co-showcase     # or any descriptive name
git push -u origin prem-co-showcase  # auto-opens a PR on GitHub
```
If the repo has NO remote but GitHub already has it:
```bash
git remote add origin https://github.com/$GH_USER/$GH_REPO.git
git fetch origin
# then run the diff/checkout/push above against origin/main
```

## Step C — Scratch/staging copy (remote already canonical)
Safe to throw the local copy away and re-pin to remote's final state — but only
after confirming the remote holds what you want to keep (e.g. v2.0.0).

```bash
cd /path/to/scratch-copy
git rebase --abort 2>/dev/null          # kill any mid-rebase state first
git checkout -q main 2>/dev/null
git reset --hard origin/main
git clean -fd                            # removes untracked scratch files
```
Confirm the remote final state first:
```bash
curl -s "https://raw.githubusercontent.com/$GH_USER/$GH_REPO/main/SKILL.md" \
  | head -3     # expect e.g. version: 2.0.0
```

## Step D — Live scheduler state
Files like `revenue/moltbook/posted.json`, `post-research-ideas.json` are
rewritten by a running cron. LEAVE THEM. Do not commit, do not reset.

## Step E — Pre-existing / unrelated
Old commits (different date), no remote, different project → leave alone unless
the user explicitly asks.

## Verification (after every push)
Query the SPECIFIC branch/SHA on GitHub — the default-branch listing query
misses branch-only pushes:
```bash
curl -s "https://api.github.com/repos/$GH_USER/$GH_REPO/commits?sha=<branch>&per_page=1" \
  -H "Authorization: token $GITHUB_TOKEN" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['commit']['message'][:60], d[0]['commit']['author']['date'])"
curl -s "https://api.github.com/repos/$GH_USER/$GH_REPO/branches" \
  -H "Authorization: token $GITHUB_TOKEN" \
  | python3 -c "import sys,json;print([b['name'] for b in json.load(sys.stdin)])"
```
