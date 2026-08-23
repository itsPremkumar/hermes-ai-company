# Production-Readiness Techniques (reference)

Reusable patterns from a real "make it production-ready + auto-find/fix bugs
+ visual verification" pass on a Node/TS video-generator repo. Condensed for
reuse; not a mirror of project docs.

## 1. Goal-prompt template (drives the whole pass)

Structure the agent's mandate as explicit phases with verification gates:
- PHASE 0 Baseline (typecheck exit code, `npm test` counts, `git status`,
  smell sweep, write BASELINE.md)
- PHASE 1 Static analysis (gstack health/devex-review or tsc/eslint)
- PHASE 2 Dynamic/QA (gstack qa; reproduce each failure; classify
  [NETWORK] vs [REAL BUG])
- PHASE 3 Fix with root cause (fails-before/passes-after test per bug;
  backward-compat shim; never delete old code)
- PHASE 4 Visual verification (render + ffmpeg + vision_analyze)
- PHASE 5 Hardening (smoke script, CI)
- PHASE 6 Report (QA_REPORT.md)
Hard constraints to embed: ZERO-COST (no paid keys/Claude Code/cloud),
BACKWARD COMPAT, NO PUSH without approval, RAM discipline (kill hogs via
`taskkill -F -PID <id>`), MAX 3 parallel subagents in waves 3->3->1.

## 2. Visual verification recipes (Node + ffmpeg-static)

ffmpeg-static is a dep; require it: `const ff = require('ffmpeg-static')`.
It ships only `ffmpeg.exe` (no `ffprobe` binary) -- use `ffmpeg -i` for stream
info, not `ffprobe -show_entries` (that flag errors on the static build).

- Streams + duration:
  `ff.execFileSync(ff, ['-i', mp4])` -> parse stderr for `Stream #0:0 Video:`
  and `Stream #0:1 Audio:` + `Duration:`.
- Black-frame check (mandatory for video):
  `ff.execFileSync(ff, ['-i', mp4, '-vf', 'blackdetect=d=0.3:pix_th=0.15', '-f', 'null', '-'], {stderr:true})`
  -> PASS = no `blackdetect` line in stderr.
- Extract frames for vision:
  `ff.execFileSync(ff, ['-y','-i',mp4,'-vf','fps=1/2','-vframes','3','frame_%02d.png'])`
  then `vision_analyze` each: confirm real scenes, correct assets, legible captions.

## 3. Bug-fix patterns that recurred (reusable)

### 3a. Flaky cold-start backend under RAM pressure
Symptom: integration test that spins a heavy Python backend fails only
inside the FULL `npm test` suite (passes standalone). Cause: hardcoded startup
deadline (e.g. 40s) exceeded when the machine is RAM-pressured after other
heavy tests. Fix: make deadline configurable (env var) + longer (120s), and
widen the readiness probe to also accept `/health` not just `/models/status`.
Verify: re-run the FULL suite -> test that was `not ok` becomes `ok`.

### 3b. Network tests FAIL instead of SKIP
Symptom: offline/sandbox runs show `host unreachable` as a FAILURE, not a SKIP.
Cause: the guard calls `ctx.skip(...)` THEN `throw new Error(...)` -- the throw
turns the skip into a fail. Fix: after `ctx.skip()`, `return` (don't throw).
Secondary cause: a test stubs only ONE of several network sources (e.g.
`freeImageAdapter`) while another (e.g. Openverse) still runs a live call and
adds results -> assertion `5 !== 2`. Fix: make the enable-flag a LIVE function
(`openverseEnabled()` reading `process.env` at call time) instead of a
module-load `const`, and have the test set `process.env.OPENVERSE_ENABLED='false'`
+ restore in `finally`. This isolates the stub -> deterministic count.

### 3c. "Offline fallback returns null" because it required a missing module
Symptom: `generateFallbackVisual` returns `null` -> `'fallback produced'`
assertion fails. Cause: it `require()`d a module that doesn't exist in the
repo (threw inside try -> caught -> null). Fix: replace with a self-contained
generator using an already-present dep (ffmpeg-static lavfi gradients for
image, zoompan+anullsrc for video). Keep the exact signature/return type for
backward compat. Verify: test asserts `source:'asset-creator'`, real
`.jpg`/`.mp4` on disk, size > 0.

### 3d. Provider metadata not loaded
Symptom: bundled-provider tests fail (`durationSec: 0`, `mood: undefined`).
Cause: loader only read per-track sidecar `.json`, but repo ships an
aggregated `metadata.json` array. Fix: read BOTH (sidecars win). Also fix the
mood filter so tracks lacking mood metadata are EXCLUDED when a specific mood
is queried (unknown mood -> 0 results).

## 4. Consolidation discipline (avoid redundant fixtures)
When adding a QA smoke command, point it at the EXISTING input script JSON
(the project's canonical `agentic-scripts.json`) rather than creating a
separate `qa-smoke-sample.json`. Delete the duplicate. Verify the plan stage
still runs against the existing file before committing.

## 5. Verification discipline
- Subagent self-reports are NOT trusted. After parallel fixes, run the
  targeted suites + full `npm test` + typecheck YOURSELF.
- Keep a BASELINE.md (before) and QA_REPORT.md (after) with real counts.
- Commit each fix locally; only `git push` after explicit user approval.
