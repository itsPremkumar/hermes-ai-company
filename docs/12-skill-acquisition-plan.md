# 12 — Skill Acquisition Plan (per-bot, from Skills Hub)

**Goal:** every bot gets role-specific skills from the 90k-skill Skills Hub
(`hermes skills search/install`), installed into `bots/<bot>/skills/` here first,
then deployed to the live profile.

## Selection policy (advanced plan)

1. **Trust order:** official ★ → clawhub(community) → skills.sh(community).
2. **Security gate:** `hermes skills install` runs the built-in scanner.
   Dangerous verdict = auto-blocked. We NEVER use `--force` past a dangerous verdict
   (proven: it cannot be overridden anyway).
3. **Install-then-copy flow:** install to THIS session's profile → verify files →
   copy into `bots/<bot>/skills/` → deploy to target bot profile on next restart.
4. **RAM/context law:** max **3 new hub skills per bot** per wave; souls stay ≤4 KB;
   skills only load when used, but each adds context — less is more.
5. **One search wave per bot-role** (queries below), pick top 1–2 relevant hits,
   skip anything duplicating an already-assigned local skill.

## Per-bot acquisition table

| Bot | Search queries | Candidates found | Install picks (wave 1) |
|---|---|---|---|
| ceo | strategic planning; decision framework | ✓ | pending review |
| cto | system architecture; technology radar | ✓ | pending review |
| chief-of-staff | kanban orchestration; project coordination | ✓ | pending review |
| research-analyst | deep research; market research | ✓ | deerflow candidate (clawhub) |
| data-engineer | data pipeline; sql analysis | ✓ | pending review |
| tech-lead | code review; refactoring | ✓ | pending review |
| fullstack-dev | git workflow; api development | ✓ | pending review |
| backend | rest api; database design | ✓ | pending review |
| frontend | react; css design | ✓ | pending review |
| qa-lead | testing; test automation | ✓ (grafana/testing…) | ❌ BLOCKED by scanner (dangerous verdict) — skipped per policy |
| devops-engineer | docker deployment; ci cd pipeline | ✓ | pending review |
| security-engineer | security audit; owasp | ✓ | pending review |
| technical-writer | documentation; technical writing | ✓ | anthropic documentation ✅ already installed |
| vp-sales | competitor analysis; pricing | ✓ | pending review |
| hr-recruiter | recruiting; interview | ✓ | pending review |
| ui-ux-designer | design system; ux | ✓ | pending review |

Raw candidate dump: `snapshots/skill-acquisition-raw.json` (167 candidates).

## Execution procedure (repeatable)

```bash
# 1. search
hermes skills search "<query>" --json
# 2. install into current profile (scanner gates automatically)
hermes skills install <identifier> --yes
# 3. if BLOCKED (dangerous): skip - never force
# 4. copy into project kit + live bot profile
cp -r %LOCALAPPDATA%/hermes/skills/<category>/<name> bots/<bot>/skills/
cp -r bots/<bot>/skills/<name> %HERMES_HOME%/profiles/<bot>/skills/
# 5. record in this file + commit
```

## Wave status

- [x] Wave 0: role-mapped local skills (14 installs, done earlier)
- [x] Candidate search for 16 key roles (167 raw)
- [x] Wave 1 executed:
  - ✅ `official/devops/watchers` → devops-engineer (kit + live profile)
  - ✅ `official/security/oss-forensics` → security-engineer (kit + live profile)
  - 🚫 `skills-sh/grafana/skills/testing` → BLOCKED by security scanner (dangerous, 8 findings) — policy: skip, never force
  - ❌ `deerflow` → fetch failed (registry unavailable)
  - Lesson: community skills.sh skills are mostly unsafe; prefer `official/*` sources
- [x] Wave 2: watchers + oss-forensics deployed to LIVE profiles (verified on disk)
- [ ] Wave 3: review remaining pending-review candidates from the raw dump
