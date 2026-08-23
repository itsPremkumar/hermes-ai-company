# Verify AI agent comparison claims (Hermes vs Paperclip vs OpenClaw)

When a user pastes an AI-generated "comparison" doc about Hermes / Paperclip / OpenClaw
(or any agent stack), DO NOT trust its quantitative claims. Verify against live sources.

## The recurring trap (2026-07-15)
Two different AI-generated docs claimed fabricated stats:
- Hermes "140,000 GitHub stars in under 3 months, released Feb 2026, v0.18.0"
- Paperclip "38,000 stars in 4 weeks, 53,000 by early April, latest v2026.626.0"

**All of those were wrong.** Real GitHub API values (2026-07-15):
| Repo | Owner | Created | Stars | Forks | Latest release |
|---|---|---|---|---|---|
| `NousResearch/hermes-agent` | NousResearch | 2025-07-22 | 214,936 | 39,999 | v0.18.2 (2026-07-08) |
| `paperclipai/paperclip` | paperclipai (org) | 2026-03-02 | 73,676 | 13,726 | v2026.707.0 (2026-07-07) |
| `openclaw/openclaw` | — | — | (license NOASSERTION, NOT MIT) | — | — |

## How to verify (reusable pattern)
1. Stars / created / forks / latest release:
   `curl -s -H "Accept: application/vnd.github+json" https://api.github.com/repos/<owner>/<repo>`
   `curl -s -H "Accept: application/vnd.github+json" https://api.github.com/repos/<owner>/<repo>/releases/latest`
2. Latest *stable* release tag lives in `releases/latest`; newer **canary** tags (e.g.
   `canary/v2026.714.0-canary.16`) exist on `master` but are NOT "releases" — check `git tag -l`.
3. Source repos resolve (HTTP 200): `NousResearch/hermes-paperclip-adapter`, `paperclipai/paperclip`.
   Third-party blog comparisons (e.g. remoteopenclaw.com) may be OpenClaw-affiliated — treat star
   ratings/winners as editorial opinion, not authority. Their factual claims usually check out, but
   the narrative is often slanted and omits operational fragility (e.g. agents getting stuck in error).

## What to keep vs discard from such docs
- KEEP: the "different layers, not competitors" thesis; worker-vs-manager framing; the list of
  where each tool wins (Hermes = coding/memory/research; Paperclip = org/budgets/governance).
- DISCARD: any specific star count, release date, or version number not API-verified.
- ADD (the docs always miss it): the user's *integrated live setup* (Paperclip boss + Hermes employee),
  the monitoring requirement (agents get stuck), and the 3 human money-gates (no agent earns without
  the founder crossing marketplace-account / payment-link / first-publish).
