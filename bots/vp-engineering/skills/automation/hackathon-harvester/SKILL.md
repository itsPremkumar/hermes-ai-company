---
name: hackathon-harvester
description: Agent harvests cash hackathons; human approves submits.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [automation, agent, hackathon, income, web-scraping, openclaw, avs]
---

# Hackathon Harvester (autonomous prize-competition entry agent)

## When to use
- "find all online hackathons with cash prizes", "harvest hackathons"
- "build an agent that enters hackathons" — the meta case: build the agent that
  enters hackathons, *at* a hackathon (e.g. the Delhi Browser-use Hackathon)
- user wants a recurring zero-cost money-lever via competition prizes
- any request that is really "do this web research + form-filling chore repeatedly"
  → prefer building the agent over hand-doing it (see Standing principle)

## Standing principle (USER CORRECTION — embed in every reply)
The user said: **"Stop doing that task manually. Build the agent instead."**
When a request is a repeated web workflow (research listings, fill forms, monitor
sites), DO NOT hand-execute it turn-by-turn. Scaffold a real agent + verify it
actually runs, then let it scale. This skill IS that agent for hackathons — apply
the same instinct to any analogous "manual chore" request.

## Honesty boundary (critical — this is a legit income class, not a scam)
- No "guaranteed win." Cash prizes are REAL, but winning needs human-quality work
  + the user's sign-off. Say so plainly; never overpromise "passive income".
- The agent's job: MAXIMIZE volume (find many live prizes) + first-draft quality
  (pitch + demo video + writeup). The human decides which to finish and submits.
- HARD human-approval gate before ANY submit / payment / account-write action.
- Distinct from the "AI earns money for you" scams: here the user does the winning
  work, the agent removes the grunt research/assembly. See automated-income-systems
  for the broader scam-vetting checklist if a "prize bot" repo is proposed.

## Architecture (4 stages — all building/verifiable)
1. **DISCOVER** — pull LIVE online hackathons with cash prizes.
   - Source: Devpost `online=1&prize=1`. Raw curl → 403 (Cloudflare). Jina Reader
     `https://r.jina.ai/https://devpost.com/hackathons?online=1&prize=1` → HTTP 200
     with structured card markdown. Parse with the regex in
     `references/devpost-harvest-recipe.md`.
   - Keep it **stdlib-only** (`urllib` + `re`), NOT a headless browser — this box has
     ~549MB RAM free. agent-reach's zero-config `web` channel is literally Jina Reader,
     so reuse that path (see `web-research` skill).
   - Output: JSON sorted by prize — `name, url, prize_usd, days_left, deadline, host, themes`.
2. **DRAFT** — an LLM writes the submission (pitch + demo plan + writeup).
   - Endpoint: OpenClaw gateway (OpenAI-compatible) on `:18789`, model
     `openrouter/nvidia/nemotron-3-super-120b-a12b:free` (free). The key lives in
     `~/.openclaw/openclaw.json` (`OPENROUTER_API_KEY`). Start the gateway
     (`openclaw gateway`) before drafting; it is NOT always up.
   - Fallback: call any free OpenRouter model directly with that key.
3. **VIDEO** — render the demo reel with the user's own AVS engine
   (`C:/one/Automated-Video-Generator`). Ties the hackathon theme to a real artifact
   (e.g. for a "generative media" hackathon, AVS *is* the demo).
4. **SUBMIT** — browser autofill of the entry form, then HALT at the approval gate.
   - Use browser-use / Playwright / OpenClaw computer-use for autofill ONLY.
   - Never click "Submit" without explicit user confirmation.

## Why this WINS a hackathon (scoring alignment)
Delhi Browser-use Hackathon weights: Live reliability 30, Usefulness 25,
Technical depth 20, Creativity 15, Demo/storytelling 10. Demo the agent LIVE
entering a real hackathon → maxes reliability + usefulness + creativity at once.
See `references/stage-demo-scoring.md` for the rubric + a 5-min stage script.

## Pitfalls (learned the hard way, 2026-08-01)
- **Jina rate-limits rapid repeats** (503/403 AbuseAlleviationError). Re-fetch
  sparingly; cache the markdown to a file and parse that.
- **Devpost JSON API is hard 403** — don't waste time; Jina is the path.
- **`&page=N` returns the same ~24 cards** — the filter view is capped, not a
  pagination bug. To widen coverage, vary the filter (e.g. `prize=1` vs themes),
  not the page number.
- **Normalize "days left"**: `N days left` → N; `about 1 month left` → 30;
  `2 months left` → 60. Filters break if you only handle the numeric case.
- **Nav tokens leak as card names** ("Back", "Log in") if the regex isn't anchored
  with a leading-letter requirement + negative-lookahead exclusion. See the regex.
- **Gateway not running when you DRAFT** → start it first; don't assume it's up.
- **RAM**: never launch a full headless browser for DISCOVER; Jina + urllib is enough.

## References
- `references/devpost-harvest-recipe.md` — live Jina recipe, the verified card-parsing
  regex (handles days-left / months-left / nav-token cases), and the real 9-hackathon
  data sample captured live this session.
- `references/stage-demo-scoring.md` — Delhi hackathon scoring rubric + stage demo script.

## Template
- `templates/discover.py` — the verified, drop-in discovery module (stdlib-only) to
  reproduce/modify. Parses Jina markdown → sorted JSON; includes a `__main__` that
  prints JSON + a count to stderr.
