# Bot: `junior-dev`

**Team:** junior-dev · **Profile path (live):** `%HERMES_HOME%/profiles/junior-dev/`

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
| `SOUL.md` | persona + standing orders (deploy to `profiles/junior-dev/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create junior-dev --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/junior-dev/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/junior-dev/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/junior-dev/.env   # REQUIRED: keys
# use
hermes -p junior-dev chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
