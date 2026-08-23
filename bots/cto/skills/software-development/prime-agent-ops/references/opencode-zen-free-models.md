# OpenCode Zen free models (verified 2026-08-07)

Endpoint: `GET https://opencode.ai/zen/v1/models` with `Authorization: Bearer <OPENCODE_ZEN_API_KEY>`.
The API is reachable and the key authenticates even when the account has no payment method
(the 401 only appears when you actually CALL a paid model via the chat endpoint).

## Free model ids (working)
- `deepseek-v4-flash-free`  — fast, good general
- `mimo-v2.5-free`
- `nemotron-3-ultra-free`
- `laguna-s-2.1-free`       — returned exactly "PONG" in test
- `longcat-2.0-free`

## Free model ids (BROKEN — do not use)
- `ling-3.0-flash-free`  → `404 ... This model is unavailable for free. The paid version ...`
- `north-mini-code-free` → `401 Provider returned error`

## Chat completion probe that works
```bash
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"Reply with exactly the single word PONG."}],"max_tokens":20}' \
  https://opencode.ai/zen/v1/chat/completions
```

## Note on prime-agent
prime-agent's default `opencode` model is PAID (claude/gpt family). On an account with no
payment method this surfaces as `401 No payment method`. Always pass `--model <free-id>`.
prime-agent passes the model id straight to `/zen/v1`, so any of the working free ids above work.

## Key recovery
Hermes stores `OPENCODE_ZEN_API_KEY` plaintext in `~/.hermes/.env` (uncommented, len 67).
Extract at runtime, never echo:
```bash
KEY=$(grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" | grep -E '^\s*OPENCODE_ZEN_API_KEY=' | tail -1 | sed -E 's/^[[:space:]]*OPENCODE_ZEN_API_KEY=[[:space:]]*//; s/[[:space:]]*$//; s/^"|"$//g')
```
OpenRouter is NOT recoverable from Hermes (only a secret_fingerprint is stored; `.env`'s
`OPENROUTER_API_KEY` is commented out).
