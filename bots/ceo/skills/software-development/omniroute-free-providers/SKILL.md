---
name: omniroute-free-providers
description: >-
  Discover, verify, and route to COMPLETELY FREE (no signup, no API key, no OAuth)
  LLM/video providers exposed by the local OmniRoute gateway (C:/one/omniroute).
  Use when the user wants "free models with no signup", "anonymous AI providers",
  "test a free model end-to-end", or to wire a $0 LLM path into a pipeline.
  Covers the vetted noAuth / anonymousFallback provider list extracted from
  omniroute source, plus the run + chat/completions test flow. NOT for paid
  providers or anything needing an API key.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [llm, free-models, no-signup, omniroute, openrouter, agentic]
---

# OmniRoute — Completely Free (No-Signup) Model Providers

OmniRoute (C:/one/omniroute) is a local OpenAI-compatible gateway (Next.js app):
it exposes `/v1/chat/completions`, `/v1/models`, `/responses`, etc. on a port.
It bundles a large provider registry that includes several providers that need
NO API key, NO signup, NO OAuth — they work anonymously. This skill lists the
vetted ones (extracted from omniroute source `src/shared/constants/providers/`
at v3.8.46) and the test-run flow.

## The verified NO-SIGNUP / NO-KEY provider list

These are taken straight from the omniroute registry. All work without any
credential. (`noAuth: true` = keyless by design; `anonymousFallback: true` =
free tier served to anonymous requests.)

**Fully keyless (`noAuth: true`) — anonymous LLM:**
- **opencode** — OpenCode Free. Public endpoint `opencode.ai/zen/v1`. Kimi, GLM,
  Qwen, MiMo, MiniMax. Rate-limited.
- **duckduckgo-web** — DuckDuckGo AI Chat. Anonymous multi-model chat.
- **theoldllm** — The Old LLM (Free). GPT-5.4, Claude 4.6 Opus/Sonnet/Haiku + more.
  Auto-generates access tokens via embedded Playwright browser. No key.
- **chipotle** — Chipotle Pepper AI (Free). IPsoft Amelia. Anonymous sessions. Rate-limited.
- **mimocode** — MiMoCode (Free). Xiaomi MiMo models. Auto JWT via device fingerprint. Streaming.

**Anonymous fallback (`anonymousFallback: true`) — free tier, no account:**
- **opencode-zen** — `opencode.ai/zen` free models.
- **opencode-go** — `opencode.ai/go` free models.
- **pollinations** — keyless tier: `openai`, `openai-fast`, `openai-large`,
  `qwen-coder`, `mistral`, `deepseek`, `grok`, `gemini-flash-lite-3.1`,
  `perplexity-fast`, `perplexity-reasoning`. (Premium models like claude/gemini
  need a Pollinations key — skip those for the free path.)

**Free but NOT strictly no-signup (excluded from the keyless list):**
- **kilo** (`kilocode`) — anonymous fallback exists but primary path is device-OAuth.
- **puter** — free models but needs a free-account Auth Token.
- **auggie** — local CLI, needs `auggie login`.

**Video (free, no key):**
- **veoaifree-web** — Veo AI Free: VEO 3.1 / Seedance video gen, 6 req/hr per IP.

## How to run OmniRoute + do a free test call

The packaged `bin/omniroute.mjs` path in old `.bat` launchers is STALE — use the
real npm entry.

```bash
cd /c/one/omniroute/node_modules/omniroute/dist
# env lives at C:/Users/PREM KUMAR/.omniroute/.env (REQUIRE_API_KEY=false by default)
npm start          # -> node scripts/dev/run-next.mjs start
```

Then (once the server is listening, default port 20128 or per .env):

```bash
# list models (OpenAI-compatible)
curl -s http://127.0.0.1:20128/v1/models | head
# chat completion against a free provider, e.g. duckduckgo-web
curl -s http://127.0.0.1:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"duckduckgo-web","messages":[{"role":"user","content":"Say hi in one word."}]}'
```

Prefer one of the genuinely keyless providers (opencode, duckduckgo-web,
pollinations, mimocode) for a clean no-credential test.

## Pitfalls
- Old `start-omniroute.bat` references `bin/omniroute.mjs` which NO LONGER EXISTS
  in the installed package — use `npm start` in the `dist` dir instead.
- `REQUIRE_API_KEY` defaults to false in `C:/Users/PREM KUMAR/.omniroute/.env`,
  so anonymous requests are accepted. If a test returns 401/403, check that flag
  and that you are NOT passing a model that needs a key (e.g. pollinations' claude).
- Port may differ from 20128 — read it from `.env` (`OMNIROUTE_PORT` / `PORT`).
- This is a heavy Next.js app; first start is slow. Check
  `C:/one/paperclip-company/omniroute.log` for "Starting server..." / ready lines.
- `theoldllm` and `mimocode` mint ephemeral tokens internally; they may be slower
  or rate-limited. `duckduckgo-web` / `opencode` are the most reliable for a quick
  smoke test.

## See also
- `references/free-providers.md` — full extracted registry detail with model IDs
  and rate-limit notes.
