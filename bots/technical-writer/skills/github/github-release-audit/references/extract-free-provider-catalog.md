# Extracting the authoritative no-auth / free provider catalog from an AI gateway

When a user asks "what providers are free with no API key / no signup?" for an AI
gateway/router repo (OmniRoute, OpenRouter, one-api, etc.), DO NOT trust the README marketing
numbers ("90+ free"). Read the source catalog. README counts conflate key-required tiers,
one-time signup credits, and keyless access.

## Worked example — OmniRoute (v3.8.40+ catalog, refreshed 2026-06-17)

### 1. Find the catalog
README cross-references the source of truth: `open-sse/config/freeModelCatalog.ts`.
That file re-exports per-model data from `open-sse/config/freeModelCatalog.data.ts`.

```bash
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/main/open-sse/config/freeModelCatalog.data.ts -o free.ts
grep -nE 'freeType: "(keyless|recurring-uncapped)"' free.ts
```

### 2. The three "free" buckets (freeType field)
- `recurring-daily` / `recurring-monthly` — real documented token budget (Mistral ~1B/mo, Gemini ~60M/mo). Often still needs an API key.
- `recurring-uncapped` — permanently free, no published token cap, rate-limited. e.g. SiliconFlow, GLM-CN/Z.AI, OpenCode Zen, Kilo-gateway, Tencent, Baidu. Some need a free account but NO paid key.
- `keyless` — no API key. BUT `keyless` != no sign-in. Several keyless providers still require a login/session cookie (Google Antigravity `agy`, Qwen-web, Meta Muse Spark, DuckDuckGo, Blackbox, OpenCode). Split them.

### 3. TOS field matters
Each entry has a `tos` verdict: `ok` / `caution` / `avoid` / `unknown`. A proxy/router user
should prefer `ok`/`caution`. `avoid` entries (Antigravity, Blackbox, DuckDuckGo, Qwen-web)
explicitly prohibit proxying — they exist in the catalog but are not recommended for a
self-hosted router.

### 4. Tier A — truly zero-auth, zero-signup (real model IDs from the catalog)
- Pollinations (keyless): openai, openai-fast, openai-large, qwen-coder, mistral, deepseek, grok, grok-large, kimi, glm, minimax, qwen-large, qwen-vision, mistral-large, + ~8 more (text/image/audio).
- Puter (keyless, 33): gpt-5.5/5.4/-mini/-nano, gpt-4o/-mini, o3, claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-7, gemini-3-flash/3.1-pro, deepseek-v4-pro/flash, grok-4.3/4.20, llama-4-scout/maverick, mistral-*, qwen3.6-plus, perplexity/sonar*.
- GLM-CN / Z.AI (recurring-uncapped, tos=ok): glm-4-flash, glm-4.5-flash, glm-4.7-flash.
- OpenCode Zen (recurring-uncapped): opencode/deepseek-v4-flash-free, opencode/nemotron-3-super-free, opencode/nemotron-3-ultra-free, opencode/mimo-v2.5-free, opencode/north-mini-code-free, opencode/big-pickle.
- Kilo-gateway free (recurring-uncapped): kilo-auto/free, stepfun/step-3.7-flash:free, poolside/laguna-m.1:free, poolside/laguna-xs.2:free, nvidia/nemotron-3-ultra-550b-a55b:free, nvidia/nemotron-3-super-120b-a12b:free, nex-agi/nex-n2-pro:free.
- SiliconFlow (recurring-uncapped): DeepSeek-V3.2, DeepSeek-V3.1, DeepSeek-R1, Qwen3-235B, Qwen3-Coder-480B, Qwen3-32B, Kimi-K2.5, GLM-4.7, gpt-oss-120b, ERNIE-4.5-300B.
- Tencent (recurring-uncapped): hunyuan-pro. Baidu (recurring-uncapped): ernie-4.0-8k.
- UncloseAI (keyless): Hermes-3-Llama-3.1-8B, qwen3.6:27b, gemma4:31b. Liquid (keyless): liquid-lfm-40b.

### 5. Tier B — keyless but REQUIRES login/session cookie (NOT "no sign-in")
`agy` (Google Antigravity, 16 models), `qwen-web`, `muse-spark-web` (Meta), `duckduckgo-web`,
`blackbox`, `opencode` (GitHub login), plus FriendliAI, iFlytek, Coze, NLPCloud, MonsterAPI,
Baichuan, FreeModel, PublicAI, Inference-Net, SenseNova, SparkDesk, T3-web. Most flagged avoid/caution.

### 6. Output to the user
- Split Tier A (truly zero-auth) from Tier B (login-gated keyless).
- State rate-limit caveat: uncapped = rate-limited, not heavy 24/7 load.
- Call out ToS `avoid` providers explicitly; recommend ok/caution for a self-hosted router.
- Offer a ready-to-paste connection config filtered to Tier A (or coding-only models).

## Generalization
For other gateways, look for files named like `*free*.ts`, `providerCatalog`, `freeModelCatalog`,
or a docs/reference/FREE_TIERS.md. The key insight: the source data file (not the README) has the
real `modelId` list and the free-type enum that lets you separate "no key" from "no sign-in".
