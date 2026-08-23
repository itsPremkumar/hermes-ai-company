# Offline Test Pattern (CI-safe, no network)

Media providers hit the network. Unit tests must run offline + deterministically in CI. Monkeypatch the provider objects after construction, then assert on the filtered titles.

## Skeleton (video adapter example)
```ts
import assert from 'node:assert/strict';
import test from 'node:test';
import { FreeVideoAdapter } from './adapter.js';

function fakeVideos(titles: string[]) {
    return titles.map((title, i) => ({
        id: `fake-${i}`, title, creator: 'tester', license: 'PD', licenseUrl: '',
        provider: 'fake', downloadUrl: `https://example.com/${i}.mp4`,
        thumbnailUrl: null, durationSeconds: 10, resolution: '1920x1080',
        fileSizeBytes: 5000000, format: 'mp4', sourcePageUrl: '',
    }));
}

test('OFFLINE video: "lion" rejects Japanese brand commercials (ライオン ナテラ)', async () => {
    const adapter = new FreeVideoAdapter() as any;
    adapter.archive = { name: 'archive', search: async () =>
        fakeVideos(['ライオン ナテラ 篠ひろ子 懐かCM 1993年11月 LION', 'Lion MyLink startup animation', 'LION detergent commercial']) };
    adapter.wiki = { name: 'wikimedia', search: async () => fakeVideos(['Male lion resting in savanna']) };

    const all = await adapter.searchAll('lion', { count: 10 });
    const titles = all.flatMap((s: any) => s.results.map((r: any) => r.title));
    assert.ok(titles.length >= 1, 'at least the real lion video remains');
    assert.ok(!titles.some((t: string) => /ライオン|ナテラ|mylink|detergent|cm|commercial/i.test(t)), 'brand clips filtered');
    assert.ok(titles.some((t: string) => /lion/i.test(t) && !/ナテラ|mylink/i.test(t)), 'real lion video present');
});
```

## Network tests: skip, don't fail
Wrap any test that hits a real host so CI never flakes:
```ts
async function skipIfUnreachable(host: string, t: TestContext, timeoutMs = 4000) {
    try {
        const c = new AbortController();
        const to = setTimeout(() => c.abort(), timeoutMs);
        const r = await fetch(host, { method: 'HEAD', signal: c.signal });
        clearTimeout(to);
        if (!r.ok && r.status >= 500) throw new Error('5xx');
    } catch {
        t.skip(`host unreachable: ${host}`);
        return;
    }
    if (process.env.CI === 'true') { t.skip('network test skipped in CI'); return; }
}
```
- Use ONLY for tests that MUST touch the network (real provider smoke tests).
- Tests that exercise logic (relevance filter, ranking) must be OFFLINE (monkeypatched) so they always run.

## Acceptance for a fix
At least one OFFLINE test per off-topic class you claim to fix (compound, brand/commercial, non-Latin). Plus a REAL end-to-end download (separate script, run manually) confirming filenames/titles are on-topic and ffprobe/file says valid.
