---
name: open-source-stack-research
description: Build a verified open-source tool/agent stack for a given function or company blueprint. Use when a user asks "find all free projects for X", "what open-source tools do I need for Y", "search for the best project for Z", or wants a department-by-department tool map. Emphasizes LIVE GitHub verification, honest canonical-vs-verified marking, and the rate-limit workaround.
---

# Open-Source Stack Research

The user wants free, self-hostable, open-source projects (MIT/Apache/GPL/BSD preferred) mapped to
functions or company departments. Goal: a customizable, $0-software-cost stack — NOT a SaaS list.

## When to use
- "find all the free projects for an AI company / video gen / telecalling / crawling"
- "what tools does this department need"
- "search for the best web crawler project and give me the link"
- Building/maintaining a company blueprint folder (department → project map)

## Steps
1. **Search GitHub API** for the category. Use `curl -sL "https://api.github.com/..."`:
   - repo: `https://api.github.com/repos/<owner>/<repo>`
   - search: `https://api.github.com/search/repositories?q=<query>&sort=stars&per_page=N`
   - For multi-repo star/license pulls, loop with `urllib.request` in python and **sleep 0.3–1.5s
     between calls** (see pitfall).
2. **Record per project**: name, ★ (live), license (SPDX), link, one-line role. Prefer the
   `license.spdx_id` field. Flag AGPL/NOASSERTION (not OSI) so the user knows obligations.
3. **Mark verification honestly**:
   - `✅` = star count pulled live this session
   - `(canonical)` = well-known repo, NOT re-verified (rate-limited / not checked)
   Never present an unverified star count as fact.
4. **Check the homepage/link resolves** (optional): `curl -s -o /dev/null -w "%{http_code}"`.
5. **Categorize by function**, not just dump. For a company: Executive, Research, Engineering,
   Marketing, Sales/CRM, Finance, Voice, Support, Infra, Security, plus a "compulsory baseline"
   (IAM, secrets, DB, storage, observability, deploy, CRM, ERP, docs, automation, support, analytics).
6. **Flag experimental/concept projects** explicitly (e.g. "Paperclip Maximus = concept only, no
   production repo"; tiny repos = evaluate maintenance before prod). This honesty is expected.
7. **Output shape**: a master index + per-category files; each file = Role / Recommended projects
   (★, license, link) / Why / Integration. Keep it forkable and customizable.

## GAP-VALIDATION — prove the gap is REAL before proposing to BUILD
When the user asks "what should we build", "is this gap taken", or "find the best problem",
do NOT just list existing projects — prove the space is not already solved by a mature one.
This is a distinct step from *finding* projects (above); it is the *build-vs-skip* decision.
1. **Topic-count scan**: `https://github.com/topics/<topic>` → read "Here are N repos" + top-3
   stars. Low N + tiny top stars = nascent/unsolved. (e.g. `memory-server`=24 repos is the real
   candidate space for "agent memory server"; `ai-agents`=55k is saturated.)
2. **False-friend detection**: a topic that SOUNDS like your gap may be another domain. OPEN the
   top repos and read descriptions. Classic traps: `shared-memory` = OS IPC (iceoryx/cpp-ipc),
   NOT agent memory; `knowledge-graph` = code-to-graph visualizers, NOT memory substrates.
3. **Competitor-maturity check** on nearest 2-3: stars, last-commit date, issues/PRs, license
   (MIT vs open-core), and SINGLE-agent/user vs truly MULTI-AGENT SHARED.
4. **Decision rule**: gap is OPEN only if no candidate is (a) adopted (>>1k★/real use),
   (b) truly multi-agent shared, (c) MIT/Apache not open-core. If open → BUILD but state your
   WEDGE (what you do they don't: e.g. conflict detection, fully-local embeddings, MIT).
Full recipe + 2026-07-18 evidence in `references/gap-validation.md`.

## PITFALL — GitHub API rate limiting (403)
Unauthenticated `api.github.com` calls get `HTTP Error 403: rate limit exceeded` after ~50–60
requests/IP, sometimes immediately on a shared IP. Workarounds that worked:
- Add a `User-Agent` header: `urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})`.
  (Helps but does NOT eliminate the limit.)
- **Space calls out** with `time.sleep(1.2)` between requests in python loops.
- If fully blocked: pause, then retry later; OR verify a smaller critical subset only; OR note
  repos as `(canonical)` and move on. Never invent star counts to fill gaps.
- The `curl` HTML site scrape (duckduckgo etc.) is unreliable for structured data — prefer the API.

## PITFALL — verify the SPECIFIC repo, not just the search
`search/repositories` can return forks or near-names. Before citing a star count, confirm
`repos/<owner>/<repo>` returns the expected `full_name` and `description`. (e.g. "Agent-Reach" is
`Panniantong/Agent-Reach`, 54k★, MIT — not a lowercase variant.)

## PITFALL — "best project" needs a criterion
When asked "best crawler / best X", rank by: live stars, license (AGPL has obligations), maintenance
activity, and fit (AI-native vs legacy scraper). For web intelligence the consensus set is
Agent-Reach (social), Crawl4AI (local), Firecrawl (AI extraction), Browser Use (interactive),
SearXNG (private search). State the tier (must-have / enterprise / specialized).

## PITFALL — "open-source" claims are often FALSE; verify the LICENSE file
AI-generated comparisons (and marketing READMEs) routinely mislabel projects as free/OSS.
Before declaring a project usable for a license-clean (MIT/Apache) project, fetch the ACTUAL
license and read it:
- `fishaudio/fish-speech` shows `NOASSERTION` on GitHub but is the **Fish Audio Research
  License = NON-COMMERCIAL** (commercial use forbidden). REJECT for any published/commercial work.
- `debpalash/OmniVoice-Studio` is **AGPL-3.0** — network use forces source disclosure.
- `coqui-ai/TTS` (XTTS) is **MPL-2.0** (file-level copyleft) AND **archived**. REJECT for new builds.
- `microsoft/VibeVoice` had its **TTS code removed** by Microsoft — only ASR/Realtime remain, no cloning.
Verify via: `curl -s https://raw.githubusercontent.com/<owner>/<repo>/main/LICENSE | head` and
the `license.spdx_id` from the GitHub API. Flag NOASSERTION/AGPL/MPL/non-commercial explicitly.

## PITFALL — license-clean + RAM-fit is the real filter for low-spec machines
On a 6GB / no-GPU laptop the deciding constraint is model SIZE, not just license:
- Prefer tiny always-on models for default roles: `hexgrad/Kokoro-82M` (Apache-2.0, **312MB**) for
  narration (no cloning, built-in voices only).
- Clone engines must be loaded ON-DEMAND then UNLOADED: `swivid/F5-TTS` (MIT, ~1.3GB) or
  `resemble-ai/chatterbox` (MIT, ~1.8GB, HF-gated) or `QwenLM/Qwen3-TTS` 0.6B (Apache, ~1.7GB).
  Load ONE at a time; never stack TADA-3B / Chatterbox-Multilingual / Qwen-1.7B (OOM).
- Bundled "studios" like `jamiepine/voicebox` (MIT) are NOT pre-bundled with weights — models
  download on-demand from HF and are load/unload-able per engine via REST. Run headless
  (`python -m backend.main`) to skip the GUI and save RAM.
  - **Voicebox control surface (verified):** `POST /models/load` loads ONE engine (downloads first
    time), `POST /models/{name}/unload` frees its RAM without deleting weights, `POST /speak` and
    `POST /generate` do synthesis, built-in MCP server ships in `backend/mcp_server/`. Efficient
    pattern for low-RAM: wake backend → load one engine → generate → unload → kill process. See
    `references/voicebox-operational.md` for the full recipe + the `vibevoice-community` fork notes.
- **Corporate-owned model repos can be PULLED; permissive aggregators can't.** Microsoft deleted the
  TTS code from `microsoft/VibeVoice` (responsible-AI after misuse) but could NOT touch
  `jamiepine/voicebox` because the latter only aggregates third-party MIT/Apache engines. Prefer
  aggregator-style projects for longevity. The community fork `vibevoice-community/VibeVoice` (MIT)
  restored Microsoft's deleted TTS code, but its 1.5B model is too heavy for 6 GB laptops.
- Reject cloud/paid (ElevenLabs, Azure) and non-cloning tools mislabeled as TTS (RVC = voice
  conversion, not text-to-speech).

## Reusable knowledge bank
Condensed verified stacks live in `references/verified-stacks.md` (crawlers, voice, ERP/CRM,
agent frameworks, OpenClaw ecosystem). The **Voice cloning / realistic TTS** section there is a
license-verified, RAM-graded bank built from a full 2026-07 audit — reuse it directly instead of
re-researching. Update it as you verify new repos so future sessions start warm.
- `references/voicebox-operational.md` — Voicebox headless run + REST/MCP load-unload control surface,
  the `vibevoice-community` fork (restored TTS code), and the corporate-ownership resilience lesson.
  Use when the user wants to RUN a local voice stack, not just pick one.
- `references/gap-validation.md` — 4-step recipe to prove a product gap is NOT already solved
  before you propose building it (topic-count scan, false-friend detection, competitor-maturity
  check, wedge template). Use when the user says "find the best problem to build" / "is this
  gap taken". Evidence from the 2026-07-18 SAMM/shared-agent-memory investigation.
