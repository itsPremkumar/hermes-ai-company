# Canonical-domain migration recipe (sproutern.com → sproutern.dpdns.org)

Verified 2026-08-04 on `sproutern-hermes` (~250 files, 2972 refs, 408 files changed).
Reusable whenever a Vercel-hosted site's canonical domain changes.

## 1. Survey before touching anything
```bash
grep -rn "old\.com" . --include="*.ts" --include="*.tsx" --include="*.js" \
  --include="*.json" --include="*.md" --include="*.xml" --include="*.txt" 2>/dev/null \
  | grep -v node_modules | grep -v "\.next" | grep -v "\.git/" | wc -l
# Categorize the patterns:
grep -rhoE "(https?://(www\.)?old\.com|www\.old\.com|old\.com)" src/ public/ scripts/ \
  2>/dev/null | sort | uniq -c | sort -rn
```
Expect ~4 shape classes: `https://www.old.com` (majority), `https://old.com`,
bare `www.old.com`, bare `old.com` — plus capital-brand `Old.com` in prose.

## 2. Update the source-of-truth config FIRST
`src/lib/seo/site-config.ts`-style files (SEO_SITE_URL) get the new domain so
everything derived from them follows. `src/lib/site-config.ts` (env-driven
SITE_URL) may need NO change — it already reads NEXT_PUBLIC_SITE_URL/VERCEL_URL.

## 3. Ordered perl replaces (www-first, email-excluding)
```bash
cd /c/one/<repo>
FILES=$(grep -rl "old\.com" . 2>/dev/null | grep -v node_modules | grep -v "\.next" | grep -v "\.git/")
# Pass 1: full URL www forms
for f in $FILES; do
  perl -pi -e 's{https://www\.old\.com}{https://new.domain}g; s{http://www\.old\.com}{https://new.domain}g;' "$f"
done
# Pass 2: remaining bare www
for f in $FILES; do perl -pi -e 's{www\.old\.com}{new.domain}g;' "$f"; done
# Pass 3: non-www URL forms
for f in $FILES; do
  perl -pi -e 's{https://old\.com}{https://new.domain}g; s{http://old\.com}{https://new.domain}g;' "$f"
done
# Pass 4: bare old.com NOT preceded by @ (email lookbehind preserves mailboxes)
for f in $FILES; do perl -pi -e 's{(?<![\w.@])old\.com}{new.domain}g;' "$f"; done
# Pass 5 (separate): capital-brand prose "Old.com" → "New.domain"
for f in $(grep -rl "Old\.com" . 2>/dev/null | grep -v node_modules | grep -v "\.next" | grep -v "\.git/"); do
  perl -pi -e 's{Old\.com}{New.domain}g;' "$f"
done
```
Order matters: www BEFORE bare, URL forms BEFORE bare, else double-substitution.

## 4. Hand-edit logic files, don't blind-replace
- `proxy.ts` / `middleware.ts`: canonical-host checks (`hostname === 'old.com' || hostname === 'www.old.com'`). The bulk replace may leave a redundant `a || a` — clean to `hostname === 'new.domain'`. The new domain typically has NO www variant; drop the www canonicalization.
- `next.config.ts` / `vercel.json` redirect targets.
- ad-service paths like `srv.adstxtmanager.com/ACCOUNT_ID/old.com` — an ad-account path, NOT a site link; decide deliberately (usually leave).

## 5. Emails: intentionally preserved
`support@old.com`, `contact@old.com` etc. (~50 refs) are mailboxes, not links.
Verify they survived:
```bash
grep -rn "old\.com" . 2>/dev/null | grep -v node_modules | grep -v "\.next" | grep -v "\.git/" \
  | grep -vE "@old\.com|mailto:|email:|Email:"
# empty = only mailboxes remain → migration complete
```
Tell the user to change mailbox domains separately when the new mailbox exists.

## 6. Verification (the part that proves it)
```bash
# a) corruption check — no double-domain
grep -rn "new\.domain.*new\.domain" . 2>/dev/null | grep -v node_modules | grep -v "\.next"
# b) sitemaps all new
grep -hoE "https://[a-z.]*old[a-z.]*" public/sitemap-*.xml | sort | uniq -c
# c) typecheck — background it (3-6 min on heavy apps): ./node_modules/.bin/tsc --noEmit
# d) tests — SEO suites must pass
# e) PROVE pre-existing errors aren't yours (stash-test):
git stash push -m "migration" && ./node_modules/.bin/tsc --noEmit 2>&1 | grep -c "error" ; git stash pop
#   same error count BEFORE and AFTER your change = pre-existing, not yours.
```

## 7. Environment notes (this box)
- `npm ci --no-audit --no-fund` works; `yarn install` HANGS (see windows-msys-tooling).
- `jest.config.ts` with `next/jest` import fails under Next 16 ("Cannot find module 'next/jest' ... import from 'next/jest.js'?"). Workaround: temp minimal config using `babel-jest` + `next/babel` preset; delete after.
- Node/Next dev servers run on ports 3137/3141 — NEVER `taskkill //IM node.exe` (kills them).
