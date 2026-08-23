# CodeQL `js/unused-local-variable` ≠ ESLint `no-unused-vars` (AVS)

CodeQL's `js/unused-local-variable` query is NOISIER than ESLint's
`no-unused-vars` and produces false positives. In the 2026-08-03 session,
ESLint reported 0 unused-var ERRORS across `src/`, but CodeQL still listed 17
`js/unused-local-variable` alerts — many on symbols that ARE used.

## Don't blindly delete
Before removing a symbol CodeQL flags:
1. `grep -c "SymbolName" <file>` — if count > 1 (import + >=1 use), it is
   used. If exactly 1 (the declaration line), it is genuinely unused.
2. `npm run typecheck` (`tsc --noEmit`) — confirm no broken references after
   deletion.
3. `npx eslint src/ remotion/ --quiet` — must stay at 0 errors (CI gate).

## Confirmed genuinely-unused (safe to delete) in that session
- `music-verifier.ts`: `import * as path` (no `path.` usage)
- `style-engine.ts`: `const GRADES = [...]` (declaration only)
- `agentic-preview.ts`: `execSync` in the `child_process` import
- `tts.ts`: `const os = require('os')`
- `remotion-codegen.ts`: `const dotPos = (t) => {...}` (never called)
- `render.ts`: `logWarn`, `logError` imports (only `logInfo` used)
- `AuroraShader.tsx` / `PrismDispersion.tsx`: unused `interpolateColors`
  import, unused `waveY` / `beamLen` locals
- test files: unused `ws`, `const r =`, `addMusic` import

## Confirmed FALSE POSITIVES (do NOT delete — would break build)
- `render.ts` captions import (`chunkCues`/`mergeWordsToLines`/`fmtSrt`) — all used
- `search.ts`: `isSafeUrl`, `recordProviderFailure/Success` — used 5x
- `PrismDispersion.tsx`: `spread` — used in beam style

## Heuristic
If ESLint (`--quiet`) is clean on the symbol but CodeQL flags it, treat as a
false positive unless grep proves otherwise. Deleting a used symbol fails
`tsc --noEmit` and is worse than leaving a CodeQL noise alert.
