#!/usr/bin/env bash
# prompt-refine helper — CALLS THE MODEL HERMES IS ALREADY CONFIGURED WITH
# (zero extra cost, works for every user). Reads provider/base_url/api_key/model
# from ~/.hermes/config.yaml; if that is a local Ollama placeholder and a real
# provider key is in env, falls back to OpenRouter free models. Retries on 429
# and tries several free slugs. Fast-fails (<=~5s) on a dead endpoint.
#
# Usage: refine.sh "raw prompt"   (or: refine.sh < file.txt)
# Exit: 0 ok | 1 no input | 2 endpoint unreachable | 3 empty response

set -uo pipefail

if [ "$#" -ge 1 ]; then PROMPT="$*"; else PROMPT="$(cat)"; fi
if [ -z "${PROMPT// /}" ]; then echo "ERROR: no prompt provided" >&2; exit 1; fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
CONFIG="$HERMES_HOME/config.yaml"
PYBIN="$(command -v python || command -v python3 || echo python)"

BASE_URL="http://127.0.0.1:11434/v1"
API_KEY="ollama"
MODEL="moondream"

if [ -f "$CONFIG" ]; then
  _bu="$(grep -E '^\s*base_url:' "$CONFIG" | head -1 | sed 's/.*:[[:space:]]*//')"
  _ak="$(grep -E '^\s*api_key:' "$CONFIG" | head -1 | sed 's/.*:[[:space:]]*//')"
  _md="$(grep -E '^\s*default:' "$CONFIG" | head -1 | sed 's/.*:[[:space:]]*//')"
  [ -n "$_bu" ] && BASE_URL="$_bu"
  [ -n "$_ak" ] && API_KEY="$_ak"
  [ -n "$_md" ] && MODEL="$_md"
fi

# If configured key is a placeholder/ollama and a real key exists, prefer it so
# we never block on a dead local server.
if [ "$API_KEY" = "ollama" ] || [ -z "$API_KEY" ]; then
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    BASE_URL="https://openrouter.ai/api/v1"
    API_KEY="$OPENROUTER_API_KEY"
    [ "$MODEL" = "moondream" ] && MODEL="meta-llama/llama-3.2-3b-instruct:free"
  elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    BASE_URL="https://api.anthropic.com/v1"
    API_KEY="$ANTHROPIC_API_KEY"
  fi
fi

SYSTEM="You are a prompt editor. Rewrite the user's instruction so it is grammatically correct, clearly structured, and unambiguous. Preserve ALL intent, requirements, constraints, and tone. Do NOT add new tasks or change the meaning. Return ONLY the improved prompt text — no commentary, no quotes, no preamble."

AUTH_HEADER="Authorization: Bearer $API_KEY"

if [ "$API_KEY" = "ollama" ] || [ "$MODEL" = "moondream" ]; then
  MODELS=("meta-llama/llama-3.2-3b-instruct:free" "meta-llama/llama-3.3-70b-instruct:free" "qwen/qwen3-next-80b-a3b-instruct:free")
else
  MODELS=("$MODEL")
fi

REFINED=""
for MODEL in "${MODELS[@]}"; do
  for attempt in 1 2 3; do
    BODY="$($PYBIN - "$PROMPT" "$SYSTEM" "$MODEL" <<'PY'
import sys, json
p, s, m = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({"model": m, "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}], "temperature": 0.2}))
PY
)"
    RESP="$(curl -s --max-time 30 -X POST "$BASE_URL/chat/completions" -H 'Content-Type: application/json' -H "$AUTH_HEADER" -d "$BODY")"
    if [ -z "$RESP" ]; then echo "ERROR: endpoint unreachable at $BASE_URL" >&2; exit 2; fi
    REFINED="$(printf '%s' "$RESP" | $PYBIN -c "import sys,json
try:
    d=json.load(sys.stdin)
    if 'choices' in d: print(d['choices'][0]['message']['content'].strip())
    else: print('')
except Exception: print('', end='')" 2>/dev/null)"
    if [ -n "${REFINED// /}" ]; then break 2; fi
    if printf '%s' "$RESP" | grep -q '"code":429'; then sleep 6; continue; fi
    break
  done
done

if [ -z "${REFINED// /}" ]; then echo "ERROR: model returned empty/invalid response" >&2; exit 3; fi
printf '%s\n' "$REFINED"
exit 0
