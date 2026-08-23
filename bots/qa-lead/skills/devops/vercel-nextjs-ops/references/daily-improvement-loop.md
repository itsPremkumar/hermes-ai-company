# Daily Autonomous Improvement Loop (Vercel + free plan)

Proven pattern for a **self-improving Vercel site** driven by a daily cron, using
only FREE signals. Built live on `sproutern` (Next.js 16, Hobby plan, team
`prems-projects-27978e99`) 2026-07-14.

## Hard facts (verified live)
- The Vercel MCP in `.mcp.json` (`https://mcp.vercel.com`) is **editor-side only**
  (Cursor/OpenCode). Hermes reaches the same data via the **Vercel CLI** (already
  logged in as the user) — do NOT block on the MCP. `vercel --version` 55.x.
- Hobby plan = NO Observability Plus. Most aggregate metrics are gated (see map).
- `vercel metrics <id> --since 7d` is the max window Speed Insights returns on Hobby
  (30d requests -> "hobby plan only grants last 7 days". Use 30d for pageviews).

## Complete signal map — free vs gated (tested live)
✅ FREE (usable daily feedback):
- `vercel.analytics_pageview.count` (30d window) — total pageviews (the #1 KPI)
- `vercel.speed_insights.{lcp,fcp,cls,ttfb,inp}_ms` + `*_count` (7d window)
- `vercel ls` (deployments: age/status/duration), `vercel inspect <id>`,
  `vercel logs <url>` (λ/ε/◇ request lines — grep for 4xx/5xx), `vercel activity`
- `vercel rollback <id>`, `vercel promote`, `vercel redeploy` (safety)
- `vercel project inspect`, `vercel domains ls`, `vercel project web-analytics`/
  `speed-insights` (config/feature flags), `vercel alerts`

🔒 GATED (needs Observability Plus / Pro — NOT on free):
- `vercel.request.count`, `vercel.function_invocation.*`, `vercel.middleware_invocation.*`
- `vercel.firewall_action.count`, `vercel.bot_id_check.count`, `vercel.external_api_request.*`
- `vercel.isr_operation.*`, `vercel.image_transformation.*`
- `vercel.ai_gateway_request.*`, `vercel.sandbox.*`, `vercel.workflow_operation.*`

**Workaround for gated data:** `vercel logs <url>` still streams RAW request lines
(status code, path, latency) on Hobby even though the aggregate function metrics are
gated. Grep `vercel logs <url> 2>&1 | grep -E " 5[0-9]{2} | 4[0-9]{2} "` to catch
errors that the gated metrics would otherwise show. This is the only free error signal.

## The closed-loop architecture (cron `0 3 * * *`, bounded, keyless)
```
STEP 1 MEASURE : pageviews(30d) + LCP/CLS/FCP/TTFB/INP(7d) + vercel ls + vercel logs (grep 4xx/5xx)
STEP 2 DIAGNOSE: rank signals; pick the 1 worst (e.g. LCP 1925ms, or a spiking 5xx)
STEP 3 IMPROVE : ONE scoped, git-committed edit (never a full rewrite)
STEP 4 BUILD   : npm run build (webpack, --max-old-space-size=8192, ignoreBuildErrors) — timeout-bounded
STEP 5 DEPLOY  : git push -> Vercel auto-deploys
STEP 6 VERIFY  : re-pull LCP + pageviews + logs; if LCP regresses >20% or build fails -> vercel rollback <last-good>
STEP 7 REPORT  : append IMPROVEMENT_LOG.md (before->after numbers); else backlog item
```

### Cron prompt shape (self-contained, bounded)
```
cd <repo>
MEASURE  : vercel metrics vercel.analytics_pageview.count --since 30d
          vercel metrics vercel.speed_insights.lcp_ms --since 7d
          vercel ls | head ; vercel logs <prod-url> 2>&1 | grep -E " 5[0-9]{2} " | tail
DECIDE   : pick weakest signal
IMPROVE  : one edit, git commit
BUILD    : rm -rf .next && timeout 540 npm run build   (keyless, ignoreBuildErrors)
DEPLOY   : git push origin main
VERIFY   : re-pull; rollback on regression
REPORT   : <150 words, before->after numbers
Rules: ONE change/day. Never full rewrite. Bound every command. Private repo ->
never force-push/rewrite history. If blocked, backlog + stop.
```

## Improvement backlog (free-signal-driven, Sproutern example)
1. **Speed** — `next/image`, lazy-load, trim heavy imports -> attack LCP (was 1925ms).
2. **Monetization** — add `src/config/monetization.ts` + `AffiliateStrip`/`SponsorCTA`/
   `UpiDonate` components (zero-approval: Amazon `?tag=`, sponsored->/contact,
   Gumroad/Razorpay, UPI `premkumar016555@oksbi`). All OFF by default (AdSense-safe).
3. **SEO/content** — replace auto-generated / future-dated blog pages (unblocks AdSense
   reapply; the original `gen-content.ts` blog caused the "low-value content" rejection).
4. **Reliability** — fix top 5xx from `vercel logs`.
5. **Trust** — Privacy / About / Contact / Terms pages.

## Human-quality DAILY CONTENT track (the key user requirement)
The user wants **genuinely human-written, high-quality content** added daily — NOT
thin AI spam (which got the site AdSense-rejected). Pattern proven on Sproutern:

- New blog posts live as markdown in `src/content/blog/<slug>.md` and are auto-rendered
  (no code change per post). Frontmatter shape the site expects:
  ```yaml
  ---
  title: '...'
  date: 'YYYY-MM-DD'        # NEVER future-date (AdSense "low-value" cause)
  category: '...'
  readTime: 'N min read'
  excerpt:
    '...'
  author: 'Sproutern Career Team'
  keywords:
    - a
    - b
  ---
  # Heading
  real 900-1500 word human-voiced body with ## sections + FAQ
  ```
- Don't use the thin `scripts/gen-content.ts` for the body. Have the agent AUTHOR the
  words (real voice, specific examples, a take, an FAQ), then a small writer script only
  formats/validates/writes. Enforce a quality floor (e.g. reject <800 words) so no thin
  content ships. Keep the writer IDEMPOTENT (skip if slug exists).
- Reuse the existing content engine for *freshening*: `scripts/content-freshness.ts`
  bumps "Last Updated" + adds FAQ/Related to stale (90d+) posts (Google rewards freshness).
  `scripts/trending-content-engine.ts` discovers trending keywords — but its `--ai` mode
  needs `GOOGLE_API_KEY`; without it, template-based (free, no key). Prefer agent-authored
  bodies over templates for quality.

### Proven writer guard (verified 6/6 ad-hoc checks)
A `daily_content_writer.py` that: rejects <800-word bodies (exit 2), writes correct
frontmatter, uses TODAY's IST date (no future-dating), and skips existing slugs. The
guard REJECTED a 613-word draft and ACCEPTED a 940-word human-voiced post — exactly the
quality gate you want in the loop.

## Caveats
- The loop is **hypothesis-driven**: free signals show outcomes (speed, traffic, errors)
  but NOT root cause (which function is slow). Infer from `vercel logs`; upgrade only if
  the user accepts Pro (don't recommend it unprompted).
- On the ~6GB host, BOUND everything: build `timeout 540`, one change/day, keyless build
  (`ignoreBuildErrors` + 8192MB heap) so a tsc OOM never blocks a legit deploy.
- Private repo: commits stay private; never `git filter-branch`/force-push history.
