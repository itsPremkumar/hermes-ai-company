# Free provider live-probe results (time/region SENSITIVE)

Re-run `scripts/probe_providers.py` from the host before trusting the catalog.
Status varies by IP/region and DRIFTS over time (providers add auth, trim their
anonymous tier, or go paid without notice). Two dated snapshots below, host IP
in India. **Always re-verify — do not trust a snapshot older than a few days.**

## SNAPSHOT 2026-07-20 (latest, corrects earlier)
Verified with live `curl` to each `/models` and a real chat round-trip.

### Working anonymously (keyless, no signup, $0)
| Provider | Endpoint | Result |
|---|---|---|
| `opencode` (Zen) | `https://opencode.ai/zen/v1/chat/completions` | ✅ 200, `cost:"0"`, NO key. Use the REAL `-free` model ids (P7): `deepseek-v4-flash-free`, `hy3-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free`, `big-pickle` (stealth). Earlier "401" was WRONG model names, not the endpoint. NOTE host is `opencode.ai` NOT `api.opencode.ai`. |
| `pollinations_text` | `https://text.pollinations.ai/openai` | ✅ 200. **Anon tier TRIMMED to `openai-fast` only** (GPT-OSS-20B; aliases `openai`, `gpt-oss`). Legacy ids (`deepseek`, `qwen-coder`, etc.) now 404 "legacy API deprecated for authenticated users — migrate to enter.pollinations.ai". |
| `kilocode` | `https://api.kilo.ai/api/openrouter/chat/completions` | ✅ `kilo-auto/free` returns text. Also lists `:free` models. |

### Now BLOCKED / gated (were once "free")
| Provider | Endpoint | Result 2026-07-20 |
|---|---|---|
| `freemodel_dev` | `api.freemodel.dev/v1` | ❌ `/models`=200 (gpt-5.6-luna/sol/terra) but chat=**403 "No valid credentials"** — key-gated now. (An earlier 500 was just "container instances exceeded" = overloaded, transient — not the same as gated. Distinguish overload from auth.) |
| `mimocode` | `mimo.mi.com` | ❌ now a **PAID one-time-purchase** product ("One-time purchase unlocks..."), no longer free. |
| `duckduckgo` | `duckduckgo.com/duckchat/v1/status` | ❌ protocol changed: returns obfuscated **`x-vqd-hash-1`** JS anti-bot challenge (was simple `x-vqd-4`). Solving needs a JS engine — not keyless-feasible from a plain HTTP client. |
| `pollinations_gen` | `gen.pollinations.ai` | ❌ HTTP 000 (unreachable from this IP). |
| `opencode_go` | `opencode.ai/zen/go/v1` | ❌ 401 for the tried model; use the `zen/v1` (`opencode`) path with `-free` ids instead. |

## How to re-probe (stdlib, no deps)
`python scripts/probe_providers.py` — prints per-host HTTP status. Use a short
per-host timeout (8-12s) and an overall cap (45-60s). Treat non-200 or empty as
DOWN. For each candidate: GET `/models` first, then send a real chat with a
model id FROM that list (never a guessed id — see P7).

## Omniroute source (authority for the list, NOT for live status)
`C:\one\omniroute\node_modules\omniroute\dist\open-sse\mcp-server\server.js`
- ~lines 38820-39640: `NOAUTH_PROVIDERS`; ~line 41256: `anonymousFallback:true`.
These flags are STALE/geo-blocked from this host — verify live, never trust.
