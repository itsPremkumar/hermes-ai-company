# node:test mock.module on Node 22 — proven facts & working templates

Everything below was verified empirically on **Node v22.23.1** (Windows/MSYS)
during a session that repaired 6 broken adapter test files (env-tools,
input-store, server-bootstrap, pipeline-commands, api-routes,
videos-controller) in the Automated-Video-Generator repo.

## The hard rules (all empirically proven)

1. `mock.module` is GATED behind `--experimental-test-module-mocks`. `tsx --test`
   does NOT forward the flag. Use:
   `node --import tsx --experimental-test-module-mocks --test "src/**/*.test.ts"`
   Put that exact command in `package.json` `test:unit` (and `test:coverage`).

2. `mock.module(spec, …)` may be registered **at most ONCE per specifier per
   process.** There is NO `mock.resetModules()` and NO `mock.registry` on
   Node 22. `mock.restoreAll()` clears spies + module mocks for the NEXT
   import but does NOT un-register, so a second `mock.module('fs', …)` THROWS:
   `Invalid state: Cannot mock 'fs'. The module is already mocked.`

3. ESM modules evaluate ONCE and are cached. After the first `import('./sut.js')`
   in a test, later `mock.module` + `await import` in another test is a no-op
   for that graph — the SUT keeps the first (possibly stale) binding.

4. `mock.reset()` only clears spies (`mock.fn`/`mock.method`). It does NOT free
   a `mock.module` registration and does NOT let you re-register.

5. `mock.method(obj, 'exec', fn)` FAILS on a read-only ESM namespace export
   (`import { exec } from 'child_process'`): `The argument 'methodName' must be
   a method. Received undefined`. Replace the WHOLE namespace instead:
   `mock.module('child_process', { namedExports: { exec: mock.fn(...) } })`.

## The ONLY robust pattern

- Register every `mock.module('fs'|'child_process'|'./relative', …)` EXACTLY
  ONCE at module top-level (before any `import('./sut.js')`).
- Use a mutable `const state = { … }` object; mock closures READ `state` at
  call time.
- `await import('./sut.js')` ONCE at top-level (after the mocks).
- Each `test()` mutates `state` then calls the already-imported function.
- `afterEach(() => { mock.restoreAll(); /* reset state vars */ })`.

## Proof probes (re-run to confirm environment)

```bash
node --experimental-test-module-mocks --input-type=module -e "
import { mock } from 'node:test';
console.log('resetModules:', typeof mock.resetModules); // undefined
console.log('restoreAll :', typeof mock.restoreAll);     // function
console.log('method     :', typeof mock.method);         // function
console.log('module     :', typeof mock.module);         // function
"
```

```bash
# Single-registration + mutable state: BOTH tests pass (proven):
#   mock.module('fs', { readFileSync: () => STATE.content })
#   test A: STATE.content='OPENAI_API_KEY=AAAAbbbbCCCCdddd' -> 'AAAA****dddd'
#   test B: STATE.content='OPENAI_API_KEY=XXXXyyyyZZZZwwww' -> 'XXXX****wwww'
```

```bash
# Re-registration FAILS (proven): second mock.module('fs') throws
#   'Invalid state: Cannot mock fs. The module is already mocked.'
```

## Known-good templates (copy + adapt)

### fs + paths (env-tools style)
```ts
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';

const fsState = {
  existsImpl: () => false,
  readImpl: () => '',
  writeImpl: (_c: string) => {},
};
mock.module('fs', {
  namedExports: {
    existsSync: (p: string) => fsState.existsImpl(p),
    readFileSync: () => fsState.readImpl(),
    writeFileSync: (_p: string, c: string) => fsState.writeImpl(c),
  },
});

test('reads + masks', async () => {
  fsState.existsImpl = () => true;
  fsState.readImpl = () => 'OPENAI_API_KEY=sk-abc0123def456';
  const { readEnvConfig } = await import('./env-tools.js');
  const r = await readEnvConfig();
  assert.equal(r.OPENAI_API_KEY, 'sk-a****f456'); // first4 + '****' + last4
});
```

### child_process.exec (pipeline-commands style)
```ts
const execState = { impl: (cmd: string, cb?: any) => cb?.(null, 'out', '') };
mock.module('child_process', {
  namedExports: {
    exec: mock.fn((cmd: string, _o: any, cb?: any) => { execState.impl(cmd, cb); return {} as any; }),
  },
});
// test: execState.impl = (cmd, cb) => { execCalls.push(cmd); cb?.(null,'',''); };
```

### express controllers (videos-controller style)
```ts
const svcState = { listImpl: () => [], getImpl: () => undefined };
mock.module('../../application/media-app.service', {
  namedExports: { mediaAppService: {
    listPublishedVideos: (req: unknown) => svcState.listImpl(req),
    getPublishedVideo: (id: string, req: unknown) => svcState.getImpl(id, req),
  } },
});
```

## Gotchas still valid

- `mock.module('fs', { namedExports: { onlySome } })` REPLACES the whole `fs`
  module — any member the SUT's graph uses (mkdirSync, statSync, readdirSync,
  renameSync, promises.*) becomes `undefined`. Spread the real fs then
  override: `...require('fs'), existsSync: () => true`. (When mocking via
  `mock.module` for `fs` you typically must provide EVERY member the SUT graph
  touches, or the import throws on access.)
- `mock.module` specifier MUST match the SUT's literal import string.
  `import * as fs from 'fs'` -> mock `'fs'` (NOT `'node:fs'`). `import * as cp
  from 'child_process'` -> mock `'child_process'` (NOT `'node:child_process'`).
  Proven: `'node:fs'` does NOT intercept `import ... from 'fs'`.
- The `mock.module` interception was PROVEN to work (a probe with both `fs`
  and `../../shared/runtime/paths` mocked returned the fake `FOO=bar`). Earlier
  "mock not applied" symptoms were actually ESM-cache/stale-binding, not
  specifier mismatch.
