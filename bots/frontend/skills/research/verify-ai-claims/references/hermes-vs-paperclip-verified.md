# Hermes vs Paperclip — verified numbers bank

Live GitHub API data captured **2026-07-15** while fact-checking two
AI-generated "Hermes Agent vs Paperclip AI (July 2026)" comparison docs.
Use this as the ground-truth bank when an AI pastes claims about these two.

## Verified facts (GitHub API, 2026-07-15)

| Field | Hermes Agent (`NousResearch/hermes-agent`) | Paperclip (`paperclipai/paperclip`) |
|---|---|---|
| Stars | **214,936** | **73,676** |
| Forks | 39,999 | 13,726 |
| Created | **2025-07-22** | **2026-03-02** |
| Latest release | **v0.18.2** (tag `v2026.7.7.2`, pub 2026-07-08) | **v2026.707.0** (pub 2026-07-07) |
| Owner | `NousResearch` | `paperclipai` (org) |
| Description | "The agent that grows with you" | "The open-source app everyone uses to manage agents at work" |

Recent Hermes tags: `v2026.7.7.2`, `v2026.7.7`, `v2026.7.1`, `v2026.6.19`, `v2026.6.5`.
Recent Paperclip tags: `v2026.707.0`, `v2026.626.0`, `v2026.618.0`, `v2026.609.0`, `v2026.529.0`.

## Fabricated claims found in the pasted docs (DO NOT repeat)

- "Hermes = **140,000 GitHub stars in under 3 months**, released **Feb 2026**,
  **v0.18.0**" → real: 214,936 stars; created **2025-07-22**; latest **v0.18.2**.
  (Under-counts stars AND misstates the launch date AND the version.)
- "Paperclip released March 2026 by @dotta, 38k→53k stars" → date is roughly
  right (2026-03-02) but the star figures were already stale/low vs the live
  73,676; and "v2026.626.0 (June 2026)" was presented as latest when a newer
  **v2026.707.0** (July) existed.

## Lesson (this is the reusable technique)

AI comparison docs lie about **three** measurable things, not just stars:
1. **Star / fork counts** (usually off by 2–10×).
2. **Version numbers** — verify against `/releases/latest` (tag_name) and `/tags`.
3. **Release / launch dates** — verify against repo `created_at` and release `published_at`.

Opinion/positioning text (worker-vs-manager framing, "complementary not
competitors", budget/governance advantages) is usually sound — keep it, fix
only the numbers.

## Verification recipes (copy-paste)

```bash
# repo root: stars, license, created_at
timeout 20 curl -s "https://api.github.com/repos/<owner>/<repo>" | python -c \
  "import sys,json;d=json.load(sys.stdin);print(d.get('stargazers_count'),d.get('license',{}).get('spdx_id'),d.get('created_at'))"

# latest published release: tag + date
timeout 20 curl -s "https://api.github.com/repos/<owner>/<repo>/releases/latest" | python -c \
  "import sys,json;d=json.load(sys.stdin);print(d.get('tag_name'),d.get('published_at'))"

# recent tags (confirm a version exists)
timeout 20 curl -s "https://api.github.com/repos/<owner>/<repo>/tags?per_page=5" | python -c \
  "import sys,json;print([t.get('name') for t in json.load(sys.stdin)[:5]])"
```

Rate-limit guard: rapid API pulls can return a JSON error blob — pipe through
`python -c "json.load(...)"` and on `KeyError`/`TypeError` retry once with a 2s
sleep. Don't treat a rate-limit blob as real data.
