# Verification recipe (learned on Automated-Video-Generator, 2026-07-17)

## User's standing rule
> "give me the things that are complete free and end to end working only, then
> integrate them in their correct required position."

Meaning: a module is integrated ONLY after it is proven working (real test
runs), is free (no paid keys), and is offline-capable. Don't integrate on faith.

## Exact commands that worked (Windows / MSYS bash, low-RAM box)
```bash
# 1. Does the module even exist? (file count exposes node_modules traps)
find tools/asset-creator -name "*.js" -not -path "*/node_modules/*" | head

# 2. Run the module's own tests, BOUNDED. Offline suites = real proof.
timeout 150 npm test                      # tools/asset-creator -> 14/14
timeout 120 npx tsx --test "tests/*.test.ts"

# 3. Probe a registry/constructor the tests DON'T call (catches load crashes).
#    Write a throwaway .ts in the project root, NOT /tmp (tsx resolves /tmp to
#    a different root and fails). Use async IIFE — top-level await breaks CJS.
npx tsx probe_plugin.ts
rm -f probe_plugin.ts                     # ALWAYS delete the probe after

# 4. Typecheck the WHOLE project after each module wired in.
timeout 220 npx tsc -p tsconfig.json --noEmit | grep -c "error TS"   # want 0

# 5. Run only the suites you own (avoid a sibling's broken shared file).
timeout 150 npx tsx --test \
  src/agentic/archive.test.ts \
  src/agentic/revision.test.ts \
  src/agentic/plugins/plugins.test.ts \
  src/lib/free-image.test.ts \
  src/lib/visual-fetcher.free-image.test.ts \
  src/agentic/acquire.fallback.test.ts
```

## The real case (why verify-first is non-negotiable)
A list claimed 10 "complete but unwired" modules. Verification proved:
- **Plugin system (25 plugins):** claimed complete. Reality: `createPluginRegistry`
  THREW on the stock `agentic-plugins.config.json` because `lut-loader`'s
  `onLoad` did `path.resolve(cfg.lutDir)` with `lutDir` undefined. The crash
  blocked ALL 25 plugins. Fix: `path.resolve(cfg.lutDir ?? DEFAULT_CONFIG.lutDir)`.
  Also the plugin bundle had 21 latent TS type errors (previously un-typechecked
  because nothing imported it). Fixing the import surfaced them all; guard each
  `cfg.x` with `?? default`.
- **free-music-module:** claimed 7 providers. Reality: self-test does live
  `.search()` network calls — NOT verified offline. → skip / gate.
- **free-video-gen-lab:** 16/16 tests pass for the FALLBACK-CORE, but actual
  generation needs GPU/paid keys. → skip the providers, keep core if needed.
- **asset-creator:** 14/14 offline ffmpeg tests. ✅ integrate (offline fallback).
- **free-image:** 11/11 offline adapter tests. ✅ integrate as image ladder.
- **youtube-upload:** user said DON'T integrate. (6/6 tests pass — but excluded.)

## Sibling-agent collision pattern (CRITICAL on live multi-agent repos)
- Tool warnings like "modified by sibling subagent '...' at HH:MM:SS — after this
  agent's last read" mean another agent is LIVE on the same file.
- Symptom: `tsx` (esbuild) reports `Expected ";" but found ")"` in a file you
  didn't touch (e.g. `brain.ts`). The sibling left broken syntax; the WHOLE
  import graph cascade-fails to load (10 suites red) even though your modules
  are fine.
- Rule: **do NOT repair the other agent's live file.** Verify YOUR work via the
  suites that don't import it. A type-only `import('./brain.js').AgentBrain` and
  an optional injected `deps.brain` do NOT pull the broken module into the graph,
  so those tests still pass.
- `tsc --noEmit` passed (0) but `tsx` failed → re-run both fresh; the typechecker
  may exclude the broken file via `tsconfig.include`, but esbuild parses it.

## Gotchas
- `tsx` probe in `/tmp` → `ERR_MODULE_NOT_FOUND` (wrong root). Put probes in cwd.
- Top-level `await` in a `.ts` run via tsx/CJS → "Top-level await not supported".
  Wrap in `(async () => { ... })()`.
- Re-export a singleton you need to stub in tests:
  `export { freeImageAdapter } from './free-image/index';` so the test can
  monkeypatch `adapter.searchAll`.
- Stub the METHOD on the real instance, not the namespace binding:
  `const a = mod.freeImageAdapter; const o = a.searchAll.bind(a); a.searchAll = ...`
