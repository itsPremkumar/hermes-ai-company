# GitHub-Pages Site-Farm + Autonomous Daily Self-Improve Loop (JS variant)

A proven variant of the automated-content-site pattern, built from
`itsPremkumar/website-automation-public`. Differs from the stdlib-Python
single-money-site model: it's a **multi-site farm** (one template -> many
branded static sites) with a **Hermes-style daily loop** that improves the
code/SEO itself -- not just publishes articles.

## Architecture (repo shape)
```
website-automation/
├─ sites/
│  └─ common-website-template/     # master template (copy per site)
│     ├─ index.html / post.html / payment.html / 404.html
│     ├─ site-config.json           # name, description, url, monetagZone
│     ├─ input-data.json           # blog posts (array)
│     ├─ robots.txt / sitemap.xml
│     └─ assets/{css,js}/
├─ lib/
│  ├─ inject.js     # fill SEO/Monetag placeholders from site-config
│  ├─ measure.js   # collect real signals (live, stars, posts, meta, jsonld, sitemap, cssKb)
│  ├─ improve.js   # RULES engine: pick ONE weak signal, make ONE reversible change
│  └─ content.js   # template-based ORIGINAL 800+word post generator
├─ deploy-single-site.js / deploy-empire-repos.js / bot-deploy.js  # GitHub Pages push
├─ self-improve.js # the daily loop: measure->decide->improve->deploy->verify->log
├─ niches.js        # list of sites to build/deploy
├─ .env.example    # GITHUB_USERNAME / GITHUB_TOKEN placeholders (real .env git-ignored)
└─ cron.example     # 7 3 * * *  node self-improve.js >> logs/loop.log 2>&1
```

## The self-improve loop invariant (the key idea)
Exactly **ONE reversible change per run**, logged to each site's
`IMPROVEMENT_LOG.md`. This mirrors the Hermes daily-loop discipline:
measure -> decide the single weakest signal -> improve -> deploy -> verify.
Never big-bang rewrite. Every change is a small git-committed edit, so
`git revert` recovers.

### RULES engine (`lib/improve.js`) -- order = priority
1. `no-posts` (posts===0) -> run content generator
2. `thin-content` (posts<5) -> add 5+ original posts
3. `empty-title` -> fill `<title>` from site-config
4. `empty-desc` -> fill meta description
5. `no-jsonld` -> inject JSON-LD structured data
6. `no-sitemap` -> write valid sitemap.xml
7. `css-bloat` (>30KB) -> flag minify

Each rule: `test(m)` predicate + `apply(sitePath)` mutator. Add new
rules by appending to the `RULES` array -- no other code change.

### Measure (`lib/measure.js`)
- Local audit: post count, empty title/desc, JSON-LD present, sitemap
  valid, CSS size. Pure fs, no secrets.
- Public signals: live reachability (https GET), GitHub stars (API,
  degrades gracefully without token). `live:false` is OK locally.
- Returns a plain object the rules engine consumes.

### Content generator (`lib/content.js`)
- Template-based ORIGINAL posts (NOT spun/duplicate) -- avoids the
  "low-value content" AdSense trap that hit sproutern.
- `genPost(topic, idx)` builds an outline (intro/why/core/steps/mistakes/
  tools/conclusion) -> 800+ words. Writes `input-data.json`.
- Run: `node lib/content.js <slug> [count]`.

## Deploy path (GitHub Pages, free)
- `deploy-single-site.js`: git init in site folder -> commit -> create repo
  via REST (`POST /user/repos`) -> push -> `POST /repos/{u}/{r}/pages`
  to enable GitHub Pages. Uses embedded `https://user:token@...` URL.
- Token from `.env` (git-ignored). **No token -> loop applies the change
  locally + logs, skips deploy.** CRITICAL: the template's `deploySingle`
  calls `console.error('GITHUB_TOKEN… missing')` but does NOT throw — so if you
  call it unconditionally the loop prints a misleading `❌ Error` yet still logs
  "deployed". Guard the deploy yourself:
  `if(!token||!username){ skip } else { await deploySingle(…) }`.
- **Cross-link to the canonical company repo:** after pushing the sanitized public
  repo, add a sample-reference doc into `Hermes-Full-Autonomous-Company/revenue/`
  (same Contents-API PUT, resolve `default_branch` first — it's `master` there) describing
  this project as "another complete website template" for the money stack, and link
  back from the public README. This is the pattern for making an open-source project a
  citable building block of the canonical company repo.

## Cron (hands-off)
`cron.example` -> `7 3 * * *` (odd minute avoids :00 stampede).
On Windows the cron host may lack `/bin/bash`; the loop is plain Node,
no shell wrappers, so it runs fine.

## Security gotchas (see sanitize-private-to-public for full detail)
- Real token must NEVER be committed. `.env` git-ignored; `.env.example`
  placeholders only.
- Third-party ad/zone IDs (e.g. `10403494`) are LEAKAGE too -- replace
  with `YOUR_MONETAG_ZONE_ID` placeholder, fill per-site via `lib/inject.js`.
  Grep ALL html incl. `404.html` -- missing one file = real leak.
- Raw-CDN cache after force-push lies; verify via API blob decode.

## Honest scope
The loop makes the *system* better over time (more content, valid sitemaps,
structured data). It does NOT manufacture traffic or ad approval -- those
stay human/algorithmic gates. State that plainly in any README.

## Tooling pitfall (write_file/patch lint false-positive)
When the `write_file` / `patch` tools report
`Cannot find module 'C:\c\one\...'` with exit on a `.js` edit, it is a
FALSE POSITIVE -- the linter resolves the MSYS path wrong (`C:\c\one\...`
instead of `C:\one\...`). Verify with a real `node --check` on the actual
native path; do NOT burn turns "fixing" a file that already parses.
The `npm test` script (`node --check` on every script) is the real gate.
