# Bot: `tester`

**Role:** Tester

> Exploratory test checklists.

**Team:** tester · **Profile path (live):** `%HERMES_HOME%/profiles/tester/`

## Identity
| | |
|---|---|
| Model pin | `poolside/laguna-s-2.1:free` |
| Fallback chain | — |
| Tools enabled | minimal |
| Assigned skills | `apple`, `autonomous-ai-agents`, `creative`, `devops`, `email`, `github`, `media`, `mlops`, `note-taking`, `productivity`, `research`, `smart-home`, `social-media`, `software-development` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/tester/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Deployed skills
- apple
- autonomous-ai-agents
- creative
- devops
- email
- github
- media
- mlops
- note-taking
- productivity
- research
- smart-home
- social-media
- software-development

## Run / rebuild this bot
```bash
# create
hermes profile create tester --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/tester/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/tester/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/tester/.env   # REQUIRED: keys
# use
hermes -p tester chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
