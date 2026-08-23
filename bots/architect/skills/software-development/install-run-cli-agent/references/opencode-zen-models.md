# OpenCode Zen — verified models (prime-agent session, 2026-08-07)

Base URL: `https://opencode.ai/zen/v1`
Auth: `Authorization: Bearer $OPENCODE_API_KEY`
List models: `GET /v1/models`  (returns openai-style list)
Chat: `POST /v1/chat/completions`

## Key facts
- The provider works WITHOUT a payment method IF you request a `-free` model explicitly.
- prime-agent defaults to a PAID model (claude/gpt) → returns `401 No payment method`. That is NOT an auth failure; force a free model with `--model <id>`.

## Free models — verified working (real chat completions returned)
- `deepseek-v4-flash-free`  (fast, good general)
- `mimo-v2.5-free`
- `nemotron-3-ultra-free`
- `laguna-s-2.1-free`  (returns clean short answers)
- `longcat-2.0-free`

## Free models — returned errors (do NOT use)
- `ling-3.0-flash-free`  → 404 "This model is unavailable for free"
- `north-mini-code-free` → 401 "Provider returned error"

## Paid models (need payment method on the OpenCode Zen account)
claude-opus-5 / claude-sonnet-5 / claude-haiku-4-5, gemini-3.1-pro / gemini-3.5-flash,
gpt-5.5 / gpt-5.6-* , grok-4.5, kimi-k2.5/k2.6, minimax-m2.5/m2.7, glm-5.x, qwen3.5/3.6-plus, big-pickle

## prime-agent invocation (free model, from a project dir)
```bash
cd C:\one
OPENCODE_API_KEY=<key> prime-agent --provider opencode --model deepseek-v4-flash-free -p "your task"
```
