# OpenRouter-env cookbook reference

## Correct env vars for Claude Code (from official cookbook, verified working)

```bash
export OPENROUTER_API_KEY="sk-or-..."
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"   # NO /v1 suffix
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"        # NOT ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=***                              # Must be explicitly empty
```

## What each pitfall looks like

| Wrong env | Symptom |
|-----------|---------|
| `ANTHROPIC_BASE_URL=.../api/v1` | Claude Code says "model not found" — the URL path confuses routing |
| `ANTHROPIC_API_KEY=sk-or-...` (without AUTH_TOKEN) | 401 / model access errors; Claude Code reads the wrong var |
| `ANTHROPIC_API_KEY` unset (empty but not explicit) | "auth conflict" errors, cached Anthropic login interferes |

## Query live OpenRouter models

```bash
curl -s https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_KEY" \
| python3 -c "import sys,json; ms=json.load(sys.stdin)['data']; \
  [print(m['id'],'| free:',m['pricing']['prompt']=='0'and m['pricing']['completion']=='0') \
  for m in ms if 'tencent' in m['id'] or 'free' in m['id']]"
```

## Verify a specific model's cost

```bash
curl -s https://openrouter.ai/api/v1/models/tencent/hy3:free \
  -H "Authorization: Bearer $OPENROUTER_KEY"
# Expected: {"id":"tencent/hy3:free","pricing":{"prompt":"0","completion":"0"},"free":true}
```

## Claude Code version compatibility

Tested with `claude 2.1.183` on Windows/MSYS. The `claude/tengu` server
name appears in MCP initialize responses when routing through OpenRouter.
