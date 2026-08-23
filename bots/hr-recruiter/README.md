# Bot: `hr-recruiter`

**Role:** HR Recruiter

> JDs, screening criteria, market research.

**Team:** hr-recruiter · **Profile path (live):** `%HERMES_HOME%/profiles/hr-recruiter/`

## Identity
| | |
|---|---|
| Model pin | `nvidia/nemotron-nano-9b-v2:free` |
| Fallback chain | — |
| Tools enabled | `web`, `file`, `clarify`, `skills` |
| Assigned skills | `agent-native-distribution`, `apple`, `automation`, `autonomous-ai-agents`, `avs-visual-frame-qa`, `computer-use`, `creative`, `data-science`, `debugging`, `delegate-task`, `desktop`, `devops`, `dogfood`, `email`, `free-dev-team`, `github`, `gitignore-hygiene`, `gstack`, `hermes-desktop-plugins`, `hermes-themes`, `job-hunting`, `matlab`, `media`, `media-pipeline`, `media-pipeline-debugging`, `mlops`, `note-taking`, `ponytail`, `productivity`, `research`, `skill-discovery`, `smart-home`, `social-media`, `software-development`, `windows`, `windows-msys-tooling`, `yuanbao` |

## Files in this folder
| File | Purpose |
|---|---|
| `SOUL.md` | persona + standing orders (deploy to `profiles/hr-recruiter/SOUL.md`) |
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
hermes profile create hr-recruiter --no-skills --description "<see docs/02>"
# deploy identity + config from this folder
cp SOUL.md %HERMES_HOME%/profiles/hr-recruiter/SOUL.md
cp config.yaml %HERMES_HOME%/profiles/hr-recruiter/config.yaml
cp %HERMES_HOME%/.env %HERMES_HOME%/profiles/hr-recruiter/.env   # REQUIRED: keys
# use
hermes -p hr-recruiter chat
```
> Full company context: see [README](../../README.md), roster (`docs/02-fleet-roster.md`),
> SOPs (`docs/09-sops.md`, `docs/sop-workflows/`).
