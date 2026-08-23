# Vercel Web Analytics via MCP (traffic audits)

Verified end-to-end 2026-08 against project sproutern-oss.

## Connect (one-time, needs the user)
1. `setup_mcp(server='vercel', action='install')` — inline consent card in chat.
2. `setup_mcp(server='vercel', action='authorize')` — opens Vercel OAuth in the user's browser; ONLY the user can approve. `declined`/`unanswered` → finish other work, offer again later. Error 409 "already in progress" → a flow is waiting on the user; tell them to approve, do not spawn another.
3. PITFALL: running `hermes mcp test vercel` while unauthorized opens a SECOND redundant OAuth flow (extra browser tab, confusion). Use setup_mcp authorize only; test only after authorization succeeds.

## Discover ids — never guess slugs
- `list_teams` → real team id (`team_...`). Guessing a team slug from the account name FAILED ("Failed to list projects").
- `list_projects(teamId=<team_id>)` → project id (`prj_...`).

## Query patterns (`get_web_analytics`; always teamId + projectId, since + until together)
| Question | Call |
|---|---|
| Totals | `mode=count, dataset=visits, since/until` (ISO dates ok) |
| Daily trend | `mode=aggregate, by=['day']` |
| Top pages | `mode=aggregate, by=['requestPath'], limit=15` |
| Traffic sources | `mode=aggregate, by=['referrerHostname']` |
| Geography | `mode=aggregate, by=['country']` |

## Reading the numbers
- Empty-string referrer = direct/unknown traffic.
- Homepage takes ~90%+ of visitors while hundreds of deep URLs get ~0 entry points → weak indexing / no backlinks / funnel collapse after `/`.
- google.com referrers > 0 proves partial indexing even when a `site:` scrape shows nothing — GSC is the ground truth for queries/impressions; Vercel shows visits only.
- Placeholder analytics scripts elsewhere in the page (GTM/Yandex/Ahrefs/AdSense with `YOUR_*` ids) do NOT affect the Vercel beacon — stacks are independent.
