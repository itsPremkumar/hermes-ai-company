# Bot: `vp-delivery`

**Role:** VP Delivery

> Delivery risk oversight (advisory).

**Team:** vp-delivery · **Profile path (live):** `%HERMES_HOME%/profiles/vp-delivery/`

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
| `SOUL.md` | persona + standing orders (deploy to `profiles/vp-delivery/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create vp-delivery --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/vp-delivery/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/vp-delivery/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/vp-delivery/.env   # REQUIRED: keys
# use
hermes -p vp-delivery chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
