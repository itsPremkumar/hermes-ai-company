# Node.js `node:test` Runner Pitfalls

## `ctx.skip()` does NOT abort test execution

**The pitfall:** `ctx.skip()` marks a test as skipped in the output, but the test body
continues executing on the next line. If the following code makes a network call or
asserts on skipped state, the test will fail with the real error — not skip cleanly.

**Confirmed on:** Node.js v22.23.1 (reproduced in July 2026).

**Always throw after skip:**
```typescript
if (condition) {
    ctx.skip('reason for skipping');
    throw new Error('reason for skipping');  // 👈 required to abort
}
```

Without the `throw`, the test runner counts the test as failed (not skipped), with a
confusing error from the downstream code that was never supposed to run.

**Rationale:** `ctx.skip()` calls `this.signal.abort()` under the hood, which sets an
internal abort flag. The test runner checks this flag between top-level async steps
(e.g., after a subtest completes), but the currently executing async function body
is NOT interrupted. The `throw` forcibly unwinds the call stack so the abort flag
takes effect at the test-runner level.

**Edge case — test marked "SKIP" AND "FAIL":**
```text
not ok 4 - MyTest # SKIP reason
  error: 'ECONNRESET'  ← actual failure from code that ran AFTER ctx.skip()
```
If you see this pattern, the `ctx.skip()` caller forgot to `throw`.

## CI env guard for network-dependent tests

CI environments (GitHub Actions, GitLab CI, etc.) often block, rate-limit, or
starve external hosts. A probe that passes with a 3s HEAD locally can still cause
a 30s+ timeout on the actual API call in CI.

**Pattern — fail fast in CI:**
```typescript
if (process.env.CI === 'true') {
    ctx.skip(`CI env: skipping test for ${url}`);
    throw new Error(`CI env: skipping test for ${url}`);
}
```

Place this check BEFORE any network-dependent code. This avoids the false
"HEAD passes but API call times out" failure mode.

## Pre-test reachability probe (skipIfUnreachable)

For tests that call external APIs, use a quick HEAD request to check host
reachability before the actual call. Combine with the CI guard:

```typescript
async function skipIfUnreachable(
    url: string,
    ctx: any,
    timeoutMs = 3000
): Promise<void> {
    // CI environments often block or rate-limit external hosts.
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

**Key design choices:**
- `timeoutMs` parameter lets callers tune the probe per-provider (e.g., a fast API
  can use 1000ms, a slow one 5000ms).
- `axios.head()` is lightweight — no response body, HTTP-verb-only.
- The `throw` after both `ctx.skip()` calls is **mandatory** (see pitfall above).

## How to detect a "stuck-in-skip" bug

Pattern-matching on TAP output:
```bash
npx tsx --test src/**/*.test.ts 2>&1 | grep -P 'not ok.*# SKIP'
```
Every line matching this pattern is a test that both skipped AND failed — a sign
that `ctx.skip()` was called without a subsequent `throw`. Each one is a bug,
not a skipped test.
