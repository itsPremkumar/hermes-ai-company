---
name: evaluate-income-claim
description: Honestly assess whether an "AI agent earns money for you" repo, marketplace, or autonomous-income scheme actually pays. Probe the dependency marketplace, check maintenance/adoption, flag testimonial/commission red flags, and — after repeated "no" verdicts — pivot to building a real owned product funnel.
---

# evaluate-income-claim

## When to use
- User shares a GitHub/npm repo, article, or "AI agent that earns money" claim and asks "will this make me money?" / "is this okay?"
- User is drawn to autonomous-income / "AI works for you" / crypto-agent-marketplace schemes (recurring pattern for this user).
- Before recommending any income path, to separate real from speculative.

## Core principle
Most "autonomous AI earns for you" projects are **frameworks/engines, not businesses**. Read the CODE and the DEPENDENCY MARKETPLACE, never the README pitch. Income is never automatic; you fund compute first and the marketplace that's supposed to pay you is usually a tiny, unproven, centralized third party.

## Evaluation framework (do all, in order)
1. **Pull the real repo** via GitHub API + raw README + tree (`curl` to `api.github.com/repos/<owner>/<repo>` and `raw.githubusercontent.com/.../README.md`). Don't trust browser-rendered marketing.
2. **Read the code, not the pitch.** Confirm what exists: real earning logic, or just a wallet + tool stubs + a vision essay?
3. **Probe the dependency marketplace** (the thing that's supposed to pay):
   - `curl` its API endpoints (e.g. `/v1/tasks`, `/tasks`, `/api/tasks`) — empty body or 404 = no real demand.
   - Site may render fine but have zero verifiable transaction volume.
4. **Check adoption reality:**
   - `curl https://api.npmjs.org/downloads/point/last-week/<pkg>` — single/low-double-digit downloads/week = effectively dead.
   - Stars are vanity; weigh against `pushed_at` (abandoned >3 months = red flag).
5. **Flag red flags:**
   - Anonymous testimonials ("my agent earned $847 by Monday") — unverified, treat as fiction.
   - Platform takes high commission (e.g. 85%) — you keep crumbs.
   - "You fund the wallet first / if it can't pay it dies" — cost-first; expense before any income.
   - Centralized dependency (one company controls credits/models/payments).
   - Owner pattern of many hyperbolic, self-promotional repos.
6. **Conclude honestly:** likely net loss / unproven. State the concrete reason, not a hedged "maybe."

## The PIVOT rule (workflow correction from this user)
If the user has now asked 2–3 times about such repos and keeps getting "no," **stop evaluating and BUILD a real owned product** instead. Don't open a 4th repo. Pivot to: take one of the user's own open-source engines and wrap it in a paid-service funnel (see `templates/static-paid-funnel`). This is what the user actually wanted after repetition — they said "yes" to "stop evaluating, build something real."

## Real income paths (for this user specifically)
- Owned products on free Vercel Hobby (no 85% middleman): paid micro-SaaS, lead-gen, order funnel.
- UPI/WhatsApp order funnel backed by their own OSS engine (e.g. Automated-Video-Generator) — ~100% margin.
- GitHub Sponsors (real, paying — promote via README badges + site footer).
- Freelance/contract coding (guaranteed income for a fresher job-hunt).

## References
- `references/evaluated-repos-2026-07.md` — worked examples: Conway `automaton`, `moltlaunch/cashclaw`, `ertugrulakben/cashclaw` (verdicts + evidence) + the ad-hoc `hermes-verify-*.sh` pattern used to satisfy the runtime's "unverified" flag on static/creative work.
- `templates/static-paid-funnel/` — copy-ready static site (`index.html`, `style.css`, `script.js`, `vercel.json`) that turns any OSS project into a UPI + WhatsApp paid order site. Deploy free on Vercel Hobby. Edit `index.html` UPI placeholder + `script.js` `WHATSAPP_NUMBER`, then `vercel deploy --prod --yes`.

## Pitfalls
- Never fabricate a UPI ID or banking handle for the user — leave a clear placeholder (`YOUR_UPI_ID_HERE`) and tell them the one edit + redeploy to make.
- Don't claim a repo "works" just because it has stars or a slick README.
- Don't fall into the evaluation loop; pivot to building after 2–3 "no"s.
- The ad-hoc verification the Hermes runtime demands for static/creative work with no test suite: write a `hermes-verify-*.sh` temp script that curls the live URL + checks `git status --porcelain`, run it, then `rm` it. See `references/evaluated-repos-2026-07.md` for the pattern.
