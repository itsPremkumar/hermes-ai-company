# OmniRoute — No-Key / No-Signup Free Model List (snapshot)

Source of truth: `open-sse/config/freeModelCatalog.data.ts` in the OmniRoute repo
(456 models total). The catalog tags each model with `freeType`. Only `keyless` and
`recurring-uncapped` qualify as "no API key / no signup" friendly.

## Snapshot (v3.8.48 era, 2026-07)

### KEYLESS — no API key required (109 models / 14 providers)
| Provider | Prefix | Models | Notes |
|---|---|---|---|
| Pollinations | `pol/` | 24 | GPT-5, Claude, Gemini, DeepSeek, Llama 4 — **no key, no signup** |
| OpenCode | `opencode/` | 7 | no-auth tier — **no key** |
| UncloseAI | `un/` | 3 | no signup |
| Puter | `put/` | 33 | no key |
| DuckDuckGo Web | `ddg/` | 6 | Duck.ai — no key (ToS caveat) |
| Blackbox | `bb/` | 6 | no key (ToS caveat) |
| Muse Spark Web | `muse/` | 3 | no key |
| Qwen Web | `qw/` | 3 | no key (ToS caveat) |
| AGY / Antigravity | `agy/` | 16 | Claude/Gemini/GPT-OSS — no key (ToS caveat: proxy discouraged) |
| HackClub | `hc/` | 3 | no key |
| FriendliAI | `fr/` | 2 | no key |
| iFlytek | `if/` | 1 | no key (ToS caveat) |
| Liquid | `li/` | 1 | no key |
| SparkDesk | `sd/` | 1 | no key |

### UNCAPPED — permanently free, rate-limited (28 models / 6 providers)
| Provider | Prefix | Models |
|---|---|---|
| baidu | — | 1 (ERNIE) |
| glm-cn (Z.AI) | `glm/` | 3 |
| kilo-gateway | `kilo/` | 7 |
| opencode-zen | `oz/` | 6 |
| siliconflow | `sf/` | 10 |
| tencent | `ten/` | 1 |

## The "$0 Free Stack" (recommended combo for $0/mo)
```
1. pol/gpt-5            (Pollinations — no key, no signup)
2. opencode/...         (OpenCode — no auth)
3. kr/claude-sonnet-4.5 (Kiro — ~50 credits/mo, free account)
4. if/kimi-k2-thinking  (Qoder — unlimited, free account)
5. qw/qwen3-coder-plus  (Qwen — unlimited, free account)
+ Compression: aggressive (~50%) → doubles your free quota
```

## Caveats worth repeating
- Several `keyless` providers have ToS clauses discouraging third-party proxy use
  (AGY, Blackbox, DuckDuckGo, Muse Spark, Qwen Web, iFlytek, Coze). Personal/local use
  is fine; just be aware.
- `one-time-initial` freeType = needs a FREE SIGNUP to claim credit (agentrouter, together,
  deepseek, vertex, etc.) — NOT "no signup".
- Always verify against live catalog via `scripts/enumerate_free_models.py`; counts drift
  between releases.
