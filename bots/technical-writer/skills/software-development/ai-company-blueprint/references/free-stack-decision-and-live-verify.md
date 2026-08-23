# Free-Models-Only Software-Engineering Team (verified 2026-07-16)

When the user mandates **"free AI models only"** for building production software, the
standard "Claude Code + paid keys" path is OFF the table. This file records the decision
and the live-verified stack so future sessions start from the right place.

## Hard constraint
- **Claude Code requires an Anthropic API key (paid).** There is no free autonomous-coding
  tier. So "Claude Code + free models" is contradictory — Claude Code IS the paid part.
- **OpenHands CAN run on free/local models** (Ollama local, or OpenRouter free tiers).
- **Hermes (this agent) runs on free models** (e.g. `tencent/hy3:free` via OpenRouter —
  already used by the user's OpenClaw setup).

## The complete FREE team (verified live this session)
| Layer | Tool | Free? | Model source |
|---|---|---|---|
| Orchestrator/CEO | **Hermes** | ✅ (`hy3:free`) | OpenRouter free |
| Coding agent | **OpenHands** | ✅ | Ollama local OR OpenRouter free (`qwen2.5-coder`, `deepseek-coder`, `mistral`) |
| Engineering playbooks | **gstack** (reference) | ✅ MIT | — |
| Lean-code discipline | **ponytail** (optional) | ✅ | — |
| Agent framework (build-with) | **LangGraph** | ✅ OSS | bring your own free key |
| Backend | **Supabase** free tier OR self-host Postgres | ✅ | — |
| Frontend | **Next.js** | ✅ OSS | — |
| Automation | **n8n** (self-host) | ✅ fair-code | — |
| Observability | **Grafana + Prometheus + Loki** (self-host) | ✅ OSS | — |
| Team orchestration (heavy) | **Paperclip** (self-host) | ✅ MIT | — |

**Excluded because they break "free only":** Claude Code (paid key), Dify cloud beyond
free tier. **Dropped as maintenance/overkill:** Microsoft AutoGen (in maintenance mode —
last real commit 3 months ago as of 2026-07-16), CrewAI (role-play, not production-grade
for app code), the 20-repo compulsory baseline (Keycloak/MinIO/etc. — overkill for a laptop;
Supabase covers most).

## Decision rule
- The *team* = **Hermes + OpenHands + gstack** (+ ponytail optional). Everything else
  (LangGraph, Supabase, n8n, Grafana, Paperclip) is a *product dependency*, added only
  when the specific software needs it — NOT a required team member.
- Model path for a RAM-starved box (~6GB, ~70–150MB free): **prefer OpenRouter free over
  local Ollama** (Ollama needs ~4GB VRAM the box may not have). Reuse the existing
  OpenRouter key.

## Live-verified star counts (browser-verified 2026-07-16, since API was rate-limited)
| Project | Stars | Note |
|---|---|---|
| garrytan/gstack | 122k | CEO/Eng-Manager/QA playbooks; very active |
| OpenHands | 81k | autonomous SWE; very active (commits minutes ago) |
| LangGraph | 37.4k | resilient workflows; active |
| pydantic-ai | 18.6k | type-safe agents; active |
| google/adk-python | 20.6k | code-first agent toolkit; active |
| CrewAI | 55.6k | role-play crews; active (NOT recommended for prod app code) |
| microsoft/autogen | 59.8k | **maintenance mode** — do NOT use |
| Supabase | 107k | Postgres platform; very active |
| Dify | 149k | agentic workflows; very active |
| n8n | 197k | workflow automation; very active |
| Next.js | 141k | React framework; very active |
| Grafana | 75.7k | observability; very active |
| DietrichGebert/ponytail | 84.4k | lean-code discipline layer; very active |

## Technique: verifying repo stats when the GitHub API is rate-limited
The unauthenticated `api.github.com` returns HTTP 403 after ~20-30 calls and `sleep` +
`User-Agent` header do NOT clear it for the rest of the session. **Reliable fallback:
use the `browser_navigate` tool on `https://github.com/<owner>/<repo>` and read the star
count from the page snapshot** (it appears as `Star <n>` near the fork count). This gave
accurate live numbers for all repos above when the API was blocked. Use this whenever
`curl api.github.com` returns empty/403.
