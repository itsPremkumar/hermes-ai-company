# Convert network failures → clean SKIPs

A test that throws `host unreachable` / `ENOTFOUND` / `fetch failed` in an
offline sandbox is NOT a code bug — it's environment. Leaving it as FAIL makes
`npm test` red on a clean machine. Convert it to a SKIP so the suite is green
offline, while REAL logic bugs stay RED.

## The classic bug: `ctx.skip()` followed by `throw`
node:test's `ctx.skip(msg)` marks the test skipped but does NOT abort execution.
If the guard then does `throw new Error('host unreachable')`, the test is
reported as FAILED (the throw isn't the special skip sentinel). Fix:
```ts
async function skipIfUnreachable(url: string, ctx: any, timeoutMs = 3000) {
  if (process.env.CI === 'true') { ctx.skip(`CI: skip ${url}`); return; }
  try { await axios.head(url, { timeout: timeoutMs }); }
  catch { ctx.skip(`host unreachable: ${url}`); return; }   // return, DON'T throw
}
```

## When the network call is INSIDE the source (not the test)
If a test stubs one provider but the function also calls a second live source
(e.g. `searchFreeImages` stubs `freeImageAdapter` but still hits Openverse when
`OPENVERSE_ENABLED` is true), the stub won't isolate it and you get `5 !== 2`.

Root-cause fix (don't weaken the assertion):
1. Make the env gate a LIVE function, not a module-load const:
   ```ts
   // BEFORE: const OPENVERSE_ENABLED = process.env.OPENVERSE_ENABLED !== 'false';
   // AFTER:
   function openverseEnabled(): boolean { return process.env.OPENVERSE_ENABLED !== 'false'; }
   ```
   and use `if (openverseEnabled())` at the call site.
2. In the test, set `process.env.OPENVERSE_ENABLED = 'false'` before the call
   and `delete process.env.OPENVERSE_ENABLED` in `finally`. Now only the stubbed
   adapter contributes → `out.length === 2` deterministically.

## Classify before fixing
`grep -E "host unreachable|ENOTFOUND|fetch failed|ECONNREFUSED" /tmp/full.log`
→ these are [NETWORK] → SKIP. Assertions like `AssertionError: 5 == 2` or
`expected X got Y` with no network msg → [REAL BUG] → fix at cause.
