---
name: repo-analysis
description: "Deep end-to-end analysis of any GitHub repository: API metadata, file structure, tech stack, architecture, dependency security audit, mock-vs-real feature detection, and repo-health signals. Use for 'analyze / review / audit this repo' requests."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, code-analysis, security-audit, repo-review, architecture, dependency-audit]
    related_skills: [codebase-inspection, github-code-review]
---

# GitHub Repository Analysis

Turn a "analyze this repo" / "review this project" request into a structured, evidence-backed report. This goes far beyond LOC counts: it combines **GitHub API metadata** (no clone needed) with a **local clone for deep code review** (security audit, architecture, feature reality-check).

## When to Use

- User pastes a GitHub repo URL and asks to "analyze", "review", "audit", or "what is this project"
- Due diligence before forking / contributing / reusing a repo
- Checking whether a project's marketing claims match its code (mock vs real features)
- Repo health / bus-factor / security posture assessment
- **Web/research gathering during the audit** (reading the repo's web context,
  GitHub, social discussion): prefer the **web-research** skill (Agent Reach
  capability layer). It self-heals platform routing and covers social/Chinese
  platforms (Twitter, Reddit, 小红书, Bilibili) that Hermes reaches poorly alone.

## Two-phase approach

### Phase 1 — API metadata (fast, no clone)

Fetch repo overview + full file tree + language breakdown + commit history via the GitHub REST API. See `references/github-api-recipe.md` for the exact `curl` + `python` parsing commands.

Extract: name, description, primary language, stars/forks, created/updated, license, topics, open issues, default branch, archived flag, homepage.

Then read the **key human-readable files** by raw URL (README.md, package.json / pyproject.toml, AGENTS.md, CHANGELOG.md) — these reveal intent, stack, and architecture claims.

### Phase 2 — Deep review (clone required)

`git clone --depth 1 <url>` then inspect the actual code:

1. **Security audit** — `npm audit --omit=dev --json` (Node) / `pip-audit` (Python). Parse the JSON to a severity table. See `references/security-audit-recipe.md`.
2. **Architecture** — identify layering pattern (hexagonal/clean/MVC), entry points, core business logic dirs.
3. **Feature reality-check** — grep for `mock.ts`, `MockProvider`, `placeholder`, `TODO`, `stub`. Confirm whether advertised features (AI video gen, lipsync, etc.) are real or stubbed. **Critical check:** does the *main* app import the mocked modules, or are they standalone experiments? If the main pipeline never imports them, the mocks don't poison the primary path.
4. **Repo health** — bus factor (commit author counts), test count (`find -name '*.test.*'`), CI workflows present, placeholder assets / missing referenced assets (e.g. `default.mp4` referenced but absent).
5. **Bloat / hygiene** — duplicate large binaries (identical byte sizes committed multiple times), committed secrets (`.env`), git-lfs candidates.

### Phase 3 — Empirical health confirmation (proven real)

README/structure reviews are an *opinion* until you prove the repo builds, tests, and
passes CI. This is the gold-standard run — every step is a real-execution check, not a read.
Full copy-paste recipe in `references/empirical-health-recipe.md`. Sequence:

1. **Clone + structural metrics** — `find` for source/test file counts + LOC, `git rev-list --count HEAD`, `git log`/branch depth.
2. **Feature reality-check** — assert each README "✨ Key Feature" maps to an existing source file (`[ -e "$f" ]`); grep the README-named backend/provider (e.g. `edge-tts|kokoro|voicebox`) in non-test source. Missing file = marketing, not feature.
3. **Install + typecheck** — `npm ci` (background=true for heavy installs: Remotion/Electron/sharp are 5-10 min), then `npm run typecheck` → exit 0 = clean. **Typecheck passing is the single strongest health signal.**
4. **Run real unit tests** — `node --import tsx --test "src/lib/errors.test.ts" "src/lib/validation.test.ts"` (pick PURE-LOGIC tests; avoid e2e/voice/Chromium tests that hang). Proof the runner is wired, not just that files exist.
5. **CI + public metrics** — `gh run list` (conclusion per workflow), `gh api repos/.../...` for stars/forks/open_issues, `gh issue list`/`gh pr list`. Report CI conclusion explicitly — a green local typecheck with a RED public badge is a credibility gap.
6. **Doc-metric drift** — recompute every count the README/self-assessment hand-types; call out mismatches (see Pitfalls).
7. **Code-quality signals** — `TODO/FIXME/HACK` counts, raw `console.*` vs logger-import counts (high console with few logger imports = library code bypassing the logging abstraction).

**GitHub @url extraction fails?** Don't retry the URL — `gh repo view` / `gh repo clone` / `gh run list` / `gh api` are the reliable path for GitHub repos.

## Key checks for web/API projects (security posture)

- **Bind address**: does the server bind `127.0.0.1` (safe) or `0.0.0.0` (exposed)?
- **Endpoint gating**: are sensitive routes behind a local-only / auth middleware (e.g. `requireLocalAccess`, loopback check)? Is there an explicit opt-in override flag?
- **Command execution**: if the app shells out (`exec`/`spawn`), is input **allowlisted** before use? (A whitelist of commands = safe; raw string interpolation = injection risk.)
- **Secrets**: no `.env` committed; `.env.example` only.

## Portfolio / Proof-of-Work Review (job & volunteer applications)

When the user asks "is my repo enough for X application" or wants proof-of-work evidence,
run a portfolio-grade verification on top of the technical audit. Recruiters/mentors shortlist
on *signal*, not just code:

1. **CI health** — a RED CI in a portfolio repo looks careless. Check
   `GET /repos/{owner}/{repo}/actions/runs?per_page=5` and report the latest `conclusion`
   per workflow. If red (e.g. a failed `Typecheck` step), flag it as a fixable blocker.
2. **Real output, not mock** — for media/content generators, verify the *artifact* is real:
   probe generated files with magic bytes (`head -c 12 file.mp4` → `ftypisom` for MP4),
   confirm sample outputs have non-trivial size (1 MB+), and confirm the main pipeline imports
   real engines (ffmpeg/Remotion), not `MockProvider`/`stub`.
3. **Marketing vs data** — grep data/config files for `DUMMY`, `EXAMPLE`, `sample`,
   `placeholder`. A repo claiming "real user interviews" may ship only `DUMMY EXAMPLE DATA` —
   don't let the user over-claim it. State what's backed vs what's aspirational.
4. **Traction & recency** — stars/forks, last push date (active today > stale), contributor
   count (solo = flag collaboration via OSS-mentor/organization credentials).
5. **Curate, don't dump** — 100 repos with 90 at 0★ signals scatter. Surface 2–4 flagships +
   the OSS-mentor/organization credential instead of listing everything.
6. **Live-site proof** — for web apps, `curl -sL` the deployed URL (HTTP 200 + real rendered
   text) beats a screenshot. Cannot confirm traffic/analytics numbers from outside — phrase as
   "live production app I operate", never invent user counts.

See `references/portfolio-proof-verification.md` for the exact curl/python one-liners used in
a real session (GitHub metadata, languages, contributors, CI runs, magic-byte media check,
dummy-data grep, live-site fetch).

## Output format

Lead with a snapshot table (language, license, stars, contributors, size, issues), then structured sections: What it is → Tech stack → Architecture → Strengths → Weaknesses/Risks → Recommended next steps. Use tables and concrete file paths as evidence. Separate **verified-in-code** facts from **marketing claims** explicitly.

## Pitfalls (portfolio review)

- **Red CI is a credibility red-flag** in a portfolio context even if local typecheck passes —
  the public badge is what reviewers see. Fix or note it.
- **"Real users" / "X daily users" claims are unverifiable from outside** — only state what you
  can prove (live HTTP 200 + rendered content). Never fabricate analytics numbers.
- **Dummy data files** often sit next to real code; a `DUMMY EXAMPLE DATA` header in a data file
  means the "real content" marketing line is unbacked — keep the user honest about it.
- **Repo dumps hurt**: listing 100 repos (most 0★) reads as scattered. Curate to flagships.

## Pitfalls

- **`python3` may be missing** on some hosts (Windows/git-bash) — use `python`. Already captured in memory; don't hard-fail on `python3`.
- **Don't over-rely on README claims** — the README is marketing. Cross-check every "✨ feature" against actual code before reporting it as real.
- **Mock providers are often lab experiments** — a repo full of `mock.ts` files is not necessarily broken; check import graph from the main entry point.
- **Large repos**: use `git clone --depth 1` to avoid pulling full history.
- **npm audit fixes can break builds** — after `npm audit fix`, re-run typecheck/build before declaring success.
- **Doc-metric drift is common** — repos with historical report files (`IMPROVEMENT_ASSESSMENT.md`, `QA_REPORT.md`, `CODE_ORGANIZATION_REPORT.md`) often hand-type metric counts that drift from reality (e.g. README claimed "487+ tests / 75 test files" but reality was 128 files / 122 blocks). Recompute every count with `find`+`grep` and call out mismatches rather than repeating the doc's number.
- **Prove, don't assert** — a review that only reads the README/structure is an opinion. Always run the Phase 3 empirical confirmation (`npm ci` → typecheck → real unit test → `gh run list`) so every verdict is backed by execution output. See `references/empirical-health-recipe.md`.

See `references/review-checklist.md` for the full inspection checklist and `references/github-api-recipe.md` / `references/security-audit-recipe.md` for copy-paste commands. For the real-execution health-confirmation sequence (clone → typecheck → real unit tests → CI/metrics → doc-drift), see `references/empirical-health-recipe.md`.
