---
name: vercel-deploy-ops
description: Deploy, configure, and operate a Next.js (or any) site on Vercel from the Hermes agent terminal — zero-cost, no-backend strategy. Covers the Hermes-vs-OpenCode MCP distinction, project linking, env-var setup, deploy verification, Vercel Web Analytics via CLI, and keyless production-build verification. Use when a user asks to push/deploy to Vercel, set Vercel env vars, check deploy status, or read site analytics — especially when they hand you an "OpenCode / Vercel MCP" setup guide.
category: devops
---

# Vercel Deploy & Ops from Hermes

## When to use
- User wants to deploy/push to Vercel, set env vars, check build/deploy status, read analytics, or **rename/audit a Vercel project**.
- User pastes a "Vercel MCP + OpenCode" setup guide and says "do this."
- You need to verify a `next build` (or any long build) from the agent terminal.
- User asks "what improvements does this project need?" → run the audit recipe below.

## Project rename & full audit recipe (verified 2026-08-08)
Renaming a Vercel project is a **label-only** operation — the auto-generated `*.vercel.app` URL keeps the old name in it, and any attached custom domain (e.g. `sproutern.dpdns.org`) is **untouched** and keeps serving. Safe to do.

```bash
vercel project rename sproutern-hermes sproutern-oss --non-interactive   # label only; deploy URL + custom domain unaffected
vercel project ls                                   # confirm new name appears
curl -s -o /dev/null -w "%{http_code}" https://your-custom.domain/        # still 200 after rename
```

**Full "does this project need improvements?" audit** (what actually worked this session — no keychain token needed, all via CLI):
```bash
vercel project inspect <name> --non-interactive      # general + framework settings (Root Dir, Node ver, build/install cmd)
vercel ls <name> --non-interactive                   # deployments: status (Ready/Building/Error), duration, env
vercel domains ls --non-interactive                  # account-level domains ONLY (see "domain verification" caveat below)
vercel env ls --non-interactive                      # env-var COUNT (names only, no values); "No Environment Variables found" = real gap
vercel link --project <name> --scope <team> --yes     # writes .env.local so env ls / git cmds work from a non-repo dir
vercel logs <deploy-url> --non-interactive           # runtime access logs (GET 200s etc.); filter build/warn/error columns
```
**Interpretation flags:**
- `env ls` → "No Environment Variables found" + code reads `NEXT_PUBLIC_FIREBASE_*`/API keys → config is either hardcoded (security risk) or missing (features broken). Either way, add the needed keys as Vercel **Environment Variables** (settings → env vars), sourced from the repo's `.env.example`.
- Custom domain serves 200 but `vercel domains ls` doesn't list it → it's DNS-CNAME'd to the auto-generated `*.vercel.app`, NOT Vercel-managed. Fragile: add it as a Vercel domain (settings → domains) and point DNS at Vercel's records to make it first-class.
- Deployment alias `…-git-master-…` → was GitHub-connected on `master`; confirm Git → connected to the current repo so pushes auto-deploy.
- `next@16.0.7` carries a security advisory → bump to a patched 16.x.

**Cleanup after auditing:** `rm -rf .env.local .vercel` (created by `vercel link`) so nothing stray is left in the user's working dir.

## KEY INSIGHT — Hermes is NOT OpenCode
Vercel MCP setup guides are written for **OpenCode** (`~/.config/opencode/opencode.json`). Those steps do NOT apply to Hermes. Hermes manages Vercel through the **Vercel CLI**, normally already installed + authenticated.
- Check: `vercel --version` (v55+ for `vercel metrics`), `vercel whoami`, `vercel teams list`.

### "There's a Vercel MCP, check analytics there" → it's editor-side, use the CLI
When the user points at a Vercel MCP, they almost always mean a repo `.mcp.json`
(`{ "mcpServers": { "vercel": { "url": "https://mcp.vercel.com" } } }`). That is an
**editor-side MCP config (Cursor/Claude Code)** — NOT wired into Hermes's toolset, so you
have no `mcp__vercel__*` tools. Do NOT say you can't read analytics. The Vercel CLI already
authenticated as the user reaches the *same* data. Full recipe + the two plan gates:
`references/vercel-analytics-read-cli.md`.

## Workflow
1. **Link:** `vercel link --project <project> --scope <team-slug> --yes`
2. **Env vars (one env at a time):** `printf '<value>' | vercel env add <VAR> production`. ⚠️ No comma-separated envs WITH `--scope`.
3. **Deploy:** `vercel deploy --prod --yes --name <project> --build-env NEXT_PUBLIC_SITE_URL=https://<domain>` (background if >600s; large Next.js apps take ~8 min on Vercel's servers). Produces `https://<project>.vercel.app` even with no custom domain attached yet.
4. **Attach custom domain — ORDER MATTERS (free subdomain chicken-and-egg):** deploy FIRST, attach SECOND. `vercel domains add` refuses with `domain_not_owned` (403) until the subdomain's DNS zone exists AND points at Vercel.
   - **Standard free subdomain (DigitalPlat `dpdns.org`, managed DNS HEALTHY):** provider dashboard → "Use DigitalPlat DNS" → add CNAME `<sub> → cname.vercel-dns.com` → wait ~5 min → `vercel domains add <sub>.dpdns.org <project> --non-interactive`. Recipe: `references/custom-domain-attach.md`.
   - **DigitalPlat "Use DigitalPlat DNS" errors "nameservers are unhealthy" (managed-zone backend outage) — PREFERRED FIX = direct NS delegation to Vercel** (simpler than Cloudflare fallback): in DigitalPlat's manual NS form put NS1=`ns1.vercel-dns.com`, NS2=`ns2.vercel-dns.com` (NS3–8 empty), click **Update** → green "Update successful". This writes delegation straight into the parent `dpdns.org` zone (DigitalPlat's own infra, which is UP), making Vercel the FULL DNS authority — bypassing the broken managed zone entirely. No Cloudflare account / 24-7 server needed. After propagation (~10–30 min; `nslookup -type=NS <sub>.dpdns.org` → ns1/ns2.vercel-dns.com) Vercel shows "Verification Required" with two records to add IN VERCEL (not DigitalPlat): TXT `_vercel` → `vc-domain-verify=<sub>.dpdns.org,<hex>` and A `@` → `216.198.79.1`. Add them, Refresh, TLS auto-issues. Full recipe + watcher script: `references/digitalplat-direct-ns-delegation.md`. (Cloudflare Subdomain-setup remains a valid secondary fallback: `references/digitalplat-cloudflare-fallback.md`.)
5. **Verify deploy:** `vercel ls <project> --limit 3 --scope <team-slug>` → Building/Ready. ⚠️ `vercel --prod` foreground times out (>600s cap) — background or auto-redeploy.
6. **Web Analytics (v55+):** `vercel metrics vercel.analytics_pageview.count --since 30d --project <name> --prod --scope <slug>` + `--group-by request_path|country|device_type`. Some dimensions (`os`, `referrer`) are empty on the free plan — see `references/vercel-analytics-dimensions.md`.

## Domain verification — `vercel domains ls` is ACCOUNT-level, NOT the truth
`vercel domains ls` / `vercel domain inspect <d>` only see domains in the account's domain list. A custom domain **attached to a project** can be live + verified and still absent from both (verified 2026-08-04: `sproutern.dpdns.org` served production traffic, `domains ls` showed only `sproutern.com`, `domain inspect` → "You don't have access"). Authoritative check = project-level API:
```bash
TOKEN=$(node -e "console.log(require(process.env.APPDATA+'/xdg.data/com.vercel.cli/auth.json').token)")
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.vercel.com/v9/projects/<project>/domains?teamId=<team-slug>"
# → look for {"name":"<domain>","verified":true}
```
(On Windows the CLI token lives at `%APPDATA%\xdg.data\com.vercel.cli\auth.json` — the `Data/auth.json` file may lack a `token` field.)
Other domain-truth signals:
- **Vercel edge IPs are NOT always `76.76.21.21`** — `216.198.79.1` (AWS AS16509 anycast, Walnut CA) is a real Vercel edge node. `curl -sSI` → `Server: Vercel` + `X-Middleware-Geo` headers is the real proof, not the IP.
- **Cert freshness:** `echo | openssl s_client -connect <d>:443 -servername <d> 2>/dev/null | openssl x509 -noout -subject -issuer -dates` — Vercel auto-issues Let's Encrypt (issuer `CN=YR1`) for attached domains, dated TODAY for a freshly attached one.
- **Different Etags between custom domain and `.vercel.app` do NOT mean different builds** — geo/locale variation (`X-User-Locale: en-IN` vs `en-US`, X-User-Country, X-User-Currency) changes the prerendered HTML hash. Compare **JS chunk hashes** instead: `grep -oE '/_next/static/chunks/[a-z0-9-]+\.js'` on both hosts — identical chunk names = same build.
- `vercel env ls` → "Your codebase isn't linked": run `vercel link --project <name> --yes` FIRST (writes `.env.local`), then `vercel env ls`.
- **Placeholder config = missing env vars:** if `/api/config/firebase` returns `{"error":"Firebase configuration incomplete","missingKeys":[...]}` AND the browser network log shows `projects/placeholder` / `G-XXXXXXXXXX` (inspect via `performance.getEntriesByType('resource')` in browser_console), the project has ZERO env vars — auth/login is broken on every domain, not a domain problem. Firebase Auth ALSO requires each domain in Firebase Console → Authentication → Authorized domains (missing → `auth/unauthorized-domain`).

## Canonical-domain migration across the codebase (sproutern.com → new domain)
When the user says "use the new domain for SEO/GEO/AEO" they mean replacing the canonical domain in ~250 files: canonical URLs, OG/Twitter meta, JSON-LD schemas, sitemap XMLs, robots.txt, llms.txt, feeds, GEO/AEO/SGE modules, scripts (IndexNow, sitemap generators, OG-image watermark), configs (cors.json, apphosting.yaml, package.json homepage, next.config redirects). Full ordered recipe + verification: `references/domain-migration.md`. Key rules: ordered perl replaces (www-first → bare), email-excluding lookbehind `(?<![\w.@])` to preserve `support@old.com` mailboxes, handle capital-brand `Old.com` prose separately, hand-edit hostname-matching logic (proxy.ts canonical-host redirect) instead of blind-replacing, and verify with `git stash push` + typecheck to prove pre-existing errors aren't yours.

## Build verification (Next.js heavy builds)
- Foreground caps 600s; full `next build` 9–12 min → **always background**.
- Keyless builds need dummy public env; `BUILD_EXIT=0` is the truth.

## Code verification — typecheck / lint / live probe BEFORE claiming done
- **Typecheck:** `./node_modules/.bin/tsc --noEmit` (3–6 min on 600MB+ app) — **background it**; `npx tsc` is intercepted.
- **ESLint (scoped):** `./node_modules/.bin/eslint <fileA> <fileB>` → exit 0 fast.
- **Live probe:** after READY, `curl` prod + assert header/body (CORS reflection w/ `?cb=2` cache-bust).
- **Re-verify on stale hooks:** re-run typecheck+lint+live probe FRESH this turn.

## Next.js ISR & route-segment config (common Vercel build-breaker)
`export const revalidate = N` is the highest-leverage free LCP/TTFB fix for a high-traffic
**server-component** page — but **INVALID inside a `'use client'` page file** (deploy `● Error`
at `0ms`; Hobby hides message). Keep in server-component pages only. Detail: `references/nextjs-isr-pitfalls.md`.

## Next.js bundle splitting — drop a heavy lib from the GLOBAL vendor chunk
A heavy client lib (recharts, framer-motion, monaco, chart.js) loaded on **every page** (incl.
pages that don't use it) is the #1 silent JS-bloat source. `next/dynamic` ALONE does NOT fix
it — Next's default `splitChunks` hoists all `node_modules` into one shared `vendor` chunk
loaded app-wide (catch-all `vendor` cacheGroup `test: /node_modules/`). Dynamic import is
necessary but insufficient; ALSO isolate the lib into its own chunk.

**Detection (live proof — curl every referenced chunk, grep a lib symbol):**
```bash
v=$(curl -s "https://www.<site>.com/" | grep -oE "/_next/static/chunks/vendor-[a-zA-Z0-9_-]+\.js" | head -1)
curl -s "https://www.<site>.com$v" | grep -q "RadarChart\|recharts" && echo "IN GLOBAL VENDOR (fail)" || echo "recharts-free (pass)"
for c in $(curl -s "https://www.<site>.com/" | grep -oE "/_next/static/chunks/[a-zA-Z0-9_/-]+\.js" | sort -u); do
  curl -s "https://www.<site>.com$c" | grep -q "RadarChart" && echo "FOUND on: $c"
done   # no FOUND line = homepage 100% recharts-free
```
- Unique symbol per lib: recharts→`RadarChart`, framer-motion→`motionValue`, monaco→`MonacoEditor`.
- Vercel serves gzipped chunks (`transfer-encoding: chunked`) → `content-length` ABSENT; rely on symbol grep, not byte sizes.
- **Find ALL importers first:** `grep -rln "from 'recharts'" src` — a shared UI wrapper (`components/ui/chart.tsx`) silently drags the lib into global vendor.

**Fix part 1 — dynamic import:** extract lib JSX to its own file, `dynamic(() => import('./X'), { ssr: false })`.
**Fix part 2 — isolate in next.config.ts** (priority must OUTRANK the catch-all `vendor` group, usually 10):
```ts
webpack: (config, { isServer }) => {
  if (!isServer) config.optimization = {
    ...config.optimization,
    splitChunks: { chunks: 'all', cacheGroups: {
      recharts: { name: 'recharts', test: /[\\/]node_modules[\\/]recharts[\\/]/, chunks: 'all', priority: 32, reuseExistingChunk: true },
      // keep existing firebase/framework/animations/ui/icons/vendor groups
    } },
  };
  return config;
}
```
**Verify after READY:** homepage vendor symbol GONE; chart route still references it; `tsc --noEmit` + `eslint next.config.ts` pass.
Real case (sproutern 2026-07-11): recharts ~200KB was on every page via global vendor
`vendor-809f40e780fb751b.js` (had `RadarChart`). After `recharts` splitChunks group + dynamic
import, new homepage vendor `vendor-8c6123294c6c7671.js` was recharts-free and the homepage
HTML referenced zero `RadarChart` chunks → ~200KB removed from every non-chart page.

## Pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| `vercel env add` → "codebase isn't linked" | repo not linked | `vercel link --project ... --scope ...` |
| "custom environment ids that do not exist" | comma-separated envs WITH `--scope` | Run WITHOUT `--scope` after link; one env per command |
| `vercel --prod` hangs | foreground >600s cap | auto-redeploy or background |
| "no data" from metrics | Analytics not enabled | enable @vercel/analytics + deploy |
| benign Firebase/Project-Id errors in build log | keyless build w/ dummy env | expected; `BUILD_EXIT=0` is truth |
| `This is not the tsc command you are looking for` | ran `npx tsc` | use `./node_modules/.bin/tsc --noEmit` |
| CORS `*` for all origins after fix | CDN caches the CORS header | cache-bust (`?cb=2`) to verify reflection |
| `vercel ls` "Ready" grep fails | CLI column formatting | `vercel inspect <url>` for reliable status |
| "unverified" after you verified | stale re-prompt from prior-turn edit | re-run typecheck+lint+live probe FRESH this turn |
| deploy `● Error` at `[0ms]` — `export const revalidate = N` in a `'use client'` page | route-segment config invalid in client component; whole build aborts instantly | move `revalidate` to the server-component page (client-component route shells are already static by default) |
| deploy `● Error` at `[0ms]` — `dynamic(() => import('./X'), { ssr: false })` in `layout.tsx` (a Server Component) | Next 15/16 forbids `ssr: false` in `next/dynamic` inside Server Components | drop `ssr: false` (keep `dynamic()` for code-splitting); target is `'use client'` so it hydrates; `dynamic()` still splits the chunk |
| homepage still ships a heavy lib (e.g. firebase) as `<script async>` after you "removed" it | a DIFFERENT globally-imported module still statically imports it (e.g. `notification-provider` → `firebase-messaging` had `import { db } from './firebase'` + `import {...} from 'firebase/firestore'`); Next auto-preloads the chunk for any dynamic import in the module graph | grep ALL importers: `grep -rln "from './firebase'\|from 'firebase/firestore'" src`; make EVERY entry dynamic (`const { db } = await import('firebase/firestore')` inside the async fn; keep only `import type`); an `async` preload is non-blocking and does NOT hurt LCP — only matters if render-critical |
| `metrics --aggregation unique` unsupported | visitor_id not supported for pageview | use sums or dashboard |
| `--group-by device_type` only `desktop` | mobile/tablet fold into os/browser | group by `os` + `browser_name` |
| heavy lib still in homepage JS after `next/dynamic` | default splitChunks merges all node_modules into global vendor | add lib-specific splitChunks cacheGroup (priority > vendor); confirm via chunk-grep |
| `eslint next.config.ts` TS1259/TS2724 in node_modules | broken local @types/react/@types/request, NOT your edit | ignore; Vercel build passes |\n| "user said check the Vercel MCP for analytics" but no `mcp__vercel__*` tools | repo `.mcp.json` is editor-side (Cursor/Claude Code) only | use the authenticated Vercel CLI instead — `vercel metrics vercel.analytics_pageview.count --since 30d` (full recipe: `references/vercel-analytics-read-cli.md`) |\n| `vercel metrics vercel.request.count` → "Observability Plus is required" | most metrics (request/function/firewall/ai-gateway) need Pro/Enterprise | only `vercel.analytics_pageview.count` reads free on Hobby; report the gap, don't fake numbers |\n| `vercel metrics vercel.speed_insights.lcp_ms --since 30d` → "hobby plan only grants latest 7 days" | Hobby data window is 7d | use `--since 7d` for Speed Insights on Hobby |\n| `vercel deployments` → "not a valid target directory or subcommand" | correct subcommand is `vercel ls` | use `vercel ls` to list deployments |\n| `vercel inspect sproutern` → "Can't find the deployment" | `inspect` wants a deployment UID/URL, not the project name | pass a URL from `vercel ls` |\n| `curl https://api.vercel.com/v9/projects/<name>` returns nulls | `.env.local` `VERCEL_OIDC_TOKEN` scope unreliable | prefer `vercel` CLI commands (uses active session token) over hand-rolled curl |
| deploy `● Error` at prerender: `YAMLException: can not read a block mapping entry; a multiline key may not be an implicit key at line 3, column 5` then `Export encountered an error on /blog/[slug]/page` | a markdown blog post's YAML frontmatter has a single-quoted value containing an unescaped apostrophe (e.g. `title: '...I'd...'`) → YAML breaks at the next key. Common when an agent-written content generator writes `title: '{value}'` and the title contains `'`. | In the generator, escape single quotes by doubling (`'` → `''`) for ALL YAML values; verify with `python -c "import yaml; yaml.safe_load(open(f).read().split('---')[1])"`. Reference impl: sproutern `scripts/daily_content_writer.py` `yaml_sq()`. |
| build error message hidden / `vercel inspect <url>` shows empty Builds | need the actual error stack | `vercel inspect <deploy-url> --logs` streams the build/runtime logs incl. the prerender stack trace (e.g. the YAMLException + `Export encountered an error on /blog/...`). Fastest way to find WHY a deploy errored without the Vercel dashboard. |
| `vercel domains add <sub>.dpdns.org <project>` → `domain_not_owned` (403) | subdomain's DNS zone doesn't exist yet (free subdomain like `dpdns.org`); Vercel can't verify ownership | DEPLOY FIRST (`vercel deploy --prod`), create the zone in the provider dashboard ("Use DigitalPlat DNS"), add CNAME `<sub> → cname.vercel-dns.com`, wait ~5 min, THEN re-run `vercel domains add` — now it passes. Full recipe: `references/custom-domain-attach.md` |
| `vercel domains add ... --yes` → `unknown or unexpected option: --yes` | `domains add` has NO `--yes` flag (unlike `deploy --prod`) | use `--non-interactive` and pass project as positional arg: `vercel domains add <domain> <project> --non-interactive` |
| `vercel domains inspect <domain>` → "You don't have access to the domain" | domain not yet attached to a project | ignore pre-attach; `nslookup <domain>` is the real ownership/DNS signal |
| DigitalPlat "Use DigitalPlat DNS" → red banner "nameservers are unhealthy" | DigitalPlat zone-creation backend outage; managed zone can't be created | **PREFERRED FIX (no new account):** DigitalPlat's *manual NS form* writes delegation into the parent `dpdns.org` zone (which is UP) — bypass the broken managed zone. Set NS1=`ns1.vercel-dns.com`, NS2=`ns2.vercel-dns.com`, click **Update** → green "Update successful". Vercel becomes full DNS authority; after ~10–30 min add the TXT+A records IN VERCEL, not DigitalPlat. Full recipe + watcher: `references/digitalplat-direct-ns-delegation.md`. (Cloudflare Subdomain setup is the secondary fallback: `references/digitalplat-cloudflare-fallback.md`.) |
| `vercel domains add` still `permission_denied` before NS propagates | Vercel's DNS zone for `<sub>.dpdns.org` isn't created until NS actually points at Vercel AND ownership is verified | The agent CANNOT `vercel dns add` until propagation completes. Don't fight it — poll `nslookup -type=NS <sub>.dpdns.org` for `ns1/ns2.vercel-dns.com`, THEN add TXT+A. Reusable watcher: `scripts/watch_dpdns_propagation.sh`. |
| Vercel domain card shows "Verification Required" + "linked to another Vercel account" | Generic pre-verification gate; the TXT record Vercel lists is the remedy | Add the **TXT** `_vercel` → `vc-domain-verify=...,<hex>` AND **A** `@` → `216.198.79.1` in the VERCEL dashboard DNS Records tab (the records tab in the Vercel Domains card), NOT the registrar's DNS page. Refresh after ~5 min. |
| `vercel project rename X Y` succeeds but deploy URL still shows old name | rename is **label-only** by design | expected; auto-generated `*.vercel.app` keeps old slug; custom domain unaffected — verify with `curl -w "%{http_code}"` on the live domain |
| `vercel env ls` → "No Environment Variables found" | project has zero env vars | add keys from `.env.example` as Vercel env vars; don't rely on local `.env.local`; missing Firebase/API keys breaks auth/AI features |
| custom domain returns 200 but absent from `vercel domains ls` | DNS-CNAME'd to `*.vercel.app`, NOT Vercel-managed | add the domain in Vercel (settings → domains) + repoint DNS at Vercel records to make it first-class |
| `vercel git connect` → "No local Git repository found" | ran outside a cloned repo | `vercel link` works from anywhere; `git connect` needs to be inside the repo dir |
| OIDC token from `.env.local` fails `curl` API calls | short-lived / scope unreliable | prefer `vercel` CLI subcommands over hand-rolled `curl` with that token |

## Recurring daily improvement (closed loop)
The user wants sproutern improved DAILY via Vercel signals as feedback on the FREE Hobby plan. The full pattern — the verified complete 94-metric FREE-vs-GATED split, the closed-loop cron architecture, loop invariants, the improvement backlog, and the keyless-build + AdSense-history facts — lives in `references/daily-improvement-loop.md`. Load it whenever the user says "improve the site daily", "run a daily loop", or "use the MCP/analytics as feedback". A reusable behavioral verifier (no jest/eslint/tsc on the relay) is at `references/verify_loop.py` — copy to `scripts/` and run `python scripts/verify_loop.py`. Two footguns that broke the first build are documented there: `sys.exit(0)` instead of `sys.exit(main())` in loop scripts, and the relay/cron-sandbox having NO `/bin/bash` (verify with `sh -n`, not `bash -n`).\

## Overlap
Pairs with `money-engine` / `automated-income-system`. Curator may consolidate.
