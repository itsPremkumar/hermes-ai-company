# Codebase Onboarding — Command Recipes

Copy-paste recipes for the cheap-first workflow (shaped for MSYS/git-bash on Windows, but POSIX-portable).

## 1. Ground truth (no blind re-clone)
```bash
cd /c/one/<repo>
git remote -v
git branch -a
git status
git fetch --all --prune
# Find newest branch by committer date:
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | sed 's#origin/##'); do
  echo "$(git log -1 --format='%ci' origin/$b)  $b"
done | sort -r | head
git pull --ff-only origin main   # only if behind
```

## 2. Cheap structure map
```bash
less package.json        # scripts + bin + deps => entry points + toolchain
find src -type f | sort  # tree
# Curated orientation (read BEFORE source):
#   llms.txt, README.md, AGENTS.md, SKILL.md, .cursor/rules/*.mdc
```

## 3. Golden path (pick ONE feature)
- Entry point → orchestrator/controller → `types.ts` / `models.py` → config (`config.ts`) → renderer/composer.
- Multi-pipeline repo: list each pipeline's entry; note which core `lib/` they share.

## 4. Empirical verify (proves current + compiles)
```bash
npm run typecheck            # Node/TS  (background if slow)
pytest -q                    # Python
go build ./...               # Go
cargo build                  # Rust
```
A clean result is the evidence the remembered map is real, not stale.

## 5. Persist compact map
- One memory entry, <~700 chars: module responsibilities, dual/multi-pipeline layout,
  key file pointers, and the verify command. Memory total cap ~2200 chars.
- If near cap, `replace` to consolidate an existing entry rather than `add` (overflow is rejected).
