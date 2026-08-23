# Bot: `product-owner`

**Team:** product-owner · **Profile path (live):** `%HERMES_HOME%/profiles/product-owner/`

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
| `SOUL.md` | persona + standing orders (deploy to `profiles/product-owner/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create product-owner --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/product-owner/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/product-owner/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/product-owner/.env   # REQUIRED: keys
# use
hermes -p product-owner chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
