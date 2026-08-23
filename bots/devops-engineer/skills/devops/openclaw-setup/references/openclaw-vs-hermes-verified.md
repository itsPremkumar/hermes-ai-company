# OpenClaw vs Hermes Agent — VERIFIED facts (July 2026)

Live GitHub API pull on 2026-07-14:
`timeout 20 curl -s "https://api.github.com/repos/<owner>/<repo>"` → parse
`stargazers_count`, `license.spdx_id`, `open_issues_count`, `created_at`, `language`.

| Field | OpenClaw (`OpenClaw/OpenClaw`) | Hermes (`NousResearch/hermes-agent`) |
|---|---|---|
| Stars | 382,920 | 214,750 |
| License | NOASSERTION (custom — NOT MIT) | MIT |
| Open issues | 6,624 | 24,213 |
| Language | TypeScript | Python |
| Created | 2025-11-24 | 2025-07-22 |
| Homepage | openclaw.ai | hermes-agent.nousresearch.com |

## OpenClaw verified capabilities (capability list, 2026-07-14)
- web.search / web.fetch ✅ (real internet)
- model.run (tencent/hy3:free via OpenRouter) ✅
- image.generate/edit/describe, video.generate/describe ✅ (need provider key)
- tts / audio.transcribe ✅ ; embedding.create ✅
- Telegram channel: LIVE & connected (bot @prem123aibot, polling, "works")
- browser plugin ✅ enabled; codex-supervisor ❌ disabled; admin-http-rpc ❌ disabled
- Agent file/exec write: ❌ PROVEN ABSENT (agent returned code but refused to save file)

## Architecture truth (vs AI-generated comparisons)
- OpenClaw = multi-channel gateway / orchestrator (WhatsApp, Telegram, Discord,
  iMessage, Signal, Slack, Teams, Matrix, Zalo, Google Chat...). ClawHub =
  3,286–5,700+ community skills. Heavier footprint.
- Hermes = self-improving headless runtime; parent-subagent model; lean MEMORY.md +
  SQLite FTS memory; runs on $5 VPS / serverless / Pi-class; MIT; 80+ curated
  skills; builds its own.
- Both are COMPLEMENTARY layers, not rivals. On this host: Hermes = brain+hands
  (does work/learning); OpenClaw gateway = chat door (Telegram).

## ⚠️ Recurring AI-comparison hallucination (seen in 3 pasted docs)
- Hermes star count stated as 30k → 30k → 66k (all WRONG; real 214,750).
- OpenClaw license claimed "MIT" (WRONG; it's NOASSERTION/custom).
- Hermes "zero stale issues" (WRONG; 24k+ open).
- Hermes min spec "4vCPU+16GB + RL pipeline" (WRONG; lightweight $5 VPS).
- Hermes 3 "3B/8B" (WRONG; Llama 3.1 8B/70B/405B).
- TOI 2026-07-14 confirms Nous $1.5B valuation raise; "$75M round" unverified.
- Real models confirmed: GPT-5.6 (Luna), Meta Muse Spark 1.1.
- OpenClaw rename: Clawdbot → Moltbot (Jan 27 2026, Anthropic trademark) → OpenClaw.
  Creator Peter Steinberger joined OpenAI Feb 2026; project lives in a foundation.

## Verification method (reuse — also in `verify-ai-claims` skill)
1. GitHub stats via API (above).
2. Narrative/claim cross-check: `curl -s "https://r.jina.ai/https://html.duckduckgo.com/html/?q=<URLENCODED>"`
   — Jina renders DDG without the bot-block Google/Bing throw.
3. Article links in a paste: fetch via `https://r.jina.ai/<URL>` to confirm they
   exist and what they actually say (don't trust the citation's paraphrase).
4. Flag every discrepancy in a Claim | Verdict | Evidence table before acting.
