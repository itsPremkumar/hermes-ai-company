# Audit caveats: env vars & domain ownership (corrected 2026-08-08)

Two findings from the sproutern-oss Vercel audit that *correct* the pitfall-table
entries in SKILL.md. Read this before acting on `vercel env ls` / `vercel domains add`
results.

## 1. "No Environment Variables found" is NOT always a bug
`vercel env ls` → "No Environment Variables found" means the project has zero env
vars. But that is **by design** if the repo's `.env.example` declares every variable
OPTIONAL with safe placeholders and the build never fails without them.

Verified case (sproutern-oss): `.env.example` header literally says
*"ALL variables are OPTIONAL — the site builds and runs with none set. The app uses
safe placeholders when these are absent, so the build never fails."*

→ Action: read `.env.example` FIRST. If vars are optional, do NOT tell the user the
site is "broken" or "missing config". Only list the keys as *optional enhancements*
(login/AI/ads/forms) the user may add. Reserve the "add from `.env.example`" action
for repos where the code has NO placeholder fallback (vars required).

## 2. `domain_not_owned` (403) on an already-serving domain = manual-only, not fixable via CLI
`vercel domains add <sub>.<freedns> <project> --non-interactive` returned:
`{"status":"error","reason":"domain_not_owned","message":"Not authorized to use
<sub>.<freedns> (403)..."}`

This happened on `sproutern.dpdns.org`, which **already served HTTP 200** (DNS-CNAME'd
to the auto-generated `*.vercel.app`). Root cause: the Vercel account does NOT own or
control `dpdns.org`; the domain was only DNS-pointed, never registered/verified in
Vercel. Vercel therefore refuses to add it because it can't verify ownership without a
dashboard challenge.

→ Do NOT fake success or claim the domain was "added". The fix is **manual, in the
Vercel dashboard**:
  1. Vercel Dashboard → `sproutern-oss` → Settings → Domains → enter `sproutern.dpdns.org`.
  2. Vercel issues a verification record (TXT `_vercel` + A `@` → `216.198.79.1`).
  3. Place those records in the dpdns DNS provider; refresh; Vercel issues TLS.

**Distinguish from the OTHER `domain_not_owned` 403** (documented in SKILL.md
`custom-domain-attach.md`): that one is "zone doesn't exist yet" and IS fixed by
creating the DNS zone + CNAME→`cname.vercel-dns.com` + waiting for propagation, after
which CLI add works. This one ("account doesn't own it") is NOT — it needs the manual
verification step regardless. Tell them apart by whether the domain is a free subdomain
you merely point DNS at vs. one whose zone you created in the provider dashboard.

## 3. Verify third-party named exports against the PINNED dependency version before editing imports
When adding an icon/component import (e.g. `Github` from `lucide-react`), confirm the
named export exists in the **repo's pinned version**, not just latest.

Verified case: `lucide-react@^0.539.0` (sproutern) DOES export `Github` (brand icons
present in 0.x). But `lucide-react@1.x` (installed ad-hoc) DROPPED all brand icons →
`Github` would be undefined → build break. Check the actual pin:
```bash
grep '"lucide-react"' package.json          # see the pinned range
npm install lucide-react@<pinned> --no-audit --no-fund
node -e "const l=require('lucide-react'); console.log('Github' in l ? 'YES':'NO')"
```
Same caution applies to any `import { X } from 'some-lib'` edit: resolve `X` against
the installed/locked version, not assumptions. Then prove the edit compiles with
`tsc --noEmit` (see code-verification.md).
