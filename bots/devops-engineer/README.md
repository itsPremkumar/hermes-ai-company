# Bot: `devops-engineer`

**Role:** DevOps Engineer

> Vercel MCP deploys, CI pipelines, cleanup routines.

**Team:** devops-engineer · **Profile path (live):** `%HERMES_HOME%/profiles/devops-engineer/`

## Identity
| | |
|---|---|
| Model pin | `poolside/laguna-s-2.1:free` |
| Fallback chain | `nvidia:nvidia/llama-3.3-nemotron-super-49b-v1`, `openrouter:poolside/laguna-s-2.1:free`, `openrouter:z-ai/glm-5.2:free` |
| Tools enabled | `terminal`, `file`, `cronjob`, `skills` |
| Assigned skills | `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/devops-engineer/SOUL.md`) |
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
hermes profile create devops-engineer --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/devops-engineer/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/devops-engineer/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/devops-engineer/.env   # REQUIRED: keys
# use
hermes -p devops-engineer chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
