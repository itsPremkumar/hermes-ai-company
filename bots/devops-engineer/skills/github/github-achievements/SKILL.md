---
name: github-achievements
description: Earn legitimate GitHub profile Achievements (badges) for a user — the badge roadmap, what each badge requires, which can be triggered deterministically via gh/MCP, and the hard rule that badges cannot be minted by API/fake activity. Use when the user says "earn more github badges/achievements", "increase my github profile", or asks which badges they have/are missing.
---

# github-achievements

Help a user earn **real, legitimate** GitHub Achievements (the puzzle-piece badges
on a profile). The core constraint: badges are granted ONLY by genuine platform
activity — there is no API or MCP call that mints them, and faking stars/commits/PRs
breaks GitHub ToS and destroys profile credibility (esp. for a job-seeker profile).

## The one rule that governs everything
- **Never fabricate activity.** No fake stars, no fake commits, no invented
  co-authors, no bot PRs. Every badge earned must come from a real action the user
  actually did or explicitly authorized.
- Badges can't be read or written via API (the `achievements` GraphQL field was
  removed by GitHub — `Field 'achievements' doesn't exist on type 'User'`). To see
  current badges, **screenshot the live profile** (browser + vision) and read the
  Achievements row. Don't promise to "list your badges via API".

## Badge roadmap (tiers by effort)

### Tier A — instant, zero-cost, deterministic via gh/MCP (do first)
| Badge | Legit trigger | How (gh) |
|---|---|---|
| **Quickdraw** | Open + close/transfer an issue or PR on your own repo within 5 min | `gh issue create` then `gh issue close` on own repo |
| **YOLO** | Merge a PR with NO review to your own repo | open a PR, `gh pr merge --merge --delete-branch` (needs UNPROTECTED branch — verify `gh api .../branches/main/protection` → 404) |
| **Pair Extraordinaire** | A commit co-authored by a *real, different* GitHub user | needs a real co-author handle from the user — DO NOT invent one. Use `Co-authored-by: Name <email>` trailer |
| **Profile polish (visual, not an official badge)** | shields.io stat widgets in profile README | see quirks: verify badge hosts are alive first |

### Tier B — short term, real activity (1–4 weeks)
| Badge | Trigger | Action |
|---|---|---|
| **Starstruck x3/x9** | repos reaching 10★ / 100★ | push sproutern/free-llm-router to 10★ via honest promo (pin, star-history chart, marketing reels) |
| **Pull Shark x3/x9** | more merged PRs | route AVS/sproutern work through PRs (even own repos) to multiply count |
| **Galaxy Brain x3** | 2 / 8 / 16 accepted Discussion answers | find active Discussions in popular repos, answer helpfully |
| **Public Sponsor** | sponsor any dev via GitHub Sponsors | costs $1+ — user's call |
| **Sponsorship (received)** | get sponsored | grow reach (sproutern reels) → attract sponsors |

### Tier C — longer term / has cost or prerequisite
| Badge | Trigger | Caveat |
|---|---|---|
| **Open Sourcerer** | merged PR to a qualifying org (GitHub, Homebrew, Electron…) | needs real OSS contribution |
| **Heart On Your Sleeve** | profile README + sponsor someone | — |
| **Time Warp** | commit on your GitHub birthday | calendar-based |
| **Adventurer** | commit on Jan 1 | calendar-based |
| **Arctic Code Vault** | had commits in 2020 archived snapshot | NOT attainable anymore (2020-only) |
| **Mars 2020 / Polar / Footprint** | commit during specific event windows | mostly missed |

## Housekeeping that makes badges "land" better
- Archive/curate low-value auto-generated repos so flagship repos dominate the pinned view.
- Pin top 6 repos. Add a social preview image + enable GitHub Sponsors profile.

## Verify before claiming done
- Screenshot the live profile (`https://github.com/<user>`) via browser + vision;
  confirm the new badge tiles render (not broken images).
- For README badge changes: verify each badge host is alive
  (`curl -s -o /dev/null -w "%{http_code}" <url>`) BEFORE committing — dead hosts
  (e.g. `visitor-badge.laowi.com` is offline, http_status=000) show as broken images
  on a job-seeker profile. Remove them.
- Don't "fix" a shields.io value that disagrees with a manual sum — e.g.
  `github/stars` badge showed 115 while owned-repo `stargazerCount` summed to 62; the
  badge is a real GitHub number (includes profile repo + other sources), just not
  "stars received on my code". Leave it.

## See also
- `github-repo-growth` for the secure MCP wiring + reach levers.
- `github-repo-growth/references/gh-api-quirks.md` for the Windows `gh.exe` path bug
  and the working stdin/base64 git-data pipeline used to create PRs without touching
  the local working tree.
