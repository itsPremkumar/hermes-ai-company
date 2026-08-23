---
name: hermes-agent-team
description: "Build role-based bot teams inside Hermes."
version: 1.0.0
author: bunny
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, multi-agent, profiles, team, bots, soul-md, orchestration, setup]
    related_skills: [hermes-agent, persistent-orchestrator]
---

# Hermes Agent Team

Build a complete multi-agent development team inside Hermes. Each bot gets its own profile, model config, SOUL.md personality, and dedicated chat — then you orchestrate work across them.

## When to Use This

- "Create a new bot named X"
- "Set up a full dev team"
- "I need multiple specialized agents"
- "Build me an AI engineering team"
- "Create a Jarvis-like assistant"
- User wants distinct agent personalities that collaborate

## Core Workflow

### 1. Create the Profile

```bash
# Clone from an existing profile (recommended — inherits config, .env, skills)
hermes profile create <name> --clone-from <source> --description "Role: what this bot does"

# Or create empty and configure from scratch
hermes profile create <name> --clone --description "Role: what this bot does"
```

**Flags:**
- `--clone-from SOURCE` — copy config.yaml, .env, SOUL.md, skills from source profile
- `--clone` — copy from currently active profile
- `--clone-all` — full copy of all state (excluding history)
- `--description TEXT` — one-liner role description (used by kanban decomposer)
- `--no-skills` — start with no bundled skills
- `--no-alias` — skip wrapper script creation

### 2. Configure the Model

```bash
# Set model + provider for one profile
hermes config set model.default <model-name> -p <name>
hermes config set model.provider <provider> -p <name>

# Batch configure multiple profiles
for p in bot1 bot2 bot3 bot4; do
  hermes config set model.default <model> -p "$p"
  hermes config set model.provider <provider> -p "$p"
done
```

**Common free models:**
- `meituan/longcat-2.0:free` via `nous`
- Any OpenRouter free tier model

### 3. Write SOUL.md Personality

Each bot gets a unique identity at `~/.hermes/profiles/<name>/SOUL.md`. This file is loaded into the system prompt and defines:

- **Identity** — role, symbol, style
- **Personality** — how the bot thinks and speaks
- **How You Work** — the bot's workflow steps
- **Boundaries** — what the bot does NOT do
- **Communication** — speech patterns, vocabulary, tone
- **Skills Spotlight** — what the bot specializes in

**Template structure:**
```markdown
# BotName

You are **BotName** — the [role] on this [team type].

## Identity
- **Role:** [Specific role]
- **Symbol:** [Emoji]
- **Style:** [2-3 adjectives]

## Personality
[3-5 sentences on how this bot thinks]

## How You Work
1. [Step one]
2. [Step two]
3. ...

## Boundaries
- You don't [what this bot avoids]
- You escalate to **[BotName]** for [specific concern]

## Communication
[How this bot talks]

## Skills Spotlight
[Domain-specific expertise]
```

See `references/soul-templates.md` for full role templates (architect, frontend, backend, devops, qa-engineer, etc.)

### 4. Verify Each Bot

```bash
# Quick chat test
hermes chat -q "Introduce yourself briefly." -p <name> -Q

# Check model/provider
hermes config show -p <name>

# Verify Nous/auth
hermes auth list nous -p <name>
```

### 5. Orchestrate

Start a bot:
```bash
<pname> chat              # Interactive chat
<pname> chat -q "..."     # One-shot query
```

From Bunny (orchestrator), you can message any bot:
```bash
hermes -p <bot-name> chat --in ~ -c "Bot Chat" --create-if-missing -Q -q "Message from 🤖 bunny: <task>"
```

Or use **Bot Mode** in the desktop app to see all bots in the sidebar and @mention between them.

## Team Composition Templates

### Full Dev Team (5+1)

| Bot | Role | Specialty | SOUL.md |
|---|---|---|---|
| **Bunny** | Orchestrator | Generalist, systematic, honest | Already exists |
| **Architect** | System Design | Patterns, scalability, tech decisions | Pragmatic big-picture |
| **Frontend** | UI/UX | React/Vue, CSS, a11y, pixel-perfect | Design-obsessed |
| **Backend** | Server-Side | APIs, databases, security, scale | Logic-driven, paranoid |
| **DevOps** | Infrastructure | CI/CD, Docker, cloud, monitoring | YAML/Terraform thinker |
| **QA Engineer** | Quality | Test automation, bug hunting, TDD | Edge-case skeptic |

### Task Routing

```
Plan:       Bunny → Architect
Design:     Architect (schema) + Frontend (UI) + Backend (APIs)
Build:      Frontend + Backend (parallel)
Test:       QA Engineer + Frontend (unit) + Backend (integration)
Deploy:     DevOps
Monitor:    DevOps + QA Engineer
```

## Bot Mode (Desktop)

For visual team management, use **Bot Mode** (desktop plugin):
- Sidebar shows all bots with avatars
- Click any bot → dedicated chat
- @mention between bots for task assignment
- Each bot has independent chat history and personality

## Pitfalls

1. **Wrong flag:** `--clone` copies from the *active* profile. Use `--clone-from <name>` to copy from a specific profile.

2. **PATH warning:** Wrapper scripts are created at `~/.local/bin` on Linux/macOS or `~\.local\bin` on Windows. Add to PATH to use `botname.bat` as a global command.

3. **Model not working after config:** Restart the CLI/gateway process. Config changes need a fresh session.

4. **Empty SOUL.md:** If a profile has no SOUL.md, the bot loads with no personality. Always write at least a minimal identity block.

5. **OAuth inheritance:** When cloning, `.env` and auth.json are copied. The new profile inherits the source's API keys. Verify with `hermes auth list <provider> -p <newname>`.

6. **Profile name rules:** Lowercase, alphanumeric, hyphens/underscores only. No spaces.
