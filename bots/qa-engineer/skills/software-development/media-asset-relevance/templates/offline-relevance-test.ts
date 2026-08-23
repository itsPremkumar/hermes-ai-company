// OFFLINE deterministic relevance test — copy + adapt. No network; runs in CI.
// Proves a generic query returns ON-TOPIC assets and EXCLUDES off-topic
// domain providers (NASA space / MetMuseum art) + off-topic compounds.
import assert from 'node:assert/strict';
import test from 'node:test';
import { FreeImageAdapter } from '../../src/lib/free-image/adapter.js';

function fakeResults(titles: string[]) {
  return titles.map((title, i) => ({
    id: `fake-${i}`, title, creator: 'tester', license: 'PD', licenseUrl: '',
    provider: 'fake', downloadUrl: `https://example.com/${i}.jpg`,
    thumbnailUrl: null, width: 1920, height: 1080, fileSizeBytes: 1000, sourcePageUrl: '',
  }));
}

test('OFFLINE: "<topic>" excludes NASA space photos and MetMuseum art', async () => {
  const adapter = new FreeImageAdapter() as any;
  adapter.wiki = { name: 'wikimedia', search: async () => fakeResults(['Lion (Panthera leo) resting', 'Stone lion statue (off-topic)']) };
  adapter.archive = { name: 'archive', search: async () => fakeResults(['Male lion portrait', 'Lion King poster (off-topic)']) };
  // NASA/MET MUST NOT be queried for a generic query — throw if they are:
  adapter.nasa = { name: 'nasa', search: async () => { throw new Error('NASA must NOT be queried for "lion"'); } };
  adapter.met = { name: 'met', search: async () => { throw new Error('MetMuseum must NOT be queried for "lion"'); } };

  const all = await adapter.searchAll('lion', { count: 10 });
  const sources = all.map((s: any) => s.source);
  assert.ok(!sources.includes('nasa'), 'NASA excluded for generic "lion"');
  assert.ok(!sources.includes('metmuseum'), 'MetMuseum excluded for generic "lion"');
  const titles = all.flatMap((s: any) => s.results.map((r: any) => r.title));
  assert.ok(!titles.some((t: string) => /stone lion|lion king/i.test(t)), 'off-topic compounds filtered');
  assert.ok(titles.some((t: string) => /lion/i.test(t)), 'on-topic assets present');
});

test('OFFLINE: "<topic>" searchBest ranks a REAL asset first', async () => {
  const adapter = new FreeImageAdapter() as any;
  adapter.wiki = { name: 'wikimedia', search: async () => fakeResults(['Lion (Panthera leo) resting', 'Stone lion statue (off-topic)']) };
  adapter.archive = { name: 'archive', search: async () => fakeResults(['Male lion portrait', 'Lion King poster (off-topic)']) };
  adapter.nasa = { name: 'nasa', search: async () => fakeResults(['Lion nebula in infrared (OFF-TOPIC)']) };
  adapter.met = { name: 'met', search: async () => fakeResults(['Sea lion sculpture (OFF-TOPIC)']) };

  const best = await adapter.searchBest('lion', { count: 10 });
  assert.ok(best !== null, 'should return a result');
  assert.ok(/lion/i.test(best.title) && !/nebula|stone lion|lion king|sea lion/i.test(best.title),
    `top hit must be on-topic, got: "${best.title}"`);
});

test('OFFLINE: space query still includes NASA', async () => {
  const adapter = new FreeImageAdapter() as any;
  adapter.wiki = { name: 'wikimedia', search: async () => [] };
  adapter.archive = { name: 'archive', search: async () => [] };
  adapter.nasa = { name: 'nasa', search: async () => fakeResults(['Lion nebula', 'Spiral galaxy']) };
  adapter.met = { name: 'met', search: async () => [] };
  const all = await adapter.searchAll('galaxy nebula', { count: 10 });
  assert.ok(all.some((s: any) => s.source === 'nasa'), 'NASA INCLUDED for space query');
});
