# Backing up Hermes "learned" skills to GitHub

## What "learned" means (clarify before acting)
In the Hermes desktop app, the "Skills 97" list shows a blue `Learned` tag on each
entry. This is a **status label**, not a learning process:
- `Learned` = the skill is **installed + enabled** in Hermes's library (acquired from
  ClawHub / GitHub / bundled). The blue toggle = active for new sessions.
- The `×N` number = **usage count** (how many times invoked), sourced from
  `hermes/skills/.usage.json`.
- It does NOT mean "the AI studied it like a student." Do not explain it that way to
  the user — say "installed and enabled."

## Where they live
```
%LOCALAPPDATA%/hermes/skills/<category>/<name>/
                                    ├── SKILL.md
                                    ├── references/
                                    ├── scripts/
                                    └── templates/
```
Example: `%LOCALAPPDATA%/hermes/skills/devops/paperclip-self-host/SKILL.md`.

## Why back them up
Operating principle #1: **GitHub = single source of truth.** These skill folders are
local-only and would be lost on machine reset. The company repo
(`Hermes-Full-Autonomous-Company`) is the canonical store, so copy them in.

## The backup script
`scripts/backup_learned_skills.py` (committed to the company repo root):
1. Walks `%LOCALAPPDATA%/hermes/skills/<cat>/<name>/`.
2. Skips `.curator_backups` and any dir without a `SKILL.md` (pure reference/template
   subdirs of a category — not skills).
3. Copies each skill folder into `<repo>/skills/<category>/<name>/` via `shutil.copytree`,
   then removes any `__pycache__` it finds.
4. Writes `<repo>/skills/SKILLS_INDEX.md` — a table of all skills sorted by `use_count`
   descending (name | category | uses | state).
5. Writes `<repo>/skills/usage_snapshot.json` — the raw `.usage.json` dump.

Run:
```bash
cd /c/one/paperclip-company
python backup_learned_skills.py
git add skills/ backup_learned_skills.py
git commit -m "Backup N Hermes learned skills to skills/ with usage index"
git push origin master
```

## Verification (ad-hoc, temp script)
Write a `hermes-verify-*.py` under `%TEMP%`, run it, then DELETE it:
- Source count `find %LOCALAPPDATA%/hermes/skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l`
  equals the backup count under `skills/`.
- No `__pycache__` in backup (`find skills -name __pycache__ | wc -l` == 0).
- `SKILLS_INDEX.md` + `usage_snapshot.json` exist; index lists 100 rows.
- Spot-check a known skill preserved full structure (e.g. `skills/devops/paperclip-self-host/`
  has SKILL.md + references/ + scripts/ + templates/).
- Confirm live on GitHub: `curl -sS -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/itsPremkumar/Hermes-Full-Autonomous-Company/master/skills/SKILLS_INDEX.md` → 200.

## Scope separation (don't conflate)
- **Hermes "learned" skills** = the ecosystem library (paperclip-local-company, money-engine,
  ai-company-blueprint, vercel-deploy-ops, etc.) — 100 folders, maintained by the Hermes
  project / community.
- **Our 31 ClawHub skills** = the products we published to clawhub.ai this session
  (codebase-inspection, secret-scanner, web-research, etc.) — separate registry.
- Overlap: only `web-research` appears in both.

## Notes
- The backup is a SNAPSHOT. Re-run `backup_learned_skills.py` periodically (or on a cron)
  to capture newly-learned skills / usage changes.
- Never commit the Hermes secrets adjacent to skills (`.usage.json` is fine — it has no
  credentials). The repo `.gitignore` already excludes `.moltbook_key` and other secrets.
