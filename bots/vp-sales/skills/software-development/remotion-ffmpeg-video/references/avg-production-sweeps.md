# AVG: Bounded production-grade sweeps (Correctness → Resilience → Security → Docker/CI)

Context: user drove the repo (`itsPremkumar/Automated-Video-Generator`) to
"production-ready" via a written prompt demanding an infinite
`while(!ProductionReady)` loop. On a 6 GB RAM laptop with a flaky npm/Docker
network, that loop OOMs or stalls. The working model that actually shipped is a
**bounded per-subsystem sweep**: analyze ONE subsystem, fix highest-impact
concrete bugs (read the code, don't assume), add tests, hold the green gate,
commit on a feature branch, merge to main, push. Stop a subsystem when it has
no remaining critical/high issues; move on. THIS IS THE PROVEN EXECUTION MODEL.

## Green gate (must hold before every push)
- `npm run typecheck` → 0 errors
- `npm run test:unit` → green
- No secrets in the diff (`.env` gitignored, placeholders in docs only)
- Commit message names the subsystem + what changed
- Push to `origin/main` via `gh`/git (NO native GitHub MCP on this box)

## Sweep 1 — Correctness: real media probing (duration no-op bug)
- `silence.ts`: duration from absent `DURATION:` hint → `1e9` → silence removal
  no-op in prod.
- `scene.ts`: `duration ?? 0` → chapters/trim empty in prod.
- `reframe.ts`/`brand.ts`: dims via fragile ffmpeg stderr regex.
FIX: new `operations/probe.ts` — `probeMedia(file, runner?)` (ffprobe-static),
`parseProbe` pure, injectable. Removed dead code.
TEST: inject `fakeProbe` `{duration:12.5}` + `fakeRunner`; assert "removed 1
silent span" (NOT 0). Create real temp file so `fs.existsSync` passes.

## Sweep 2 — Error handling & resilience
- `dispatch.runOne` no guard → throwing op crashed `doTask`.
- `download-media.ts`/`voiceover.ts` no transient retry.
- `reframe.ts` invalid preset → `0/0` → NaN → crash.
FIX: new `retry.ts` `withRetry` (bounded exp backoff + jitter). Wrap network +
TTS. `dispatch` try/catch around switch. `reframe` validates preset pre-IO.

## Sweep 3 — Security & input validation
- NO committed secrets. `src/app.ts` ALREADY hardened (CSP/CORS/rate-limit).
- REAL gap: `dispatch` passed `input.out` → path traversal.
FIX: new `security.ts` — `safeOutputPath(out?)` (rejects `..`/absolute outside
`output/`), `redactSecrets`. Sanitize at single chokepoint. Import path
`../../agentic/operations/security.js` from `src/adapters/http/`.

## Reusable testing technique
- `node --test` via `tsx --test` (NOT jest): `import { test, describe } from
  'node:test'` + `node:assert/strict`.
- Inject mock `runner` + `probe`; keep real binaries for integration tests.
- `patch` lint spurious TS6053 on Windows paths — confirm with `typecheck`.

## Docker / CI (Sweep 4 — DONE, CI green)
- `Dockerfile` correct (node:20-bookworm, full npm ci, python3-venv, edge-tts
  venv, linux/amd64, /api/health, npm retry).
- Local `npm ci` ECONNRESET (env limit). SOLUTION: GH Actions `ci.yml` builds +
  pushes to GHCR free in CI. Confirmed GREEN (Lint & Format, TS 18/20/22, Unit
  Tests, Docker GHCR, Secret Scan, Audit, Render E2E). See
  `references/avg-ci-workflow-validation.md`.

## Additional hardening (subsequent session — full-list completion)
A second verified audit ("another AI's plan") executed end-to-end. The
user-supplied external audit had FALSE claims ("no agentic tests",
"`plugins/` exists with unused files") — REJECTED after code verification.

### Tier-1 (critical) — committed, CI green
- **C1 Remotion drift**: `@remotion/captions@^4.0.490` vs others `^4.0.487`.
  Remotion needs ALL `@remotion/*` identical. Aligned.
- **C2 SSRF**: `free-video/downloader.ts` + `visual-fetcher.ts` no URL guard.
  New `lib/net-safety.ts` → `isSafeUrl()` (http/https only; rejects
  private/loopback/link-local/169.254.169.254/IPv6 ULA). Applied before every
  stream download. + `net-safety.test.ts` (6 cases).
- **C3 ffmpeg drawtext injection**: orchestrate.ts escaped only `'`/`:`, missed
  `\"`,`,`,`\`. New `lib/ffmpeg-text.ts` → `ffmpegDrawtextEscape()` (handles
  `\ : ' " ,`). Applied at all 5 drawtext sites.
- **C4 secret on disk**: `.env` had real `VOICEBOX_PROFILE_ID` UUID. Scrubbed
  on disk (history clean — gitignored, never committed).

### Tier-2 — committed, CI green
- **L3**: `@remotion/bundler` `require()`d but undeclared → added `^4.0.487`.
- **M1 loopback**: `app.ts` CORS gate missed `::1`. Exported
  `isLoopbackHostname` from `middleware/local-only.ts`, reused in `app.ts`.
- **M2 secret redaction**: `readEnvConfig(showSecrets)` returned RAW secrets →
  now always masks. `redactSecretsIn()` wired into `error-handler.ts`.
- **M4 OS-aware fonts**: orchestrate.ts pinned `C:/Windows/Fonts/arial.ttf`
  first (broke macOS). Added `~/Library/Fonts`, `/Library/Fonts`,
  `/System/Library/Fonts/Supplemental`, Linux fallback.
- **L6 dead code**: inlined `configToRequest_buildReq` wrapper. NOTE:
  `diversityPenalty` + alleged unreachable branch :613 checked — NOT dead —
  left as-is.

### H7 / M8 — fail-closed verification + final-render gate
- ROOT BUG: `media-verifier.ts` returned `passes:true, confidence:5` when AI
  unavailable → off-topic assets passed SILENTLY. Fixed: `failClosed` option
  (default TRUE); `unavailableResult()` returns `passes:false` fail-closed.
- **M8**: new `verifyFinalRender(filePath, keywords, opts)` samples N frames
  across finished MP4, AI on EACH, fails gate if ANY frame fails. Added
  `aiVerify.finalMode: 'signal' | 'vision'`; `gate.ts` X16 uses it when
  `'vision'`. + `media-verifier.test.ts` (4 cases).

### H2 / M3 / H5 — ffmpeg consolidation, bounded cache, infra tests (committed, CI green)
- **H2 single runner**: new `src/lib/ffmpeg.ts` — `ffmpegPath()` (cached resolve of
  ffmpeg-static), async `runFfmpeg(args, {timeoutMs, captureStdout})` (kills on
  stall, rejects `FfmpegError` instead of swallowing), `runFfmpegSync`,
  `ffmpegCanRun()` (REAL probe, not a `-filters` name check). Migrated
  `media-verifier.ts`'s `runFfmpeg` to use `ffmpegPath()` instead of the latent
  `spawn('ffmpeg')` (PATH-dependent — would fail where ffmpeg isn't on PATH).
  + `ffmpeg.test.ts` (4 cases: resolve, probe, sync version, fail-closed reject).
- **M3 bounded cache**: `visual-fetcher.ts saveCache` now ATOMIC
  (write temp + `renameSync`, never leaves a truncated `.video-cache.json` under
  crash/concurrency) + capped `CACHE_MAX_ENTRIES=2000` with FIFO eviction of
  oldest keys. The in-memory singleton was already there; the file write was not.
- **H5 infra test**: `middleware/rate-limit.test.ts` (3 cases: allow≤max then
  block, per-IP independence, window reset). NOTE: `createMemoryRateLimiter`
  ALREADY evicts expired entries per request — the audit's "grows forever" claim
  was OVERSTATED; left as-is after confirming.
- **H3**: pattern established (PATH bug fixed). Full 69-site spawnSync→async
  deferred — would risk the render path; sync helpers acceptable.

### L1 — tsconfig strictness (PITFALL, cost a wasted turn)
ADDING `strict`-family flags is a real hardening win BUT easy to under-fix:
- `noImplicitReturns: true` on Express `async (req,res)=>{ try{...}catch{...} }`
  handlers flags `TS7030: Not all code paths return a value`. The fix is NOT
  just adding `return` before the **try**-path `res.json(...)` — you MUST also
  `return res.status(500).json(...)` on the **catch** path, or the error
  persists. (This was missed once: added `return` only on try-path, typecheck
  stayed at 4 errors, burned a turn.)
- `noUnusedLocals` / `noUnusedParameters: true` surfaced **180** errors — mostly
  in `remotion/*.tsx` render components (unused `dimsFromProps`, `fps`, `title`,
  etc.). Do NOT force these into the same pass — they touch render-critical code.
  Revert those two flags; schedule the unused-var cleanup as its OWN careful wave
  (prefix `_` or delete). Keep only the SAFE flags that add 0 errors:
  `noImplicitReturns`, `noFallthroughCasesInSwitch`.
- RULE: after editing tsconfig, re-run `npm run typecheck` and COUNT errors; only
  commit when the count is 0. Never report a strictness fix done until the error
  number actually drops to 0.

### False external-audit claims (verify before acting — more found this pass)
- **L5 "504 TODO/FIXME debt"**: `grep -rnE "TODO|FIXME" src/` → **0** markers.
  NON-ACTION. (The 1181 `//` comments are debug logs/section headers, not debt.)
- **env-var count "~20 magic vars"**: real count is **81** distinct
  `process.env.*` across `src/`. Created `docs/ENVIRONMENT.md` consolidated table
  + linked from `docs/SETUP.md`.
- **M7 false doc**: `AGENTS.md` claimed "X1–X6 IDs were retired" — FALSE;
  `gate.ts` has X1–X6 (pre-render holistic) + X7–X15 (post-render) + X16
  (opt-in AI). Corrected the doc with the accurate gate breakdown.

### Session-discipline lessons
- When handed an "external audit", VERIFY every claim against code before
  acting. User explicitly values catching false claims. This pass rejected
  L5 (0 TODOs) and corrected M7 (X1–X6 alive) + env count (81 not 20).
- Hold green gate before every push; commit per logical group
  (`feat/tier1-security`, `feat/tier2-contained`, `feat/h7-final-gate`,
  `feat/ffmpeg-consolidation`).
- tsconfig strictness: add flags incrementally, verify error count hits 0 before
  claiming done (see L1 pitfall above).
- REMAINING (not executed): H1 (split 2164-line orchestrate.ts), H4 (converge
  legacy+agentic pipelines), H6 (surface structured errors), M5
  (workspace-root — NOTE `resolveProjectPath` already exists in
  `shared/runtime/paths.ts`, likely largely satisfied), L2 (reduce `any` in MCP
  registration), L4 (sub-project drift), L7 (optional Swagger).
