# Worktree Unmerged-Code Audit & Merge-vs-Cherry-Pick — Worked Recipe

Full worked recipe backing Phases 5–6 of the umbrella. Real session:
`C:\one\Automated-Video-Generator` with 5 worktrees, user asked "which worktree
code from the last 2 days is NOT merged into main, and would merging be useful?"

## Step 1 — Map worktrees to branches, find unmerged ones
```bash
git worktree list                                   # dir -> branch -> HEAD sha
git branch -a                                       # + '+' marks worktree-checked-out branches
git log --all --since="2 days ago" --pretty=format:"%h %ci %d %s" --date=iso
```
Per worktree branch B:
```bash
git merge-base --is-ancestor B main && echo YES || echo NO   # already merged?
git rev-list --count main..B                                 # commits ahead
git log main..B --pretty=format:"    %h %ci %s" --date=iso
```
Then sweep EVERY local branch (worktrees are only a subset):
```bash
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  c=$(git rev-list --count main..$b 2>/dev/null)
  [ "$c" != "0" ] && [ -n "$c" ] && echo "$c  $b"
done | sort -rn
```

## Step 2 — The raw diff LIES; diff against merge-base instead
`git diff main..B --stat` on a long-forked branch shows massive DELETIONS.
That means **main advanced**, not "B deleted code." B's real work =
```bash
MB=$(git merge-base main B)
git diff $MB..B --stat            # B's actual additions/changes only
```
In the session, `main..prod-grade` showed −2870 lines (scary); `$MB..prod-grade`
showed the truth: +297/−40 across 23 files (Wave F–O on main caused the phantom deletions).

## Step 3 — Semantic presence check (blob hashes always differ once main moved)
Never conclude "missing from main" from a differing hash. Grep the behavior:
```bash
git grep -n "ffmpegDrawtextEscape" main -- src    # security fix already on main independently?
git grep -n "taskkill" main -- src                 # tree-kill present?
git show main:package.json | grep -i "@remotion/shapes"   # dep declared?
git show main:src/.../file.ts | sed -n '160,175p'  # read the actual function body on main
```
Classify each of B's changes: `ALREADY-ON-MAIN` (independently landed) /
`MISSING-FROM-MAIN` (genuinely useful) / `SUPERSEDED` (main has a better version) /
`OBSOLETE` (old prototype replaced by later work).

## Step 4 — Merge-vs-cherry-pick decision (never guess from commit list)
```bash
git merge --no-commit --no-ff B          # DRY RUN
git diff --cached --stat                  # what a 3-way merge really changes
sed -n '/<<<<<<< /,/>>>>>>> /p' <conflicted-file>   # READ every conflict hunk
git merge --abort                         # back out
```
- A 3-way merge is **far safer** than the raw diff — it preserves main's newer work,
  usually only a handful of files + one or two conflicts.
- **Read each conflict for direction.** In the session the `visual-fx.ts` conflict
  revealed **main was AHEAD** (captured ffmpeg stderr `stdio:['ignore','ignore','pipe']`)
  vs the old branch swallowing it (`stdio:'ignore'`). A full merge would REGRESS that.
- Verdict when main has diverged + carries newer fixes: **"merge = partly useful, partly
  harmful"** → cherry-pick the genuinely-missing commits, do NOT wholesale-merge.

## Step 5 — Cherry-pick only the useful, verify empirically
```bash
git cherry-pick <sha>       # each lands independently, no old-code regression
npx tsc --noEmit            # or the project build/test — MUST pass
git grep -n "<the-fix>" main -- src   # re-confirm each fix is now present
```
Report which commits you left OUT and WHY (already-on-main / behavior-changing / superseded).
Session example (4 landed cleanly, tsc clean):
- backend python **tree-kill** (`taskkill /T`) — main only did SIGTERM → zombie python.exe
- 4 explicit **@remotion/** deps — phantom transitive on main, `npm ci` could break
- **coverage-floor CI gate** + `check-coverage.mjs` — main only reported, didn't enforce
- **audio-ducking expr fix** — `String.raw` with `\\\\` injected stray backslashes into a
  `volume='...'` filter (commas must stay RAW in ffmpeg *volume* exprs, unlike *drawtext*)

Left OUT: security escape / stderr-surfacing / ESLint fixes (already on main independently);
`visual-fx.ts`/`sfx.ts` older versions (would regress main).

## Step 6 — Worktree audits double as latent-bug discovery
Reading the diverged branch's fixes against main often surfaces bugs STILL LIVE on main
that the branch already fixed but never landed. Treat "why did the old branch change this?"
as a bug-hunt lead. Real finds this session, all confirmed present on main:
- `-ss` **before** `-i` in frame/thumbnail extraction (`gate.ts`, `artifacts.ts`, `export.ts`,
  `render.ts`, `export-fx.ts`) → undecodeable frames on J-cut/itsoffset/shifted streams;
  the vision QA then validates a black frame. Fix: `-ss` AFTER `-i` for single-frame grabs.
- inconsistent default (`candidatesPerAsset` = 4 in some files, 2 in others).

## Standing user rules (do not violate)
- **Commit but do NOT push** without an explicit go.
- **Never delete/modify old code** — cherry-pick ADDS, it doesn't rewrite; prefer standalone + shim.
- Flag any pre-existing uncommitted file as "not mine, left untouched" (e.g. a modified
  PR template) — never sweep it into your commits.
- Max delegation children = 3 (RAM). Waves 3→3→1 for 7 tasks.
