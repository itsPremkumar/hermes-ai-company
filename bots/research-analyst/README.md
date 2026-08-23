# Bot: `research-analyst`

**Team:** research-analyst · **Profile path (live):** `%HERMES_HOME%/profiles/research-analyst/`

## Identity
| | |
|---|---|
| Model pin | `nvidia/nemotron-3-super-120b-a12b:free` |
| Fallback chain | `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free` |
| Tools enabled | `web`, `x_search`, `session_search`, `memory`, `skills`, `clarify`, `todo` |
| Assigned skills | — |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/research-analyst/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Run / rebuild this bot
```bash
# create
hermes profile create research-analyst --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/research-analyst/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/research-analyst/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/research-analyst/.env   # REQUIRED: keys
# use
hermes -p research-analyst chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
