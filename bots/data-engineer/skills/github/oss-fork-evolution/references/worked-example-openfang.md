# Worked example — OpenFang (rightnow-ai/openfang) stale-fork evolution

Verified facts pulled live (GitHub API) on 2026-07-19. Use as the template for any
"fork + evolve a stale OSS repo" task.

## Maintenance-health check (Step 0 results)
- Stars: 18,032 | Forks: 2,278 | License: Apache-2.0 + MIT (dual; README says "MIT only" — WRONG)
- Default branch: `main`. Last commit on `main`: `acf2587` "bump v0.6.9" **2026-05-12**.
- Open PRs: **39**. Several updated into July: #1269 (2026-07-15), #1267 (2026-07-13).
- Those July PRs: `merged_at == null`, `state == "open"` → **unmerged backlog**, NOT abandoned.
- Conclusion for user: "main frozen, but project is alive; 39 PRs piled up unmerged."

## Agentic-OS landscape (live star counts, the user asked "is it the major hub?")
- OpenClaw 383k (TS, active) — THE major hub in this niche
- AutoGPT 185k, Dify 149k, OpenHands 81k, Goose 51k (Rust), CrewAI 55k, AutoGen 59k,
  LlamaIndex 50k, LangGraph 37k, smolagents 28k, Agent Zero 18k, ElizaOS 18k
- **OpenFang 18k** → ~21x smaller than OpenClaw. Not the major hub.

## Stale-fork rescue (the user's fork had diverged)
Fork `itsPremkumar/openfang` `main` was at `c3dcf02 "bugfix batch"` (pre-v0.2.5 era),
while upstream `main` was `acf2587` (v0.6.9). Recipe used:
```bash
git clone --depth 1 https://github.com/itsPremkumar/openfang.git
cd openfang
git remote add upstream https://github.com/rightnow-ai/openfang.git
git fetch upstream
git branch legacy-fork-main main        # preserve old fork work
git reset --hard upstream/main          # align to v0.6.9
git push origin legacy-fork-main
git push --force origin main
```

## CI-as-build-gate (this box: no Rust, 6GB RAM, 31GB free — can't build 137K-LOC Rust)
1. CI present: `.github/workflows/ci.yml` (check on ubuntu/macos/windows + test);
   `actions/permissions` = `enabled:true`.
2. Branch + merge a safe, isolated upstream PR:
```bash
git checkout -b evolve
git fetch upstream pull/1267/head:pr1267
git diff main pr1267            # 7 files: MiniMax M3 catalog + Anthropic driver, all self-contained
git merge --no-edit pr1267      # clean → commit 14c711f
git push origin evolve
gh pr create --repo itsPremkumar/openfang --base main --head evolve \
  --title "evolve: integrate #1267 MiniMax M3 + Anthropic driver (CI proof)"
```
3. That PR triggers the 3-OS Actions CI → real compile/test verification on GitHub runners.

## Pitfalls confirmed this session
- OpenClaw README fetched via `curl .../README.md` returned EMPTY (redirect/encoding
  quirk). Fix: `curl -sL --compressed .../README.md -o f.md` (the `--compressed` flag).
- google.com/search was bot-blocked (sorry/index page). Use DuckDuckGo HTML or Wikipedia
  for definitions instead.
- `python3` is MISSING on this Windows host; use `python` (Hermes venv, 3.11.15).
- `search_files` tool fails on paths with a space (`C:\Users\PREM KUMAR\...`) — use
  `grep -n -i` via the `terminal` tool for those paths.
- OpenClaw project facts: TS monorepo (pnpm), `packages/*` (23) + `apps/*`, MIT,
  Node 24.15+, Gateway daemon on WS `127.0.0.1:18789`, skills on ClawHub.
