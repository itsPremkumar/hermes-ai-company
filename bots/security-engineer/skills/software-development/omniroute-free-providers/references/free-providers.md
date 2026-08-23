# OmniRoute free-provider registry — extracted detail (v3.8.46)

Source: `node_modules/omniroute/dist/open-sse/mcp-server/server.js` and
`src/shared/constants/providers/noauth.ts`. Below are the keyless / anonymous
providers with their registry metadata and model lists, so a future session can
pick a model without re-reading the 95k-line bundle.

## noAuth: true (keyless by design)

### opencode (alias oc) — "OpenCode Free"
- website: https://opencode.ai  | serviceKinds: [llm]
- freeNote: public OpenCode endpoint with Kimi, GLM, Qwen, MiMo, MiniMax models.
- base endpoint: https://opencode.ai/zen/v1
- no signup, no API key. Rate limits apply.

### duckduckgo-web (alias ddgw) — "DuckDuckGo AI Chat"
- website: https://duckduckgo.com/duckchat  | serviceKinds: [llm]
- freeNote: anonymous access to multiple AI models via DuckDuckGo.
- best for a quick smoke test.

### theoldllm (alias tllm) — "The Old LLM (Free)"
- website: https://theoldllm.vercel.app  | serviceKinds: [llm]
- freeNote: GPT-5.4, Claude 4.6 Opus/Sonnet/Haiku, + more. No API key — tokens
  auto-generated via embedded Playwright browser instance.
- may be slower / rate-limited.

### chipotle (alias pepper) — "Chipotle Pepper AI (Free)"
- website: https://amelia.chipotle.com  | serviceKinds: [llm]
- freeNote: Chipotle's Pepper AI (IPsoft Amelia). Anonymous sessions, no API key.
  Reverse-engineered SockJS/STOMP protocol. Rate-limited.

### mimocode (alias mcode) — "MiMoCode (Free)"
- website: https://mimo.mi.com  | serviceKinds: [llm]
- freeNote: Xiaomi MiMo models via bootstrap JWT auth. No API key; auto-generates
  JWT via device fingerprint. Supports streaming.

### veoaifree-web (alias veo-free) — "Veo AI Free"
- website: https://veoaifree.com  | serviceKinds: [video]
- freeNote: VEO 3.1, Seedance. 6 requests/hour per IP. No auth.

## anonymousFallback: true (free tier, no account)

### opencode-zen (alias opencode-zen) — "OpenCode Zen"
- website: https://opencode.ai/zen

### opencode-go (alias opencode-go) — "OpenCode Go"
- website: https://opencode.ai/go

### pollinations (alias pol) — "Pollinations AI"
- website: https://pollinations.ai
- keyless tier models: openai, openai-fast, openai-large, qwen-coder, mistral,
  deepseek, grok, gemini-flash-lite-3.1, perplexity-fast, perplexity-reasoning.
- PREMIUM models (claude, gemini, midjourney) REQUIRE a Pollinations API key —
  do NOT use them for the no-signup path.

## Excluded (free but needs a credential — not strictly no-signup)
- kilocode: device-OAuth primary; anonymous fallback exists but not keyless.
- puter: free models but needs a free-account Auth Token (puter.com/dashboard).
- auggie: local CLI, needs `auggie login`.
- github-models / kilo: apikey / oauth respectively.

## Quick model pick for a test run
Most reliable keyless smoke test: `duckduckgo-web` or `opencode`.
Next best: `pollinations` with model `openai-fast` (or `deepseek`, `mistral`).
These need zero credentials and return OpenAI-compatible chat completions.
