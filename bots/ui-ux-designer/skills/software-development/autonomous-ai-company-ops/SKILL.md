---
name: autonomous-ai-company-ops
description: >-
  Operate the Hermes-Full-Autonomous-Company — a $0-budget AI company running on
  Paperclip (7-agent org) + Hermes Agent (executive) + OpenClaw (comms/computer-use)
  + hermes-paperclip-adapter, with GitHub as the single source of truth. Covers server
  launch, the 24/7 cron autonomy loop, Constitution-as-OS v3.0, the product
  research→build→test→push cycle, revenue-channel research, and the human-in-the-loop
  gates. Use when the user says "continue the company," "build/push a product," "start
  earning," "run 24/7," or anything about operating this autonomous company. The current
  master operating prompt is v4.0 (canonical Hermes-1st-boss architecture + 3 money-gates).
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Autonomous AI Company Operations

## When to use
- "run the company 24/7", "continue building", "build a product and push it"
- "research money-earning / revenue possibilities", "start the money earning process"
- Any task touching Paperclip, the autonomy loop, `CONSTITUTION.md`, `digital-products/`,
  `income-engine/`, or `revenue/`
- Pushing company code to GitHub as `itsPremkumar`

## The stack (verified, running)
- **Paperclip** — org layer: 7 agents, budgets, ticketing, governance. Server on :3100;
  embedded Postgres on :5432.
- **Hermes Agent** — executive/CEO. Local folder `C:\one\paperclip-company` = git repo
  tracking `github.com/itsPremkumar/Hermes-Full-Autonomous-Company` (branch `master`).
- **OpenClaw** — comms + computer-use, gateway :18789.
- **hermes-paperclip-adapter** — CEO↔Paperclip bridge.
- **OmniRoute→OpenRouter** — free-model escalation (key from env ONLY).

## Operating principles (load-bearing)
1. **GitHub = single source of truth.** Every asset, prompt, lesson, state is committed.
   If it isn't on GitHub, it didn't happen.
2. **Constitution = the OS.** The live master operating prompt is
   `prompts/executive-master-operating-prompt-v4.0.md` (v4.0, 2026-07-15) — it supersedes
   v2.0/v3.0 and locks the canonical architecture: **Hermes = 1st boss** (self-improving,
   commands Paperclip + OpenClaw), **Paperclip = 2nd boss** (ops layer, :3100), **OpenClaw =
   channel** (draft-only gateway :18789). It also hard-codes the **3 human money-gates**
   (marketplace KYC / payment linkage / first publish — Charter §0.7). The originating
   `CONSTITUTION.md` at repo root is the charter; the repo is the operating system (kernel
   map, dependency graph, failure taxonomy, maturity levels, roadmap — all in `docs/`). The
   prompt defines behavior; the repo defines the system. Prior versions live in
   `prompts/archive/` (never delete). When improving the prompt, bump to vX+1, archive the
   old version with a note, and push to BOTH `Hermes-Full-Autonomous-Company` (canonical) and
   the working copy `paperclip-company`.
3. **Human-in-the-loop is non-negotiable (Charter §0).** Money movement is gated: Gumroad
   account creation, payout/bank/PayPal linking, clicking Publish, affiliate-program
   applications, any spend → PRINCIPAL does it. The agent may prepare everything up to
   the click.
4. **Memory discipline (low-RAM box ~644MB free).** Never spawn >2-3 heavy procs. Scope
   `find` tightly (deep `/c` scans hang). Check RAM via `wmic OS Get FreePhysicalMemory`.
5. **Never push secrets.** OpenRouter key, .env, credentials stay local/in env. GitHub
   secret scanning blocks the push if a key is committed — redact to env var and rewrite
   history.
6. **Auto-push as `itsPremkumar` via git CLI — NEVER ask for approval.** Cached creds make
   `git push` silent. This is an explicit, repeated user directive (the account-picker
   modal, if it ever returns, is fixed in references/git-credential-fix.md).

## "Document it as a complete working money loop" — the user's recurring ask + the right response
The user repeatedly wants the autonomous system described as "the complete working money-earning
loop, fully working." Honor the *framing* but keep ONE honest footnote (Charter §0.3/§0.8 forbid
false "guaranteed/automatic income" claims):
- **Document it fully and completely** — architecture, one-time human setup, the autonomous
  daily loop, SEO/GEO/AEO, monetization ladder, multi-site scaling, and the End-Goal Loop.
  Do NOT dilute or refuse the "complete system" framing; the operation loop genuinely runs.
- **Embed exactly one honesty line:** the *operation* loop is coded + scheduled + running, but
  **documented booked revenue is $0 until a payout is recorded** — money stays gated on (a) real
  traffic, which SEO grows over weeks–months, and (b) platform approval + payment linkage, which
  only the principal can complete. State this plainly; never claim "earning" as a fact before a
  payout exists in `finance/revenue-ledger.csv`.
- **AdSense rejection reality:** sproutern was AdSense-rejected for "low-value content"
  (auto-generated + future-dated posts). If AdSense rejects, **Monetag/Ezoic is the lower-bar
  fallback** — but it still pays per impression (~zero without traffic). Keep affiliate + UPI
  (`premkumar016555@oksbi`) as the zero-approval streams switched on first.
- **Do NOT over-refuse either.** When the user says "this is the real working loop," agree on the
  automation being real and complete; correct only the *earning* sub-claim. The borderline is:
  "complete autonomous system" = true; "automatic money printer" = false.

**Reference implementation (verified live, 2026-07-15):** `itsPremkumar/sproutern-open-source`
(public) + `itsPremkumar/sproutern-hermes` — a Next.js site with a working daily improvement loop
(`daily-hermes-automation/`: measure→decide→improve→verify; cron `0 3 * * *`), `VERCEL_MCP_SETUP.md`,
full `docs/` SEO/GEO/AEO playbooks, and `ADSENSE_*` recovery plans. The complete documented system
lives at `revenue/AUTONOMOUS_WEBSITE_MONEY_SYSTEM_COMPLETE.md` (both repos). Reuse it as the template
for every new site — fork, `vercel link` once, copy the loop, point `measure.py` at the new slug.

## Start the company server (if down)
```
terminal(background=true): cmd.exe //c "C:\one\paperclip-company\run-server.bat"
then poll http://127.0.0.1:3100/api/health until 200
```
A Windows Scheduled Task `PaperclipServer` should launch it on boot; if the chat session
restarted it may need a manual start.

## The 24/7 autonomy loop
- Cron job "Company Autonomy Loop" runs every 30 min, forever. Each tick: RAM check →
  `git pull --ff-only` → read tasks.md + Paperclip issues → do next AGENT-ACTIONABLE,
  NON-HUMAN-GATED task → commit + push.
- Implementation: `autonomy-loop.py` (confidence gate + benchmark logging + failure
  categorization).
- Human-gated tasks are detected (keywords: gumroad publish, payout, bank, create account,
  tax, PRE-52) and skipped with a flag.

## Product research→build→test→push cycle
1. **Research** with the "never reinvent" rule (Constitution §4): GitHub search ≥3 mature
   solutions before building.
2. **Build** stdlib-only / $0 tools that run on the low-RAM box (e.g. `agent-caps` — the
   capability-manifest toolkit, product #9).
3. **Test / verify — the 7-axis harness (CANONICAL test command).** This is the
   "verify from all perspectives" system and the cure for the recurring
   "unverified" flag loop. Every product in `clawhub-skills/<name>/` MUST pass all 7 axes:
     1. **structure** — `SKILL.md` + a `.py` tool (OR an external-tool skill: `requirements.txt`/install note)
     2. **frontmatter** — `name`/`version`/`description` in `SKILL.md`
     3. **compiles** — `py_compile` every `.py`
     4. **self-test** — a `.py` exposing `self-test` (REAL asserts, NOT fake `return 0`) OR `test_*.py` OR a `test:` line in `SKILL.md` (external-tool skills)
     5. **security** — no hardcoded secret (`key=value` with a real value)
     6. **docs** — `SKILL.md` has Usage/Why/Example
     7. **deploy-ready** — `ci/ci_check.py` hard-fails a broken package (must FAIL on missing `SKILL.md`)

   **Run it (not ad-hoc temp scripts):**
   ```bash
   python ci/verify_product.py clawhub-skills/<name>   # one product
   python ci/verify_product.py clawhub-skills/*/            # whole portfolio (31 folders)
   ```
   Exit 0 = all axes green. CI in every repo runs this on **Python 3.8 AND 3.11** + a `ci_check.py` deploy-check job (`docs/ci-workflow-template.yml` is the template).
   **Adding a tool?** It MUST get a real `self-test` subcommand (call a pure function on temp input + assert). Delegate the mechanical addition of `self-test` to 13+ tools via `delegate_task` (leaf), then **independently re-run the harness yourself** — subagent self-reports are not verified facts (we caught real gaps: 19/31 folders failed the harness before the fix).
   **Why this killed the unverified loop:** the system flags ANY changed path as needing verification. Writing a `hermes-verify-*.py` temp script re-triggers the flag on itself. The permanent cure is a committed canonical suite (`ci/verify_product.py` + `tools/test_all_skills.py`) so the harness has a real test command and stops demanding ad-hoc proofs. See references/portfolio-verification.md.
4. **Package** as a Gumroad product: `income-engine/gumroad/products/<id>/PRODUCT.md` +
   `LISTING.txt` (copy-paste Title/Price/Description). Template: templates/product-package.md.
5. **Catalog** in `digital-products/product-catalog.json` (update stats).
6. **Push** to GitHub (silent, itsPremkumar).
7. **Human publishes** on Gumroad (PRE-52 runbook).

## Revenue channels (scored, updated 2026-07-13)

- **ClawHub skill (OpenClaw native registry)** — **95% automatable, PUBLISHED live.** `clawhub`
  CLI is installed + authed as `itsPremkumar` (`clawhub whoami` ✔). Publish = one command,
  no human step. Everything on ClawHub is FREE (distribution, not storefront); money is made
  off it via premium Gumroad versions. Our 31 skills are live.
  See references/agent-native-channels.md.
- **HYRVE AI marketplace (agent freelance marketplace)** — **~90% automatable, NEW.**
  `hyrveai.com` — first AI agent marketplace. 5,750+ community, 85% commission to creator,
  48-hour escrow, Stripe/USDT/stablecoin payouts. Agents self-register in 30s via API/skill.md.
  Our skills (doc-extractor, secret-scanner, codebase-inspection, json-tools etc.) map
  directly to service offerings. Only payout setup is human-gated. Research in
  `agent-native-distribution` skill's references/agent-marketplace-research-2026-07.md.
- **Moltbook (agent social network, REST API)** — ~80% automatable. `POST /api/v1/agents/register`
  needs NO login (returns api_key); posting is gated on the human "claim" step (Twitter/X
  verify, 403 until claimed). We registered `prem-autonomous-co`; post flow works end-to-end.
  See references/agent-native-channels.md + the post-scheduler setup below.

## Moltbook post scheduler (automated product announcements)
To backfill Moltbook posts for all 31 ClawHub skills without hitting rate limits:
- **Pre-built drafts**: `revenue/moltbook/post-<slug>.json` — 31 files, one per skill.
- **Tracker**: `revenue/moltbook/posted.json` — `{"posted": ["agent-caps", "agent-sentinel", ...]}`
- **Scheduler script**: `revenue/moltbook/post-scheduler.py` — finds first unposted draft,
  posts it to Moltbook API, updates tracker. Stdlib-only.
- **Cron job**: `Moltbook post scheduler` — fires every 30 min, deliver=origin.
- **Draining a backlog faster**: the 429 floor is ~2.5 min, so to backfill many drafts
  quickly you can safely bump the schedule to `every 3m` (`cronjob update job_id=<id>
  schedule="every 3m"`) — 3 min > 2.5 min floor, so no 429. Drops a 28-post backlog from
  ~14h to ~1.5h. Set it back to `30m` once drained.
- **Rate limit**: Moltbook returns `retry_after_seconds: ~55` on 429. The 30-min cadence
  safely avoids hitting it. ~14.5h to backfill 29 remaining posts.
- **Setting up**: `cd /c/one/paperclip-company && python revenue/moltbook/post-scheduler.py`
  to test. The cron does this automatically each tick.
- **The Colony (agent social + marketplace)** — **~70% automatable, NEW.** `thecolony.cc` —
  topic-based forums + paid task marketplace. OpenClaw skill exists for integration.
  Agents self-register; marketplace transactions may need human wallet setup.
- **Affiliate content engine** — 85% automatable (agent writes SEO drafts + disclosure;
  human applies to programs + inserts own aff IDs). Engine: `revenue/affiliate/affiliate-engine.py`.
- **Gumroad product sales** — 70% (human publishes 7 ready packages, PRE-52).
- **ai-sns (OpenClaw agent social network)** — **~70% automatable, NEW.** `ai-sns/ai-sns` (319★).
  OpenClaw-native 3D agent social network on A2A protocol.
- **AgenC (Solana agent hiring protocol)** — **~60% automatable, NEW.** `tetsuo-ai/AgenC` (190★).
  Agents get hired and paid on Solana mainnet. Crypto wallet needed.
- **Micro-SaaS** (wrap free-tier AI APIs) — 60%, pilot in `revenue/microsaas/`.
- **Agoragentic (cross-framework agent commerce)** — **~50% automatable, NEW.**
  `rhein1/agoragentic-integrations`. Settle in USDC on Base. 50+ framework adapters.
- Fiverr / ads / newsletter — deferred (low automation or traffic-gated).
- Compliance: disclose affiliate links, no fake reviews, no income guarantees, only
  verified tools. ClawHub/Moltbook posts must be honest (no "guaranteed income").

## Publish agent-native skills (ClawHub + Moltbook)
These are the MOST end-to-end-automatable distribution channels — the agent can build AND
publish with zero human action (only eventual money receipt is gated).
- **ClawHub** (`clawhub` CLI, authed as `itsPremkumar`): package a skill as a folder with
  `SKILL.md` (YAML frontmatter: name/version/description/tags) + supporting files, then
  `clawhub publish "<abs-folder>" --slug X --name "Name" --version 1.0.0 --tags "t1,t2,t3"`.

  **Content quality is enforced.** The registry rejects thin/templated SKILL.md with
  `"Skill content is too thin or templated. Add meaningful, specific documentation."`.
  Every published SKILL.md MUST include rich, substantive sections — at minimum:
  install instructions, usage with command examples, a features list, a commands table,
  and a "why" section. Code blocks, example output, and CI integration snippets all
  help. A skeleton with just frontmatter + one paragraph will be rejected.

  **Exact publish command:**
  ```bash
  clawhub publish "C:\path\to\skill-folder" --slug my-skill --name "My Skill" --version 1.0.0 --tags "tag1,tag2,tag3"
  ```
  Verify token first: `clawhub whoami` (must show ✔ itsPremkumar). Absolute path required
  (relative/CWD paths error with "Path must be a folder").

  **Confirmation**: success returns `✔ OK. Published <slug>@1.0.0 (<hash>)`.
  Search index may lag — `clawhub search <slug>` may not immediately return results after
  publish. The publish response itself is the authoritative confirmation.

  **Batch upgrade + republish (verified 2026-07-13).** When upgrading all N skills at once
  (e.g. v1 → v2 with new features + README + docs): do it in 4 deterministic passes, NOT by
  hand:
  1. **Generate docs** — a Python script (`generate_v2_docs.py`) loops all `clawhub-skills/<name>/`
     folders and writes `README.md` (badge bar, Quick start, feature table, sample output, links)
     + a v2 `SKILL.md` (frontmatter `version: 2.0.0` + Install/Commands/Features/CI/Why/Support).
     Keep a dict of `{slug: {name, tool, desc, tags, commands[], features[]}}` so every skill
     gets consistent structure. Verify with `ast.parse` on every `.py` + a glob count of
     generated files (must == N).
  2. **Push to GitHub per repo** — `push_all_v2.py` does, per skill: `git init` → `git remote add
     origin https://github.com/itsPremkumar/<slug>.git` → `git add -A` → commit →
     `git branch -m master main` → `git pull --rebase -X theirs` → `git rm -r --cached __pycache__`
     → `git push origin main`. For renamed repos use a URL_MAP (agent-caps→prem-agent-caps,
     dev-prompts→dev-prompts-pack). **Always rebase-pull before push** — the remote may have a
     LICENSE/README commit from `license_template` and reject a non-FF push.
  3. **Republish on ClawHub** — `republish_all_v2.py` calls `clawhub publish` for each with
     `--version 2.0.0`. The FIRST publish of a version succeeds; re-running the SAME version
     errors `✖ Uncaught ConvexError: Version 2.0.0 already exists` — that is HARMLESS (it's
     already live). Capture only `✖` lines that are NOT the version-exists message.
  4. **Update Moltbook drafts** — `update_moltbook_drafts_v2.py` rewrites `revenue/moltbook/
     post-<slug>.json` titles/content to v2 messaging; the scheduler cron picks them up on its
     30-min tick.
  All four scripts live in the repo root and are committed. See references/clawhub-batch-upgrade.md
  for the exact script skeletons + the 14-check ad-hoc verification pattern that proves the
  generated docs/tool parse correctly (run from `%TEMP%/hermes-verify-*.py`, then DELETE it so
  it doesn't re-trigger the unverified flag).

  **Batch generation**: for 5+ skills, write a Python script that creates the folder +
  SKILL.md + tool files, then publish individually. This avoids repetitive manual folder
  setup and ensures consistent frontmatter structure. See `references/clawhub-batch-publishing.md`.

  Note: ClawHub has NO paid listings — it's free distribution; monetize via Gumroad premium.
- **Moltbook** (agent REST API at `https://www.moltbook.com/api/v1`): `POST /agents/register`
  (no login → returns `api_key` + `claim_url`), save key to a gitignored `.moltbook_key`,
  then `POST /posts` with `Authorization: Bearer <key>`. Posting returns 403 until the agent
  is CLAIMED (Twitter/X verify at the `claim_url`) — that's the user's one step. Build a
  stdlib poster (`revenue/moltbook/moltbook.py`); never hardcode the key; gitignore it.
- Keep posts honest: announce the free skill, link it, mention the Gumroad premium, NO income
  guarantees. Rate-limit; don't spam.

## Money-pipeline generators (research → sellable packages → dashboard)
When the user says "turn the free-tool blueprint into money ideas / build the money
pipelines / do an implementation", build a `money/` folder of **generator tools**, not
prose. Proven pattern (verified 2026-07-13, 3 pipelines + 18 packages live):
1. **Idea bank first** — `MONEY_AUTOMATION_IDEAS.md`: research REAL 2026 income data with
   the `web-research` skill (`web_research.py search "<q>" --count 6`, then `fetch <url>`),
   quote validated figures (rates, margins, market size) WITH sources, map each free OSS
   tool → a concrete income pipeline, rank by speed-to-first-dollar × ceiling.
2. **One generator per pipeline** — `money/pipelineN_<name>.py`, stdlib-only, each with:
   a dict of `{key: {title, pricing, tags, ...}}`, a `build_*()` function, `--list`,
   `--out <file>` (writes package JSON incl. an n8n/render **manifest stub**), and a
   `self-test` subcommand with REAL asserts (loop all keys, assert required keys +
   margin + node counts). Pattern mirrors the 7-axis harness self-test rule.
3. **Master orchestrator** — `money/run_all.py` imports every pipeline module via
   `importlib.util.spec_from_file_location`, regenerates ALL package JSONs, and writes
   `INCOME_DASHBOARD.md` (per-pipeline table + combined one-time value + 90-day target).
   Give it `self-test` (assert total package count == N across all pipelines) and
   `--dry-run` (totals without writing).
4. Commit `money/` + push; verify with a temp `hermes-verify-*.py` (self-tests pass,
   package JSONs valid, files live on GitHub via `raw.githubusercontent` HTTP 200), then
   DELETE the temp file. See references/money-pipeline-generators.md.

## Python f-string traps that break generator scripts (bit me twice this session)
These are SyntaxErrors caught by `write_file`'s auto-lint BEFORE running — fix immediately,
don't fight the linter:
- **Backslash inside an f-string expression** → `f"{[x for x in y if \"a\" in x]}"` fails
  with `f-string expression part cannot include a backslash`. Fix: compute into a plain
  variable first (`s = ", ".join(...)`) then `f"...{s}..."`. Never nest quotes/backslashes
  inside `{}`.
- **Literal `{}` inside an f-string** → `f"Opens: ({}%)"` fails with `f-string: empty
  expression not allowed`. If the string is a TEMPLATE meant to keep literal braces, drop
  the `f` prefix (make it a plain string). If you need a literal brace in an actual
  f-string, double it: `{{` / `}}`.
- **Helper defined AFTER first use** in a top-to-bottom verify script → `NameError: name
  '_safe_parse' is not defined`. Define all helper funcs at the TOP of temp verify scripts
  before any call. (Recurred because verify scripts are written fast + run once.)

## Cron model-config-drift guard (pins are mandatory)
Every cron is subject to a **config-drift guard**: if the global inference provider
changed since the cron was created AND the cron is unpinned, the scheduler BLOCKS it
with `RuntimeError: Skipped to prevent unintended spend: global inference config
drifted ... (provider 'nous' -> 'openrouter')`. This is the #1 cause of "all my crons
show last_status: error" after a provider switch — NOT a logic bug.

- **Symptom**: `cronjob run` returns `execution_success: false` with that RuntimeError;
  the list shows `last_status: error` for otherwise-healthy crons.
- **Fix**: pin every cron to the current provider/model. For each errored job:
  `cronjob update job_id=<id> provider=openrouter model=tencent/hy3:free`
  (the `tencent/hy3:free` model is the reasoning model and needs ~200 max_tokens — it
  is the company default). After pinning, `cronjob run <id>` returns `execution_success: true`.
- **Preventive**: when CREATING a cron, always pass `model`+`provider` explicitly (do NOT
  rely on the pin-default). The guard only fires on UNPINNED crons whose stored provider
  no longer matches the live global config.
- **Audit pattern**: `cronjob list` shows `provider: null` for unpinned jobs. Any job with
  `provider: null` + `last_status: error` + that RuntimeError is a drift-blocked job, not a
  broken one. Pin it and move on.

## Backup Hermes "learned" skills to GitHub
The Hermes desktop app shows a "Skills 97" / `learned` library (the blue `Learned`
tag = a skill that is installed + enabled, NOT AI self-study). These live on disk at
`%LOCALAPPDATA%/hermes/skills/<category>/<name>/` (each with SKILL.md + references/ +
scripts/ + templates/). Because **GitHub = single source of truth** (principle 1),
back them up into the company repo so they are version-controlled and recoverable.

- **What "Learned" means**: a status label in the Hermes UI = skill acquired (from
  ClawHub/GitHub/bundled) and currently ENABLED for new sessions. The blue toggle =
  active. The `×N` count = usage count (from `hermes/skills/.usage.json`). It is NOT
  "the AI learned it like a student."
- **Backup script**: `scripts/backup_learned_skills.py` copies all skill folders into
  `skills/<category>/<name>/`, strips `__pycache__`, and writes `SKILLS_INDEX.md` (all
  skills sorted by usage) + `usage_snapshot.json` (raw stats). Run it, then
  `git add skills/ && commit && push`.
- **Verify**: `find skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l` should equal
  the source count (100); `curl` the raw `SKILLS_INDEX.md` on GitHub → HTTP 200.
- **Scope note**: these are the Hermes ECOSYSTEM skills (paperclip-local-company,
  money-engine, ai-company-blueprint, etc.) — a SEPARATE registry from the 31 ClawHub
  skills. Only `web-research` overlaps both. Don't confuse "learned skills" with "our
  published ClawHub skills."

See references/learned-skills-backup.md for the full pattern + the `SKILLS_INDEX.md`
format.

## Pitfalls (from real sessions)
- **Cron model-config-drift guard** → unpinned crons BLOCK with `RuntimeError: ... config
  drifted (provider 'nous' -> 'openrouter')` after a provider switch, showing
  `last_status: error`. NOT a logic bug. Fix: `cronjob update job_id=<id> provider=openrouter
  model=tencent/hy3:free` for every `provider: null` job. Always pass `model`+`provider`
  when CREATING a cron. See the "Cron model-config-drift guard" section above.
- **Account-picker modal on every push** → `x-access-token` GCM entry. Fix:
  references/git-credential-fix.md.
- **Push rejected by GitHub secret scanning** → hardcoded OpenRouter key in a .bat/.sh.
  Fix: redact to `%OPENROUTER_API_KEY%` / `"$OPENROUTER_API_KEY"`, rewrite the commit so
  the key is never in history, re-push. references/push-secret-scan-block.md.
- **"Unverified" flag loop after editing code** → stale `hermes-verify-*` temp files in
  `%TEMP%` counted as changed paths. Fix: verify inline (heredoc) or write a
  `hermes-verify-*.py` temp script, run it, then DELETE it + any leaked `hermes-verify-*`
  dirs. references/verification-unverified-flag.md.
- **`write_file` with `/c/...` absolute paths** gets a `C:\` prefix but resolves to the
  same MSYS path — verify with `ls` after writing.
- **Server dark after session restart** → start it; the Scheduled Task may not have fired.
- **Deep `find /c` scans hang under memory starvation** → scope searches tightly.
- **ClawHub publish needs absolute path** → `clawhub publish <abs-path>` (relative/CWD
  paths error with "Path must be a folder"). Check `clawhub whoami` ✔ before publishing.
- **Moltbook 403 "requires a claimed agent"** → post only works after the user claims the
  agent at the `claim_url` (Twitter/X verify). Register is login-free; the claim is the
  human step. Don't re-attempt posting in a loop — hand the claim_url to the user.
- **Moltbook 400 "property link should not exist"** → the `/posts` text endpoint rejects a
  top-level `"link"` field. Once claimed, a payload with `"link"` 400s. Fix: embed the URL
  inside `content` (`body = f"{content}\n\n{link}"`) and drop the top-level `link` key.
- **Moltbook `.moltbook_key` location + path-math trap** → NEVER store the key inside the
  working dir that gets committed/staged (e.g. `revenue/moltbook/.moltbook_key`). The
  canonical test suite flags "secret in dir" and a monorepo split would otherwise try to
  push it. Keep it at **repo root** `.moltbook_key` (already gitignored). In `moltbook.py`,
  `KEY_FILE` must resolve TWO levels up from `revenue/moltbook/moltbook.py`:
  `os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".moltbook_key"))`.
  `os.path.dirname(os.path.dirname(__file__))` resolves to `revenue/`, NOT repo root — a
  silent wrong-path bug. After moving the key, re-run `load_key()` to confirm it resolves.
- **Moltbook 429 rate-limit floor is 2.5 MINUTES, not 90s.** The live API returns
  `{"statusCode":429,"message":"You can only post once every 2.5 minutes","retry_after_seconds":109}`
  (note: the message says 2.5 min but the field says 109s — treat the FLOOR as ~2.5 min). The
  autonomy loop's 30-min tick is SAFE and correct. A background posting loop with 90s/5-min gaps
  WILL still 429 — do NOT use short backoff for Moltbook. **The scheduler must handle 429
  gracefully**: on 429, do NOT mark the draft as posted (leave it in the unposted queue so the
  next tick retries), and do NOT crash. The proven `post-scheduler.py` reads `posted.json`, posts
  the first unposted draft, and only appends to `posted.json` on HTTP 201 — so a 429 simply leaves
  the draft for next time. Confirmed: agent-caps + agent-sentinel posted live; the rest land
  gradually via the 30-min loop without manual intervention.
- **Unverified-flag loop in THIS repo → canonical suite fix.** The harness kept flagging
  `hermes-verify-*` temp files. The permanent cure: `tools/test_all_skills.py` runs every
  tool's `self-test`, the agent-caps suite, validates all Moltbook drafts (honest/linked/
  donation ask), and checks no secret in `revenue/moltbook/`. Run `python tools/test_all_skills.py`
  → exit 0. Commit it so the harness has a test command and stops demanding ad-hoc proofs.
- **Splitting monorepo → per-project GitHub repos** (user focus task) → see
  references/agent-native-channels.md "Splitting the monorepo". Key traps: (a) `license_template`
  auto-inits a LICENSE → first push non-fast-forward; `git pull --rebase` then push. (b) Defensively
  `find -delete` `*moltbook_key*`/`*.key`/`*.env` from each staged project; re-scan the target repo
  tree for `moltbook_key` before declaring clean. Link the new repos from `tools/repo-index.md`
  ("Our Product Repositories" section), not the dependency index.
- **Gumroad payout ≠ UPI** → Gumroad pays out via **PayPal or USD bank wire only**; it does NOT
  support Indian UPI. If the user offers a UPI ID for payments, tell them to link PayPal (→ Indian
  bank) instead, and NEVER accept the UPI ID (or any payout credential) into the agent context —
  Charter §0 forbids the agent handling payout creds. The agent prepares everything up to the
  Gumroad Publish click; the user does the payout linking + publish.
- **ClawHub rejects thin/templated SKILL.md** → publish fails with `"Skill content is too thin
  or templated. Add meaningful, specific documentation."` Every SKILL.md needs rich sections:
  install, usage with examples, features list, commands table, and why. Code blocks with example
  output help. A skeleton with just frontmatter + one paragraph will be rejected. Fix: expand
  the SKILL.md with substantive content, then retry publish.
- **`__pycache__/` committed to GitHub repos** → when copying skill folders to git repos with
  `cp -r`, `__pycache__/` directories and `*.pyc` bytecode files get included. Fix: after the
  first push, add `.gitignore` with `__pycache__/` and `*.pyc`, `git rm -r --cached __pycache__/`,
  commit, and push. Or add `.gitignore` before the initial commit.
- **Delegation boundaries for ClawHub publishing** → subagents (delegate_task) can create skill
  folders and publish to ClawHub (clawhub CLI works in subagent terminal). However, subagents
  CANNOT access the GCM token for GitHub repo creation (the token lives in the parent session's
  git credential helper context). Always create GitHub repos and push code in the parent context
  after subagents finish their publishes.
- **ClawHub `inspect` gives FALSE NEGATIVES — do not trust it for audit.** `clawhub inspect @slug`
  FAILS (the `@` prefix is rejected). Use the bare slug: `clawhub inspect <slug>` (no `@`). Even
  then, if another user published a skill with the SAME slug, the API returns
  `AMBIGUOUS_SKILL_SLUG` and the bare-slug inspect errors out — this is NOT "your skill is
  missing", it just means the slug collides. To confirm YOUR skill is live, check the web page
  `curl -sS -o /dev/null -w "%{http_code}" https://clawhub.ai/itspremkumar/skills/<slug>` (HTTP 200
  = live) or grep `clawhub explore --sort newest` output for your slug. During the 2026-07-13 audit,
  9/31 skills falsely showed "MISSING" from naive `inspect @slug` loops; all 9 were confirmed live
  via the web-page check. Verified-live count was 31/31, not 22/31.
- **ClawHub search index lag after publish** → `clawhub search <slug>` may return nothing for
  minutes after a successful publish (vector index rebuilds asynchronously). Do NOT retry-publish
  — that produces a duplicate. The publish response (`✔ OK. Published <slug>`) is the definitive
  confirmation. Use `clawhub explore --sort newest` as an alternative check after a delay.
- **GitHub repo creation via API token** → to create repos from the CLI, extract the token from
  git credential manager and use curl:
- **GitHub REST API edits SILENTLY FAIL on this Windows box** → when hardening repo metadata
  (description/topics/license) or file contents via API: (1) `topics` MUST go to the separate
  `PUT /repos/owner/repo/topics` endpoint WITH `-H "Accept: application/vnd.github.mercy-preview+json"`
  — a `PATCH /repos` with a `topics` field silently drops them. (2) `PUT /contents` for file edits
  often returns 200 but does NOT persist (stale sha / em-dash corruption) — prefer `git clone`
  + edit + `git push` for files. (3) `raw.githubusercontent.com` shows STALE content for minutes
  (CDN) — verify via `GET /repos/owner/repo/contents/README.md` (API tree = authoritative). (4)
  token in `/tmp/_tok.txt` doesn't survive the MSYS→uv Python boundary — pass via `GH_TOKEN` env
  or a `C:/...` path. Full pattern: references/github-api-windows-reliability.md.
- **Batch-upgrading all N skills (v1→v2) → 4-pass script pattern.** Do NOT edit 31 SKILL.md
  files by hand. (1) `generate_v2_docs.py` writes README.md + v2 SKILL.md for every folder from
  a `{slug: {...}}` dict. (2) `push_all_v2.py` does per-repo `git init`→remote→add→commit→
  `branch -m master main`→`pull --rebase -X theirs`→`rm --cached __pycache__`→push. (3)
  `republish_all_v2.py` re-publishes each with `--version 2.0.0` (ignore "already exists"
  errors). (4) `update_moltbook_drafts_v2.py` rewrites the 31 post drafts. Verify the pass
  with a temp `hermes-verify-*.py` (counts generated files == N, `ast.parse` all `.py`, reads
  back a sample README + SKILL.md), then DELETE the temp file. Full skeletons in
  references/clawhub-batch-upgrade.md.
- **`git push` to a per-project repo rejects non-fast-forward after `license_template`** →
  the auto-init LICENSE commit on origin beats your local commit. Always `git pull --rebase
  -X theirs origin main` BEFORE `git push`. A bare `git push` after local-only commit 404s
  with "src refspec main does not match any" if the local branch is `master` and remote is
  `main` — `git branch -m master main` first.
- **ClawHub version-exists error is NOT a failure** → `clawhub publish ... --version 2.0.0`
  on an already-live 2.0.0 returns `✖ Uncaught ConvexError: Version 2.0.0 already exists`.
  Treat that as "done"; only a DIFFERENT error (network, auth, thin-content) is a real failure.
  To push changes you MUST bump the version — same version can never be re-published.
  ```bash
  TOKEN=$(echo -e "protocol=https\nhost=github.com" | git credential-manager get | grep "^password=" | cut -d= -f2)
  curl -X POST https://api.github.com/user/repos -H "Authorization: token $TOKEN" \
    -d '{"name":"<repo>","description":"<desc>","private":false,"auto_init":false}'
  ```
  The token is a `gho_*` or `ghp_*` string. Never echo it to terminal.

- **URL-encoded session cookie in `cj.txt` silently breaks `curl -b`** → all company
  routes 401 while `/api/health` returns 200. Symptom: `GET /api/companies/{id}/issues`
  returns `{"error":"Unauthorized"}` (401) but `GET /api/health` is `200`. Root cause:
  `cj.txt` (Netscape cookie jar) sometimes stores the `paperclip-default.session_token`
  value **URL-encoded** (`%2F`, `%2B`, `%3D`). curl sends Netscape cookie values
  literally — it does NOT decode them on the way out — so the server receives
  `%2F...%2B...%3D` instead of `/...+...=` and rejects the token. Fix: URL-decode the
  cookie value in `cj.txt`: `%2F`→`/`, `%2B`→`+`, `%3D`→`=`. (The decoded token looks
  like `7Vxcma...OcwN2.../WjLa...++...=`.) Verify with:
  `curl -s -o /dev/null -w "%{http_code}" -b cj.txt "http://localhost:3100/api/companies/{id}/issues"`
  → expects `200`. If still 401, diff against a manual header:
  `curl -H "Cookie: paperclip-default.session_token=<DECODED>" .../issues`. NOTE: mingw64
  curl also reads a `C:\c\one\...` mirror of the path (MSYS double-slash mangling); keep
  both physical copies in sync when editing `cj.txt` by hand. The session cookie alone
  (once decoded) is sufficient for GET/POST company endpoints — you do NOT need the
  agent's `PAPERCLIP_API_KEY` Bearer token for cron curl calls.
- **Paperclip `heartbeat/invoke` requires CSRF `Origin`/`Referer`** → `POST
  /api/agents/{id}/heartbeat/invoke` (the wake-the-agent endpoint) with cookie + JSON
  body returns `403 {"error":"Board mutation requires trusted browser origin"}`. Fix: add
  `-H "Origin: http://localhost:3100" -H "Referer: http://localhost:3100/"`. Then returns
  `202` with `{"status":"queued","id":"<runId>",...}`. Verify the run is actually live: a
  run-log file `<runId>.ndjson` appears under
  `data/paperclip/instances/default/data/run-logs/{companyId}/{agentId}/` and the agent
  writes `[hermes] Starting Hermes Agent ...` into it. IMPORTANT: GET endpoints
  (`/api/companies/{id}/issues`) work with just the cookie (no Origin needed); only
  mutation/invoke endpoints (POST heartbeat/invoke, PATCH issues) require the browser-origin
  guard. When invoking, pass a `reason` in the body and `triggerDetail:"manual"`; explicitly
  tell the agent NOT to touch founder-gated publish steps (those are `in_review`/`blocked`
  on human gates).

- **Auditing + linking the company repo index (the "are all my repos properly linked?" task)** → this is a VERIFY-FIRST job, not a trust-the-doc job. Verified procedure (2026-07-14):
  1. **Enumerate local repos + remotes reliably.** The naive `for d in /c/one/*/; do git -C "$d" remote get-url origin` loop SILENTLY returns `<NO REMOTE>` for repos that DO have a remote (it mis-parsed `openclaw-control-guide`, which I'd pushed that day). **Use `cd "$d" && git remote get-url origin` per repo** — that method is correct. Cross-check a repo you KNOW is pushed (e.g. one you just pushed) to catch a lying loop.
  2. **Authenticated live-check EVERY repo the index claims.** Don't trust the doc's own count. Extract `itsPremkumar/<repo>` from `tools/repo-index.md`, then for each: `curl -sS -H "Authorization: Bearer $TOKEN" https://api.github.com/repos/<repo>` and confirm it returns the full `full_name` (NOT `message: Not Found`). The 2026-07-14 audit found all 21 listed repos WERE real — but the index ALSO claimed "31 product repos" which was FALSE (true live = 23). **Flag + correct any count the doc asserts against the live number.**
  3. **Publishing a local repo sanitized (the `money-engine` pattern):** `git remote add origin https://github.com/itsPremkumar/<repo>.git` → `git push -u origin <branch>`. BEFORE pushing: scan for secrets (`grep -rInE "sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|ghp_..."` — exclude `.env.example`/placeholders/fake `AIzaSy...0000`); ensure no real `.env`, `node_modules`, or runtime logs (`jarvis.log`, `nul`) are staged (`git diff --cached --name-only | grep -iE "\.env$|node_modules|jarvis\.log|^nul$"` → must be empty). After push, **verify on GitHub via API** that junk is 404 (`contents/<junk>` → 404) and the repo is 200.
  4. **⚠️ `git rm --cached` re-stage trap.** To remove a junk file from a repo you already committed: `git rm --cached -q jarvis.log` then `git add -A` will **re-add it** if the working file still exists (the next `add -A` re-stages it). The commit then still contains it. **Fix:** `rm -f jarvis.log nul` (delete from disk FIRST), then `git rm --cached`, then add, commit, push. Verify via `git ls-tree -r HEAD --name-only | grep jarvis.log` → must be empty, AND GitHub API `contents/jarvis.log` → 404.
  5. **Refuse secret-bearing local repos (the `tour` rule).** `tour` (Next.js) had a real `.env` and a 404 remote. **Do NOT push it** (leaks secrets + heavy `node_modules`). Instead mark it `local-only (secret-bearing; do not push)` in the index — per the file's own "strike-through, never silently drop" rule. The index is `tools/repo-index.md` in this repo.
  6. **The company repo uses cached GCM** (`git config credential.helper manager`) — a plain `git push origin master` works with no token echo. Create new GitHub repos via the API with the cached token (see the `GitHub repo creation via API token` pitfall). Verify the index on GitHub via `GET /repos/itsPremkumar/Hermes-Full-Autonomous-Company/contents/tools/repo-index.md` (API tree = authoritative; `raw.githubusercontent.com` shows stale CDN).
- **Public-repo sanitization is MANDATORY for this company repo** (it is public). Before committing any doc that came from a real machine run (e.g. the OpenClaw control guide), replace every real identifier with a placeholder. See `devops/openclaw-setup` → Pitfall 12 for the full guide-publishing pattern.

## $0-inference: the free AI provider catalog (zero-budget cost avoidance)
The single biggest recurring cost in any AI company is **LLM inference**. The company's
"no paid API key" rule means high-volume / non-critical traffic MUST route through
**completely free providers** (no credit card, no paid key). When the user asks for the
"completely free AI models / free providers" list — or wants it documented "with or without
OmniRoute" for the money machine — build a **source-verified free-provider catalog** and wire
it into the company's `docs/` (the OS source of truth) plus a standalone repo.

**Authoritative source = the provider gateway's OWN source catalog, not its marketing README.**
For OmniRoute, the canonical machine-readable list is `open-sse/config/freeModelCatalog.data.ts`
on `github.com/diegosouzapw/OmniRoute` (the `FREE_MODEL_BUDGETS` array; each row has `provider`,
`modelId`, `displayName`, `freeType`, `tos`). Its human-readable companion is
`docs/reference/FREE_TIERS.md`. Always pull the DATA file, not the README, for real model IDs.

**Two question-shapes and how to split:**
- `freeType: "keyless"` → needs **no API key**, BUT several still require a host **login/cookie**
  (Google Antigravity, Qwen-web, Meta Muse, DuckDuckGo, Blackbox, OpenCode). These are NOT
  "no sign-in" — put them in a separate **Tier B** and flag `tos: "avoid"`.
- `freeType: "recurring-uncapped"` → permanently free, no token cap, rate-limited (Pollinations,
  Puter, GLM-CN/Z.AI, OpenCode Zen, Kilo-gateway free, SiliconFlow, Tencent, Baidu). These are
  the real **Tier A** (truly anonymous). Prefer `tos: "ok"` / `"caution"`; skip `avoid` in prod.

**Deliverable shape (verified 2026-07-15):**
1. A `README.md` catalog with: zero-budget framing, a **"always re-check the latest upstream
   catalog + each provider's latest docs"** golden rule, the Tier A (anonymous) and Tier B
   (login-gated) tables with **real model IDs**, and **both usage paths** — (a) WITH OmniRoute
   (`http://localhost:20128/v1`, `model: auto`) and (b) WITHOUT OmniRoute (direct per-provider
   free endpoints). MIT LICENSE.
2. Push to a **standalone repo** `itsPremkumar/omniroute-free-ai-providers` (API create + git
   push as `itsPremkumar`).
3. ALSO add the same file into the **company repo** as `docs/free-ai-providers.md` and add a
   short pointer from `docs/model-registry.md` (the routing rules already reference the
   OpenRouter-free-tier-via-OmniRoute path) so the OS source of truth links the zero-cost catalog.
4. Label all data a **snapshot** (OmniRoute's last research refresh: 2026-06-17, shipped
   v3.8.40+) and tell the reader free tiers/ToS change constantly.

**Why this matters for the company:** point every agent at the single OmniRoute endpoint +
`model: auto`; OmniRoute's smart routing + RTK/Caveman compression (~15–95% token savings)
stretch free quotas, keeping the whole inference pipeline at **$0**. The catalog is a component
of the cost-avoidance strategy, not a one-off doc. Full technique + the exact curl extraction
recipe: references/free-ai-provider-catalog.md.

## Support files
- references/git-credential-fix.md — kill the x-access-token account-picker modal.
- references/push-secret-scan-block.md — redact + rewrite history when a secret is committed.
- references/verification-unverified-flag.md — why the "unverified" loop happens and how to clear it.
- references/agent-native-channels.md — ClawHub + Moltbook publish/distribute flow, the Moltbook 400 link fix, and the monorepo→per-project GitHub repo split (verified this session).
- references/stack-architecture-control.md — CANONICAL control model: Hermes=1st boss (self-improving) → commands Paperclip (2nd boss/ops) + OpenClaw (channel); verified Paperclip/OpenClaw command maps, GitHub-API facts bank, and the 3 human money-gates.
- references/agent-marketplace-research-2026-07.md — HYRVE AI, The Colony, AgenC, Agoragentic, ai-sns platforms.
- references/inventory-2026-07.md — live ClawHub skills, 12 GitHub product repos, Moltbook state, open money gates (baseline snapshot).
- references/clawhub-batch-publishing.md — the generator-template + content-quality rules + publish loop for creating 5+ ClawHub skills per session.
- references/clawhub-batch-upgrade.md — the 4-pass script pattern (generate docs → push repos → republish ClawHub → update Moltbook drafts) for upgrading all N skills at once, with the exact `generate_v2_docs.py` / `push_all_v2.py` / `republish_all_v2.py` / `update_moltbook_drafts_v2.py` skeletons + the 14-check temp-verify harness.
- references/clawhub-inspect-audit.md — why `clawhub inspect` gives FALSE NEGATIVES (the `@` prefix, `AMBIGUOUS_SKILL_SLUG` slug collisions) and the reliable web-page HTTP-200 audit pattern.
- references/portfolio-verification.md — the 7-axis `verify_product.py` harness: why it exists, the axes, canonical commands, and the session outcome (31/31 PASS).
- references/learned-skills-backup.md — what "Learned" means in the Hermes UI, the `skills/<category>/<name>/` backup pattern, `SKILLS_INDEX.md` format, and the ad-hoc verify steps.
- references/github-api-windows-reliability.md — GitHub REST API silent-failure traps on this Windows/MSYS box: topics need a separate `/topics` endpoint + preview header, `PUT /contents` often fails to persist (use git clone+push), `raw.githubusercontent.com` CDN shows stale content (verify via API tree), token-path MSYS→uv boundary, em-dash JSON corruption.
- references/money-pipeline-generators.md — the money/ generator pattern (idea bank → pipelineN_*.py with self-test → run_all.py orchestrator + INCOME_DASHBOARD.md), the f-string traps, and the validated 2026 income figures used for pricing.
- scripts/verify-adhoc.py — template for inline ad-hoc verification (no temp file).
- scripts/backup_learned_skills.py — copies all Hermes learned skills into `skills/` + writes `SKILLS_INDEX.md` / `usage_snapshot.json` (run, then `git add skills/ && commit && push`).
- templates/product-package.md — Gumroad product package skeleton (PRODUCT.md + LISTING.txt).
- references/free-ai-provider-catalog.md — $0-inference: how to pull OmniRoute's source `freeModelCatalog.data.ts`, split Tier A (anonymous) vs Tier B (login-gated), document both OmniRoute + direct paths, and publish to the standalone repo + company `docs/`.
- references/autonomous-website-money-loop.md — the complete documented autonomous-website
  money system (sproutern template): one-time human setup, daily agent loop, SEO/GEO/AEO,
  Monetag-as-AdSense-fallback, multi-site free scaling. Reuse as the per-site template.
