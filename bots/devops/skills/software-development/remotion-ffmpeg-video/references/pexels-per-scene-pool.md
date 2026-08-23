# Pexels per-scene image diversity — the WORKING fix

P25 described making `writeScriptHeuristic()` emit a distinct `[Visual:]` keyword
per scene. That is NECESSARY but NOT SUFFICIENT: every scene's keyword list still
contains the topic noun ("coffee"), and `fetchVisualsForScene` loops over
`individualQueries` trying the topic noun FIRST, so all 3 scenes returned the SAME
top Pexels photo (`27860686`). The keyword heuristic alone still yielded 3 identical
images.

## The mechanism that actually guarantees distinct photos

**Fetch ONE pool of ~12 photos for the topic ONCE, then assign scene `i` -> `pool[i]`.**

```ts
// orchestrate.ts, inside runAgenticPipeline (before acquireDeps)
const STOP = new Set(['a','an','the','of','for','to','and','or','in','on','with','about',
  'facts','fact','benefits','benefit','how','what','why','tips','ways','things',
  '5','3','10','top','best','amazing','fascinating','interesting','daily','changed','change','vs']);
const topicNoun = ((req.topic || plan.title || 'video') as string)
  .toLowerCase().split(/\s+/).filter((w) => w && !STOP.has(w.replace(/[^a-z]/g, ''))).join(' ')
  || 'video';
let sharedImagePool: { url: string }[] = [];
const getImagePool = async () => {
  if (sharedImagePool.length > 0) return sharedImagePool;
  const variants = [topicNoun, `${topicNoun} photo`, (req.title || '').trim(), `person ${topicNoun}`]
    .map((s) => s.trim()).filter(Boolean);
  for (const q of variants) {
    try {
      const pool = await searchImages(q, 12, 2, plan.orientation, 1);
      if (pool.length > 0) { sharedImagePool = pool.map((p) => ({ url: p.url })); break; }
    } catch { /* try next variant */ }
  }
  if (sharedImagePool.length === 0) {
    try { const res = await fetchVisualsForScene([topicNoun], false, plan.orientation);
      if (res) sharedImagePool = [{ url: res.url }]; } catch { /* ignore */ }
  }
  return sharedImagePool;
};
```

Then in `acquireDeps.fetchVisual(keywords, kind, orientation, sceneIndex = 0)`:

```ts
const pool = await getImagePool();
if (pool.length > 0) {
  const pick = pool[sceneIndex % pool.length];
  const DEAD_HOSTS = /flickr\.com|staticflickr\.com|live\.staticflickr/i;
  if (pick && pick.url && !DEAD_HOSTS.test(pick.url)) {
    return [{ url: pick.url, localPath: '', source: 'pexels',
      license: undefined, licenseUrl: undefined, width: 0, height: 0 }];
  }
}
// ...fall through to the keyword retry ladder (P25) as a secondary path
```

`sceneIndex` is passed by `acquire.ts` (`deps.fetchVisual(scene.searchKeywords, kind,
plan.orientation, i)` - `i` is the loop index). Add `sceneIndex?: number` to the
`AcquireDeps.fetchVisual` type.

`searchImages` must accept a `page` param (added: `searchImages(q, perPage=1,
retries=3, orientation='portrait', page=1)` and forward `page` into axios `params`).

## Proven result

Coffee topic: scene 0 -> `27860686`, scene 1 -> `31711944`, scene 2 -> `38466981`
(3 distinct real photos, all gates X7-X15 PASS). The shared-pool path is what made
this happen - the keyword diversity alone did not.

## The cache-poisoning trap (separate bug, same symptom)

The retry ladder's LAST-RESORT safe term was hardcoded `['coffee', ...]`. When a
non-coffee video (e.g. "walking") had an empty pool, the ladder fell to that term,
hit a STALE `.video-cache.json` entry `image:coffee:portrait -> 27860686`, and
served a coffee photo into the walking video. **Fix: make the last resort topic-aware:**

```ts
ladder.push([topicNoun || 'coffee', 'nature', 'city', 'technology'].slice(0, 1));
```

## `.video-cache.json` location GOTCHA

The cache is at the PROJECT ROOT (`.video-cache.json`), NOT in
`agentic-pipeline/cache`. Clearing the wrong directory wastes a whole session -
the stale coffee entry keeps poisoning every render. To force a fresh fetch:
`rm -f .video-cache.json` (from the repo root).

## Pexels data gaps are real (not a code bug)

Some topics return ZERO results for certain queries (e.g. "walking", "person
walking", "walking outdoors" all returned EMPTY via the API this session). When the
pool is empty for a topic, the pipeline correctly falls back to BRIGHT placeholder
cards (P23) - never black, never off-topic. Don't try to "fix" Pexels; the fallback
is the right behavior. Verify with a direct curl:
```bash
KEY="<key>"
curl -s "https://api.pexels.com/v1/search?query=walking&per_page=3&orientation=portrait" \
  -H "Authorization: $KEY" | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const j=JSON.parse(d);console.log((j.photos||[]).map(p=>p.id).join(', ')||'EMPTY')})"
```

## Visual verification: use blackdetect, not signalstats-on-PNG

`signalstats ... metadata=print:key=lavfi.signalstats.YAVG` on a still PNG frame
emits NOTHING - it only works on a video stream. The reliable offline check is the
same one X10 uses:
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
"$FFMPEG" -i render/<job>.mp4 -vf "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep -i black_start
# no "black_start" line => non-black => visually valid
```
This is sufficient evidence that per-scene images rendered (no empty/black scenes).
