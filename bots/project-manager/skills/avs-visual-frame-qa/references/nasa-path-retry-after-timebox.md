# NASA c:\ local-path download bug + Retry-After + acquire timebox (2026-08-17)

## NASA path bug
**Root cause**: NASA images API sometimes returns local Windows paths (`c:\...`) as
fallback URLs. These were passed to the downloader which rejected them with a
confusing SSRF guard error ("refused unsafe download URL: scheme c: not allowed").

**Fix** (`src/lib/free-image/providers/nasa.ts:76-87`):
- Validate fallback URLs are `http(s)://` before accepting them
- Skip any non-http(s) URL (local paths, etc.)

## Retry-After header respect
**Root cause**: Wikimedia returns HTTP 429 with `Retry-After` headers. We were
ignoring them and using fixed exponential backoff, which can prolong bans.

**Fix** (`src/agentic/operations/retry.ts` + `src/lib/visual-fetcher/download.ts`):
- Added `getRetryAfterMs()` function to extract Retry-After delay from error response headers
- Added `getRetryAfter` option to `RetryOptions` interface
- When `getRetryAfter` returns > 0, use it instead of computed backoff
- Also increased download retry base from 800ms → 8s (free providers need more patience)

## Acquire stage timebox
**Root cause**: The acquire stage could wedge for 30min+ on slow downloads
(observed in Tech gadgets run that hit the 30min watchdog).

**Fix** (`src/agentic/orchestrator/pipeline.ts`):
- Wrapped `acquireAssets()` in `withTimeout()` — defaults to 120s
- Overridable via `ACQUIRE_TIMEBOX_MS` env var
- On timeout, proceeds with empty candidates instead of hanging forever

## Verification
- Typecheck passes ✅
- All video-analyzer tests pass (10/10) ✅
- All video-analyzer-blackguard tests pass (2/2) ✅
- 24 variety videos render and pass QA ✅

## Gotchas for future sessions
1. **NASA images**: Always validate URLs from NASA API — they can return local paths on Windows
2. **HTTP 429**: Always respect `Retry-After` headers — ignoring them prolongs bans
3. **Stage timeboxes**: Every network-bound stage needs a timeout — the watchdog is a last resort, not a strategy
4. **MSYS path handling**: Native Windows programs (ffmpeg, NASA downloader) can't handle MSYS `/c/...` paths — always use `C:\...` or `C:/...` form
