# Deterministic network mocking for `node:test` (axios-based media fetchers)

Pattern used to add the first tests to an untested Openverse/Pexels fetcher without
hitting the network. Keeps CI green and deterministic.

## Module under test (existing shape — do NOT change its API)
```ts
// openverse-fetcher.ts
import axios from 'axios';
export async function searchOpenverseImages(query: string, count = 5) {
  const { data } = await axios.get('https://api.openverse.engineering/v1/images/', {
    params: { q: query, page: 1, page_size: Math.min(count, 50) },
    headers: { 'User-Agent': UA }, timeout: 15000,
  });
  return data.results.map((r: any) => ({ type: 'image', url: r.url,
    width: r.width || 0, height: r.height || 0, photographer: r.creator || undefined }));
}
```

## Test seam — override the singleton, restore after each
```ts
import assert from 'node:assert/strict';
import test from 'node:test';
import axios from 'axios';
import { searchOpenverseImages } from './openverse-fetcher';

const realGet = axios.get;
const stubGet = (impl: (url: string, cfg: any) => any) =>
  (axios.get as unknown) = (url: string, cfg: any) => Promise.resolve(impl(url, cfg));
const restoreGet = () => (axios.get as unknown) = realGet;

test.afterEach(() => restoreGet());

test('maps Openverse results to MediaAsset[]', async () => {
  stubGet((_u, _c) => ({ data: { result_count: 1,
    results: [{ id:'1', title:'t', url:'https://x/y.jpg', thumbnail:'', creator:'Jane',
      license:'CC0', license_version:'1.0', license_url:'', attribution:'', width:4000, height:3000 }] } }));
  const a = await searchOpenverseImages('sunset', 5);
  assert.equal(a.length, 1);
  assert.equal(a[0].photographer, 'Jane');
});
```

## Why this shape
- `axios.get` is a singleton — overriding it on the module you import is enough;
  no DI refactor needed for a first-pass test.
- Stub returns a resolved `{ data }` shaped exactly like the real endpoint. Add a
  test that rejects (set `err.code = 'ECONNREFUSED'`) to assert error propagation.
- Never call the real endpoint from a test. `npm test` must run offline/CI-clean.

## Run gate
```bash
npx tsx --test "src/lib/openverse-fetcher.test.ts"
npm test            # typecheck + full unit
prettier --check "src/lib/openverse-fetcher.test.ts" "src/lib/openverse-fetcher.ts"
```

## Bonus: export-private-helpers trick
To test pure helpers that were `const`-scoped inside a module, change
`const foo = (...)` → `export const foo = (...)` (non-breaking) and import in the
test. This surfaced a real latent bug: a keyword normalizer deduped case-sensitively
(`"Sunset"`≠`"sunset"` → two distinct stock-search queries). Fix: dedup via a
`seenLower = new Set<string>()` while preserving first-seen casing.
