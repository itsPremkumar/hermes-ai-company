# Post-Migration Traffic Recovery — Case Study & Methodology

Case study: sproutern.com → sproutern.dpdns.org (August 2026)

## Diagnostic methodology (run in order)

1. **Verify new domain is live.** Crawl homepage + deep pages + key assets.
   Confirm HTTP 200 + correct HTML. (Jina Reader works for zero-config page
   reading via `curl -s "https://r.jina.ai/https://new-domain.org"`)

2. **Check SEO infrastructure endpoints** on the new domain:
   - `robots.txt` — should Allow all public paths, list Sitemap directive
   - `sitemap.xml` — MUST contain actual `<url>` entries; empty `<urlset>` is
     the #1 silent killer (Google discovers nothing)
   - `sitemap-index.xml`, `sitemap-news.xml`, image sitemaps if they exist
   - `llms.txt` — AI-context files (if used)

3. **Check search engine indexation.** Search `site:new-domain.org` and
   `site:old-domain.com` on both Google and DuckDuckGo:
   - Old domain returning results + new domain returning ZERO = indexation gap
   - Old domain pages dead (connection error, SSL fail) = stranded link equity
   - Use Jina Reader + DuckDuckGo HTML for reliable zero-config searching

4. **Compare HTTP headers** between old and new:
   - `Strict-Transport-Security`, `X-Robots-Tag`, canonical `<link>` tags
   - Confirm new domain is not accidentally `noindex`

5. **Audit the sitemap content.** Pull `sitemap.xml` and count `<url>` entries
   vs actual pages. A site with 282 blog posts + 90 tools should have hundreds
   of URLs in the sitemap, not zero.

6. **Check redirect status.** Old domain should 301-redirect to new domain
   path-by-path. If the old domain is fully dead with no redirect, all
   backlinks and bookmarks are lost.

## Common root causes (ranked by impact)

| Priority | Root cause | Why it kills traffic |
|---|---|---|
| P0 | Empty sitemap.xml | Google has no crawl list |
| P0 | No 301 redirects from old domain | All backlinks/bookmarks dead |
| P0 | New domain not indexed at all | Invisible to search |
| P1 | No Google Search Console on new domain | No sitemap submission, no monitoring |
| P1 | Free/dynamic DNS domain (e.g. `.dpdns.org`) | Flagged as disposable, lower trust |
| P1 | Canonical tags still point to old domain | Google thinks old domain is authoritative |
| P2 | Backlinks stranded on old domain | Lost link equity |
| P2 | `noindex` accidentally left in headers | Pages excluded from index |

## Recovery plan (execute by priority)

1. **Fix sitemap.xml** — dynamically generate from data source in
   `app/sitemap.ts` (Next.js App Router). Must include all blog posts, tools,
   games, static pages. Verify it returns real `<url>` entries.

2. **Set up Google Search Console** — add new domain property, verify via DNS
   TXT or meta tag, submit sitemap. Monitor weekly for index count.

3. **Request indexing** — GSC URL Inspection → "Request Indexing" for homepage,
   top tools, top blog posts. Submit to Bing Webmaster Tools too.

4. **Verify canonical tags** — every page should have
   `<link rel="canonical" href="https://new-domain.org{path}" />`.

5. **Restore old domain redirects** — if recoverable, point old domain anywhere
   and 301-redirect path-by-path to new domain to pass link equity.

6. **Rebuild backlinks** — find who links to old domain (search `site:old-domain`),
   ask them to update to new domain. Update social profiles, GitHub, LinkedIn.

7. **Consider a proper domain** — free dynamic DNS domains carry SEO stigma.
   A `.in` / `.org` / `.dev` domain (~$10-15/yr) is more credible. Point it at
   Vercel, 301 the free domain to it.

8. **Fresh content + social signals** — publish new posts, share on socials to
   build crawl priority while waiting for indexation.

## Verification after recovery

- Re-check `site:new-domain.org` weekly — should grow from 0 to full count
- Monitor GSC "Pages" report for indexed count trending up
- Monitor GSC "Performance" for impressions/clicks returning
- Re-crawl sitemap.xml after any content update to confirm it's still populated

## Specific findings from sproutern.com → sproutern.dpdns.org (Aug 2026)

| Finding | Detail |
|---|---|
| Old domain status | Dead — `ERR_CONNECTION_CLOSED`, DNS → old hosting |
| New domain status | Live on Vercel, HTTP 200, serves correctly |
| Sitemap.xml | EMPTY — `<urlset>` with zero `<url>` entries |
| robots.txt | Proper, allows all key paths, lists sitemap directives |
| llms.txt | Present, AI-ready |
| Indexation gap | `site:sproutern.dpdns.org` = ZERO results; `site:sproutern.com` = ~10 dead pages still indexed |
| Key issue | 282 blog posts + 90+ tools + 88 games completely undiscoverable |

## Why this matters

A domain migration is not complete when the code is live. Without:
- A populated sitemap.xml
- 301 redirects from old domain
- Google Search Console setup + sitemap submission
- Canonical tags pointing to new domain

...the new domain is invisible to search engines regardless of content quality.
The recovery window is weeks to months — every day without a sitemap is a day
Google cannot discover or rank your pages.
