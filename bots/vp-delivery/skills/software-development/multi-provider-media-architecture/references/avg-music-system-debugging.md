# AVG Music System — Debugging Real Logic Bugs

Reusable root-cause patterns from fixing failing unit tests in the Automated-Video-Generator
(AVG) music system (`src/music-system/`, `src/lib/free-music.ts`). All were genuine
`AssertionError`s — NOT network errors — so the fix is always in the source, never in the test.

## How to triage (workflow that worked)

1. Run the failing suite first to get exact assertions + line numbers:
   `node --import tsx --test src/music-system/music-system.test.ts`
   `node --import tsx --test src/lib/free-music.test.ts`
2. Read the test file FULLY — capture every assertion shape (esp. subtests).
3. `grep -rln "symbolUnderTest" src/` to find the source when the test file imports from a
   different module than you expect (e.g. `listFreeMusicProviders` lives in `src/lib/free-music.ts`,
   NOT under `src/music-system/`).
4. Read the source. Root-cause each failure at `file:line`. Common AVG causes:
   - metadata fixture shape mismatch
   - filter/branching that passes through items that should be excluded
   - async handling / wrong return shape
   - legacy shim list drift vs the new registry
5. Fix at cause. Do NOT delete/modify unrelated working code.
6. Re-run both suites. Then `npm run typecheck`.

## Bug 1 — `BundledProvider` returns empty metadata

- **Symptom:** subtests "reads bundled tracks" (`t.durationSec > 0`) and "filters by mood"
  (`t.mood.includes('dramatic')`) fail; tracks get `durationSec: 0`, `mood: undefined`.
- **Root cause:** `loadMetadata()` (in `src/music-system/providers/bundled.ts`) only parsed
  per-track `<base>.json` sidecar files. The repo actually ships a single aggregated
  `metadata.json` as an **array** keyed by `filename`. So no metadata loaded.
- **Fix:** read `metadata.json` as an array of `{ filename, ... }`; key the map by
  `filename.replace(/\.[^.]+$/, '')`; skip `metadata.json` when scanning for sidecars; let
  per-track sidecars (if any) take precedence.

## Bug 2 — unknown mood returns all tracks (should be 0)

- **Symptom:** "returns empty for unknown mood" (`mood: 'metal'`) returns 5, expects 0.
- **Root cause:** mood filter only *excluded* a track when `query.mood !== 'any' AND
  meta.mood exists AND no match`. Tracks with no mood metadata fell through and were included.
- **Fix:** when `query.mood !== 'any'`, require `meta?.mood?.length` and a case-insensitive
  match. No mood metadata => excluded. Unknown mood => 0 results.

## Bug 3 — `listFreeMusicProviders` missing a source

- **Symptom:** test asserts names include `ccmixter`, `internet-archive`, `local`.
- **Root cause:** `defaultProviders()` in `src/lib/free-music.ts` returned
  `['local','open-lofi','internet-archive','fallback-ambient']` — `open-lofi` (upstream audio
  deleted) instead of `ccmixter`, which the new registry (`providers/index.ts`
  `registerDefaultProviders()`) actually registers.
- **Fix:** add a legacy `CcMixterFreeProvider` wrapper delegating to the new `CcMixterProvider`
  (same `search()` + `mapToLegacy` pattern as the other `XxxFreeProvider` classes); swap
  `OpenLofiProvider` -> `CcMixterFreeProvider` in `defaultProviders()`. The new registry is the
  source of truth for which providers exist.

## Verification gate

- `node --import tsx --test src/music-system/music-system.test.ts` -> 19/19
- `node --import tsx --test src/lib/free-music.test.ts` -> 4/4
- `npm run typecheck` -> should be `exit 0`. NOTE: a pre-existing error in an UNRELATED file
  (`src/agentic/pipeline/acquire.ts` — `import.meta` in CommonJS, edited by a sibling subagent)
  may make typecheck exit non-zero. Confirm the ONLY errors are outside the music module before
  concluding your edits are clean; leave unrelated concurrent work to its owner.
- Commit locally, do NOT push:
  `git add src/music-system/providers/bundled.ts src/lib/free-music.ts`
  `git commit -m 'fix(music-system): correct BundledProvider + listFreeMusicProviders'`
