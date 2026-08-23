---
name: safe-repo-improvement
description: >-
  Improve or "audit" an existing codebase WITHOUT trusting surface claims and WITHOUT
  destructive mistakes. Use when the user asks "does this project need improvement / fixing?",
  when you suspect repo-hygiene problems (large file in history, bloat, missing tests,
  silent no-op setup scripts), or when you're about to run a destructive git op
  (force-push, filter-repo/BFG history rewrite, mass delete) to "fix" a hygiene issue.
  Covers: verify repo-state claims with git tooling BEFORE acting, the decision rule for
  whether a history rewrite is worth it, and closing real gaps by adding tests to untested
  modules (which surfaces latent bugs). Distinct from verify-codebase (trust/correctness of
  unfamiliar code) and repo-hardening (dependency vulns) — this is the *measurement
  discipline + test-driven gap closure* angle.
---

# safe-repo-improvement

Verify repo-state claims with git tooling BEFORE acting — especially before destructive git
operations. Then close the REAL gaps with tests (tests on untested modules surface bugs).

## When to use
- User asks "does this project need improvement / fixing?" (often with only a screenshot).
- You suspect repo-hygiene problems: large file in history, bloat, missing tests, a
  `prepare` script that is a silent `node -e "process.exit(0)"` no-op masking setup.
- You're about to run a destructive git op (force-push, filter-repo/BFG, mass delete) to
  "fix" a hygiene issue.

## Core principle
Inspect reality; don't trust claims — not the user's screenshot, not your own earlier guess.
A hypothesis about a defect is NOT evidence. Measure first, then decide.

## Workflow
1. **Triage the actual project** (not the screenshot):
   - `git status`, `git log --oneline -10`, `du -sh .`
   - `npm run typecheck`, `npm audit --omit=dev`, test inventory
     (`find src -name '*.test.ts' | wc -l`) vs source modules (`find src -name '*.ts' -not -name '*.test.ts' | wc -l`).
   - Read the real source of the modules in question — assess architecture, DI, error handling.
2. **For every "fix this" hypothesis, MEASURE before acting.**
   Example: claimed "14 MB `.mcp-jobs.json` bloating every clone."
   - Tracked now? `git ls-files | grep` + `git ls-tree -r --name-only origin/main | grep`.
   - Live size? `du -h .mcp-jobs.json`.
   - Historical blob sizes? See `references/git-blob-size-recipe.md`.
   - **Decision rule:** a force-push history rewrite only pays off when the blobs are LARGE
     (megabytes). A 15 KB ignored file already gitignored is NOT worth a destructive
     rewrite — skip it and say why. (Real case: a "14 MB" guess was 16 KB live + ~15 KB
     history → rewrote nothing, avoided a needless force-push.)
3. **Close the REAL gaps with tests.** In a mature project the genuine, verifiable gap is
   usually *untested paths* — network/media-fetch integrations break in prod while unit
   tests mock everything else. Add tests:
   - For network code, stub the HTTP client at a test seam (override `axios.get`) — no real
     network, deterministic, CI-safe. See `references/axios-mock-test-pattern.md`.
   - Export previously-private pure helpers just enough to test them (non-breaking `export`
     additions). Then write tests for parsers/selectors/math.
   - Tests on untested modules frequently surface latent bugs — FIX the bug and KEEP the
     test. (Real case: a keyword-normalizer deduped case-sensitively, so `"Sunset"` and
     `"sunset"` became two distinct stock-search queries — caught and fixed via test.)
4. **Always re-run the project's actual gate** after edits: `npm test` (typecheck + unit),
   `prettier --check`. Report real pass/fail counts.

## Pitfalls
- Assuming file size from a `git status`/listing. A "14 MB" guess was 16 KB live. Verify
  with `du` and `git cat-file -s`.
- Force-pushing to remove a tiny ignored file — pure downside, zero upside.
- Treating a `prepare`/`postinstall` silent no-op as "setup ran." Note it, don't trust it.
- Claiming work is done without fresh verification evidence. Run the gate; show the counts.

## Verification evidence to report
- `npm run typecheck` exit code (0 = clean)
- `# tests / # pass / # fail` from the real runner
- `prettier --check` result (CI `format:check` must pass)

## References
- `references/git-blob-size-recipe.md` — exact commands to decide if a history rewrite is worth it.
- `references/axios-mock-test-pattern.md` — deterministic network mocking in `node:test`.
