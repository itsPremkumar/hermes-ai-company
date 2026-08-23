# Hermes model-catalog snapshot (free-llm-router)

Safe, copy-paste `models:` list for the `free-llm-router` Hermes provider block.
Every id is quoted because it contains `:` (e.g. `pollinations_text:openai-fast`),
which YAML would otherwise parse as a mapping. Generated from
`free_llm_router.catalog.all_models()` on 2026-07-20 (58 entries: the `free`
catch-all + 57 `provider:model` pairs).

```yaml
models:
  - "free"
  - "pollinations_text:openai"
  - "pollinations_text:openai-fast"
  - "pollinations_text:openai-large"
  - "pollinations_text:qwen-coder"
  - "pollinations_text:mistral"
  - "pollinations_text:deepseek"
  - "pollinations_text:grok"
  - "pollinations_text:gemini-flash-lite-3.1"
  - "pollinations_text:perplexity-fast"
  - "pollinations_text:perplexity-reasoning"
  - "opencode:kimi-k2.6"
  - "opencode:kimi-k2.7-code"
  - "opencode:glm-5.2"
  - "opencode:glm-5.1"
  - "opencode:glm-5"
  - "opencode:mimo-v2.5-pro"
  - "opencode:mimo-v2.5"
  - "opencode:minimax-m3"
  - "opencode:minimax-m2.7"
  - "opencode:gpt-5"
  - "opencode:gpt-5.1"
  - "opencode:gpt-5.2"
  - "opencode:gpt-5.3-codex"
  - "opencode:claude-opus-4-6"
  - "opencode:claude-sonnet-4-6"
  - "opencode:claude-haiku-4-5"
  - "opencode:deepseek-r1"
  - "opencode:deepseek-v3"
  - "opencode_go:kimi-k2.6"
  - "opencode_go:kimi-k2.7-code"
  - "opencode_go:glm-5.2"
  - "opencode_go:mimo-v2.5-pro"
  - "opencode_go:minimax-m3"
  - "opencode_go:gpt-5"
  - "opencode_go:gpt-5.1"
  - "pollinations_gen:openai-fast"
  - "pollinations_gen:openai"
  - "pollinations_gen:mistral"
  - "pollinations_gen:deepseek"
  - "pollinations_gen:qwen-coder"
  - "pollinations_gen:grok"
  - "pollinations_gen:gemini-flash-lite-3.1"
  - "freemodel_dev:auto"
  - "duckduckgo:gpt-4o-mini"
  - "duckduckgo:claude-3-haiku"
  - "duckduckgo:llama-3.1-70b"
  - "duckduckgo:mixtral-8x7b"
  - "mimocode:mimo-v2.5-pro"
  - "mimocode:mimo-v2.5"
  - "mimocode:mimo-v2-pro"
  - "mimocode:mimo-v2-omni"
  - "mimocode:mimo-v2-flash"
  - "kilocode:kilo-auto/free"
  - "kilocode:stepfun/step-3.7-flash:free"
  - "kilocode:minimax/minimax-m2.5:free"
  - "kilocode:nvidia/nemotron-3-super-120b-a12b:free"
  - "kilocode:arcee-ai/trinity-large-preview:free"
```

Provider notes (India, 2026-07-20): only `pollinations_text:*` actually answer
anonymously. `opencode*`, `kilocode*`, `duckduckgo`, `mimocode`, `freemodel_dev`
are catalogued for portability but are key-gated / geo-blocked from this host.
