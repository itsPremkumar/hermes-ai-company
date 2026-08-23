# 01 — System Architecture

## Layers (top → bottom)

```
┌─────────────────────────────────────────────────────────────┐
│ OWNER (human)                                               │
│  • approvals, UI-only steps, phone escalations (future)     │
└──────────────┬──────────────────────────────────────────────┘
               │ chat / @mentions / needs-you badge
┌──────────────▼──────────────────────────────────────────────┐
│ ORCHESTRATION LAYER (Hermes Desktop + Gateway)              │
│  • Bot Mode roster (25+ bots = Hermes profiles)             │
│  • Gateway PID runs 24/7 via Scheduled Task                 │
│    Hermes_Gateway_<profile>  (autostart at logon)               │
│  • Always-on cron scheduler (gateway store) fires routines  │
└──────────────┬──────────────────────────────────────────────┘
               │ routines / dispatch ticks
┌──────────────▼──────────────────────────────────────────────┐
│ PRODUCTION LAYER                                            │
│  • Kanban board it-company-ops (SQLite, WAL)                │
│  • kanban_dispatch.sh v2 — sole release valve:              │
│      blocked → ready (ONE card/tick) → spawn ONE worker     │
│  • Worker = `hermes -p <bot>` in its own git worktree       │
└──────────────┬──────────────────────────────────────────────┘
               │ completed card
┌──────────────▼──────────────────────────────────────────────┐
│ QUALITY GATE                                                │
│  • qa-lead standing order (SOUL.md): never trust self-report│
│  • scripts/qa_harness.py: compile · tests · self-tests ·    │
│    secrets · docs — exit 0 or the work does not ship        │
└──────────────┬──────────────────────────────────────────────┘
               │ verified artifact
┌──────────────▼──────────────────────────────────────────────┐
│ DELIVERY                                                    │
│  • GitHub push/PR as <github-account> (public product repos)    │
│  • Vercel MCP for site deploys (already connected)          │
└─────────────────────────────────────────────────────────────┘
```

## The Bot-Mode primitive

A **Bot is a Hermes profile**: isolated `config.yaml`, `.env`, `SOUL.md`, `memories/`,
`skills/`, sessions under `%HERMES_HOME%\hermes\profiles\<name>\`. Bot Mode is a UI over
this primitive. Everything in this company therefore also has a CLI equivalent
(`hermes -p <bot> chat`).

## Inference architecture

| Lane | Provider | Model | Used by |
|---|---|---|---|
| primary | OpenRouter | nvidia/nemotron-3-super-120b-a12b:free | most bots |
| primary | OpenRouter | z-ai/glm-5.2:free | longcat-replacements |
| primary | OpenRouter | nvidia/nemotron-nano-9b-v2:free | light/radar jobs |
| fallback 1 | NVIDIA NIM | nvidia/llama-3.3-nemotron-super-49b-v1 | 11 key bots |
| fallback 2 | OpenRouter | poolside/laguna-s-2.1:free | builders |
| fallback 3 | OpenRouter | z-ai/glm-5.2:free | everyone |

Guard: `scripts/model_health.py` pings the OpenRouter catalog; `:free` tiers DO get retired
(happened 2026-08-22, caught within hours by this guard).

## Design decisions (and why)

1. **Pure Hermes only** — no Paperclip/OpenClaw/third-party daemons. Reason: 6 GB RAM;
   every extra daemon is permanent overhead. Old stack deleted from disk.
2. **One worker at a time** — each bot process ≈ 400–600 MB. Two workers thrash the box.
3. **Cards live in `blocked`** — the gateway's embedded dispatcher auto-spawns every
   ready/todo card and ignores caps on Windows; `blocked` is the only state it never
   touches. Our script releases exactly one.
4. **Two cron stores, one truth** — desktop-app store dies with the app; gateway store
   (`hermes cron create`) runs always-on. All real jobs live in the gateway store.
5. **Skills are file-backed per profile** — copied into `<profile>/skills/`; visible after
   next session start, no daemon needed.
