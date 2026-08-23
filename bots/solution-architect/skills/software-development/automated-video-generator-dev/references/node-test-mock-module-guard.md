# node:test `mock.module` guard pattern (reusable)

## Problem
Some test files call `mock.module('./x.js', {…})` at top level to stub a
module. On Node builds where `node:test`'s `mock.module` is unavailable
(this box: Node v22.23.1, `typeof mock.module === 'undefined'`), the call
THROWS at import time → the ENTIRE test file crashes (exitCode 1, no
subtests run). This looks like a cascade of failures but is a single
load-time error.

## Symptom
```
not ok 1 - src/lib/media-verifier.test.ts
  failureType: 'testCodeFailure'
  error: 'mock.module is not a function'
```

## Fix (do NOT rewrite the tests)
Guard the experimental API behind a typeof check so the REAL contract
tests still execute on unsupported builds:

```ts
import { test, describe, mock } from 'node:test';
// …
if (typeof mock.module === 'function') {
  mock.module('./ollama-client.js', {
    namedExports: { generateContentWithImage: async () => '…' },
  });
}
```

If the mock is NOT exercised by the current test bodies (they pass explicit
result objects), skipping it on unsupported builds is harmless. After the
guard, `media-verifier.test.ts` runs 6/6 (was a hard crash).

## When to apply
- A test file uses `mock.module` / `mock.fn` / any experimental `node:test`
  API and crashes on load under an older Node.
- Prefer guarding over deleting — the mock documents intent for newer builds.
- If you must verify the mock is actually used, add a separate test that
  asserts the stubbed behavior, but keep it inside the `typeof` guard so it
  self-skips on unsupported Node.
