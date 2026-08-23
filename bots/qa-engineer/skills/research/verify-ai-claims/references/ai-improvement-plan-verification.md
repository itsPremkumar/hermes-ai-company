# Pasted "improvement plan" verification — evidence bank

Reusable recipe + real example from session 2026-07-18 (Automated-Video-Generator
AVG agentic pipeline). Another AI pasted a prioritized "agentic-system improvement
plan" for this repo. Verified it against the live codebase before acting.

## The four-category probe (run, then judge)
```bash
# A) "Feature X not wired into render" -> grep the consumption site
grep -rn "resolveCaptionTheme\|captionTheme" src/agentic/orchestrate.ts
# B) "File F.ts (untested, N lines)" -> does it exist, at what path/size?
for f in genre-style platform-export dispatch registry beat-sync speed-ramp glitch film-grain; do
  found=$(find src -name "$f.ts" 2>/dev/null | head -1); echo "$f -> ${found:-NOT FOUND ANYWHERE}"; done
# C) "Module M has no dedicated test" -> standalone + indirect coverage
ls src/agentic/gate.test.ts src/agentic/orchestrate*.test.ts 2>/dev/null
grep -rln "runFinalGate\|chunkCues" src/agentic/*.test.ts
# D) "Bug B in file" -> read the actual lines
grep -nE "readFileSync\(.*\)\.toString\('base64'\)" src/agentic/brain.ts
grep -nE "Promise.all\(sceneFetches\)" src/agentic/acquire.ts
```

## Real Claim | Verdict | Evidence table (this session)
| Claim from pasted plan | Verdict | Evidence |
|---|---|---|
| #7 caption-theme preset "not wired into render" | FALSE / stale | orchestrate.ts:1276-1277 calls resolveCaptionTheme() + captionThemeToDrawtext(), applied to drawtext. Done last session. |
| types.ts is 324 lines | FALSE | wc -l src/agentic/types.ts = 106. |
| orchestrate.ts has NO dedicated test | TRUE | only indirectly via render/integration/agentic tests. |
| gate.ts untested as standalone | TRUE | no gate.test.ts; only indirect via agentic.test.ts. |
| #8 brain.ts reads image to base64 with no size cap | TRUE | brain.ts:359 readFileSync(filePath).toString('base64'), no statSync guard. |
| #9 acquire.ts "shared mutable pool race" | FALSE | code uses local candidates.push() then await Promise.all (safe fan-out-then-collect), not read-then-populate. Specific bug not present (throttle #16 was real, different). |
| #16 acquireAssets fans out via Promise.all, no throttle | TRUE | acquire.ts:167 Promise.all(sceneFetches). |
| ~21 "effect modules" at flat src/agentic/ | FALSE / padded | only 2 exist there; rest under plugins/{audio,motion,transitions,color,...}/ + operations/. |
| genre-style/platform-export/dispatch "untested, large" | MISLEADING | files exist but under plugins/ + operations/; none imported by core render path (registry init only). Dormant scaffolding, not reachable -> testing = busywork. |

## Decision rule applied
- Implemented the genuinely-true items: gate.test.ts (9 tests),
  orchestrate.pure.test.ts (10 tests for exported pure helpers
  sourceFromUrl/buildDuckExpression/chunkCues), brain.ts size cap (8MB,
  returns null -> signal-gate fallback), acquire.ts bounded concurrency
  (mapWithConcurrencyLimit, max 6, zero-dep).
- Skipped the false/stale: caption-theme wiring (done), 21-module tests
  (dormant), the fake race condition.
- Result: +24 tests, typecheck 0, lint 0, prettier clean, CI green (8 jobs).

## Gotcha baked in: prettier is a SEPARATE CI gate from lint
npm run lint passing locally does NOT mean CI green — CI also runs
npm run format:check (prettier). This session's first push failed Lint & Format
because 3 files had style drift (cosmetic). Always run npm run format +
format:check before pushing a TS repo with a prettier gate.
