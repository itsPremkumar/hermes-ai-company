# Reuse Hermes's Nous key for an external MCP server (hy3:free, $0)

## Problem
An external server (OpenSpace, a custom FastMCP agent) needs an LLM. You don't want
a separate OpenRouter/OpenAI key. Hermes already runs `tencent/hy3:free` for free via
the Nous inference API. Reuse that key.

## Where the key actually is
Hermes's `.env` (`~/AppData/Local/hermes/.env`) has `ANTHROPIC_AUTH_TOKEN` but it is a
**6-char placeholder** — useless. The real key is in:

```
~/AppData/Local/hermes/shared/nous_auth.json
  access_token        ~1745 chars (the Bearer token)
  inference_base_url  https://inference-api.nousresearch.com/v1   (already OpenAI-style)
  expires_at          ISO timestamp — token rotates; re-read the file each launch
```

## Wiring (launcher snippet)
Put this in the server's bash launcher (NOT via `hermes mcp add --env`, which folds into args):

```bash
NOUS_AUTH="$HOME/AppData/Local/hermes/shared/nous_auth.json"
if [ -f "$NOUS_AUTH" ]; then
  _j="$(cat "$NOUS_AUTH")"
  export OPENSPACE_LLM_API_KEY="$(printf '%s' "$_j" | python -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)"
  _b="$(printf '%s' "$_j" | python -c "import sys,json;print(json.load(sys.stdin).get('inference_base_url',''))" 2>/dev/null)"
  case "$_b" in */v1|*/v1/) OPENSPACE_LLM_API_BASE="$_b";; */) OPENSPACE_LLM_API_BASE="${_b}v1";; "") OPENSPACE_LLM_API_BASE="https://inference-api.nousresearch.com/v1";; *) OPENSPACE_LLM_API_BASE="${_b}/v1";; esac
  export OPENSPACE_LLM_API_BASE
fi
export OPENSPACE_MODEL="openrouter/tencent/hy3:free"
```

For OpenSpace specifically the env vars are `OPENSPACE_LLM_API_KEY` / `OPENSPACE_LLM_API_BASE`
/ `OPENSPACE_MODEL` (Tier-1 override wins over provider-native vars).

## Verified behavior
- `hermes mcp test openspace` -> `Connected`, `Tools discovered: 6`.
- Live `execute_task` log proves the model is reached:
  `LiteLLM completion() model= tencent/hy3:free; provider = openrouter`
  with NO 401/auth error.
- The Nous token expires; because the launcher re-reads `nous_auth.json` every launch,
  it automatically picks up Hermes's refreshed key. No manual key rotation needed.

## Caveats
- hy3:free on the free tier is SLOW: ~2-3 min per agent iteration. A trivial 8-iteration
  task took ~9 min end-to-end. Keep delegated tasks short or warn the user.
- `inference_base_url` is already `.../v1`; the `case` guard prevents a double `/v1/v1`
  (a bug seen when naively appending `/v1`).
- This is the SAME model Hermes uses, so concurrent Hermes + server use shares the Nous
  free quota — watch rate limits on a 6 GB RAM box.
