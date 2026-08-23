# 05 — Free Resource Stack ($0/month, all probed live 2026-08-22)

## Inference

| Resource | State | Evidence |
|---|---|---|
| OpenRouter `:free` tier | ✅ 18 models live today | catalog probe (api/v1/models) |
| — nemotron-3-super-120b-a12b:free | fleet primary | pinned in 35 profiles + jobs |
| — z-ai/glm-5.2:free | secondary | pinned |
| — nvidia/nemotron-nano-9b-v2:free | radar/light jobs | pinned |
| — poolside/laguna-s-2.1:free | fallback + junior-dev pin | still has :free suffix |
| NVIDIA NIM (build.nvidia.com key) | ✅ LIVE completion test passed (`ALIVE`) | `hermes -z --provider nvidia --model nvidia/llama-3.3-nemotron-super-49b-v1` |
| Nous Portal credential | ⚠️ logged in but $0 usable credits | probe: "no active subscription or usable credits" |
| GitHub Copilot models | ❌ HTTP 403 needs paid sub | probe result kept for honesty |
| HuggingFace Inference | ❌ token present, zero credits | probe: "Add credits" |

**Rule learned:** `:free` tiers get RETIRED without notice (3 of our 4 pins died on
08-22). `scripts/model_health.py` exists because of that.

## Free platform features in use

| Feature | Use |
|---|---|
| Bot Mode (bundled desktop plugin) | the entire company layer |
| Gateway + Scheduled Task autostart | 24/7 survival across reboots |
| Kanban board + capped dispatch | production line |
| Cron + continuity flags | always-on routines |
| Skills Hub registry search | on-demand skills with security scanning |
| ClawHub account (<github-org>) | 31 published skills = distribution channel |
| Vercel MCP (connected) | site deploys |
| GitHub free tier (2 accounts) | product repos, Actions minutes, PRs |
| Edge TTS / local browser / local terminal | zero-cloud tool lanes |
| Bundles (/research-pack, /delivery-pack) | department SOP loading |
| Ops dashboard HTML | self-generated status page |

## Honest limits

1. If ALL THREE `:free` lanes vanish at once → work pauses until model_health alert.
   Mitigation would need a paid lane or Ollama-class local model (RAM-prohibitive here).
2. No phone escalation yet — alerts stop at this desktop until Telegram link [HUMAN STEP].
3. Nous/Copilot capacity stays locked behind subscriptions by design (company is $0).
