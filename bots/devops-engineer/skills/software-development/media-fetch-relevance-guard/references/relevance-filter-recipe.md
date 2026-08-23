# Relevance Filter Recipe (copy-paste)

Two pieces: provider-domain gating (`shouldQuery`) and the `isOnTopic` relevance gate. Apply to BOTH an image adapter and a video adapter (they must stay consistent).

## 1. Provider-domain gating
General libraries (Wikimedia, Internet Archive) always queried. Domain-specific (NASA=space, MetMuseum=art) only when the keyword is in-domain.

```ts
private shouldQuery(provider: 'wiki' | 'archive' | 'nasa' | 'met', keyword: string): boolean {
    if (provider === 'wiki' || provider === 'archive') return true;
    const k = keyword.trim().toLowerCase();
    if (provider === 'nasa') {
        return /space|nasa|galaxy|nebula|star|planet|cosmo|astronom|moon|earth|satellite|telescope|comet|asteroid|universe|milky/.test(k);
    }
    if (provider === 'met') {
        return /museum|art|painting|sculpture|met|renaissance|portrait|exhibit|artifact/.test(k);
    }
    return false;
}
```

## 2. isOnTopic (image + video — identical logic)

```ts
private static isOnTopic(keyword: string, title: string): boolean {
    const k = keyword.trim().toLowerCase();
    if (!k) return true;
    const generic = ['nature', 'city', 'background', 'texture', 'abstract', 'b roll', 'b-roll'];
    if (generic.includes(k)) return true;
    const t = (title || '').toLowerCase();

    // Compound nouns sharing a token but OFF-TOPIC.
    const offTopicCompounds: Record<string, RegExp> = {
        lion: /(stone\s+lion|sea\s+lion|lion\s+king|lioness|lion's|lions'\s|mountain\s+lion|city\s+lion|lion\s+dance)/,
        cat: /(lion|tiger|bear|wildcat|cat\s+statue)/,
        dog: /(hot\s+dog|dog\s+statue|sea\s+dog)/,
        bear: /(teddy\s+bear|grizzly)/,
    };
    // Brand / commercial leakage (e.g. "LION" the detergent brand, Japanese TV ads).
    const commercialTokens = /\b(cm|commercial|advert|detergent|shampoo|soap|brand|mylink|ナテラ|広告|商品|公式)\b|ライオン/;
    if (commercialTokens.test(t)) return false;
    // Non-Latin title for a Latin query => foreign brand/media clip, not the topic.
    const isLatinQuery = /^[\x00-\x7F]+$/.test(k);
    const nonLatinRatio =
        (t.match(/[぀-ヿ一-鿿]/g) || []).length / Math.max(1, t.replace(/\s/g, '').length);
    if (isLatinQuery && nonLatinRatio > 0.3) return false;

    for (const tok of k.split(/\s+/).filter((x) => x.length >= 3)) {
        if (offTopicCompounds[tok] && offTopicCompounds[tok].test(t)) return false;
        const re = new RegExp(`\\b${tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
        if (re.test(t)) return true;
    }
    return false;
}
```

## 3. Relevance-first ranking (not resolution-first)
```ts
const sorted = all.sort((a, b) => {
    const aOn = isOnTopic(keyword, a.title) ? 1 : 0;
    const bOn = isOnTopic(keyword, b.title) ? 1 : 0;
    if (aOn !== bOn) return bOn - aOn;            // on-topic first
    const aRes = a.resolution ? parseInt(a.resolution.split('x')[1] ?? '0', 10) : 0;
    const bRes = b.resolution ? parseInt(b.resolution.split('x')[1] ?? '0', 10) : 0;
    return bRes - aRes;                            // then resolution
});
```

## 4. Apply in every path
- `searchAll`: `res.value.filter((r) => isOnTopic(keyword, r.title))` before pushing each provider's results.
- `searchBest` / `searchAndDownloadFirst`: sort by on-topic-first.
- Legacy `fetchVisualsForScene`-style fallback that calls `provider.search()` directly: RE-ROUTE through `adapter.searchAll()` so the gate is not bypassed.
