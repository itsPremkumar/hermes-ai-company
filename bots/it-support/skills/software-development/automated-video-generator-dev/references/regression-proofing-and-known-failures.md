# AVS — Regression-proofing & known pre-existing test failures

## Why this file exists
AVS ships a huge `node --test` suite (700+ tests). A non-trivial fraction of
failures are **pre-existing and environment-specific** — NOT regressions from your
edit. Conflating them wastes cycles. Use the `git stash` proof below to tell them
apart before claiming "my change broke X".

## Known pre-existing failures (verified 2026-08-11, main @ 4118b5c)
These fail identically on the **unmodified** original code. Do NOT treat them as
regressions:

- **`src/agentic/operations/brand-audioless.test.ts` (tests B1–B3, ~145–148)** —
  fail because the local bundled `ffmpeg.exe` on this box does NOT support
  `-c:a aac`. `Command failed: ... -c:v copy -c:a aac ...`. Pure env limitation.
- **`tests/agentic/operations/new-features.test.ts` (#117)** — a 240s real-ffmpeg
  timeout test. Slow/flaky on a RAM-constrained box, not a logic bug.
- **`tests/agentic/operations/revise-restitch-prod.test.ts` (#121)** and
  **M5 (#245)** — real-ffmpeg re-stitch tests; same env root cause.
- Network-dependent tests (`WikimediaImageProvider`, `ArchiveOrgImageProvider`,
  `NasaImageProvider`, `MetMuseumImageProvider`, `FreeImageAdapter.searchAll`)
  are **SKIPPED** when hosts are unreachable (`# SKIP host unreachable`), not failed.

If these are the ONLY failures after your change → your change is clean.

## The `git stash` regression proof (REUSE THIS)
When a test fails and you suspect your edit, prove it is pre-existing BEFORE
debugging:

```bash
# 1. Stash ONLY tracked modified files (untracked new files don't affect the test)
git stash push -- src/.../fileA.ts src/.../fileB.ts
# 2. Run just the failing test against ORIGINAL code
node --import tsx --test --test-timeout=60000 "path/to/failing.test.ts" 2>&1 | grep -E "^# (tests|pass|fail)"
# 3. Restore
git stash pop
```
If it fails identically on the original → pre-existing. If it passes on original
but fails with your change → you introduced it. This single technique closed a
false-debug loop in the 2026-08-11 session (Pinterest/gen-image/batch features).

## Verifying a feature addition WITHOUT the full 6-minute suite
The full `npm run test:unit` takes ~6 min and drowns signal in env noise. For a
focused feature change, run only your own test files:
```bash
node --import tsx --test --test-timeout=120000 "src/agentic/features.test.ts" "src/agentic/features.integration.test.ts"
```
Then run the full suite once in the background (`terminal(background=true,
notify_on_complete=true)`) and grep the log for `^# (tests|pass|fail)` + `not ok`.
Compare pass/fail counts to the baseline above (752/6/2 before; +N for your new
tests). A CHANGED failure set = investigate; an unchanged one = clean.

## Golden rule
`npm run typecheck` must be GREEN after every edit (use the real command, not the
false-positive TS6053 from write_file/patch). The full suite's 6 pre-existing
failures are allowed to remain.
