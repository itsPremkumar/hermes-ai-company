# AVG — CI Environment Simulation for Test Debugging

How to reproduce CI-conditional test failures locally for the Automated-Video-Generator
test suite. This is a supplement to `avg-ci-cross-platform-gotchas.md` (cross-platform
bugs CI caught) and `avg-ci-workflow-validation.md` (GitHub Actions workflow traps).

## The CI Workflow (current as of ci.yml)

```
runs-on: ubuntu-latest
node-version: 22 (pinned in unit-test job)
install: npm ci (no .env, no apt packages for the test job)
env: CI=true (GitHub Actions default), no application env vars set
test: npm run test:unit  →  tsx --test "src/**/*.test.ts"
```

Key CI facts that differ from local:
- No `.env` file — dotenv loaded in `src/constants/config.ts` is a no-op in CI
- No `OLLAMA_URL`, `PEXELS_API_KEY`, `VOICEBOX_*`, etc. — every `process.env.X` reads undefined
- No internet access to Wikimedia, Archive.org, NASA, MetMuseum APIs
- The `test` job does NOT `apt-get install ffmpeg` (only the `render-e2e` job does)
- `CI=true` is set — the `free-image.test.ts` `skipIfUnreachable()` checks this

## Simulating CI Locally (Windows git-bash)

```bash
cd /c/one/Automated-Video-Generator

# Clear ALL application env vars + set CI=true
CI=true env \
  -u OLLAMA_URL -u OLLAMA_MODEL -u VOICEBOX_PROFILE_ID -u VOICEBOX_API_URL \
  -u PEXELS_API_KEY -u OPENROUTER_API_KEY -u GEMINI_API_KEY -u RUN_RENDER_E2E \
  npm run test:unit 2>&1 | grep -E "^# (tests|pass|fail|skipped|cancelled)"
```

### To also neutralize `.env` (dotenv loaded at import time)

```bash
cp .env .env.ci-bak && echo "" > .env && \
  CI=true npm run test:unit 2>&1 | grep -E "^# (tests|pass|fail|skipped)" && \
  mv .env.ci-bak .env
```

## Expected Counts Per Environment (saved from verified runs)

| Condition | Tests | Pass | Fail | Skip |
|---|---|---|---|---|
| Local (no CI, default env) | 411 | 401 | 0 | 10 |
| CI=true + vars stripped | 411 | 399 | 0 | 12 |
| CI=true + concurrency=2 | 411 | 399 | 0 | 12 |

The delta of 2 pass→skip comes from `free-image.test.ts` which checks `process.env.CI === 'true'` via `skipIfUnreachable()` and skips 10 external-API tests.

## How to Find Which Tests Changed Between Runs

```bash
# Capture CI-simulated output
CI=true npm run test:unit 2>&1 | grep -E "^not ok|^ok.*# SKIP" > /tmp/ci.out

# Capture local (non-CI) output
npm run test:unit 2>&1 | grep -E "^not ok|^ok.*# SKIP" > /tmp/local.out

# Diff to see what changes
diff /tmp/local.out /tmp/ci.out
```

## Known Environment-Sensitive Tests

### free-image.test.ts (lines 22-37)

```ts
async function skipIfUnreachable(url: string, ctx: any, timeoutMs = 3000) {
    if (process.env.CI === 'true') {
        ctx.skip(`CI env: skipping test for ${url}`);
        throw new Error(`CI env: skipping test for ${url}`);
    }
    try {
        await axios.head(url, { timeout: timeoutMs });
    } catch {
        ctx.skip(`host unreachable: ${url}`);
        throw new Error(`host unreachable: ${url}`);
    }
}
```

10 tests use this guard. In CI they skip. Locally they run real HTTP HEAD probes
to Wikimedia, Archive.org, NASA, and MetMuseum APIs.

### render.test.ts (lines 137-138, 153-154)

```ts
it('renders a watchable MP4 ...', async () => {
    if (!ffmpegCanRun("drawtext=text='x'")) return;
```

`ffmpegCanRun` checks if `ffmpeg-static`'s binary can actually execute the
`drawtext` filter (needs fontconfig/libfreetype). On full ffmpeg builds it works;
on minimal/stripped builds the test skips by returning early.

### render.e2e.test.ts (line 99)

```ts
const RUN_REAL = process.env.RUN_RENDER_E2E === '1' && ffmpegAvailable();
(RUN_REAL ? test : test.skip)('renders a real video from the fixture', ...);
```

Skipped even on CI because `RUN_RENDER_E2E` is explicitly set to `0` in the
render-e2e job, and is unset in the unit-test job.

### operations/integration.test.ts (line 43-44)

```ts
const canRun = ffmpegRuns();
const maybe = canRun ? test : test.skip;
```

Entire describe suite runs or skips based on whether `ffmpeg -version` succeeds.

### api-tts-provider.test.ts — Global Axios Mock Leak 🚩

This file mutates `axios.post` and `axios.get` at **module scope** (lines 25-49)
and **never restores them**. Since Node caches modules, every subsequent test file
that calls `axios.get()` or `axios.post()` receives the mock instead of the real
implementation.

```ts
// Lines 25-35 of api-tts-provider.test.ts — NEVER RESTORED
const originalPost = axios.post;
axios.post = async function (...) { ... };
const originalGet = axios.get;
axios.get = async function (...) { ... };
```

Affected files:
- `openverse-fetcher.test.ts` — saves `const realGet = axios.get` at module load
  (line 9). If api-tts-provider.test.ts loads first, `realGet` IS the mock, not
  the real axios. The `afterEach(() => restoreGet())` then restores the mock.
- `free-music.test.ts` — proxies axios.get with try/finally; the captured "original"
  is the mock. Restore puts the mock back.
- `free-image.test.ts` — uses `axios.head()` (separate method from `.get`/`.post`),
  so likely unaffected.

This is a potential CI-only failure source if file load order differs between
Windows and Linux filesystems (unlikely with alphabetical glob but possible).
Files are loaded in lexical order of their full path under `src/`:
- `src/lib/api-tts-provider.test.ts` (a comes before f, o)
- Always loads before `free-music.test.ts` and `openverse-fetcher.test.ts`

### ollama-bootstrap.test.ts (lines 7-11)

```ts
const origEnv = { ...process.env };
test.afterEach(() => { process.env = { ...origEnv }; });
```

Saves entire `process.env` at module load and restores after each test. If this
file loads after `api-tts-provider.test.ts`, the "original" env includes the
TTS_PROVIDER and VOICEBOX values from `.env` (not present in CI). Safe enough
since it restores per-test, but the "original" snapshot is stale.

## Test Structure Reference

```
package.json:
  "test:unit": "tsx --test \"src/**/*.test.ts\""

Test runner: tsx v4.x + Node 22 (node:test)
Test files: 48+ matching src/**/*.test.ts (approx 268 subtests, 411 individual tests)
Concurrency: default = os.availableParallelism() (~16 local, 2 CI)
  Use: npx tsx --test --test-concurrency=2 ... to match CI
Timeouts: none set globally (default = no timeout)
```

## Debugging Checklist for AVG CI Failures

1. [ ] Check if CI workflow has changed (`.github/workflows/ci.yml`)
2. [ ] Run with `CI=true` + stripped env vars — match CI counts?
3. [ ] Check for new `.env` variables added to `src/constants/config.ts`
4. [ ] Match CI concurrency: `--test-concurrency=2`
5. [ ] Check if `free-image.test.ts` tests are skipped or running (network-dependent)
6. [ ] Look for new `skipIfUnreachable`-style guards in test files
7. [ ] Check for module-level mock pollution (axios, child_process, fs)
8. [ ] Compare specific TAP output: enumerate `not ok` lines without `# SKIP`
9. [ ] If CI shows a failure that can't reproduce: check Linux vs Windows path differences
10. [ ] If nothing found: check CI's Node version (matrix: [20, 22]) — run `nvm use 20` etc.
