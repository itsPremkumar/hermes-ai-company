---
name: domain-migration-ops
description: Use when migrating a site's domain across a codebase.
---

# Domain Migration Ops

Safely rebase a whole site from `old-domain.com` → `new-domain.org` across
~hundreds of files, then verify and register in GSC. Verified end-to-end
2026-08-04 on sproutern-hermes (408 files, ~3,100 references, 188/188 SEO
tests green). The technique is the ORDERING + EXCLUSIONS; blind find-replace
corrupts emails and external paths.

## Workflow

1. **Find the source-of-truth config first.** Look for `src/lib/site-config.ts`
   / `src/lib/seo/site-config.ts` style constants (`SITE_URL`, `SEO_SITE_URL`)
   and patch them — other code usually derives from them. Then grep to find
   every other hardcoded occurrence: `grep -rn "old-domain\.com" . | grep -v
   node_modules | grep -v "\.next" | grep -v "\.git/"`.
2. **Survey special contexts BEFORE replacing** (decide what must NOT change):
   - **Email addresses** (`support@old-domain.com`, `mailto:` links) — these
     are mailboxes, not web URLs. Keep them unless the user has the new mailbox.
   - **External-account path segments** — e.g. `srv.adstxtmanager.com/ACCOUNT/sproutern.com`
     is an ad-account ID, not the site URL. Leave it, flag to user.
   - **Brand-text mentions** (`Sproutern.com` capitalized in prose, JSON-LD
     alternateName, sitemap XML comments) — replace for consistency, but in a
     SEPARATE pass from URL replacements.
3. **Ordered replacement — longest/most-specific patterns first** so earlier
   passes never re-match what later passes produce. Use `perl -pi` over a
   file list from `grep -rl`:
   ```bash
   FILES=$(grep -rl "old-domain\.com" . 2>/dev/null | grep -v node_modules | grep -v "\.next" | grep -v "\.git/")
   for f in $FILES; do
     perl -pi -e 's{https://www\.old-domain\.com}{https://new-domain.org}g' "$f"
     perl -pi -e 's{http://www\.old-domain\.com}{https://new-domain.org}g' "$f"
     perl -pi -e 's{https://old-domain\.com}{https://new-domain.org}g' "$f"
     perl -pi -e 's{http://old-domain\.com}{https://new-domain.org}g' "$f"
     perl -pi -e 's{www\.old-domain\.com}{new-domain.org}g' "$f"
     perl -pi -e 's{(?<!@)old-domain\.com}{new-domain.org}g' "$f"   # (?<!@) protects emails
   done
   ```
   Order matters: `www.` forms before bare, `https://` before bare `www.`,
   and the bare domain LAST with a `(?<!@)` negative lookbehind so
   `support@old-domain.com` survives.
4. **Capitalized/brand pass separately** (case-sensitive grep misses it):
   `grep -rn "Old-Domain\.com"` → replace to `New-Domain.org`. Do NOT touch
   JSON-LD `alternateName` if you want the old brand name kept as an alias.
5. **Manual logic files need human edits, not blind replace:**
   - `src/proxy.ts` / middleware hostname-canonicalization: after replace the
     old `www` + bare host check collapses into two identical conditions —
     simplify to one, and drop the `www` variant since new domains often have
     none. Verify redirect logic still canonicalizes correctly.
   - `cors.json` origins, `apphosting.yaml` env, `package.json` homepage +
     audit/lighthouse script URLs, `vercel.json`, `firebase-admin-messaging.ts`
     baseUrl fallbacks, prefetch hooks' `a[href^="..."]` selectors.
   - `.github/FUNDING.yml` + workflow ping URLs (often in comments).
6. **Regenerate/update SEO artifacts:** `public/sitemap-*.xml` (all `<loc>`),
   `robots.txt`, `llms.txt`/`llms-full.txt`, `humans.txt`, feed route
   (`src/app/feed.xml/route.ts`), OG-image generator watermark text,
   IndexNow/sitemap-generator scripts (`const DOMAIN = ...`).
7. **Update test assertions** that hardcode the old domain (`src/__tests__/`).

## Verification (empirical, in order)

```bash
# a) Remaining old domain: ONLY emails should survive
grep -rn "old-domain\.com" . | grep -v node_modules | grep -v "\.next" | grep -v "\.git/" | grep -v "@old-domain\.com" | grep -v "mailto:"
# b) Corruption check — no double-domain from overlapping replaces
grep -rn "new-domain\.org.*new-domain\.org" . | grep -v node_modules
# c) Count new-domain refs and sanity-check sitemap <loc>s all point to it
grep -rhoE "https://[a-z.]*new-domain[a-z.]*" public/sitemap-*.xml | sort | uniq -c
# d) Typecheck + SEO test suite. Confirm ANY pre-existing errors are NOT yours:
#    git stash push → re-run → git stash pop, compare error lines.
```

Pre-existing-error check is critical: if `tsc` shows an error, prove it exists
on clean HEAD (stash your changes, rerun, count the same error line) before
blaming the migration.

## Commit & Deploy

- `git add -A && git commit` — review `git diff --stat` (hundreds of files is
  expected), verify no `package-lock.json`/lockfile churn crept in.
- Push + verify on GitHub side via API (`gh api repos/OWNER/REPO/commits/SHA`),
  don't trust the local push echo alone.
- Vercel-connected repos auto-deploy on push; check deployment status after.

## GSC (Google Search Console) registration

Domain-property verification via DNS TXT is the recommended path (covers all
subdomains, zero code changes). Flow: user adds `new-domain.org` as a Domain
property in GSC → GSC shows a `google-site-verification=<token>` TXT value →
user adds it in their DNS panel (host = subdomain name, type TXT, value as
given) → **you verify propagation from your side with
`nslookup -type=TXT new-domain.org`** (never trust "wait a day" — if it's
published you'll see it in minutes) → user clicks VERIFY.

Pitfalls:
- TXT tokens must be EXACT — if you read them off a screenshot via OCR, OCR
  can drop characters. Have the user paste the copied value.
- Some DNS panels (DigitalPlat dpdns.org) show "Update successful" without
  actually publishing — always confirm with a live TXT lookup.
- Alternative: URL-prefix property verified by meta tag/env var or HTML file
  in `public/` — the agent can do all repo work, user only clicks Verify.

## Pitfalls

- `grep -rl` without `--include` counts MORE files than extension-filtered
  greps (binary/lock/docs) — fine for perl -pi, just expect a higher count.
- "Only domain changes in diff" greps can false-positive: a line containing
  BOTH the old domain (unchanged segment) and new domain (changed segment)
  matches both patterns. Eyeball the diff lines, don't trust the grep alone.
- jest `next/jest` import can fail on Next 16 ESM resolution — work around
  with a temp minimal jest config (babel-jest + next/babel preset) to run the
  SEO suite, delete the temp file before committing. Pre-existing, not yours.
- yarn 1 may hang on this box; use `npm ci` (see windows-msys-tooling skill).
- Reading GSC/DNS screenshots on text-only models: local OCR fallback in
  `references/screenshot-ocr-fallback.md`.

## Support files
- `references/screenshot-ocr-fallback.md` — rapidocr-onnxruntime recipe for
  reading user screenshots when vision_analyze is unavailable.
