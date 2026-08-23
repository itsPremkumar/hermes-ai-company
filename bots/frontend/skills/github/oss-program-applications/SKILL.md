---
name: oss-program-applications
description: Use when drafting OSS program/grant application answers.
---

# OSS Program & Grant Applications

Drafting answers for open-source program / grant application forms: "why does this repository qualify", maintainer role, how you'll use credits/funding, anything-else fields. Includes the OpenAI Codex for Open Source Program and similar forms.

## Golden rule
NEVER quote stats from memory, README badges, or last week's session — pull live numbers from the GitHub/npm APIs each time. Fabricated or stale numbers in an application are disqualifying, and the metrics change weekly.

## Workflow
1. **Verify repo facts in one batch** (independent calls, run together):
   - `gh repo view --json stargazerCount,forksCount,openIssuesCount,description,licenseInfo,url,nameWithOwner` (fall back to `gh api repos/<owner>/<repo>` if the view subcommand lacks fields)
   - Activity proof: `git -C <repo> log -1 --format=%cd` or `pushed_at` from the API — "last push today" is a strong signal, say it only if true
   - npm downloads: run `scripts/npm-stats.sh <package>` (bundled with this skill) — never hand-write the API calls again
2. **Draft per form section.** Common sections: role (primary/core maintainer?), why the repo qualifies (metrics + ecosystem importance), how you'll use credits/funding, anything else. Max 500 chars on most fields.
3. **Enforce character limits mechanically** — never eyeball:
   - `python -c "print(len('''<answer>'''))"` in a heredoc, then trim iteratively until ≤ limit
   - Landing at or near the cap (e.g., exactly 500/500) looks deliberate; when over, keep the strongest 2-3 stats + the positioning clause and cut adjectives
4. **Account-specific fields CANNOT be agent-filled** (OpenAI org ID, billing, personal account links). Give the user precise lookup steps instead: e.g. org ID at `platform.openai.com/settings/organization` → string starting `org-`. Never invent one.
5. **Deliver two layers**: (a) ready-to-paste exact answer, (b) a longer "full detailed" version (stats table + reasoning) so the user understands the pitch and can adapt it to other programs.

## Pitch framing that works (AI-ecosystem programs)
- Lead with **positioning, not raw numbers**: "MIT-licensed, zero-cost, self-hosted alternative to paid SaaS (name 2-3 competitors)" beats a bare star count.
- Modest traction is fine — lean on: growth trajectory (created → now), release-correlated download spikes (proof people install when you ship), daily commits, open issues from real users, permissive license, multi-surface reach (desktop app / CLI / MCP server).
- For OpenAI-flavored programs, say the **MCP server / agent-tooling angle** explicitly — it aligns with their ecosystem.
- Credit/funding-usage answers should propose an *optional* integration that keeps the existing free default intact, with measurable outcomes (cost-per-video telemetry, CI integration tests, benchmark vs current routing). That framing is what reviewers reward.

## Pitfalls
- **npm `range` API shape**: entries are `{"day": "...", "downloads": N}` — SUM the `downloads` values. Slicing the entry dict or counting entries produces garbage: `Counter(k['day'][:7] for k in days)` counts DAYS per month (~28-31), not downloads — it contradicted the `point` API (205) and caused a false alarm before the correct sum (748) was found.
- **npm counts include CI/bots/mirrors** — 205 last month ≠ 205 humans. Cite release-day spikes (e.g. 165 on a v5.0.0 launch day) as the honest adoption signal, and use the 6-month range total to show trend.
- `last-month` = trailing 30 days (start/end echoed in the response); use the range API for calendar-month comparisons.
- Verify the user's role (sole creator vs contributor) from the repo/README before calling them "primary maintainer".

## Support files
- `scripts/npm-stats.sh <package>` — verified npm download stats: last-month point + 6-month range with per-month sums and top days.
- `references/codex-oss-program.md` — Codex for Open Source question set + the verified 500-char answers crafted for Automated-Video-Generator (stats as of 2026-08-01, org-ID steps, framing notes).
