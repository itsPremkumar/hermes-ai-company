# Bot: `scrum-master`

**Role:** Scrum Master

> Ceremony facilitation (advisory).

**Team:** scrum-master · **Profile path (live):** `%HERMES_HOME%/profiles/scrum-master/`

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
| `SOUL.md` | persona + standing orders (deploy to `profiles/scrum-master/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create scrum-master --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/scrum-master/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/scrum-master/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/scrum-master/.env   # REQUIRED: keys
# use
hermes -p scrum-master chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
