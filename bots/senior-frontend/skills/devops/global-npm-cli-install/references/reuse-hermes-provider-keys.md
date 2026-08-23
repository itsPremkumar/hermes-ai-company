# Reuse Hermes's stored provider keys for a child tool (masked, never echoed)

A freshly installed agent/CLI (e.g. prime-agent) needs a model/API key to run. You must NOT ask the user to paste secrets and must NOT echo them. Hermes already holds many provider keys. Reuse one the child tool accepts.

## Where Hermes stores keys
- `C:\Users\PREM KUMAR\AppData\Local\hermes\.env` — key=value lines, MANY have LEADING SPACES, some commented out (`# KEY=...`).
- `C:\Users\PREM KUMAR\AppData\Local\hermes\auth.json` — `credential_pool` entries hold metadata + `secret_fingerprint` only (no plaintext secret).

## Masked scan (no secret ever printed)
```bash
# active (uncommented) provider keys present in .env:
grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" \
  | grep -E '^\s*(OPENCODE_API_KEY|HF_TOKEN|OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|GEMINI_API_KEY)=' \
  | sed -E 's/=.*/= (len>0, hidden)/'

# which providers Hermes knows (auth.json credential_pool, metadata only):
node -e 'const j=require(process.env.USERPROFILE+"/AppData/Local/hermes/auth.json");for(const k in (j.credential_pool||{})){const e=j.credential_pool[k][0]||{};console.log(k,"->",Object.keys(e).filter(x=>x!=="secret_fingerprint").join(","))}'
```

## Findings on THIS box (prime-agent run, 2026-08-07)
- `OPENROUTER_API_KEY` is commented out in `.env`; `auth.json` holds it only as `secret_fingerprint`. NOT recoverable as plaintext -> OpenRouter can't be sourced this way (it was the user's first choice).
- Plaintext-recoverable keys that child tools accept:
  - `OPENCODE_API_KEY` -> prime-agent provider `opencode` (OpenCode Zen).
  - `HF_TOKEN` -> prime-agent provider `huggingface`.
- Both tested: prime-agent authenticated successfully but returned provider-side billing errors:
  - OpenCode Zen: `401 No payment method` (account has no card).
  - HuggingFace: `402 monthly credits depleted`.

## Pass the key to the child WITHOUT echoing it
```bash
KEYVAL=$(grep -vE '^\s*#' "$USERPROFILE/AppData/Local/hermes/.env" \
  | grep -E '^\s*OPENCODE_API_KEY=' | tail -1 \
  | sed -E 's/^[[:space:]]*OPENCODE_API_KEY=[[:space:]]*//; s/[[:space:]]*$//; s/^"|"$//g')
[ -z "$KEYVAL" ] && { echo "key empty"; exit 3; }
OPENCODE_API_KEY="$KEYVAL" prime-agent --provider opencode -p "Reply with exactly the single word PONG." 2>&1 | tail -40
```
- Regex must use `^\s*KEY=` (leading spaces in Hermes `.env`).
- Billing errors (401/402) mean the ACCOUNT is unpaid, not that install/run failed. Report as "agent works, provider account needs funding" and offer: fix payment, top-up, a fresh key file (`~/.openrouter_key`), or a local model (Ollama/LM Studio).

## If no usable key
Offer the user to drop a fresh key into a FILE (never chat): e.g. `echo *** > "$USERPROFILE/.openrouter_key"` then read it the same masked way.
