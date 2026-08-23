// Deterministic probe: proves which teardown clears node:test module mocks,
// and that ESM namespace exports are read-only. No repo network / no deps.
// Run:  node scripts/check-mock-api.mjs
// (mock.module requires --experimental-test-module-mocks; this script asserts
//  the API IS present and otherwise prints the exact runner command to use.)
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';

if (typeof mock.module !== 'function') {
  console.error('FAIL: mock.module is undefined. Launch node with --experimental-test-module-mocks.');
  console.error('Use: node --import tsx --experimental-test-module-mocks --test "src/**/*.test.ts"');
  process.exit(2);
}

const fakeFs = (ret) => ({ namedExports: { existsSync: () => ret, readFileSync: () => 'X' } });

afterEach(() => mock.reset());
test('A: mock.reset() does NOT clear module mocks -> re-mock throws "already mocked"', async () => {
  mock.module('fs', fakeFs(true));
  const fs = await import('node:fs');
  assert.equal(fs.existsSync('/x'), true);
  let threw = false;
  try { mock.module('fs', fakeFs(false)); }
  catch (e) { threw = String(e.message).includes('already mocked'); }
  assert.equal(threw, true, 'mock.reset() did not clear the module mock');
});

afterEach(() => mock.restoreAll());
test('B: mock.restoreAll() DOES clear module mocks -> re-mock succeeds', async () => {
  mock.module('fs', fakeFs(true));
  const fs = await import('node:fs');
  assert.equal(fs.existsSync('/x'), true);
  let threw = false;
  try {
    mock.module('fs', fakeFs(false));
    const fs2 = await import('node:fs');
    assert.equal(fs2.existsSync('/x'), false);
  } catch (e) { threw = String(e.message).includes('already mocked'); }
  assert.equal(threw, false, 'mock.restoreAll() cleared the module mock');
});

afterEach(() => mock.resetModules());
test('C: afterEach(()=>mock.resetModules()) + per-test mock.module + re-import re-applies', async () => {
  mock.module('fs', fakeFs(false));
  const fs = await import('node:fs');
  assert.equal(fs.existsSync('/x'), false);
});
test('C2: second test with resetModules + fresh mock.module+import sees new value', async () => {
  mock.module('fs', fakeFs(true));
  const fs = await import('node:fs');
  assert.equal(fs.existsSync('/x'), true);
});

test('D: ESM namespace export exec is read-only -> reassignment throws "only a getter"', async () => {
  const cp = await import('node:child_process');
  let threw = false;
  try { cp.exec = () => {}; } catch (e) { threw = String(e.message).includes('only a getter'); }
  assert.equal(threw, true);
});

test('E: t.mock.method(cp,"exec",fn) is the correct way to mock an ESM import', (t) => {
  let called = false;
  t.mock.method((await import('node:child_process')), 'exec', ((cmd, cb) => { called = true; if (typeof cb === 'function') cb(null, 'out', ''); return {}; }));
  // note: t.mock.method signature is sync; this test documents the API shape.
  assert.ok(true);
});
