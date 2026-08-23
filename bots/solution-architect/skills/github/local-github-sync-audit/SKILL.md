---
name: local-github-sync-audit
description: "Audit many local git repos against GitHub and safely reconcile unsynced work (unpushed commits, dirty trees, diverged forks, broken rebases). Use when the user says 'is all my work pushed to GitHub', 'check yesterday's commits landed', 'verify nothing is left uncommitted', or owns a tree of many repos where some are real projects and others are scratch/staging copies."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Git, Sync, Audit, Reconcile, Multi-repo]
    related_skills: [github-repo-management, github-auth, git-credential-manager-windows]
---

# Local → GitHub Sync Audit & Reconcile

A recurring class for this user: a single working tree (e.g. `C:/one`) holds **dozens** of repos — real projects, scratch/staging copies, and temp dirs. The user frequently asks "did all my work get pushed?" The naive answer ("git status, looks clean") is wrong because the interesting repos have **no upstream tracking branch** or are **diverged from a differently-named remote default branch**. This skill is the disciplined version.

## When to use
- "is all yesterday's work on GitHub?"
- "check the commits were pushed"
- "make sure nothing is left uncommitted/unpushed"
- Pre-emptive housekeeping across a multi-repo tree.

## Phase 0 — Scope & assumptions
**SCOPE CONFIRMATION (NEW this session — load-bearing).** When the user says
"sync/push ALL my repos" or "sink everything to local", DO NOT blindly enumerate and
clone/push the entire GitHub account. This user owns **259 repos**; a mass clone/push
burns disk, RAM (this box is memory-starved), and time, and most repos are irrelevant
scratch. In this session the user said "sync all repositories" then **immediately
corrected**: "only the automation project — the project used for code". **Confirm scope
before any large operation**: enumerate owned repos via API, report the count + which are
already local, and ask which subset to sync (default: the active autonomous-company /
automation stack under `C:\one` + the canonical `prems-jarvis-hermes`). Only proceed to
bulk clone/push after the user confirms the subset. This is a scope-check, not a
clarification about credentials.

Do NOT assume every dirty tree is lost work. Classify each repo first:
- **Real project** → its work must reach GitHub.
- **Scratch/staging copy** (e.g. `clawhub-repos/*`) → remote already holds the canonical final state; the local copy is disposable/thoroughly re-derivable.
- **Live scheduler state** (e.g. `revenue/moltbook/*.json`) → owned by a running cron; never commit.
- **Pre-existing unrelated** (old date, no remote, different project) → leave alone unless asked.

## Phase 1 — Local audit loop (robust)
The naive `git rev-list @{u}..HEAD` **fails silently** when there is no upstream tracking branch, so a repo with no `origin` vanishes from the report. Use this fallback:

```bash
cd /root/of/repos
for d in $(find . -maxdepth 2 -name .git -type d 2>/dev/null | sed 's#/.git##'); do
  repo=$(basename "$d"); cd "$d" 2>/dev/null
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if git rev-parse --abbrev-ref @{u} >/dev/null 2>&1; then
    ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null)
  elif [ -n "$branch" ] && [ "$branch" != "HEAD" ] && git rev-parse "origin/$branch" >/dev/null 2>&1; then
    ahead=$(git rev-list --count "origin/$branch..HEAD" 2>/dev/null)
  else
    ahead="NO-UPSTREAM"   # no tracking AND no origin/<branch> -> investigate
  fi
  uncomm=$(git status --porcelain 2>/dev/null | wc -l)
  if [ "$ahead" != "0" ] && [ "$ahead" != "?" ] || [ "$uncomm" != "0" ]; then
    echo "[UNSYNCED] $repo | br=$branch | ahead=$ahead | uncommitted=$uncomm"
  fi
  cd /root/of/repos
done
```

For each flagged repo, also compute **behind** to detect divergence:
```bash
behind=$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null)
```
If `ahead>0 AND behind>0` (or local branch is `master` while remote default is `main`), it is a **diverged fork**, not a simple behind/ahead — handle per Phase 3 rule 2.

## Phase 2 — Remote cross-check (GitHub API)
List repos ordered by most-recent push to confirm the headline deliverable landed:
```bash
curl -s "https://api.github.com/users/$GH_USER/repos?per_page=100&sort=pushed" \
  -H "Authorization: token $GITHUB_TOKEN" \
  | python3 -c "import sys,json;[print(r['name'], r['pushed_at']) for r in json.load(sys.stdin)]"
```
This proves the remote has recent state but does NOT prove a *specific branch* push landed (see Phase 4).

## Phase 3 — Reconcile (priority order)
1. **Real project work** → commit selectively + push.
   - Stage real files explicitly; **exclude** `.bak` / `-backup` / `-preN` junk. Optionally add those patterns to `.gitignore`, commit, and push.
   - Never `git add .` blindly on a repo a cron may be writing to.
2. **Diverged fork** (ahead AND behind, or `master` vs `main`) → DO NOT force-push, DO NOT blind-merge. **Preserve local-new work on a new branch**:
   ```bash
   for f in $(git diff --name-only HEAD); do
     git cat-file -e origin/main:"$f" 2>/dev/null && echo "exists: $f" || echo "NEW: $f"
   done
   git checkout -b <feature-branch>
   git push -u origin <feature-branch>   # GitHub auto-opens a PR
   ```
3. **Missing remote** (local has commits, `git remote -v` empty, but GitHub has the repo) → `git remote add origin <url>`; `git fetch`; apply rule 2.
4. **Scratch/staging copy** (remote already holds final state, e.g. `version: 2.0.0`) → abort any rebase first, then reset to match remote:
   ```bash
   git rebase --abort 2>/dev/null
   git checkout -q main 2>/dev/null
   git reset --hard origin/main
   git clean -fd
   ```
   Only after confirming via the remote API the final state is what you want to keep.
5. **Live scheduler state** (e.g. `revenue/moltbook/*.json`) → DO NOT commit; a running cron owns and rewrites these.
6. **Pre-existing unrelated** → leave alone unless explicitly asked.

## Phase 4 — Verify the push actually landed
After `git push`, confirm via GitHub API on the **specific branch/SHA**, not the default-branch list (a default-branch query can miss a branch-only push):
```bash
# confirm a branch push landed
curl -s "https://api.github.com/repos/$GH_USER/$GH_REPO/commits?sha=ci/pre14-foundation&per_page=1" \
  -H "Authorization: token $GITHUB_TOKEN" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0]['commit']['message'][:60], d[0]['commit']['author']['date'])"

# confirm a new branch exists
curl -s "https://api.github.com/repos/$GH_USER/$GH_REPO/branches" \
  -H "Authorization: token $GITHUB_TOKEN" \
  | python3 -c "import sys,json;print([b['name'] for b in json.load(sys.stdin)])"
```

## Pitfalls (all hit in real use)
- `git rev-list --count @{u}..HEAD` **errors/fails silently** with no upstream tracking branch → a repo with no `origin` disappears from a naive scan. Always fall back to `origin/<branch>` or flag `NO-UPSTREAM`.
- A repo **mid-rebase** shows `HEAD -> (no branch, rebasing main)` with `UU <file>` conflict markers. `git reset --hard` will fail/lose state — run `git rebase --abort` FIRST.
- Local `master` vs remote default `main` looks like "diverged", not "behind". That is normal; treat per rule 2, not as a rebase-to-flatten.
- `git clean -fd` removes untracked files — safe on scratch copies, dangerous on a real project. Scope to scratch dirs only.
- The GitHub default-branch push-time query does not reveal a branch-specific push; always query the exact branch SHA.
- **`git -C <path>` FAILS on this Windows/MSYS host** with `fatal: cannot change to '<path>/'` even though the dir exists (the `cd /c/one` CWD is fine, but `git -C` path translation chokes). Use the explicit form instead, with **Windows backslash paths**:
  ```bash
  git --git-dir="C:\one\Repo\.git" --work-tree="C:\one\Repo" status -s
  ```
  A Python helper that loops `os.listdir(root)` and calls `subprocess.run(["git", f"--git-dir={dp}\\.git", f"--work-tree={dp}", ...])` is the robust pattern here (see `hermes-ops-dashboard` for the same trick). Don't fight `git -C`.
- **`git push` cannot create a repo** (returns `remote: Repository not found`). If a local
  repo's remote is missing on GitHub, **create it via the REST API first**, then push. After
  fixing the dual-identity GCM bug (see `git-credential-manager-windows`), `git credential
  fill` returns the token silently, so you can:
  ```bash
  TOK=$(printf 'protocol=https\nhost=github.com\nusername=itsPremkumar\n' \
          | git -c credential.https://github.com.username=itsPremkumar credential fill \
          | sed -n 's/^password=//p')
  # write repo payload to a file (avoid shell-quoting JSON), then:
  curl -sS -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
       --data @/tmp/repo_create.json https://api.github.com/user/repos
  ```
  Use `--data @file` (NOT inline `-d '...'`) — single-quoted JSON with embedded `\"` gets
  mangled by the MSYS shell. Then `git push -u origin main`.
- **Non-fast-forward on push** (tip of your branch rejected) → **`git pull --rebase`**
  (rebase local work onto remote), NOT `git pull` (merge) and NEVER `git push --force`.
  This preserves the user's local commits on top of remote history. If a rebase hits a
  conflict, abort (`git rebase --abort`) and surface it — don't silently `--force`.
- **Wrong remote URL** is common: `paperclip-company` was pointing at
  `Hermes-Full-Autonomous-Company`. Before pushing, check `git remote get-url origin`
  matches the repo name; fix with `git remote set-url origin <correct-url>`.
- When cloning missing repos at scale, use `--depth 1` (shallow) to spare disk/RAM on this
  memory-starved host; note the user can later `--unshallow` if full history is needed.

## Phase 5 — Worktree unmerged-code audit ("which branch has work not in main?")
A sibling class: the user keeps **multiple git worktrees** (e.g. `C:\one\Repo`, `C:\one\Repo-prod-grade`, `C:\one\repo-improvements`) each on its own branch, and asks "analyze the worktrees — is any code NOT merged into main?"

Robust procedure:
```bash
git worktree list                      # map each dir -> branch
# for each worktree branch B:
git merge-base --is-ancestor B main && echo MERGED || echo NOT   # cheap merged? check
git rev-list --count main..B                                     # commits ahead of main
git log main..B --pretty=format:"%h %ci %s" --date=iso           # what those commits are
```
Also sweep ALL local branches, not just worktree ones:
```bash
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  c=$(git rev-list --count main..$b 2>/dev/null); [ "$c" != "0" ] && [ -n "$c" ] && echo "$c  $b"
done | sort -rn
```

**CRITICAL — the raw diff LIES.** `git diff main..B --stat` on a branch that forked long ago shows huge **deletions**. That is NOT "B removed code"; it means **main advanced past B's fork point**. To see B's *own real work*, diff against the merge-base:
```bash
MB=$(git merge-base main B); git diff $MB..B --stat        # B's actual additions/changes
```
Then, per file, decide if it's genuinely missing from main — hashes always differ once main moved, so compare **semantically** (grep for the function/dep/behavior on main), not by blob hash:
```bash
git grep -n "someNewFunction" main -- src   # already on main independently?
git show main:package.json | grep -i "the-new-dep"
```

## Phase 6 — Merge vs cherry-pick: the "is it useful?" safety decision
When the user asks "if I merge branch X into main, will it be useful or harmful?", **never answer from the commit list alone — run a no-commit dry merge and inspect.**
```bash
git merge --no-commit --no-ff X            # DRY RUN
git diff --cached --stat                    # what a 3-way merge would actually change
sed -n '/<<<<<<< /,/>>>>>>> /p' <conflicted-file>   # read each conflict
git merge --abort                           # then back out
```
Key realizations that decide the answer:
- A **3-way merge is FAR safer than the raw diff suggests** — it preserves main's newer work and typically touches only a handful of files, not the scary deletion count.
- **Read every conflict hunk to check direction.** A conflict often reveals **main is AHEAD** of the old branch (e.g. main captures ffmpeg stderr `stdio:['ignore','ignore','pipe']` while the old branch swallows it `stdio:'ignore'`). A full merge would **regress** that — so the honest answer is "merge = partly useful, partly harmful."
- Therefore prefer **targeted cherry-picks of the genuinely-missing valuable commits** over a wholesale merge:
  ```bash
  git cherry-pick <sha1> <sha2> ...     # each lands independently, no old-code regression
  ```
- **Verify usefulness empirically after picking**: `npx tsc --noEmit` (or the project's build/test) must pass, and re-grep that each fix is now present on main. Report which commits you left OUT and why (already-on-main / behavior-changing / superseded).
- Respect the user's standing rules: **commit but do NOT push** without explicit go; **never delete/modify old code** — cherry-pick adds, it doesn't rewrite. Flag any pre-existing uncommitted file as "not mine, left untouched."

**Worktree audits double as latent-bug discovery.** Reading a diverged branch's fixes
against main often surfaces bugs STILL LIVE on main that the branch fixed but never landed —
treat "why did the old branch change this line?" as a bug-hunt lead. Real finds: `-ss` BEFORE
`-i` in single-frame ffmpeg extraction (yields undecodeable frames on J-cut/itsoffset/shifted
streams, so the vision QA validates a black frame — put `-ss` AFTER `-i`); a `String.raw` duck
expression injecting stray backslashes into a `volume='...'` filter (commas stay RAW in ffmpeg
*volume* exprs, unlike *drawtext* where you escape them); inconsistent field defaults across files.

See `references/worktree-merge-audit.md` for the cherry-pick worked recipe.
For the full-merge workflow (this session), see `references/full-merge-execution.md`.

## Phase 7 — Full merge execution (when the user says "merge everything")
When the user says "do all the possible working things in the main code" (merge everything
from a worktree branch), the execution path differs from cherry-picking:

1. **Commit all uncommitted changes in the worktree first**
   ```bash
   cd /c/path/to/worktree
   rm -f '$null' 2>/dev/null          # remove artifact empty files before staging
   git add -A                          # stage everything (modified + untracked)
   git commit -m "descriptive message"
   ```

2. **Dry-run merge on the main worktree** to preview conflicts
   ```bash
   cd /c/path/to/main-checkout
   git merge --no-commit --no-ff <branch>
   ```
   Read every conflict hunk — some reveal **main is ahead** and the worktree branch is
   older. For these, the worktree version may still be **more comprehensive** (e.g. extra
   safety checks, better test assertions). Pick the right side per hunk.

3. **Resolve conflicts, stage, and commit**
   ```bash
   # manually edit conflicted files to pick the right side
   git add <resolved-files>
   git commit -m "Merge branch '<branch>' into main"
   ```

4. **Prune stale worktrees** (deleted directories)
   ```bash
   git worktree prune
   ```

5. **Verify the merge**
   ```bash
   npm run typecheck (or: npx tsc --noEmit)
   node --import tsx --test <changed-test-file>
   ```

**Real workbook pattern (this session):** `qa/production-hardening` had 12 unmerged commits
+ 3 modified files + 4 untracked files (including `$null` artifact). The fork point was
~24h old with 20+ main commits ahead. Merge conflict was in one test file: both sides
touched the same `buildDuckExpression` assertion; the worktree version was more
comprehensive (added escaped-commas + no-gt() checks), so we took that side. Result:
1 merge commit, 7/7 tests pass, typecheck clean.

## Phase 8 — Backslash-escaping workaround in TS test files
When merging files that contain JS-string-escaped backslashes (e.g. `'\\\\,'` to match the
runtime string `\\,`), the `patch` tool can double-escape. **Never fight the tool — use
Python to read and rewrite exact bytes:**
```python
import re
path = "tests/path/to/file.test.ts"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# Fix a line that got over-escaped (replace N backslashes with 2)
lines[77] = re.sub(r"includes\('[\\\\]+,'", "includes('\\\\,',", lines[77])
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
```
Inspect with `repr()` first; write back exactly what JS needs.

## Support files
- `scripts/sync_audit.sh` — full ready-to-run scanner (local loop + behind + per-repo classification hint).
- `references/worktree-merge-audit.md` — worktree unmerged-code audit + merge-vs-cherry-pick decision recipe.
- `references/full-merge-execution.md` — full merge execution workflow (commit-pending, dry-run, resolve, land, prune, verify).
- `references/reconcile-playbook.md` — expanded decision flow with the exact commands per repo class.
