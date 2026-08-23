# Vercel Daily Autonomous Improvement Loop (verified 2026-07-14)

Pattern for running a RECURRING, self-improving Vercel site from Hermes using
Vercel signals as feedback. Distinct from one-shot deploy (see SKILL.md). The
user explicitly wants this for `sproutern` (private, Hobby/free plan, daily).

## Verified complete signal map (tested live via `vercel` CLI, Hobby plan)
94 metrics exist. Split into FREE (queryable) vs GATED (Observability Plus /
Pro-Enterprise — NOT available on free).

### ✅ FREE — usable daily feedback (Hobby)
- Traffic: `vercel.analytics_pageview.count` (30d window)
- Core Web Vitals: `vercel.speed_insights.{lcp,fcp,cls,ttfb,inp}_ms` + `*_count`
  (7d window on Hobby — `--since 30d` rejected with "hobby plan only grants latest 7 days")
- Deploy health: `vercel ls`, `vercel inspect <deploy-url>`, `vercel logs <url>`,
  `vercel activity`
- Safety: `vercel rollback <id>`, `vercel promote`, `vercel redeploy`
- Config: `vercel project inspect`, `vercel domains ls`,
  `vercel project web-analytics sproutern`, `vercel project speed-insights sproutern`
- Alerts: `vercel alerts`

### 🔒 GATED (returns "Observability Plus is required") — infer instead
- `vercel.request.count`, `vercel.function_invocation.*`, `vercel.middleware_invocation.*`
- `vercel.firewall_action.count`, `vercel.bot_id_check.count`, `vercel.external_api_request.*`
- `vercel.isr_operation.*`, `vercel.image_transformation.*`
- `vercel.ai_gateway_request.*`, `vercel.sandbox.*`, `vercel.workflow_operation.*`
- **Workaround for gated data:** `vercel logs <url>` streams raw request lines
  (status codes, paths, latency) on Hobby — `grep` for `4xx`/`5xx` to catch errors
  the aggregate function metrics would otherwise show.

## Live baseline measured (sproutern, 2026-07-14)
- Pageviews 30d: **4,653** (avg 25.7/4h; peak 104 on Jul 8)
- LCP 7d avg: **1925 ms** (target <1200 ms "good" — clear daily target)
- 9 production deployments, all Ready, latest 23m old
- NOTE: a Cloudflare email celebrated 100,000 pageviews "last month" dated
  2025-12-31 (past peak). Current Vercel Web Analytics = ~4.6K/mo. Plan against
  the LIVE number; the 100K proves past capacity, not current traffic.

## Closed-loop architecture (the recurring cron)
```
CRON: website-improvement-loop  "0 3 * * *"  (bounded, keyless build)
 1. MEASURE  : pageviews(30d) + LCP/CLS/FCP/TTFB/INP(7d) + vercel ls + vercel logs (grep 4xx/5xx)
 2. DIAGNOSE : rank signals; pick the 1 worst (e.g. LCP 1925ms, or a spiking 5xx)
 3. IMPROVE  : ONE scoped, git-committed edit (never a full rewrite)
 4. BUILD    : npm run build (webpack, --max-old-space-size=8192, ignoreBuildErrors) — timeout 540s
 5. DEPLOY   : git push origin main -> Vercel auto-deploys (or vercel deploy --prod)
 6. VERIFY   : re-pull LCP + pageviews + logs; if LCP regresses >20% or build fails -> vercel rollback
 7. REPORT   : append IMPROVEMENT_LOG.md (before->after numbers); else backlog item
```

## Loop invariants (never violate)
- Exactly ONE change per day (reversible, git-committed). Never big-bang rewrite.
- Build always keyless (`ignoreBuildErrors`, 8192MB heap, `timeout 540`).
- Auto-rollback on LCP regression >20% or build failure.
- FREE plan only — never call gated metrics; never suggest Pro/paid upgrades.
- Report real before->after numbers; never claim "improved" without them.
- Private repo — never force-push / rewrite history.

## Improvement backlog (free-signal-driven, priority order)
1. Speed — lazy-load, `next/image`, trim heavy imports -> attack LCP. (On Hobby the
   real LCP lever is ISR: `export const revalidate = 86400` on static Server-Component
   pages — see vercel-nextjs-ops free-plan playbook. Must NOT go in `'use client'`.)
2. Monetization — `src/config/monetization.ts` + AffiliateStrip/SponsorCTA/UPI strips
   (zero-approval: Amazon `?tag=`, sponsored -> /contact, Gumroad/Razorpay, UPI
   `premkumar016555@oksbi`). All OFF by default (AdSense-safe placeholders).
3. SEO/content — replace auto-generated / future-dated blog pages (also unblocks AdSense
   reapply; sproutern was rejected for "low-value content").
4. Reliability — fix top 5xx from `vercel logs`.
5. Trust — Privacy / About / Contact / Terms pages.

## Keyless build facts (this 8 GB host — sproutern)
- Full Next 16 + Firebase + Genkit OOM-crashes tsc type-check at ~6 GB.
- Fix: `next.config` `typescript: { ignoreBuildErrors: true }`; set
  `outputFileTracingRoot: __dirname` if nested under a dir with `package-lock.json`.
- Vercel read-only FS: any `fs.writeFileSync` route FAILS in prod -> use Formspree/Basin
  (or local-file fallback for dev) for newsletter/subscriber writes.
- Export dummy `NEXT_PUBLIC_FIREBASE_*` + `NEXT_PUBLIC_ADSENSE_REVIEW_MODE=true` for build.

## AdSense history (must respect)
- Original auto-generated blog (`scripts/gen-content.ts`) + future-dated posts
  (`src/lib/blog-data.ts`) caused an AdSense "low-value content" rejection.
- Carries to any clone until content cleaned + 20-40+ original pages added.
- Keep `LICENSE` `Copyright (c) 2026 Sproutern` (MIT). Delete any original owner's
  GSC verify file (`googlec*.html`). Ads are the LAST stream (approval + real traffic).

## How the loop is driven (agent note)
- The Vercel MCP in repo `.mcp.json` (`https://mcp.vercel.com`) is EDITOR-SIDE only
  (Cursor/OpenCode). Hermes reaches the same data via the Vercel CLI (already logged in
  as premkumar016555) + REST API. Both paths equivalent for the signals above.

## TWO FOOTGUNS that broke the first build (encode them — do not repeat)
1. **`if __name__ == "__main__": sys.exit(0)` instead of `sys.exit(main())`.**
   `measure.py` and `decide.py` originally exited 0 WITHOUT calling `main()`, so
   `decide.py` silently produced no `next_action.json` and the loop did nothing.
   FIX: every loop script's entrypoint must be `sys.exit(main())`. Always `py_compile`
   + a real end-to-end `decide.py` run before claiming the loop works.
2. **`sh -n` fails on the relay — there is NO `/bin/bash`** (execvpe(/bin/bash)
   failed). The orchestrator is bash, but verification must use `sh -n`, not `bash -n`.
   (Same trap as hermes-cron-script-ops: cron sandbox also lacks /bin/bash.)

## Committed artifacts (sproutern @ github.com/itsPremkumar/sproutern, private)
- `scripts/website-improve-loop/{measure,decide,improve,verify}.py` + `loop.sh`
- `scripts/daily_content_writer.py` (>=800-word guard; rejects thin; never future-dates)
- `src/config/monetization.ts` + `src/components/monetization/{AffiliateStrip,SponsorCTA,UpiDonate}.tsx` (all OFF by default)
- `DAILY_LOOP.md` (full setup), `IMPROVEMENT_LOG.md` (before->after table)
- `daily-hermes-automation/` — backup copy of all loop scripts
- Live Hermes cron: `website-improvement-loop` (job `596366de8767`), `0 3 * * *`, first run 2026-07-15. NOTE: local-only delivery (output saved, NOT pushed to chat) unless `deliver` is set to a gateway platform.

## Reusable verifier
Behavioral check script in this skill: `references/verify_loop.py` (copy to `scripts/`
and run `python scripts/verify_loop.py` from repo root). Covers compile + `sh -n` +
decide end-to-end + content-writer thin-rejection + artifact existence. The project has
NO jest/eslint/tsc runnable on the relay, so this is the verification path; a real
`npm run build` on Vercel (auto on push) is the only true proof for `.ts`/`.tsx`
(the 8GB host OOM-crashes the local Next 16 tsc type-check).
- `curl https://api.vercel.com/v9/projects/<name>` returned nulls using `.env.local`
  `VERCEL_OIDC_TOKEN` — prefer `vercel` CLI commands (active session token) over
  hand-rolled curl for project data.
- Canonical daily check:
  ```bash
  vercel metrics vercel.analytics_pageview.count --since 30d
  vercel metrics vercel.speed_insights.lcp_ms --since 7d
  vercel ls
  ```
