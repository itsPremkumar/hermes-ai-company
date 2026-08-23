# Bot: `technical-writer`

**Team:** technical-writer · **Profile path (live):** `%HERMES_HOME%/profiles/technical-writer/`

## Identity
| | |
|---|---|
| Model pin | `z-ai/glm-5.2:free` |
| Fallback chain | — |
| Tools enabled | `file`, `web`, `image_gen`, `skills` |
| Assigned skills | `agent-native-distribution`, `apple`, `automated-content-site`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/technical-writer/SOUL.md`) |
| `config.yaml` | sanitized config: model pin, toolsets, fallbacks |

## Deployed skills
- agent-native-distribution
- apple
- automated-content-site
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
hermes profile create technical-writer --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/technical-writer/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/technical-writer/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/technical-writer/.env   # REQUIRED: keys
# use
hermes -p technical-writer chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
