# Bot: `ceo`

**Team:** ceo · **Profile path (live):** `%HERMES_HOME%/profiles/ceo/`

## Identity
| | |
|---|---|
| Model pin | `nvidia/nemotron-3-super-120b-a12b:free` |
| Fallback chain | `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free` |
| Tools enabled | `memory`, `session_search`, `cronjob`, `clarify`, `todo`, `skills` |
| Assigned skills | `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `weekly-review-planning`, `windows`, `windows-msys-tooling`, `yuanbao` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/ceo/SOUL.md`) |
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
- weekly-review-planning
- windows
- windows-msys-tooling
- yuanbao

## Run / rebuild this bot
```bash
# create
hermes profile create ceo --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/ceo/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/ceo/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/ceo/.env   # REQUIRED: keys
# use
hermes -p ceo chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
