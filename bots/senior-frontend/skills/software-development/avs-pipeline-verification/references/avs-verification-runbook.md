# AVS Verification Runbook (reference)

## Exact commands (from repo root `C:/one/Automated-Video-Generator`)

### 1. Unit tests (split runners — CRITICAL)
```bash
# node:test files (style-engine, script-parser, agentic-cli, pipeline/*): use tsx --test
npx tsx --test src/agentic/ai/style-engine.test.ts src/lib/script-parser.test.ts \
  src/adapters/cli/agentic-cli.test.ts src/agentic/pipeline/*.test.ts
# → expect: # tests 36 / # pass 36 / # fail 0

# vitest will report "No test suite found" for those files — do NOT use it for them.
# typecheck:
npx tsc -p tsconfig.json --noEmit   # exit 0
```

### 2. Combinatorial matrix (the "test all varieties" loop)
```bash
npx tsx scripts/gen-matrix.ts        # writes input/scripts/agentic-scripts.json (backs up prior)
# launch in background (long: ~30-60s/job × ~40 jobs):
npx tsx src/adapters/cli/agentic-cli.ts > workspace/tmp/combo_matrix.log 2>&1
# poll:
npx tsx scripts/monitor.ts          # outputs / fails / unhandledErrors
npx tsx scripts/validate-outputs.ts # ffprobe every mp4 → VALID/TINY/CORRUPT
```
Restore original script after: `git checkout -- input/scripts/agentic-scripts.json`
(re-generate matrix overwrites the `.bak`, so restore from git, not the `.bak`).

## Expected log lines (KNOWN-GOOD, do NOT "fix" these)
- `[SPEECH-BACKEND] backend process exited early (code 1); falling back to Edge-TTS`
  → voice backend (torch/kokoro) unavailable; falls back to Edge-TTS → Windows offline speech.
  Voice gen completes ~10s. EXPECTED.
- `ℹ music duck expression unsupported on this ffmpeg build; using flat volume`
  → `volume=eval=frame`+`between()` ENOMEM on gyan.dev Win ffmpeg over real audio; pass2
  falls back to flat `volume=${full}`. Render still completes. EXPECTED.

## Real failures to catch (these ARE bugs)
- `❌ Job failed with error` in the summary / `Job failed` count > 0.
- `TypeError|ReferenceError|Cannot read|ENOENT` (excluding `ModuleNotFoundError: No module named 'fastapi'`).
- Any `.mp4` that is < 1 KB (TINY) or fails ffprobe (CORRUPT).

## Verified result from this session (commit 20af094 baseline)
40 jobs / 40 completed / 0 failed → 156 valid mp4s, 0 corrupt.
Coverage: orientation×captions×music (18) + 8 voices/languages + grade/transition/style enums +
all-19-tags job + control-surface dryRun (all top-level config fields).

## Two pitfalls already fixed (do not re-fix unless platform changes)
1. `speech-backend.ts` `ensureBackend` now detects `backendProc` exit → fail-fast (was 120s hang).
2. `render.ts` `buildDuckExpression` guards non-finite; pass2 try/catch → flat-volume fallback
   (ffmpeg ENOMEM on eval=frame duck expression over real audio).

## Notes
- Local assets used: `input/visuals/github-profile.png`, `logo-automation.png`.
- Bundled music: `input/bgm/__bundled__/*.mp3` (lofi_chill, cinematic_drone, upbeat_electronic,
  ambient_piano, ambient_nature).
- dryRun jobs return `gate.pass=false` by design; CLI counts them completed (not "Gate FAIL").
- All artifacts stay under `output/` + `workspace/` (AVS containment/RAM rules).
