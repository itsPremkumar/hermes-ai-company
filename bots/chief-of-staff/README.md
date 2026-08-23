# Bot: `chief-of-staff`

**Role:** Chief of Staff

> Runs the kanban pipeline: card creation/decomposition, routing map, SOP compliance. Owns COMPANY_WORK_SOP.

**Team:** chief-of-staff · **Profile path (live):** `%HERMES_HOME%/profiles/chief-of-staff/`

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
| `SOUL.md` | persona + standing orders (deploy to `profiles/chief-of-staff/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create chief-of-staff --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/chief-of-staff/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/chief-of-staff/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/chief-of-staff/.env   # REQUIRED: keys
# use
hermes -p chief-of-staff chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
