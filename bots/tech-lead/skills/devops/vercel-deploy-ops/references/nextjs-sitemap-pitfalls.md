# Next.js Sitemap Pitfalls (Vercel Deploy)

## Symptom
Google Search Console shows `sitemap.xml` with status "1 error" and 0 discovered pages, even though static `public/sitemap.xml` has hundreds of URLs. Or `sitemap-news/sitemap.xml` has 0 URLs.

## Root Cause A: Dynamic sitemap shadows static one
Next.js generates a dynamic sitemap at `src/app/sitemap.ts` → served at `/sitemap.xml`. This **shadows** the static `public/sitemap.xml`. If the dynamic sitemap fails (Firebase error, `shouldIndexPath` filter, empty filter), Google sees an empty sitemap.

**Fix:** Make `src/app/sitemap.ts` a sitemap **index** that references all working static sub-sitemaps:
```ts
import { MetadataRoute } from 'next';
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://your-domain.com';
  const lastmod = new Date().toISOString();
  return [
    { url: `${baseUrl}/sitemap-static.xml`, lastModified: lastmod, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${baseUrl}/sitemap-blog.xml`, lastModified: lastmod, changeFrequency: 'daily', priority: 0.9 },
    // ... all sub-sitemaps
  ];
}
```

## Root Cause B: News sitemap 48-hour filter
Google News sitemap (`sitemap-news/sitemap.ts`) often filters to posts within last 48 hours. If no posts published recently, sitemap is empty → GSC error.

**Fix:** Remove the 48-hour filter. Always return latest 100 posts sorted by date:
```ts
const latestPosts = allPosts
  .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  .slice(0, 100);
```

## Root Cause C: Stale lastmod dates
All sitemap XML files have `lastmod` from months ago (e.g. Dec 2025). Google thinks content is stale, deprioritizes crawling.

**Fix:** Update all `public/sitemap-*.xml` files with current date:
```python
import re, os, glob
from datetime import datetime
date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
for f in glob.glob('public/sitemap*.xml'):
    content = open(f).read()
    content = re.sub(r'<lastmod>.*?</lastmod>', f'<lastmod>{date}</date>', content)
    open(f, 'w').write(content)
```

## Root Cause D: site-config SITE_URL missing protocol
`site-config.ts` uses `NEXT_PUBLIC_VERCEL_URL` which is just the hostname (e.g. `sproutern.vercel.app`). `new URL('sproutern.vercel.app')` throws `ERR_INVALID_URL`.

**Fix:** Add `https://` prefix:
```ts
export const SITE_URL: string = (
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.NEXT_PUBLIC_VERCEL_URL ? `https://${process.env.NEXT_PUBLIC_VERCEL_URL}` : '') ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000')
).replace(/\/$/, '');
```

## Root Cause E: Hardcoded domain in metadata/schema
`layout.tsx` or `seo-head.tsx` hardcodes `https://domain.com` instead of using `SITE_URL`. Breaks on preview deployments, different domains.

**Fix:** Always import and use `SITE_URL` from site-config.

## Verification
```bash
curl -s https://your-domain.com/sitemap.xml | grep -c '<url>'  # Should be >0
curl -s https://your-domain.com/sitemap-news/sitemap.xml | grep -c '<url>'  # Should be >0
curl -sI https://your-domain.com/ | head -1  # HTTP 200
```

## Real case
Sproutern (2026-08-16): 486 pages indexed but only 3 clicks. Caused by empty dynamic sitemap + empty news sitemap + stale dates. After fix: GSC errors cleared, sitemaps show all URLs.
