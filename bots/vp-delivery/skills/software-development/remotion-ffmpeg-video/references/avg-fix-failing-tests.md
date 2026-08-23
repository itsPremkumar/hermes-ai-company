# AVG: Fixing "N failing unit tests" — branch-state trap + ffmpeg/network root causes

Context: a task asked to fix 8 failing AVG unit tests (generateFallbackVisual,
verifyRenderedVideo/tiny-MP4, edit primitives, video-analyzer testsrc, X7
size-floor, FfmpegSfxGenerator impact, ollama-bootstrap, openverse-fetcher).
Root causes given: (a) ffmpeg not on PATH, (b) live-service/network tests.

## LESSON 1 — verify the branch is on current main BEFORE trusting the "N failing" premise
The working branch (`fix/test-failures`) was an OLD commit (`f4d2d22`) that was
BEHIND actual `main` (`4019b3d`). At current main, ALL 8 tests already passed
(0 failures). The task's premise ("8 failing at 32643b4") described a state the
repo had already moved past.

DO NOT blindly start applying fixes to a stale branch. First:
  git log --oneline main..<branch>      # any unique commits?
  git rev-parse HEAD main               # is branch an ancestor of main?
  npm run test:unit 2>&1 | grep -iE "# (tests|pass|fail|skip)"
If the branch is behind main and tests are green at HEAD, reset it onto main:
  git reset --hard main
then re-run to confirm, then commit any genuine hardening.

## LESSON 2 — ffmpeg invocation pattern in AVG (root cause a)
System ffmpeg is NOT on PATH on this Windows box. The canonical, correct
invocation used everywhere in the repo is `require('ffmpeg-static')`
(returns the bundled `node_modules/ffmpeg-static/ffmpeg.exe`, v5.3.0).
ffprobe via `require('ffprobe-static').path` (v3.1.0).

Grep pattern to find latent bugs where code spawns a bare `ffmpeg`:
  grep -rn "spawn('ffmpeg'\|execFile('ffmpeg'\|spawnSync('ffmpeg'\|'ffmpeg', args" --include=*.ts src/
Real fix applied this session: src/lib/media-verifier.ts runFfmpeg() spawned
`spawn('ffmpeg', args)` -> silently returned null (frame extraction skipped),
so verification was a no-op. Changed to a ffmpegBin() helper that returns
`require('ffmpeg-static')` with `'ffmpeg'` fallback. Committed 297cac9.

Tests that use ffmpeg-static correctly (already green): video-analyzer.test.ts,
operations.test.ts (also ffprobe-static), gate.ts, acquire.ts (asset-creator),
free-sfx/generator.ts, render.ts (has its own fallback).

## LESSON 3 — network/service tests (root cause b) are already guarded
- ollama-bootstrap.test.ts: expects ServiceUnavailableError when Ollama is
  unreachable. Ollama IS installed here (AppData/Local/Programs/Ollama/ollama)
  but not running -> correctly throws. No live call. Test passes as-is.
- openverse-fetcher.test.ts: stubs `axios.get` so it never hits the network.
  Maps/wraps results deterministically. Passes offline.
These need NO change. The task asked to "make them skip gracefully" but they
already pass offline — do not weaken them by converting to skip.

## LESSON 4 — tooling quirks on this box
- search_files / the repo path "Automated-Video-Generator" (under C:/one) fails
  with "rg: ... The system cannot find the file specified (os error 2)" from the
  search_files tool, even though the path exists. WORKAROUND: use `grep -rn`
  via the terminal tool instead of search_files for this repo.
- The `patch` tool's lint step reports a spurious TS6053 "file not found" for
  absolute Windows paths — the edit still applied; verify with `npm run typecheck`.
- Full `npm run test:unit` runs ALL `src/**/*.test.ts` via tsx and takes ~60s /
  ~316 tests. There is exactly ONE pre-existing SKIP (render.e2e "renders a real
  video from the fixture", gated on RUN_RENDER_E2E) — not one of the 8.

## LESSON 5 — BRANCH-INSTABILITY TRAP (seen during a "now check" follow-up)
The working tree / checked-out branch can SILENTLY CHANGE between turns on this
host. Observed sequence in one session: started on `fix/test-failures`, a later
turn surfaced `feat/new-features` (with 11 failing tests + broken typecheck),
then a later turn showed `main` with `new-features.test.ts` and the 5 new op
modules GONE (not tracked by git, not on disk).

Symptoms that mean you are looking at a half-committed / swapped branch:
- A test file reports assertion failures but `git ls-files | grep <testfile>`
  returns NOTHING and `ls src/.../<file>.ts` says "No such file".
- `find` for the imported modules (silence.ts / noise.ts / reframe.ts /
  brand.ts / scene.ts) finds nothing, yet the test runner ran subtests from them.
- `git rev-parse --abbrev-ref HEAD` differs from what you last checked out.

RECOVERY: re-pin to the branch you actually own and re-verify; do NOT chase
failures on a branch whose source files do not exist in the tree. Before acting
on "N failures" reported by a fresh run, always `git rev-parse --abbrev-ref HEAD`
+ `git status --short` + `git ls-files | grep <the test file>` to confirm the
files are actually present and tracked. If a branch shows missing source for the
very modules its tests import, treat it as broken/incomplete and stop — report
it rather than attempting edits against non-existent files.

## LESSON 6 — feat/new-features: known bug classes (root-caused, source was missing)
When `feat/new-features` IS present and green-tree, these were the failure
root causes for new-features.test.ts (5 ops: silence/scene/reframe/noise/brand
+ route + real-ffmpeg integration). Capture so a future session fixes fast:

A. silence.ts `buildKeepFilter`: emitted `between(t\,0\,2)` (backslash-escaped
   commas). Inside a single-quoted ffmpeg expression `between(t,0,2)` the commas
   are literal, so the escaping is WRONG and breaks the filter. Fix: emit
   `between(t,${s},${e})` with NO backslash escaping.

B. Mocked-runner tests (silence/noise/reframe `...mocked runner` suites):
   after the ffmpeg call the function did `if (!fs.existsSync(output)) return
   {ok:false}` — but the INJECTED mock runner never writes a file, so `r.ok`
   was always false. Fix: guard with `if (!opts.runner && !fs.existsSync(output))`
   so real-runner-only enforcement stays, mock passes.

C. brand.ts `hexToRgb`: was a non-exported local function but the test imported
   it (`import { hexToRgb } from './brand.js'`) -> typecheck TS2459 + runtime
   undefined fn. Fix: `export function hexToRgb(...)`.

D. brand.ts `rgbExpr`: returned decimal `"31:111:235"` but ffmpeg drawbox color
   wants hex `0x1f6feb` -> "Invalid 0xRRGGBB color string: '31'". Fix:
   `0x` + [r,g,b].map(x=>x.toString(16).padStart(2,'0')).join('').

E. brand.ts `buildBrandFilter`: gated the `movie=` logo overlay on
   `fs.existsSync(kit.logo)`. The unit test passes a non-existent path and
   expects `movie=` (builder should emit based on `kit.logo` presence, not file
   existence — existence belongs at execution time). Fix: `if (kit.logo)`.

F. reframe.ts `parseDimsHint`: only parsed a fake `DIM:w,h` sentinel that the
   MOCK emits; real ffmpeg `-i` output has no such token, so real autoReframe
   failed with "could not determine source dimensions". Fix: also parse the real
   resolution string `(\d{2,4})x(\d{2,4})` from `-i` stderr.

G. route.ts noise strength: `/heavy|strong|aggressive/` did NOT match
   "heavily" (the prompt "denoise this clip heavily" -> audio defaulted to
   'medium'). Fix: add `heavily` to the regex -> `/heavy|heavily|strong|.../`.

H. adapters/mcp/register-operations-tools.ts: the `registerOperationsTools`
   closing `}` was placed BEFORE the convert/video/social/demux tool registrations,
   leaving ~20 `server.registerTool(...)` calls DANGLING at module top level ->
   typecheck TS1128 "Declaration or statement expected". Fix: move the function
   close `}` to the END (after the last registerTool call).

All of A–H are CODE bugs (fix the code, not the tests); none required test
deletion. The test file itself was correct/spec.

## LESSON 7 — reproduce the exact test scenario to localize a test-vs-isolation divergence
When a function returns the "wrong" value inside a test but the "right" value in
a quick standalone check, the difference is usually the mock-runner shape or an
existence assertion. To localize, write a throwaway `_dbg.ts` that imports the
MODULE (.ts path) and replicates the test's runner + inputs EXACTLY, then print
the result. CAVEATS on this box:
- tsx standalone scripts using top-level `await` fail with "Top-level await is
  currently not supported with the cjs output format" — wrap everything in an
  `async function main(){...}; main().catch(e=>{console.error(e);process.exit(1)})`.
- tsx cannot resolve `./src/.../x.js` from a script in the repo root (works only
  inside `--test` mode). Use the absolute Windows path:
  `import { foo } from 'C:/one/Automated-Video-Generator/src/agentic/operations/x.ts'`.
- Delete the temp `_dbg.ts` after to avoid confusing later runs.

## Final-state recipe for a green AVG gate
  git rev-parse --abbrev-ref HEAD   # confirm you are on the branch you own
  npm run typecheck                # must be 0 errors
  npm run test:unit                # 316 tests, 0 fail, 1 skip (the E2E render)
Branch deliverable: fix/test-failures (1 commit ahead of main: media-verifier
hardening 297cac9). If you are asked about feat/new-features failures, first
confirm its source files actually exist in the tree (Lesson 5) before editing.
