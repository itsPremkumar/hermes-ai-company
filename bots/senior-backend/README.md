# Bot: `senior-backend`

**Role:** Senior Backend Engineer

> Reserve depth for complex server tasks.

**Team:** senior-backend · **Profile path (live):** `%HERMES_HOME%/profiles/senior-backend/`

## Identity
| | |
|---|---|
| Model pin | `poolside/laguna-s-2.1:free` |
| Fallback chain | — |
| Tools enabled | `browser`, `clarify`, `code_execution`, `computer_use`, `cronjob`, `delegation`, `file`, `image_gen`, `memory`, `session_search`, `skills`, `terminal`, `todo`, `tts`, `vision`, `web` |
| Assigned skills | `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/senior-backend/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Deployed skills
- agent-native-distribution
- apple
- automation
- autonomous-ai-agents
- avs-visual-frame-qa
- computer-use
- creative
- data-science
- debugging
- delegate-task
- desktop
- devops
- dogfood
- email
- free-dev-team
- github
- gitignore-hygiene
- gstack
- hermes-desktop-plugins
- hermes-themes
- job-hunting
- matlab
- media
- media-pipeline
- media-pipeline-debugging
- mlops
- note-taking
- ponytail
- productivity
- research
- skill-discovery
- smart-home
- social-media
- software-development
- windows
- windows-msys-tooling
- yuanbao

## Run / rebuild this bot
```bash
# create
hermes profile create senior-backend --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/senior-backend/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/senior-backend/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/senior-backend/.env   # REQUIRED: keys
# use
hermes -p senior-backend chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
