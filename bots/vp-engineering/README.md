# Bot: `vp-engineering`

**Role:** VP Engineering

> Engineering oversight (advisory).

**Team:** vp-engineering · **Profile path (live):** `%HERMES_HOME%/profiles/vp-engineering/`

## Identity
| | |
|---|---|
| Model pin | `(inherit)` |
| Fallback chain | — |
| Tools enabled | minimal |
| Assigned skills | — |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/vp-engineering/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create vp-engineering --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/vp-engineering/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/vp-engineering/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/vp-engineering/.env   # REQUIRED: keys
# use
hermes -p vp-engineering chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
