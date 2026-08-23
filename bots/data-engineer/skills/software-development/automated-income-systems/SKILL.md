---
name: automated-income-systems
description: Design, build, and maintain zero-cost, Hermes-agent-automated online income systems (affiliate blogs, Gumroad product factories, free tool hubs) that run hands-off via cron. Use when the user wants to "make money online for free / with zero investment / fully automated" and has only a laptop + internet + Hermes.
---

# Automated Income Systems (zero-cost, Hermes-automated)

## When to use
- User asks to "make money online," "passive income," "zero investment," "fully automated money," or wants the agent to build AND run a money-making system.
- They have a laptop + internet + Hermes and want NO paid tools.
- User has a running Paperclip company with Hermes agents and wants to monetize it (see the Paperclip-specific revenue architecture below).

## Paperclip + Hermes Agent Company Revenue Architecture

If the user already has a Paperclip company running (7+ Hermes agents with heartbeat), use this architecture instead of the static-site approach:

### Core Stack
- **Paperclip** — orchestrator (company board, agent management, issue tracking)
- **Hermes agents** (CEO, CTO, CMO, COO, CFO, HoP, QA) — autonomous workforce
- **Claude Code** — heavy code generation (CLI tools, NPM packages, complex templates)
- **OpenCode** — parallel code builds, review, documentation

### Revenue Streams for Agent Companies

| Stream | Product | Price (USD) | Margin | Built By |
|:-------|:--------|:-----------:|:-----:|:---------|
| Prompt Libraries | Sales prompts, dev prompts, content prompts | $9-$19 | 95% | Hermes CMO |
| Blueprint Kits | Paperclip company blueprints, content machine | $47-$97 | 95% | Claude Code + Hermes CTO |
| Ebooks | "Zero to $10k/mo" style guides | $19-$29 | 95% | Claude Code |
| CLI Tools | Agent-config-generator, prompt-executor | Free + $29 Pro | 95% | OpenCode |
| Video Templates | Remotion/AVG video packs | $29 each | 95% | AVG pipeline |
| Fiverr Services | 5 gigs (setup, content, code review, video) | $49-$299 | 90% | Hermes COO |

### Implementation Process
1. **Create Paperclip issues** — one per product/revenue stream, assigned to the right agent
2. **Agents build products autonomously** — via Paperclip heartbeat/API
3. **Built products go to** `revenue/digital-products/` organized by category
4. **Platform listings** (Gumroad, Fiverr, Medium, GitHub Sponsors) set up in `revenue/platform-setup/`. See `references/platform-listing-copy.md` for copy structure, tone rules, pricing patterns, and a pre-publish checklist. Worked examples from a real build live under the subdirectories.
5. **Financial tracking** via `revenue/financial-dashboard.md` (updated weekly)
6. **Automated cron** — `revenue-engine-pulse` checks progress every 2h

### Target: ₹5,00,000/mo ($6,000/mo) from Tier-1 Countries (US, UK, CA, AU, EU)
See the complete financial model at `revenue/REVENUE-MASTER-PLAN-v2.md`
Key metric: 300 digital product sales + 10 Fiverr orders + Medium earnings + GitHub sponsors

## Core honesty principle (embed in every reply)
The agent can automate **creation + publishing 100%**, but THREE things only the user can do (all free, ~20 min once):
1. Open the free payout accounts (Amazon Associates, ShareASale, Gumroad) and paste IDs into config.
2. One `git push` to a free GitHub repo + enable Pages.
3. Drive traffic (post weekly drafts to Reddit/Quora/X). No visitors = no income.
Also: this compounds weekly, it is NOT overnight passive income, and you cannot guarantee earnings. State this plainly — do not overpromise. The deliverable is working, self-running software; the income is the user's to activate.

## Proven 8-stream architecture (all free, all verified building)
A–F below; G–H close the loop.
- **A. Affiliate blog** — agent researches 3-5 real products via web search, writes a 1200-1800 word SEO buying guide with `{{AMAZON:Keyword}}` / `{{SHAREASALE:id:kw}}` affiliate tokens, rebuilds + publishes. Monetizes via Amazon Associates / ShareASale.
- **B. Gumroad product factory** — `generate.py` emits a real, usable digital product (Notion template, prompt pack, budget sheet) into `gumroad/products/<slug>/` as `PRODUCT.md` + `LISTING.txt`; user uploads to Gumroad (free) and sets a price.
- **C. Free tools hub** — a static client-side HTML/JS calculator page (compound interest, BMI, loan) monetized via affiliate "sponsored picks". No backend, no tracking.
- **D. Fiverr affiliate guides** — `fiverr/generate.py` emits "how to hire on Fiverr" niche guides with a `{{FIVERR:category}}` token (expands to `fiverr.com/categories/<cat>?source=affiliate_fiverr&aff_id=<id>`). Fiverr Affiliates is free to join and pays per referred first-time buyer.
- **E. Print-on-Demand (Printify)** — `pod/generate.py` emits an SEO POD listing (niche + product type + 3 design angles + title/13 tags/description + a free Stable-Diffusion design prompt). User pastes into a **free Printify storefront**; Printify prints + ships only on each sale → **no upfront cost, highest upside**.
- **F. Traffic drafts (the moneymaker)** — `promo/generate.py` reads ALL published assets (articles, Gumroad products, POD listings) and writes **ready-to-post drafts** for Reddit / Quora / X / Pinterest into `content/_promo-drafts.md`, dated, newest-on-top. THE AGENT ONLY DRAFTS — the user pastes into their free social accounts. Without this, streams A–E produce assets nobody sees. Cron runs weekly (Sat), after the other streams have produced content.
- **G. Support/FAQ layer** — `support/generate.py` emits a static `docs/support.html` (self-serve FAQ) + `content/_support_prompts.md` (a copy-paste prompt for a LOCAL LLM/Ollama to answer customer questions). This removes manual support labor. **MUST be invoked by `build.py` itself** (see Pitfalls: generator-into-docs), not only run manually, or it gets wiped by `autorun.sh`'s `rm -rf docs`.
- **H. Owned service funnel (India-native, manual-fulfillment) — NEW, VERIFIED live 2026-07-14.**
  Unlike passive streams, this is a DIRECT, OWNED service business: a static order site where real
  customers pay YOU (no middleman, no commission) for work you fulfill using your OWN open-source
  engine. Built + deployed this session as `Prem AI Video Studio` on the user's own
  `Automated-Video-Generator` (Remotion+Edge-TTS faceless videos). Stack: **Vercel Hobby ($0)**
  static site → order form opens a **pre-filled WhatsApp deep-link** (`https://wa.me/<intl-number>?text=<encoded>`)
  to the user's number → customer pays via **UPI** (creator-owned, India-native; the one payment
  method Gumroad/PayPal do NOT support). Margin is near-100% because the engine is free/self-hosted
  and fulfillment costs minutes of local compute. **Why it beats the agent-marketplace repos:** no
  dead marketplace, no 85% cut, no anonymous testimonials — you control the customer + the payout.
  **When to use:** user has a reusable engine/product and wants REAL paying customers fast. Delivery
  is manual (you/agent render the video), so it's not "autonomous income" — be honest about that.
  See `references/owned-service-funnel.md` for the verified deploy recipe (vercel.json static config,
  WhatsApp link builder, UPI placeholder pattern, live-verify curl checks) and `templates/service-order-site/`
  for the copy-paste site scaffold.

All eight cross-link on the site for SEO + cross-traffic. One Hermes cron per stream (different weekday) runs: generate asset → rebuild → publish.

### Agent-native distribution + direct-earning channels (expanded 2026-07)

For an OpenClaw/Hermes/Paperclip stack, this distribution class outperforms the
static-site streams because the publish step is itself agent-automatable. New in
2026-07: **direct-earning marketplaces** where agents work and get paid directly.

#### Free distribution channels (build + publish, agent-automatable)
- **ClawHub** (`clawhub.ai`) — OpenClaw's native skill/plugin registry. `clawhub` CLI
  publishes a skill folder (`SKILL.md` + tool) in ONE command. Everything on ClawHub is
  **FREE** — it is a *distribution* channel, not a storefront. Money is made *off* it
  (premium Gumroad versions, custom builds, setup-as-a-service). **Automatability: ~95%**
  — if the `clawhub` CLI is already authed (`clawhub whoami` ✔), the agent can build +
  publish with zero human action. This is the most end-to-end-automatable channel.
- **Moltbook** (`moltbook.com`) — "Reddit for AI agents"; a social network where agents
  post autonomously. Has a live REST API (`/api/v1`, Bearer token). Flow: `POST
  /agents/register` → returns `api_key` + `claim_url` (human verifies via Twitter/X) →
  `POST /posts` needs a **claimed** agent (403 until claimed). **Pitfalls:** (1) the
  `/posts` text endpoint REJECTS a top-level `link` field (400 "property link should not
  exist") — embed URLs in the post body; (2) aggressive **rate-limit (429)** on bulk
  posting — space posts out (retry every ~45-90s, max a few per session); (3) the API
  key must be gitignored (`.moltbook_key`) and NEVER exported to product repos.
  **(4) INVALID `submolt` = SILENT 404 (HIT 2026-07, cost real posts):** `POST /posts`
  accepts `submolt` ONLY as the `name` of an EXISTING submolt (e.g. `general`,
  `technology`, `science`, `gaming`, `art`, `music`, `cryptocurrency`, `news`). A made-up
  name like `"clawhub"` returns **404 "Submolt not found"** — and the draft-based scheduler
  (`post-scheduler.py`) only appends to `posted.json` on 200/201, so a 404 draft just
  never posts and looks "queued" forever. Symptom: scheduler runs OK (`last_status: ok`)
  yet nothing appears on Moltbook. **FIX:** (a) every draft's `submolt` must be a real
  submolt name — grep `post-*.json` for any non-allowlisted value and rewrite; (b) harden
  `moltbook.py`/`post-scheduler.py` with a `validate_submolt()` that rejects unknown names
  BEFORE the network call (allowlist or fetch-valid-list), so a bad draft fails LOUD instead
  of 404-ing silently; (c) the canonical `post()` in `moltbook.py` is the single source
  of truth — call IT, not a duplicated inline POST in the scheduler.
  **Verify a post actually landed:** after `post()`, fetch it back by id
  (`GET /api/v1/posts/<id>`) and assert HTTP 200 — a 201 from `post()` alone is NOT
  proof it's visible. The research-post fix this session: `post-research-ideas.json` used
  `"clawhub"` → 404; changed to `"technology"` → 201 + live.
- **GitHub OSS repos** — each ClawHub skill gets its own public GitHub repo under
  `github.com/itsPremkumar/<slug>` for independent forking, installing, and selling.

#### Direct-earning marketplaces (agents work and earn money directly) — NEW
- **HYRVE AI** (`hyrveai.com`) — First AI agent marketplace. 5,750+ community, **takes ~85%
  commission (creator keeps ~15%)** — verified 2026-07-14 by reading its own README; a near-
  predatory cut. Agents self-register via API. Payments: Stripe (USD/EUR), USDT, stablecoin via
  MPP. **Treat as UNVERIFIED for real payouts** — its companion `ertugrulakben/cashclaw` repo
  uses anonymous "$847 by Monday" / "Guard saved me $4,700" testimonials, ~2k/week npm
  downloads, and ZERO audited transactions. **Automatability ~90% but income unproven and margin
  destroyed by the commission.** Prefer a DIRECT owned service (pattern below) over this.
- **The Colony** (`thecolony.cc`) — Agent social network + marketplace. Topic-based forums
  with paid tasks and document sales. OpenClaw skill exists for direct integration.
  **Automatability: ~70%**.
- **AgenC** (`tetsuo-ai/AgenC`, 190★) — Agent hiring protocol on Solana mainnet.
  Agents get hired and paid in tokens. **Automatability: ~60%** (Solana wallet needed).
- **Agoragentic** (`rhein1/agoragentic-integrations`) — Cross-framework agent commerce.
  50+ framework adapters, settle in USDC on Base. **Automatability: ~50%**.

#### Monetization funnel (revenue layer)
- **Gumroad** — the *storefront* money layer. Premium versions of free ClawHub skills,
  prompt packs, etc. Human-gated: user creates account + links payout + clicks Publish.
- **Affiliate programs** — Amazon Associates, ShareASale, Fiverr Affiliates. User fills
  IDs into config; agent drafts content with token placeholders.
- **Donation layer** — each ClawHub skill README + Moltbook post carries a donation ask
  (GitHub Sponsors / Buy Me a Coffee). Works only AFTER an audience exists.

**Funnel:** ClawHub (free skill = distribution) → Moltbook + Colony (agent posts
announcements) → HYRVE / AgenC (direct earnings) + Gumroad + affiliates (indirect
revenue). The agent runs everything except payout account linking and Gumroad publish.

- **Per-project repo split:** when a product is reusable, ALSO push its source to its own
  GitHub repo (create via API `POST /user/repos`, stage files, `git pull --rebase` the
  auto-LICENSE, then push). Keep a `repo-index.md` in the main repo linking every product
  repo URL + status. Exclude secrets (`.moltbook_key`, `*.key`) from product repos.
- **Payment reality (India / global):** Gumroad, GitHub Sponsors, Buy Me a Coffee, and
  PayPal ALL pay out via **PayPal or bank wire (USD)**. **UPI is NOT supported by any of
  them** — do not ask the user for a UPI ID, and never put payout credentials in agent
  context. Chain for an Indian creator: buyer → platform → PayPal → withdraw to Indian
  bank. See `references/agent-native-channels.md` for the condensed research + recipes.

### Verify a program is real BEFORE building on it
Search-engine HTML endpoints (DuckDuckGo/Bing) often return captchas/empty for automated fetches. Two reliable checks instead:
1. **Program is live/free** — hit its official page directly with curl + check HTTP status:
```bash
curl -s -o /dev/null -w "%{http_code}" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" --max-time 15 URL
# 200 = live / free to join;  301/404 = moved or gone;  000 = blocked
```
2. **Find candidate repos** — GitHub repo-search API (see `references/github-repo-discovery.md`):
```bash
curl -s "https://api.github.com/search/repositories?q=<query>&sort=stars&order=desc&per_page=5" | python -c "import sys,json; d=json.load(sys.stdin); [print(it['stargazers_count'], it['full_name'], (it.get('description') or '')[:70]) for it in d.get('items',[])]"
```
Build only on what returned 200. Confirmed this session: Fiverr Affiliates (200),
Amazon Associates (200), Spreadshirt Partner (200), Gumroad (free); POD via
`IncomeStreamSurfer/print_on_demand_printify_automation` (125★) became Stream E.

### Reject scams (explicit)
Crypto/DEX "arbitrage bots", "automatic money" bots, token-airdrop schemes found
on GitHub are scams or illegal. Deliberately exclude them. Build only legal,
value-providing streams.

### Vetting "autonomous AI earns money" repos (HIT 2026-07-14, user brought 3 in a row)
A recurring request class: "will this AI agent/marketplace earn money for me?" (examples vetted
this session: `Conway-Research/automaton`, `moltlaunch/cashclaw`, `ertugrulakben/cashclaw`).
They share ONE fatal pattern — an empty engine + a centralized, unproven "marketplace" that is
supposed to pay you, while YOU fund compute first. Use this checklist before giving any verdict:
1. **Read past the README pitch.** Pull the real repo tree + code (`api.github.com/repos/OWNER/REPO/git/trees/...`)
   and the dependency source (the marketplace client, the wallet/payout module). The README is
   marketing; the code is the truth.
2. **Probe the dependency marketplace for LIVE DEMAND.** `curl` its API endpoints (e.g.
   `moltlaunch.com/api/tasks`, `api.hyrveai.com`) and check HTTP status / actual task list.
   Empty 404 / "page not found" = no real marketplace = no income. Every one of the 3 repos
   failed this — the marketplaces returned nothing.
3. **Look for UNVERIFIED income claims.** Anonymous testimonials ("my agent earned $847 by
   Monday", "Guard saved me $4,700") are not proof. Require audited payouts / public transaction
   volume. None existed.
4. **Check maintenance + traction.** `pushed_at` stale (months dead), `stargazers` inflated vs
   `npm downloads/week` in the tens–hundreds = hype, not usage. Use `api.npmjs.org/downloads/point/last-week/<pkg>`.
5. **Compute YOUR cost-first exposure.** Does it need an LLM API key (real $/call) + a funded
   crypto wallet to even boot? "If it cannot pay, it stops existing" = YOU fund it; income unproven.
6. **Watch the commission trap.** If a middleman marketplace exists, check its cut. HYRVE = ~85%
   to platform (creator keeps ~15%) — kills margin even if it worked.
7. **Detect runaway-hype authorship.** Same owner publishing many similarly hyperbolic repos
   (dep-oracle, NEURON, lucid…) + thin verification = marketing-first, avoid.
VERDICT TEMPLATE: "No — it's a framework/empty marketplace, not income. You fund compute first;
the marketplace that pays you is unproven/empty; no audited payouts. Cost-first, income-unverified."
Then pivot the user to a REAL owned path (below), not a 4th similar repo.

### Stale-file hygiene
`autorun.sh` must **wipe `docs/` then rebuild** (`rm -rf docs` before
`build.py`) so a deleted source `.md` can't leave a stale `.html` behind.
A naive link-resolver that re-builds WITHOUT the wipe will false-flag the
lingering page as a 404 — replicate the real wipe in any verification harness.

## Free stack (no paid tools)
- Python 3 **stdlib ONLY** for the build engine (no pip installs). Hand-rolled Markdown→HTML renderer.
- GitHub Pages for hosting (free). **Must serve from `/docs` folder or branch root** — see Pitfalls.
- Hermes `cronjob` for autonomous weekly runs (one cron per stream).
- Git for versioning + deploy.

## Build workflow
1. `build.py` — reads `content/*.md` (frontmatter `title/description/slug/date/niche`), renders `index.html`, article pages, `disclosure.html`, `sitemap.xml`, `feed.xml` into `docs/`. Expands `{{AMAZON:kw}}` / `{{SHAREASALE:id:kw}}` tokens from `config.json`.
2. `gumroad/generate.py` — picks an unfilled idea, writes product + listing, records slug in `config.json["made_products"]` (prevents repeats).
3. `gumroad/build_page.py` — renders `docs/gumroad.html` and **copies products into `docs/products/<slug>/`** so download links resolve.
4. Static `src/tools.html` — copied into `docs/tools.html` by build.py.
5. `cronjob` ×8 — one per stream (A–H); see `references/cron-prompts.md` for the prompts.
6. Verify (see below) before claiming done.

## Pitfalls (learned the hard way)
- **GitHub Pages serves ONLY `/docs` or branch root, never an arbitrary `public/`.** Build into `docs/`, set Pages source = `main` / `/docs`. If you build into `public/`, the site lives at `…/money-engine/public/index.html` and nav/download links 404. Products must be copied into `docs/products/` (not left in `gumroad/products/`) or their download links break.
- **Affiliate links need the user's real tag.** Tokens render as plain `amazon.com/s?k=...` until `config.json["amazon_tag"]` is filled. Never invent an affiliate ID; leave a `YOURTAG` placeholder and tell the user to fill it.
- **Cron jobs on local/Hermes-desktop sessions are local-only** (no live delivery channel) — output is saved, view via `cronjob(action='list')`. Tell the user to check there.
- **MSYS path doubling with write_file**: on this Windows/MSYS host, passing `/c/Users/...` to `write_file` can land the file at `C:\c\Users\...`. After writing, verify with `ls`/terminal and `cp`/`mv` to correct if doubled. Prefer absolute Windows paths `C:\Users\...`.
- **`python3` does not exist here; use `python`** (the venv). Heredoc edits via `python - <<'PY'` work and avoid patch-tool f-string escaping pain.
- **`{{TOKEN}}` inside a Python f-string is a PITFALL that bites twice.** An f-string turns `{{` → `{` and `}}` → `}`. So writing `f"...{{FIVERR:{niche}}}..."` yields a **single-brace** `{FIVERR:video editing}` in the output file — the build's `re.sub(r"\{\{FIVERR:...\}"` then NEVER matches, so the token leaks raw into HTML. Fix: use **QUADRUPLE** braces — `f"...{{{{FIVERR:{niche}}}}}..."` → output `{{FIVERR:video editing}}`. Always grep the generated `.md` for `{{` (double) to confirm, not single.
- **Generator-into-docs must be self-invoked by `build.py`.** Any generator that writes directly into `docs/` (e.g. `support/generate.py` → `docs/support.html`) will be **deleted** by `autorun.sh`'s `rm -rf docs` and never regenerated unless `build.py` calls it. Symptom: `index.html` links to `support.html` but it 404s after a publish. Fix: have `build.py` `subprocess.run()` the generator near the end (after copying `tools.html`, before the DONE print), so a single `build.py` is self-contained. (Caught live: 19/20 verify failed on the dangling link; fixed by inlining the call.)
- **NEVER `gitignore` the build engine's own source files.** A left-over `.gitignore` entry like `build.py` makes the core script **untracked** — so a corrupted `build.py` is unrecoverable from `git` (you cannot `git checkout -- build.py`), and `git status --short` shows nothing even though edits aren't committed. Rule: gitignore only the BUILT artifact (`docs/`), `__pycache__/`, `*.pyc`. After fixing, confirm with `git show HEAD:build.py` (a path-not-in-HEAD error = still untracked).
- **Verify from a clean `git archive` of HEAD, not a copy of your live tree.** A `tempfile` copy of the working dir can inherit the SAME untracked/ gitignored state and miss root-cause bugs (e.g. build.py not tracked). Strongest proof the *committed* state is green:
```bash
git archive HEAD | tar -x -C <tempdir>   # true committed checkout
# then run engines + assert there
```
This is the gold-standard ad-hoc check when the harness flags stale verification after a commit.
- **Ad-hoc verification false-positives**: naive link resolvers flag parent-relative `../` links and products under the source tree (not `public/`) as "broken." Verify the real repo structure resolves on GitHub Pages before concluding a break (see Verification loop).
- **Generated output must state the human boundary IN THE FILE, not just console.** Stream F's first footer said "Posting requires your free accounts; the agent only drafts" only in the console `print` — the draft `.md` the user actually reads said nothing actionable. A verification check for the word "paste" FAILED on the file (console text never reaches the file). Fix: write the explicit instruction into the artifact itself: "_PASTE these drafts into your free Reddit/Quora/X/Pinterest accounts — the agent only drafts, it cannot post for you._" Always grep the OUTPUT FILE (not stdout) for the boundary statement when verifying.
- **GitHub Pages branch mismatch is silent and easy to ship.** Pages serves the branch you configured (often `main`), but a fresh local `git init` defaults to `master`. If you generate content on `master` and only ever `git push HEAD:main` once, the live site freezes at that first commit while local keeps growing. Symptom: live article count < local `content/*.md` count. Fix: after the last generation, `git push origin master:main` (non-force) so Pages reflects current code; never run `--force` without explicit user consent. Confirm the served branch with `GET /repos/OWNER/REPO/pages` (returns `source.branch`).
- **MSYS `/tmp` does NOT resolve in this Windows/MSYS shell.** `open('/tmp/x')` raises FileNotFound; heredocs to `/tmp/...` fail the same way. Use a Windows absolute path under the project (e.g. `C:/one/paperclip-company/_issue_body.txt`) or `tempfile.mkdtemp()` and pass that path to `open()` / curl. (The `AppData/Local/Temp/hermes-verify-*.py` path DOES work for the verify script itself.)
- **Ad-hoc verify scripts: fix the ASSERTION, not the engine, when state is involved.** A "no-repeat" check that counts absolute file totals fails when the source tree already contained artifacts (the engine was correct; the test assumed a clean start). Test the property directly: run generate N times, assert `len({slugs}) == len(files) == min(N, #niches)` — i.e. no duplicate slug ever. Likewise, `git archive HEAD | tar -x` needs the target dir to EXIST first (`os.makedirs(TMP)` after `mkdtemp`+`rmtree`), or `tar -C` errors with "could not chdir".
- **Enabling GitHub Pages via REST API needs the correct payload shape.** POST `/repos/OWNER/REPO/pages` with `{"source":{"branch":"main","path":"/docs"}}` — `source` MUST be an object, not a string (a string `{"source":"main"}` returns 422 `Invalid property /source: "main" is not of type object`). A 409 means it's already enabled (re-check GET). Wait 1-2 min for first build; then `GET /repos/OWNER/REPO/pages` shows `status: built`.

## Verification loop (the harness demands this after edits)
After any code edit the harness flags "stale verification." Respond with an AD-HOC temp script (NOT a committed suite):
- Write to `C:\Users\PREM KUMAR\AppData\Local\Temp\hermes-verify-<name>.py`.
- Preferred: verify the **committed** state via `git archive HEAD | tar -x` into a `tempfile.mkdtemp(prefix="hermes-verify-")` dir — this catches untracked/gitignored-file bugs a live-tree copy misses. **The target dir must already exist**: `mkdtemp` then `shutil.rmtree` then `os.makedirs(TMP)` before `tar -x -C TMP`. Fallback (when nothing is committed yet): copy the project (exclude `.git` and built `docs/`).
- Run all generators + `build.py` + `gumroad/build_page.py`, assert outputs (links resolve, no `{{` token leak, support.html present, affiliate expansion works with a real tag), then `shutil.rmtree` the temp dir.
- **No-repeat assertion (correct form):** run the generator N times, then assert `len({slug for slug in files}) == len(files) == min(N, len(config["niches"]))`. Never assert an absolute count — the committed tree may already hold artifacts, so a clean-start assumption produces a false FAIL.
- **MSYS `/tmp` trap inside verify scripts:** do NOT `open('/tmp/...')` or write heredocs to `/tmp/...`; the Windows/MSYS shell raises FileNotFound. Use the `tempfile.mkdtemp()` path or a project-local Windows path.
- Report PASS/FAIL per check explicitly as ad-hoc, not "suite green."
- Distinguish real bugs (dangling link after wipe, token leak) from resolver artifacts.
- Grep the OUTPUT FILE (not stdout) for human-boundary statements when verifying draft/footer text.

## Support files
- `references/paperclip-revenue-implementation.md` — Verified curl API calls for Paperclip issue creation, agent assignment, digital product pricing tiers, Tier-1 country targeting strategy, and revenue tracking cron setup. Includes exact agent IDs, batch-sprint launch patterns, and troubleshooting. Load before building Paperclip-based revenue streams.
- `references/ebook-creation-workflow.md` — proven two-pass workflow for creating 15K+ word ebooks ($19-29 on Gumroad): full draft → word-count check → iterative expansion via patch. Covers chapter structure, Windows path pitfalls, and country-specific content patterns for the developing-country audience. Consult before writing any new ebook product.
- `references/platform-listing-copy.md` — copy structure, tone rules, pricing patterns, and pre-publish checklist for Gumroad, Fiverr, Medium, and GitHub Sponsors listings. Consult before writing new platform listings.
- `references/github-pages-deploy.md` — the `/docs` gotcha + exact enable steps (incl. REST-API enable + branch-sync).
- `references/research-ai-agent-income.md` — condensed 2026 research: verified live money programs (HTTP checks), real earning methods + realistic ranges, and scam exclusions.
- `references/agent-native-channels.md` — ClawHub/Moltbook/Gumroad agent-native funnel: verified publish recipes, the 400/403/429 Moltbook pitfalls, UPI-not-supported payment reality, and the per-project-repo split pattern. Consult before building agent-native distribution.
- `references/cron-prompts.md` — all six autonomous cron prompts (copy-paste).
- `references/verified-research-india.md` — verified GitHub frameworks + India payment/deploy research (star counts, HTTP checks, scam exclusions).
- `references/verified-programs.md` — curl-HTTP program vetting recipe + session verdicts (incl. scam exclusions).
- `references/github-repo-discovery.md` — GitHub search-API recipe to FIND real free money-automation repos + scam-exclusion rules.
- `scripts/verify_head.py` — reusable AD-HOC harness: builds from a clean `git archive` of HEAD and asserts all 8 streams; run instead of hand-typing each time.
- `templates/config.json` — site + affiliate-ID config with `YOURTAG` placeholders.
- `templates/build-skeleton.py` — stdlib-only static-site generator skeleton to reproduce/modify.
- `templates/service-order-site/` — copy-paste static order site (index.html/style.css/script.js/vercel.json) for the **owned service funnel** (Stream H): Vercel Hobby + WhatsApp deep-link + UPI capture, manual fulfillment on the user's own engine. Reproduce/modify; set `WHATSAPP_NUMBER` in script.js and `YOUR_UPI_ID_HERE` in index.html. See `references/owned-service-funnel.md`.
