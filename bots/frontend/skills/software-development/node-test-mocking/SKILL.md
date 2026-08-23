---
name: node-test-mocking
description: Use Node's built-in test runner (node:test) mock API correctly — mock.module, mock.method, mock.fn, and module-mock teardown. Covers the --experimental-test-module-mocks gate, the tsx flag-forwarding gotcha, the mock.reset() vs mock.resetModules()/mock.restoreAll() trap, and the read-only ESM namespace export problem. Trigger when diagnosing "mock.module is not a function", "already mocked", "Cannot set property exec of #<Object> which has only a getter", or writing/repairing TypeScript/Node unit tests that mock fs/child_process/express/controllers.
---

# node-test-mocking

Diagnose and fix tests that use Node's `node:test` `mock` API (`mock.module`,
`mock.method`, `mock.fn`). The API is stable but has three footguns that cause
entire test files to fail at import time — none of them obvious from the error
message alone.

## Reference: proven Node-22 facts & copy-paste templates
See `references/node22-mock-module-proven.md` for the empirically-verified rules
(no `resetModules`, single-registration-only, specifier matching), proof probes,
and known-good `fs` / `child_process` / express-controller test templates.
- A test file throws `mock.module is not a function` / `import_node_test.mock.module is not a function`.
- A test throws `Invalid state: Cannot mock 'X'. The module is already mocked.`
- A test throws `Cannot set property exec of #<Object> which has only a getter`.
- You are writing or repairing `*.test.ts` that mock `fs`, `child_process`,
  `express` controllers, or any dependency via `mock.module`.
- You run tests with `tsx --test ...` and module mocks mysteriously don't apply.

## The three footguns (all proven empirically on Node v22.x)

### Footgun 1 — `mock.module` is GATED behind a flag
`mock.module` only exists when Node is launched with
`--experimental-test-module-mocks`. Without it:
- `node -e "import('node:test')"` → `typeof m.mock.module === 'undefined'`
- `node --experimental-test-module-mocks -e …` → `typeof m.mock.module === 'function'`

**tsx does NOT forward this flag.** `tsx --test …` leaves `mock.module`
undefined. You MUST launch node directly and load tsx via a preload:
```
node --import tsx --experimental-test-module-mocks --test "src/**/*.test.ts"
```
This was verified to expose `mock.module` (tsx's own `--test` path does not).

### Footgun 2b — you literally CANNOT re-register a module mock (no reset API).
`mock.module(spec)` may be called at most ONCE per specifier for the whole
process. There is no `mock.resetModules()` (verified undefined on Node 22.23.1)
and `mock.restoreAll()` does NOT un-register it. So this ALWAYS throws on the
second test:

```ts
test('a', async () => { mock.module('fs', {…}); … });
test('b', async () => {
  mock.module('fs', {…});   // ← Invalid state: Cannot mock 'fs'. The module is already mocked.
});
```

The SUT module is also cached after the first `import`, so a fresh
`mock.module` + re-`import` in a later test is a no-op for that graph anyway.
→ Register each `mock.module` EXACTLY ONCE at top-level; vary behavior with
mutable `let` state. See the RIGHT pattern in Footgun 2.

**What this bug actually LOOKS like in practice (the time-sink):** the
first test passes; test #2+ either (a) throws `Invalid state: Cannot mock 'X'.
The module is already mocked.` the instant it calls `mock.module`, or
(b) — worse — runs WITHOUT throwing but against the STALE cached module, so an
assertion like `result.OPENAI_API_KEY.startsWith('sk-')` fails with
`result.OPENAI_API_KEY is undefined` (the mock never applied to the cached
binding). The naive "fix" (`afterEach(() => mock.resetModules())` or
`afterEach(() => mock.restoreAll())` + re-`mock.module` inside each test) is
EXACTLY what makes it worse: `mock.resetModules()` is undefined (throws),
and `restoreAll()` + re-register throws `already mocked`. You cannot re-register.
The ONLY escape is the single-top-level-registration + mutable-STATE pattern
below. This was re-derived from scratch and proven with a throwaway probe
during a real 36-test adapter-suite failure.

Empirical proof you can re-run to confirm this on any Node 22 box:
```bash
node --experimental-test-module-mocks --input-type=module -e "
import { mock } from 'node:test';
console.log('resetModules:', typeof mock.resetModules);   // 'undefined'
console.log('restoreAll :', typeof mock.restoreAll);       // 'function'
console.log('method     :', typeof mock.method);           // 'function'
console.log('module     :', typeof mock.module);           // 'function'
"
```
If you ever see `mock.module is not a function` in that probe, the runner is
missing `--experimental-test-module-mocks` (Footgun 1), not a version gap.
This is the trap that wastes the most time, and the naive "fix" makes it
worse. `mock.module(spec)` installs a loader hook so the NEXT `import(spec)`
returns the mock. But ESM modules are evaluated ONCE and cached. If the SUT
(or anything in its graph) was already imported in an earlier test, the cached
binding is reused — your new `mock.module` + `await import()` inside the later
test is a **no-op for that graph**.

Symptom: test #1 passes (it got the mock), test #2+ runs against the
REAL module (or the stale binding from test #1) → silent wrong behavior,
`0 !== 5` on an in-loop `execCalls.length` assertion, or a hang.

WRONG (what `resetModules()` + per-test re-import produces — DO NOT do this):
```ts
afterEach(() => mock.resetModules());        // still only mocks test #1
test('a', async () => {
  mock.module('fs', { namedExports: { readFileSync: () => 'x' } });
  const { readEnvConfig } = await import('./env-tools.js'); // cached after test 1
});
test('b', async () => {
  mock.module('fs', { namedExports: { readFileSync: () => 'y' } });
  const { readEnvConfig } = await import('./env-tools.js'); // SAME cached module
  // ← gets test a's value, not 'y'
});
```

RIGHT — mock ONCE at module top-level, import the SUT once, and drive
per-test behavior through MUTABLE `let` state that `afterEach` resets:
```ts
import { test, mock, afterEach } from 'node:test';
import assert from 'node:assert/strict';

let fsContent = 'default';
const execCalls: string[] = [];

mock.module('fs', { namedExports: {
  existsSync: () => true,
  readFileSync: () => fsContent,        // reads mutable state
  writeFileSync: () => {},
}});
mock.module('child_process', { namedExports: {
  exec: (cmd, _opts, cb) => {               // callback-style exec
    execCalls.push(cmd);
    if (typeof cb === 'function') cb(null, 'mock stdout', '');
    return {} as any;
  },
}});

const { readEnvConfig, runPipelineCommand } = await import('./env-tools.js');

afterEach(() => { fsContent = 'default'; execCalls.length = 0; mock.restoreAll(); });
// NOTE: mock.module is registered ONCE above and is NEVER re-registered.
// mock.restoreAll() clears spies + module mocks but does NOT permit
// re-calling mock.module for the same specifier — so drive variation via
// the mutable `let` state, never via re-registration.

test('reads + masks secret', () => {
  fsContent = 'OPENAI_API_KEY=sk-abc0123def456\n';
  const r = await readEnvConfig();
  assert.ok(r.OPENAI_API_KEY!.includes('****'));
});
test('runs allowed command', () => {
  await runPipelineCommand('generate');
  assert.equal(execCalls.length, 1);   // ← works now
});
```
Why this works: `mock.module` is called ONCE so the SUT's module binding is
stable; the `let` variables are the per-test seam; `mock.reset()` clears the
spies/mocks between tests (here it DID clear module mocks — the "already
mocked" error only appears when reset is omitted entirely).

### Footgun 3 — ESM namespace exports are READ-ONLY
If the SUT does `import { exec } from 'child_process'`, `exec` is a frozen
property on the ESM namespace. A test doing `(cp as any).exec = mockFn` throws:
`Cannot set property exec of #<Object> which has only a getter`.
**Fix:** use `mock.module('child_process', { namedExports: { exec: mockFn } })`
(see Footgun 2 top-level pattern). Never reassign an imported binding.

## Correct pattern (top-level mock + mutable state — works under ESM caching)
1. `afterEach(() => mock.restoreAll())` + reset your mutable `let` state
   (clears spies between tests; never re-register a module mock).
2. At MODULE top-level (ONCE), call `mock.module('fs', …)` / `mock.module('child_process', …)` with `namedExports` whose functions READ
   mutable `let` variables.
3. `await import('./sut.js')` ONCE at top-level, AFTER the mocks —
   so the SUT binds to the mocked graph.
4. Each test mutates the `let` variables (e.g. `fsContent = '…'`);
   `afterEach` resets them. Do NOT call `mock.module` or `await import`
   INSIDE a test — that re-triggers the ESM-cache trap in Footgun 2.

### DON'T do this (per-test re-import — only test #1 gets mocked)
```ts
// WRONG: breaks under ESM caching
test('a', async () => {
  mock.module('fs', { namedExports: { readFileSync: () => 'x' } });
  const sut = await import('./sut.js'); // cached after test 1
});
test('b', async () => {
  mock.module('fs', { namedExports: { readFileSync: () => 'y' } });
  const sut = await import('./sut.js'); // same cached module → gets 'x', not 'y'
});
```

## Minimal runner fix (CI)
If package.json uses `tsx --test …`, change `test:unit` to:
```
node --import tsx --experimental-test-module-mocks --test "src/**/*.test.ts"
```
and add the same flag to `test:coverage`.

## Verification recipe
Run the suite with the gated runner and confirm 0 "mock.module is not a
function" and 0 "already mocked" errors:
## Verification recipe
Run the suite with the gated runner and confirm 0 "mock.module is not a
function", 0 "already mocked", and 0 "only a getter" errors:
```bash
node --import tsx --experimental-test-module-mocks --test "src/adapters/**/*.test.ts" 2>&1 \
  | grep -E "not ok|mock.module is not a function|already mocked|only a getter"
```
Also confirm no in-loop count regressions (`0 !== N`) — that symptom
means the ESM-cache trap (Footgun 2) is still in play: mocks are set
inside `test()`, so only test #1 got the mock.

## Pitfalls
- **tsx CJS transform FORBIDS top-level `await`.** If you write
  `const sut = await import('./sut.js')` at module top-level (the pattern in
  the RIGHT example above), tsx throws
  `Top-level await is currently not supported with the "cjs" output format`.
  Under tsx you CANNOT register the mock at top-level AND `await import` the
  SUT at top-level. Resolution: register `mock.module(spec, …)` at top-level
  (it's a synchronous call — fine), but do the `await import('./sut.js')`
  INSIDE each `test()` (after the mock is already registered). Because the
  mock was registered before any import of the SUT, the loader applies it.
  This is the ONE exception to "don't await import inside test()" — it is
  REQUIRED under tsx, and it works (the ESM-cache trap in Footgun 2 only
  bites when you re-register the mock, which you are not doing). Concrete
  working shape under tsx:
  ```ts
  import { test, mock } from 'node:test';
  mock.module('./video-analyzer.js', { namedExports: {
    analyzeDimensions: () => state.dims,   // reads mutable state
    detectBlackFrames: async () => [], detectFreezeFrames: async () => [],
    analyzeAudio: async () => state.audio,
  }});
  const state = { dims: { width: 1080, height: 1080, codec: 'h264' },
                 audio: { peakDb: -12, meanVolumeDb: -20, clipping: false } };
  test('X14 fails on wrong aspect', async () => {
    const { verifyRenderedVideo } = await import('./gate.js'); // import INSIDE test (tsx needs this)
    state.dims = { width: 720, height: 1280, codec: 'h264' };
    const r = await verifyRenderedVideo(tmpFile, 10, { expectedDimensions: { w: 1080, h: 1080 } });
    assert.strictEqual(r.checks.find(c => c.id === 'X14')!.pass, false);
  });
  ```
  Note: the code-under-test must IMPORT its dependency via ESM `import` (so
  `mock.module` intercepts it) — an inline `require('./dep')` inside the SUT
  will NOT be intercepted. If the SUT uses inline `require`, promote it to a
  top-level `import * as dep from './dep.js'` first (that edit also makes the
  test cleaner).
- **A function that only runs its checks when the file EXISTS still needs a
  real file in the test.** e.g. `verifyRenderedVideo(mp4)` only computes
  X10–X15 (dimensions, codec, black-frame, audio) when `fs.existsSync(mp4)`
  is true. Passing a fake path → the checks are never pushed →
  `r.checks.find(c => c.id === 'X14')` is `undefined` →
  `Cannot read properties of undefined (reading 'pass')`. In the test, write
  a tiny dummy file (e.g. `writeFileSync(tmp, 'dummy')`) before calling.
- **Don't trust the error location.** "mock.module is not a function" points at
  the call site but the real cause is the missing runner flag (Footgun 1).
- **Don't put `mock.module`/`await import` INSIDE `test()`.** Under ESM
  caching only test #1 gets the mock; later tests run against the real
  module. Mock ONCE at module top-level, import the SUT once, drive
  per-test values through mutable `let` state (see Footgun 2).
- **Broaden the `fs` mock or a transitively-imported `jobStore` breaks.**
  `mock.module('fs', { namedExports: {onlySome} })` REPLACES the whole
  `fs` module — any member the SUT's dependency graph uses (mkdirSync,
  statSync, readdirSync, rmSync, promises.*) becomes `undefined` and
  throws inside the SUT. Spread the real fs then override only what you
  control: `...realFs` + your overrides.
- **`mock.reset()` does NOT clear module mocks; `mock.resetModules()` does
  NOT exist on Node 22.x.** PROVEN empirically on Node v22.23.1:
  - `Object.getOwnPropertyNames(mock)` filtered to functions → `[]` (methods
    are non-enumerable, do not trust a `typeof` check).
  - `typeof mock.resetModules === 'undefined'` and `typeof mock.registry === 'undefined'`
    → there is NO per-process module-mock reset API.
  - `mock.reset()` only clears spies (`mock.fn`/`mock.method`); it does NOT
    free a `mock.module` registration.
  - `mock.restoreAll()` clears spies + module mocks for the NEXT import, but
    it does NOT permit re-calling `mock.module` for the same specifier.
  - Consequence: `afterEach(() => mock.reset())` → later tests hit the REAL
    module (mock silently gone). `afterEach(() => mock.restoreAll())` + a
    SECOND `mock.module('fs', …)` in a later test → throws
    `Invalid state: Cannot mock 'fs'. The module is already mocked.`
  - THE ONLY robust pattern: register each `mock.module(spec, …)` EXACTLY ONCE
    at module top-level and never re-register. Drive per-test variation
    through mutable `let` state the mock closures read at call time. Use
    `afterEach(() => mock.restoreAll())` + reset your mutable state. Do not
    rely on any "re-register the mock in each test" approach — it cannot work.
  - CLARIFICATION (the #1 misread): `mock.restoreAll()` "clears module mocks"
    means it clears them so the NEXT `import` of the SUT uses the REAL module
    again — it does NOT free the specifier for a second `mock.module` call.
    So `afterEach(restoreAll)` + `mock.module('fs', …)` INSIDE a later test
    throws `already mocked`. Never call `mock.module` inside a test. The mock
    closure reading mutable `let` state IS your per-test seam — not re-registration.
- **Windows path note:** ripgrep-based `search_files` can fail on MSYS-style
  paths like `/c/one/...`; fall back to `grep -rn` via the terminal in that
  environment.
- **mock.module does NOT intercept a real subprocess spawn.** If the SUT calls a
  backend that `spawn()`s an external process (e.g. a Python TTS server via
  `ensureBackend()`), mocking the *imported* module that wraps the spawn is
  insufficient — the spawn still fires (the real backend boots and logs). This
  was the actual outcome when mocking `speech-backend.js`'s `ensureBackend` to
  return `true` in a voice-stage test: the mock applied but the real Python
  process still spawned. For spawn-based integrations, PREFER a green `t.skip`
  when the backend isn't provisioned (keeps CI from going red) over a mock that
  won't reliably intercept the spawn. If you must mock, also stub the
  `child_process` `spawn`/`execFileSync` that actually launches the process,
  not just the wrapper module.
- **SUT must import the dep via ESM `import` for `mock.module` to intercept
  it — the #1 silent "mock didn't apply" cause.** If the SUT pulls the dep in
  with an INLINE `require('./dep')` (often inside a function body, e.g.
  `const ana = require('./video-analyzer.js')` at the top of a method),
  `mock.module('./dep.js', …)` does NOT patch that `require` binding on Node
  22 — the real module runs. Symptom: the test "passes" but for the WRONG
  reason — e.g. you mock `analyzeDimensions` to return a wrong size, the SUT
  calls the REAL analyzer on a non-existent file, the check throws, and
  `r.checks.find(c => c.id === 'X14')` is `undefined` →
  `Cannot read properties of undefined (reading 'pass')`. Fix: promote the
  inline `require` to a top-level `import * as dep from './dep.js'` in the
  SUT (this edit is also cleaner). This was the actual root cause of a
  `verifyRenderedVideo` X14 test failing-then-passing-then-failing across 4
  iterations until the `require` was found and converted. Decision tree when a
  mock "doesn't apply": (1) is the runner gated with
  `--experimental-test-module-mocks`? (2) was `mock.module` registered ONCE at
  top-level BEFORE any `import` of the SUT? (3) does the SUT load the dep via
  ESM `import` (not inline `require`)? (4) if the SUT only runs its checks
  when a file exists, did the test write a real dummy file? Miss any one → the
  mock is silently inert.
- **Two-stage import ordering under tsx: register mock at top-level, but ALSO
  register BEFORE a static `import` of the SUT.** If the test file has a
  static `import { runFinalGate } from './gate.js'` at the top, that import is
  hoisted and evaluated BEFORE your top-level `mock.module('./video-analyzer.js')`
  runs — so gate.js's static `import * as ana from './video-analyzer.js'` is
  already bound to the REAL analyzer before the mock is installed, and the
  mock never applies (even with `await import` inside the test). Fix: remove
  the static import of the SUT from the test file and load it via
  `await import('./gate.js')` inside each test, AFTER `mock.module` has run at
  top-level. This is distinct from the top-level-await-under-tsx ban (that's
  about `await import` at module top-level); here `mock.module(spec)` is a
  sync call at top-level (fine), and the `await import` happens inside the
  test (allowed). Verified pattern: `import { test, mock } from 'node:test';`
  then `mock.module('./video-analyzer.js', { namedExports: {…} });` at
  top-level, then inside each `test()` do `const { sut } = await import('./sut.js')`.
  (This is exactly the gate.test.ts / media-verifier.test.ts shape that passed.)

## User-preference note (diagnostic tasks)
For "diagnose + fix plan / report" tasks this user wants: evidence-backed
diagnosis (real command output, not assertions), the EXACT fix (file:line +
code), and NO edits / NO commits unless explicitly told. Deliver the report;
do not modify the repo. Prove fixes with throwaway probes in a scratch dir and
delete them.
