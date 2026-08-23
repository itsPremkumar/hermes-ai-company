# Empirical repo health confirmation (real-execution recipe)

Read-README reviews lie. A GitHub repo "looks healthy" until you prove it typechecks,
tests, and passes CI. This is the gold-standard confirmation run. Every step below was
executed successfully on a 64k-LOC TypeScript repo and is safe to reuse on any cloneable repo.

## 1. Clone (shallow) + structural metrics

```bash
gh repo clone <owner>/<repo> ./repo && cd ./repo
# source files / LOC
find src bin remotion tests -name '*.ts' -o -name '*.js' 2>/dev/null | grep -v node_modules | wc -l
find src bin remotion tests \( -name '*.ts' -o -name '*.js' \) 2>/dev/null | xargs wc -l 2>/dev/null | tail -1
# test files vs non-test source
find src -name '*.test.ts' | wc -l
find src -name '*.ts' ! -name '*.test.ts' | wc -l
# test block count (t.test/it/describe)
find src remotion tests -name '*.test.ts' | xargs grep -hoE "t\.test\(|it\(|describe\(" | wc -l
# commit depth + activity
git rev-list --count HEAD
git log --oneline -15
git branch -a
```

## 2. Verify headline feature claims against actual source (not README prose)

Map every "✨ Key Feature" in the README to a concrete source file. If the file path
claimed by the feature exists, the feature is real; if absent, it's marketing.

```bash
for f in src/mcp-server.ts src/render.ts src/speech/app.py remotion/index.ts \
         input/scripts/input-scripts.json .env.example Dockerfile electron-builder.config.js; do
  [ -e "$f" ] && echo "OK   $f" || echo "MISS $f"
done
# grep for the backend/provider the README names (e.g. edge-tts, kokoro, voicebox)
grep -rilE "edge-tts|kokoro|voicebox" src/ 2>/dev/null | grep -v test | head
```

## 3. Install deps + prove it typechecks (definitive health signal)

```bash
npm ci 2>&1 | tail -15          # background=true on heavy installs (Remotion/Electron/sharp take minutes)
npm run typecheck 2>&1 | tail -40   # tsc --noEmit; exit 0 = clean
```
Heavy installs (Remotion + Electron + sharp) are 5-10 min — run `npm ci` with
`background=true` + `notify_on_complete`, do other review work meanwhile, then `process wait`.

## 4. Prove the test harness actually runs (don't trust the count)

Run 1-2 PURE-LOGIC unit tests (no network, no voice backend, no Chromium) to confirm the
runner is wired, not just that files exist:

```bash
node --import tsx --test "src/lib/errors.test.ts" "src/lib/validation.test.ts" 2>&1 | tail -20
# expect: # pass N  # fail 0
```
Avoid `src/render.e2e.test.ts` / voice integration tests early — they need Chromium /
torch backends that hang or need credentials. The repo itself often skips these in CI
(search the CI workflow for `skip`/`:voice` exclusions).

## 5. CI + public metrics (the badge a reviewer sees)

```bash
gh run list --repo <owner>/<repo> --limit 10          # conclusion per workflow
gh api repos/<owner>/<repo> --jq '{open_issues:.open_issues_count, stars:.stargazers_count, forks:.forks_count}'
gh issue list --repo <owner>/<repo> --state open
gh pr list   --repo <owner>/<repo> --state open
```
Report CI conclusion (success/failure) explicitly — a GREEN local typecheck with a RED
public CI badge is a credibility gap.

## 6. Doc-metric drift check (self-assessment docs lie too)

Repos with historical report files (IMPROVEMENT_ASSESSMENT.md, QA_REPORT.md,
CODE_ORGANIZATION_REPORT.md) frequently hand-type metrics that drift from reality. This
session: README claimed "487+ tests" / "75 test files" but reality was 128 files / 122
blocks. Recompute every count with `find`+`grep` and call out mismatches.

## 7. Code-quality signals worth surfacing

```bash
grep -rniE "TODO|FIXME|HACK|XXX" src/ | grep -v test | wc -l     # unfinished work
grep -rniE "console\.(log|warn|error)" src/ | grep -v test | wc -l  # raw logging
# does the project have a logger abstraction that library code bypasses?
grep -rl "from.*lib/logger" src/ | wc -l
```
High `console.*` counts with few logger imports = library code bypassing the logging
abstraction (CLI stdout is fine; lib/service code going around the logger is a real
inconsistency for MCP/HTTP surfaces).

## When @url: extraction fails on a GitHub repo

Web auto-extraction of `https://github.com/...` sometimes returns "no content
extracted". Do NOT retry the URL — fall straight to the `gh` CLI (`gh repo view`,
`gh repo clone`, `gh run list`, `gh api`). The gh binary is the reliable path for
GitHub repos; reserve broad web tools for non-GitHub sources.
