# Reading Vercel Analytics from the Hermes terminal

## The "Vercel MCP" trap (most common user hand-off)
User says "same Vercel has an MCP, check analytics there." What they mean is a repo
`.mcp.json` like:
```json
{ "mcpServers": { "vercel": { "type": "http", "url": "https://mcp.vercel.com" } } }
```
That is an **editor-side MCP config** (for Cursor / Claude Code). It is NOT wired into
Hermes's toolset — you have no `mcp__vercel__*` tools. Do NOT claim you can't read
analytics. Reach the identical data via the **Vercel CLI**, which is normally already
installed + authenticated (`vercel whoami` → e.g. `premkumar016555`).

## Prereqs
- `vercel --version` → v55+ (needed for `vercel metrics`).
- `vercel whoami` → confirms active session token (this is what authorizes the calls).
- Find project + team: `vercel projects ls` → "Project Name / Latest Production URL / team".

## Status checks (free, always work)
```
vercel project web-analytics <name>      # -> "Web Analytics is enabled for <name>."
vercel project speed-insights <name>     # -> "Speed Insights is enabled for <name>."
```

## List deployments (FREE)
```
vercel ls            # NOT "vercel deployments" — that errors:
                     #   "deployments is not a valid target directory or subcommand"
```
Output: Age / Project / Deployment URL / Status (● Ready) / Environment / Username.

## List available metrics
```
vercel metrics schema            # 94 metrics (e.g. vercel.analytics_pageview.count,
                                  # vercel.request.count, vercel.function_invocation.*,
                                  # vercel.speed_insights.lcp_ms, vercel.firewall_action.count)
vercel metrics schema <prefix>   # narrow, e.g. vercel.web_analytics (note: prefix is NOT
                                  # a valid metric name — use the full dotted id from the list)
```

## Read pageviews (FREE — Web Analytics tier, no plan upgrade needed)
```
vercel metrics vercel.analytics_pageview.count --since 30d
# -> total / avg / min / max + 4h sparkline. Real data even on Hobby.
```

## TWO HARD GATES (hit 2026-07-14)
1. **Observability Plus (Pro/Enterprise) required** for most metrics. On Hobby/Free Pro:
   ```
   vercel metrics vercel.request.count --since 30d
   # Error: Observability Plus is required to run this query ... available on Pro and Enterprise
   ```
   Locked behind Plus: `vercel.request.*`, `vercel.function_invocation.*`,
   `vercel.firewall_action.*`, `vercel.ai_gateway_request.*`, `vercel.middleware_invocation.*`,
   `vercel.isr_operation.*`, `vercel.sandbox.*`, `vercel.external_api_request.*`,
   `vercel.bot_id_check.*`, `vercel.workflow_operation.*`.
   **Only `vercel.analytics_pageview.count` (Web Analytics) reads free.**
2. **Hobby plan = 7-day data window only.**
   ```
   vercel metrics vercel.speed_insights.lcp_ms --since 30d
   # Error: the hobby plan only grants access to the latest 7 days of data.
   ```
   Use `--since 7d` for Speed Insights on Hobby.

## `vercel inspect` needs a deployment UID, not the project name
```
vercel inspect sproutern
# Error: Can't find the deployment "dpl_sproutern" under the context <team>
```
Pass a deployment URL/UID from `vercel ls` instead.

## REST API via `.env.local` OIDC token — unreliable, prefer CLI
The `VERCEL_OIDC_TOKEN` in a project `.env.local` does NOT reliably authorize REST calls
(`curl https://api.vercel.com/v9/projects/<name>` returned nulls). The CLI uses the active
session token and just works. Use `vercel` commands; skip hand-rolled curl unless you've
confirmed the token scope.

## Worked example (sproutern, 2026-07-14)
- Live at https://www.sproutern.com (Production, all 9 deploys ● Ready).
- `vercel project web-analytics sproutern` → enabled; `speed-insights` → enabled.
- `vercel metrics vercel.analytics_pageview.count --since 30d` → **4,653 total** pageviews
  (avg 25.7/4h, max 104 on 07-08). Thin but real traffic.
- `vercel.request.count --since 30d` → blocked by Observability Plus (Hobby plan).
