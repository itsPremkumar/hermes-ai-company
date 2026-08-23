# AVS Known Test Failures & Fixes (environmental vs real)

If you see failures in `src/**/*.test.ts`, triage: some are ENVIRONMENTAL
(pre-existing, ignorable), some were real bugs since FIXED in this project.
Verify by running the same tests on a baseline worktree of the base commit.

## 1. `mock.module is not a function` (ESM mock API gap)
Files STILL affected: `adapters/http/server-bootstrap.test.ts`,
`adapters/http/videos-controller.test.ts`, `adapters/mcp/*`.
Cause: Node 22.x test runner lacks `mock.module`. **Still present** — these
files genuinely need the API; don't chase.
**FIXED (2026-07-24): `lib/media-verifier.test.ts`** — its top-level
`mock.module('./ollama-client.js', …)` crashed the WHOLE file (exitCode 1,
cascaded to make sibling runs look broken). Guard it:
`if (typeof mock.module === 'function') { mock.module(...) }`. The mock isn't
exercised by the test bodies (they pass explicit result objects), so skipping
on unsupported builds is harmless. Now runs 6/6. **Reusable pattern**: when an
experimental `node:test` API call at top level crashes a test FILE, guard it so
the real contract tests still execute — don't rewrite the tests.

## 2. `runVoiceStage generates real WAVs via live speech backend`
Cause: needs torch/kokoro venv at `C:/one/voicebox/.venv/Scripts/python.exe`
which is RAM-prohibited. The test skips gracefully when venv absent
(`voice-controller.test.ts` uses `ensureBackend()` + skip).

## 3. Wikimedia / MetMuseum image providers
Status: SKIP (`host unreachable`) — sandbox has no network to those hosts.
Not a failure.

## 4. `free-music.test.ts` `resolveFreeBackgroundMusic returns bundled music when network fails` — REAL BUG, FIXED (2026-07-24)
Symptom: `assert.ok(result.track?.provider === 'bundled', 'Provider should be bundled')`
failed. Root cause (two parts):
(a) `FallackToneProvider.name` was `'fallback-ambient'`, so the
    `preferProviders:['bundled']` filter yielded an EMPTY list → no provider
    iterated → null. Fix: renamed provider to `'bundled'` (matches the test +
    the "bundled ffmpeg-static" convention used elsewhere).
(b) The ONLINE music engine ran FIRST even when 'bundled' was preferred, and
    returned a network provider's track. Fix: skip the engine when
    `preferProviders?.includes('bundled')`. Now 4/4.
**Lesson**: a "network-failure fallback" test failing usually means (1) the
provider NAME the test expects != what's registered, and/or (2) the online path
runs before the offline fallback even when offline is explicitly preferred.

## 5. `tests/agentic/media/tts.test.ts` — `not ok` from missing `fastapi` in speech venv (ENVIRONMENTAL, confirmed 2026-07-26)
Symptom: the suite wrapper reports `not ok 1 - tests/agentic/media/tts.test.ts` and the log shows
`ModuleNotFoundError: No module named 'fastapi'` from `src/speech/main.py` (the Voicebox backend
imports `fastapi`). Cause: the speech backend's Python venv is missing `fastapi`. The test itself
falls back to Edge-TTS and its own assertions PASS (`# pass 3 # fail 0`). The suite-level `not ok`
is from a 60s *timeout* waiting on the unavailable backend, NOT a code regression.
**Confirmed**: running just `node --import tsx --test "tests/agentic/media/tts.test.ts"` in isolation
prints `# pass 3 # fail 0` — the assertions pass; only the unavailable backend makes the wrapper error.
Do NOT chase this as a download/code bug. Fix the env (install `fastapi` in the venv) only if you
actually need the Voicebox backend path; otherwise treat it as expected noise.
NOTE: also confirm "failures" attributed to the download fix are NOT this — the download fix
(commit `2636edc`) is typecheck-clean and the only unit-suite noise is the venv/fastapi + network SKIPs.

## Regression-proof recipe
```bash
git worktree add -d /c/one/avs-baseline <base-sha>
cd /c/one/avs-baseline && cmd /c "mklink /D node_modules C:\one\Automated-Video-Generator\node_modules"
npx tsx --test "src/lib/media-verifier.test.ts" ...   # confirm SAME failures
git worktree remove "C:/c/one/avs-baseline" --force     # note MSYS double-c path
```

## Full-suite baseline (as of 2026-07-24)
`lib` batch: 145 tests, 138 pass, 0 fail (7 network-host SKIPs remain).
`operations` batch: 21/21 pass. Targeted compose/overlays suites: 30/30.
The remaining ignores are the 3 network-host SKIPs + the still-broken
`http/*` / `mcp/*` mock.module files. Your feature tests must stay green;
those are environmental noise.
