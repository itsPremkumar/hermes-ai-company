---
name: hermes-profile-fleet
description: "Build a Hermes bot company with roles and models."
version: 1.0.0
author: bunny
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, profiles, multi-agent, bot-mode, team, company, models]
---

# Hermes Profile Fleet

Stand up a structured fleet of Hermes Agent profiles — a "bot company" for Bot Mode — where each profile is a named role (CEO, CTO, frontend, QA…) with its own SOUL.md personality, model, and (optionally) provider keys. This is the org-level pattern that sits *above* `hermes-agent`'s single-instance spawning: many persistent profiles, each independently configurable, not throwaway `hermes chat` subprocesses.

## When to use
- "Create a new bot/profile like bunny"
- "Build a dev team / IT company / agent org with roles"
- "Give every agent its own model based on what it does"
- Any request for a hierarchy of named agents with distinct responsibilities

## Core workflow

### 1. Create profiles (clone-from, NOT --clone)
```bash
# WRONG: hermes profile create architect --clone bunny   -> error "unrecognized arguments"
# RIGHT:
hermes profile create architect --clone-from bunny \
  --description "System architect: design patterns, tech decisions, scalability"
```
- `--clone-from SOURCE` copies config.yaml, .env, SOUL.md, and skills from the source.
- `--description` is used by the kanban decomposer to route tasks by role — always set it.
- A wrapper `.bat` is created in `~/.local/bin/` (not on PATH by default — tell the user to add it).

### 2. Configure the model (per profile)
```bash
hermes config set model.default <model_id> -p <profile>
hermes config set model.provider <provider> -p <profile>
```
Every profile is fully independent: own config.yaml, .env, SOUL.md, skills/, sessions/.

### 3. Write the SOUL.md personality
Each role needs a distinct SOUL.md. Template structure that worked well:
```
# <Role Title>
You are the **<Role>** — one-line purpose.
## Identity (Role, Symbol emoji, Style)
## Core Responsibilities (bullets)
## Personality (how they think/speak)
## How You Work (numbered)
## Boundaries (what they DON'T do + who they escalate to)
## Communication (voice, vocabulary)
## Your Direct Reports (org links)
## Skills Spotlight
```
Keep escalation lines pointing at ROLE names (CEO, CTO), never at a specific bot's pet name (see Pitfall 1).

### 4. Assign task-specialized models (THE CRITICAL STEP — see Pitfall 2)
Match each role's workload to the model strongest at that task:
- Strategy/reasoning roles → reasoning-class models
- Coding roles → coding-class models
- Security/QA → strongest code model + a content-safety model
- Support/cheap roles → small/fast free models
But the model ID MUST be verified live FIRST (Pitfall 2). Do not trust a benchmark blog or a UI screenshot.

## Pitfalls (learned the hard way — 2026-08-18)

### Pitfall 1 — "Bunny" leaks into cloned SOUL.md
`--clone-from bunny` copies Bunny's SOUL.md verbatim, so other bots end up saying "escalate to **Bunny**" or "You are Bunny". After cloning, scrub the source profile's name from every new SOUL.md and replace with the proper role (CEO/CTO/…). Also give the source profile (bunny) a real role in the new org (e.g. Chief of Staff) so it isn't left as a generic "named agent". Use `scripts/scrub_soul.py`.

### Pitfall 2 — Assigning models you haven't verified are LIVE (most important)
Symptom: config writes succeed (`✓ Set model.default=…`) but every chat returns `HTTP 404: Model 'X' not found` or `Billing or credits exhausted`. Root causes observed:
- **Cached catalog is stale.** `AppData/Local/hermes/cache/model_catalog.json` and `openrouter_model_metadata.json` lag reality. NVIDIA NIM retired `nemotron-3-ultra-550b-a55b:free` but the cache still listed it.
- **Screenshot shows display/tier names, not IDs.** A Bot-Mode picker showed `Hy3:Free`, `Longcat 2.0:Free`, `Laguna S 2.1:Free` — but the catalog IDs are `tencent/hy3`, `meituan/longcat-2.0`, `poolside/laguna-s-2.1`. The `:Free` is a *tier label*, not part of the model ID. `nous:Hy3:Free` 404s; `tencent/hy3` is the ID (but may be paid).
- **Provider key not present in the profile.** A key in `bunny/.env` is NOT inherited by `ceo/.env`. OpenRouter said "No API key found for provider 'openrouter'" even though the key existed in bunny's .env.
- **Nous Portal $0 credits** → paid models 404 on billing even with valid OAuth.

**MANDATORY before assigning any model:** run the liveness check in `references/live-model-check.md` (enumerate the live `/v1/models` for each provider you'll use, filter `:free`/free pricing, and only assign IDs that appear in the live response). If a provider key is absent/commented, either propagate it (`scripts/propagate_env.py`) or pick a provider that has a working key. Never fire blind model IDs at the API and call it "configured".

### Pitfall 3 — Provider key isolation across profiles
Each profile's `.env` is separate. To use one provider (e.g. openrouter) across the fleet, the key must exist in EVERY profile's `.env`. Use `scripts/propagate_env.py` to copy a key from a source profile to all others. Commented-out keys (`# OPENROUTER_API_KEY=***`) are NOT loaded — they count as absent.

### Pitfall 4 — OpenRouter free models live UNDER openrouter, not the upstream provider
`nvidia/nemotron-3.5-content-safety:free`, `cohere/north-mini-code:free`, `poolside/laguna-s-2.1:free` are all served via the **openrouter** provider (key: `OPENROUTER_API_KEY`). NVIDIA NIM's own `/v1/models` had **0 free** models at check time. So "free NVIDIA model" almost always means "openrouter-hosted, provider=openrouter".

## Verification
After assigning models, LIVE-TEST a sample of roles (not just config writes):
```bash
hermes chat -q "Reply with just: OK" -p ceo -Q 2>&1 | tail -3
hermes chat -q "Reply with just: OK" -p cto -Q 2>&1 | tail -3
```
A `✓ Set model.default` line is NOT proof the model works. Only a real response (or a clean 404 with a clear cause) is.

## Bulk operations
- Loop over profiles in bash: `for p in ceo cto coo; do hermes config set model.default X -p "$p"; done`
- Or drive from Python (subprocess) when you need status capture — see how the fleet was built in-session.

## Reference files
- `references/live-model-check.md` — exact endpoints + filter to enumerate live free models per provider, and how to read the Bot-Mode picker vs catalog IDs.
- `references/model-specialization-map.md` — the role→model reasoning framework + a DATED snapshot of live free models (re-verify, don't trust the snapshot).
- `scripts/scrub_soul.py` — replace a source profile name with role names across cloned SOUL.md files.
- `scripts/propagate_env.py` — copy one env var (e.g. OPENROUTER_API_KEY) from a source profile .env into every profile's .env that lacks it.
