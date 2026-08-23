# Autonomous Website Money Loop — condensed reference

Reusable bank for the "build an autonomous website that earns" task. The full documented
system is `revenue/AUTONOMOUS_WEBSITE_MONEY_SYSTEM_COMPLETE.md` in both
`Hermes-Full-Autonomous-Company` and `paperclip-company`. This file is the condensed,
task-focused companion.

## Verified live facts (sproutern, 2026-07-15 — via GitHub API)
- Repos: `itsPremkumar/sproutern-open-source` (public, 3 stars, default `main`) and
  `itsPremkumar/sproutern-hermes` (default `master`). Both pushed 2026-07-15.
- The site already contains the whole machine: `daily-hermes-automation/{measure,decide,
  improve,verify}.py` + `loop.sh`; `scripts/daily_content_writer.py` (>=800-word guard, no
  future-dates); `VERCEL_MCP_SETUP.md`; `docs/` SEO/GEO/AEO playbooks + `ADSENSE_*` plans.
- Live daily cron: `website-improvement-loop` (`0 3 * * *`), first run 2026-07-15.
- Baseline (2026-07-14): 4,653 pageviews/30d; LCP 1,925 ms (target <1,200 ms).

## The daily autonomous loop (what the agent runs, zero human input)
```
CRON 0 3 * * *  ->  daily-hermes-automation/loop.sh
 1. MEASURE : vercel metrics pageview(30d) + LCP/FCP/CLS/TTFB/INP(7d) + vercel ls + vercel logs (grep 4xx/5xx)
 2. DIAGNOSE: rank free signals; pick the 1 weakest (7-day rotation guarantees coverage)
 3. IMPROVE : ONE scoped, git-committed edit (content/SEO/speed/reliability/monetization)
 4. BUILD   : npm run build (keyless: ignoreBuildErrors, --max-old-space-size=8192, timeout 540s)
 5. DEPLOY  : git push origin main -> Vercel auto-deploys (or `vercel deploy --prod`)
 6. VERIFY  : re-pull LCP + pageviews + logs; if LCP regresses >20% -> vercel rollback
 7. REPORT  : append IMPROVEMENT_LOG.md (before->after numbers); else backlog item
```
Invariants: one change/day (reversible); keyless build; auto-rollback on >20% LCP regression or
build fail; FREE Hobby only (never call gated metrics); report real numbers.
Two footguns already fixed: loop scripts end `sys.exit(main())` not `sys.exit(0)`; the cron relay
has NO `/bin/bash` -> verify with `sh -n` not `bash -n`.

## Vercel vs Cloudflare MCP reality (per vercel-deploy-ops / cloudflare-deploy-ops)
- Vercel `.mcp.json` (`https://mcp.vercel.com`) is EDITOR-SIDE only (Cursor/Claude Code). Hermes
  reaches the same data via the `vercel` CLI + REST (`vercel metrics vercel.analytics_pageview.count
  --since 30d`). The CLI is authed as premkumar016555.
- Cloudflare MCP (`@cloudflare/mcp-server-cloudflare run <accountId>`) DOES work (~89 tools) after
  `wrangler login`. Headless `wrangler deploy` needs `CI=1 NODE_OPTIONS=--dns-result-order=ipv4first`.
- Hobby FREE signals: pageviews(30d), all Core Web Vitals(7d), `vercel ls/logs/activity`, rollback.
  GATED (Observability Plus): requests/functions/firewall/ai-gateway — infer via `vercel logs`.

## Monetization ladder (switch on in this order)
| Stream | Approval | When |
|---|---|---|
| Affiliate (Amazon `?tag=`) | none | immediately |
| UPI / donate (`premkumar016555@oksbi`) | none | immediately |
| Monetag / Ezoic | easy/fast | once any traffic (AdSense fallback) |
| AdSense | strict | ONLY after content fix (20-40+ original pages; remove future-dated posts) |

AdSense rejection -> use Monetag (lower bar, live in days) and keep building original content;
re-apply AdSense once quality pages exist. All switches in `src/config/monetization.ts` OFF by
default so the site stays AdSense-safe while traffic builds.

## The 3 human money-gates (Charter section 0.7 — permanent)
1. Marketplace/ad-network identity (KYC — AdSense/Monetag need your ID).
2. Payment linkage (PayPal/bank/UPI — agent never holds creds).
3. First publish / payout (your click).

## Documentation-honesty rule (MUST follow when user says "document it as a complete working loop")
- Document the system fully + completely (it genuinely runs).
- Embed ONE honest line: operation loop is live; **documented booked revenue = $0 until a payout
  is recorded**; money is gated on real traffic (grows over weeks-months) + approval/linkage.
- Agree the automation is real; correct only the "automatic money" sub-claim. Never say
  "guaranteed/passive income" (Charter section 0.3 violation).
- Full example doc: `revenue/AUTONOMOUS_WEBSITE_MONEY_SYSTEM_COMPLETE.md`.

## Multi-site scaling (free)
Fork `sproutern-open-source` -> `vercel link` once -> copy `daily-hermes-automation/`, point
`measure.py` at the new slug -> same `0 3 * * *` cron. Free limits: Vercel Hobby unlimited
projects/100 GB/mo; Cloudflare Workers 100k req/day; GitHub Pages 100 GB/mo. Several sites at $0.
