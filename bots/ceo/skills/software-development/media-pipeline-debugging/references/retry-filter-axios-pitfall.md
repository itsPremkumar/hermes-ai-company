# Retry Filter: AxiosError Catch-All Pitfall

## The Class-Level Trap

A retry filter that treats **all AxiosErrors** as transient will infinitely retry
downloads that can **never** succeed — because axios wraps many non-retryable
failures as AxiosErrors too.

## Signal: Infinite Retry on Download

```
[retry] download:candidate_1.mp4: attempt 1 failed (maxContentLength size of 157286400 exceeded); retrying in 1017ms
[retry] download:candidate_1.mp4: attempt 2 failed (maxContentLength size of 157286400 exceeded); retrying in 1745ms
... infinite loop until timeout
```

The file is genuinely too large (150 MB+ Pexels video). Each retry wastes ~1–2
seconds and the process only stops when the outer pipeline timeout fires.

## Root Cause

```typescript
// ❌ CATCHES ALL: every axios error (including maxContentLength exceeded) retries
function isDownloadRetryable(err: unknown): boolean {
    // ...
    return e.name === 'AxiosError' || e.name === 'FetchError' || e.name === 'TimeoutError';
}
```

When `maxContentLength` is exceeded, axios throws with `name: 'AxiosError'`.
The blanket `e.name === 'AxiosError'` check means the error passes `shouldRetry`
and keeps getting retried — even though it's a permanent failure.

## Fix

Add a **non-retryable guard BEFORE** the catch-all name check:

```typescript
function isDownloadRetryable(err: unknown): boolean {
    if (!err || typeof err !== 'object') return false;
    const e = err as { status?: number; response?: { status?: number }; code?: unknown; message?: string; name?: string };

    // Non-retryable guards — checked FIRST, before any catch-all
    if (typeof e.message === 'string' &&
        /maxContentLength|content.length|too large|size exceeded|content too large/i.test(e.message)) {
        return false;  // ← bail immediately: this will never succeed
    }

    const status = Number(e.status ?? e.response?.status ?? 0);
    if (status === 429 || (status >= 500 && status < 600)) return true;  // transient → retry

    const code = String(e.code ?? '');
    if (['ECONNRESET', 'ETIMEDOUT', 'ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNABORTED'].includes(code)) return true;
    if (typeof e.message === 'string' && /timeout|stall|reset|aborted|network|econn/i.test(e.message)) return true;

    return e.name === 'AxiosError' || e.name === 'FetchError' || e.name === 'TimeoutError';
}
```

## Which Other Errors Are Non-Retryable Despite Being AxiosError?

| Error | Axios Property | Why Non-retryable |
|---|---|---|
| `maxContentLength exceeded` | `message.includes('maxContentLength')` | File is genuinely too large |
| HTTP 401 / 403 | `response.status === 401/403` | Auth/permission — won't change |
| HTTP 404 | `response.status === 404` | Resource doesn't exist |
| Invalid URL | `code: 'ERR_INVALID_URL'` | Programming error |
| TLS cert failure | `code: 'ERR_TLS_CERT_ALTNAME_INVALID'` | Config/environment issue |

## Where to Check

Any retry filter in the codebase that uses `e.name === 'AxiosError'` as a
catch-all should add non-retryable message/status guards FIRST. Sibling pattern:
`download.ts:isDownloadRetryable` (visual-fetcher downloader).

## Why NOT to Make `maxContentLength` Infinite

Don't raise `MAX_DOWNLOAD_BYTES` to accommodate these files — oversized
downloads eat bandwidth, fill workspace disk, and slow the pipeline. Let them
fail fast and let the pipeline's offline/fallback path handle the scene.
