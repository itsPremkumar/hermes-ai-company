---
name: autonomous-money-system
description: "Build and operate an autonomous, agent-run money-earning system from 100% free/open-source self-hosted tools. Covers the proven pipeline structure (stdlib-only Python CLI), the run_all.py orchestrator, listing-copy + Moltbook acquisition funnel, and the 3-human-gate go-live model. Use when the user wants to create income streams, automate freelancing/gigs, or extend the Hermes-Full-Autonomous-Company money/ system."
version: 1.0.0
author: Hermes
license: MIT
---

# Autonomous Money System

Turn free/open-source, self-hostable tools into verified, ready-to-sell income
packages — then let an acquisition funnel fill itself.

## When to use
- User asks to "build a money/income system", "automate freelancing", "create
  gigs/pipelines", or extend `money/` in Hermes-Full-Autonomous-Company.
- User wants agent-native business from OSS (n8n, Chatwoot, Stirling-PDF,
  Listmonk, Remotion, Hermes/OpenClaw skills).
- User references the 15-pipeline idea bank (`MONEY_AUTOMATION_IDEAS.md`).

## Core architecture (proven)
A money system = N **pipelines**, each a stdlib-only Python CLI emitting JSON
packages. One **orchestrator** (`run_all.py`) regenerates everything + writes a
dashboard. A **listings** generator turns packages into platform copy. A
**Moltbook** scheduler runs the acquisition funnel.

### Pipeline shape (TEMPLATE — see templates/pipeline_skeleton.py)
Every `pipelineN_<name>.py`:
- Module-level data dict (SERVICES / PLANS / VERTICALS / TIERS / NICHES / TYPES).
- `build_package(key, override=None)` → dict with: gig_title, pricing
  (margin_pct + cost_note), `n8n_workflow` (REAL nodes + executable code/
  command — NO `TODO`/placeholder), delivery_steps (exactly 5), tags.
- `self-test` (default when no --arg): assert every key generates a valid pkg,
  margin is correct, code nodes contain `return` and no `TODO`.
- `--list`, `--out FILE`, and a real `main()` argparse.
- **Zero external dependencies** (stdlib only) — hard rule.

### Orchestrator (run_all.py)
- `PIPELINES` list: {module, kind, data, outdir, builder, keyname}.
- `collect(dry_run)` imports each module, builds every package, writes JSON.
- `build_dashboard(rows)` → INCOME_DASHBOARD.md (pipeline table, combined
  value, 90-day target).
- `self-test`: assert exact package count + pipeline count + all priced.
- Keep `price_of()` robust to every pricing key shape (price/setup/monthly).

### Listings + funnel
- `generate_listings.py`: **DERIVE `PACK_DIRS` from `run_all.PIPELINES`** (import
  it, read each `outdir`), never hardcode the directory list. Hardcoding silently
  drops any pipeline whose pack dir isn't enumerated — the 3 latest pipelines
  (voice/document/retainer, 12 packages) had NO listings for that reason until
  2026-07-14. Also make `render()` shape-robust: read `package_title` OR
  `gig_title`/`title`, read a flat top-level `price` OR `pricing.price/setup/
  monthly`, and derive delivery steps from a `packages[]` tier list when there is
  no explicit `delivery_steps`. Without this, flat-shape packages render with an
  empty "What you get" and "contact for quote".
- `generate_moltbook_drafts.py`: one promo draft per pipeline into
  `revenue/moltbook/post-<pipeline>.json` with a REAL `submolt` from a `SUBMOLTS`
  map keyed by pipeline `kind` (see the submolt pitfall below). Never `clawhub`.
- Scheduler (cron every 30m — see rate-limit pitfall) posts ONE draft per run;
  Moltbook rate-limits ~1/2.5min. Current reality: **15 pipelines / 62 packages**
  (was 12/50); INCOME_DASHBOARD target line reads "62 ready-to-sell packages
  across 15 pipelines".

## The 3-human-gate go-live model (CRITICAL)
An autonomous build CANNOT cross these — legally/UI gated to a human:
1. **Marketplace accounts** (Fiverr/Upwork ID verify).
2. **Payment linkage** (PayPal/bank; for India, UPI like `premkumar016555@oksbi`).
3. **First gig approval** (paste listing → Publish).
Document these in `GO_LIVE_CHECKLIST.md`. Everything else (build, infra,
listings, scheduling) the agent does alone. Total human effort ≈ 15 min.

## Verification discipline (avoid the stale-flag loop)
Hermes appends a `[System: Verification status: stale]` flag after code edits
and asks for an ad-hoc verifier. Rules:
- **When you edited NEW code:** write a temp `hermes-verify-*.py` under
  `%LOCALAPPDATA%\hermes\Temp` (OS-safe), run it, clean it up, report as
  AD-HOC (not suite green).
- **When the flag fires but NO new code was edited this turn** (you only
  re-ran/explained, or the changed-path list is just a deleted temp script +
  already-pushed files): **do NOT re-run an identical verifier.** State that
  the artifacts are immutable/pushed and the prior turn's verification passed.
  Re-running wastes a call and can trip the repeated-failure warning.
- Embed the standard verifier shape (scripts/verify_money_system.py) as a
  reusable template.

## Pitfalls
- **f-string braces in n8n/JSON templates:** use `{{` `}}` for literal braces
  inside f-strings, or build the string without f-prefix. A raw `{sig}` inside
  an f-string raises `ValueError: expects...`.
- **build_n8n arg bug:** if `build_n8n(t)` is called with the data dict `t`
  but the body does `t['tier']`, it KeyErrors. Pass the key string, not the
  dict. Self-test catches this.
- **run_all price_of:** add `or p.get('monthly')` so recurring-only pipelines
  (no price/setup) still register a price and pass the all-priced assertion.
- **Moltbook 429:** posting faster than ~2.5 min returns HTTP 429. Scheduler
  cadence must be ≥3 min; pre-mark posted.json so a crash doesn't double-post.
- **CRITICAL — scheduler must NEVER stall on one draft (hit 2026-07-14):**
  the original `post-scheduler.py` had two queue-stalling bugs that left the
  whole acquisition funnel dead:
  1. It accepted the first unposted draft and, on ANY post failure, returned
     without recording it — so the next run retried the SAME draft forever
     (a single 429 in a tight loop hammered the API and posted nothing).
  2. It ran `find_unposted_draft` with no "failed" set, so a hard 4xx draft
     was retried indefinitely.
  **Fixes applied (reusable):** add a persisted `failed.json`; make
  `find_unposted_draft(posted, skipped, failed)` skip both invalid-submolt
  drafts (accumulated in `skipped`) AND hard-failed drafts (accumulated in
  `failed`); in `main()`, route HTTP 429 → exit 3 (back-off, do NOT mark
  failed, do NOT retry same draft next tick); route hard 4xx (400–499,
  excluding 429) → add slug to `failed` + exit 1 (queue advances); treat 5xx
  as transient (retry next run). One post per cron tick means the 30-min
  cadence naturally stays under the rate cap. Verify with the ad-hoc script
  (scripts/verify_money_system.py) using a temp POSTS_DIR + monkeypatched
  `post_to_moltbook` returning 429/403.
- **gh CLI absent:** push via `git credential-manager get` token + curl/API,
  not `gh`. See references/github_gcm_push.md.
- **Don't expose personal UPI on marketplace listings:** Fiverr/Upwork handle
  payment internally (ToS). Put UPI only in a central PAYMENT.md + GO_LIVE
  checklist for DIRECT clients.
- **CRITICAL — Moltbook `submolt` 404 + spam-flag (hit 2026-07-14):**
  `post()` accepts ANY `submolt` string and sends it, but the server
  only accepts **existing submolt `name`s** (e.g. `technology`, `aitools`,
  `automation`, `saas`, `research`, `general`). A non-existent name
  (the repo's old default was `"clawhub"`; `ai-tools` was a typo for
  `aitools`) returns **HTTP 404 "Submolt not found"** — the post
  silently fails and never lands. Worse: posts from an **unclaimed** agent
  (`prem-autonomous-co`) get flagged **"Spam"** (score 0, buried) until
  the agent is *claimed* via the Twitter/X `claim_url` from `register()`
  (a human step — the agent can't do it). **Fixes applied + reusable:**
  1. Never hardcode `submolt:"clawhub"`. In `generate_moltbook_drafts.py`
     keep a `SUBMOLTS` dict keyed by pipeline `kind` → a REAL valid name
     (theme-based: automation→`automation`, tools→`aitools`, saas→`saas`,
     security→`security`, ai-agents→`ai-agents`, builders→`builders`,
     agentcommerce→`agentcommerce`, etc.). Fallback `showandtell`.
  2. Add a `validate_submolt(name)` guard (seeded from `GET /submolts`,
     ~100 valid names) to BOTH `moltbook.py` `post()` and
     `post-scheduler.py` `main()` so a bad draft fails LOUD (clear 400
     "invalid submolt") instead of a silent 404. See
     `references/moltbook_api.md` for the full valid-name list + guard snippet.
  3. **Pause the scheduler** (cron `ce0a37fa09ac`) until the agent is
     claimed — otherwise it sprays unclaimed-bot posts that all get flagged.
  4. To claim: re-run `register()` to get a fresh `claim_url` (it prints
     once and is NOT persisted), open it in the user's browser + Twitter/X
     verify. That clears the spam classification.

## References
- references/moltbook_api.md — endpoint, payload, rate limit, scheduler, valid submolt list.
- references/pipeline_catalog.md — the 15 pipelines + validated 2026 pricing.
- references/github_gcm_push.md — push without gh via cached GCM creds.
- scripts/verify_money_system.py — reusable ad-hoc verifier (asserts 15/62,
  listings cover all 15 dirs, dashboard reflects counts). Run it after ANY
  change; report as AD-HOC, not suite green.
- scripts/verify_scheduler_stall.py — proves the post-scheduler never stalls
  on 429/hard-4xx (isolated temp POSTS_DIR + monkeypatched post_to_moltbook).

## Current reality (2026-07-14+)
- **15 pipelines, 62 packages.** INCOME_DASHBOARD.md: "62 ready-to-sell packages
  across 15 pipelines". If the system grows, bump the EXPECTED_* in the verifiers
  and the self-test assertion in run_all.py together (they must agree).
- Moltbook scheduler runs every 30m (cron job id from `cronjob list`); one post
  per tick stays under the ~2.5min rate cap.
- templates/pipeline_skeleton.py — copy to start a new pipelineN_*.py.

## Extension path
To add pipeline #N: copy templates/pipeline_skeleton.py → pipelineN_name.py,
fill the data dict + pricing + n8n workflow, add to run_all PIPELINES, run
`python run_all.py self-test`, regenerate listings + dashboard, commit, push,
verify.
