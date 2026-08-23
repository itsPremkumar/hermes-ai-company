# Pre-push safety gate — reusable checklist (Windows/MSYS box, no `gh`)

Run these in the repo root before `git push origin main`. All proven in a real push of
`itsPremkumar/Automated-Video-Generator` (agentic video system, live Pexels key in `.env`).

## 0. Baseline
```bash
git status --short | head -60
git branch --show-current
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # expect origin/main
```

## 1. Secret scan (staged + untracked source)
```bash
git status --short | awk '{print $2}' | grep -vE "workspaces" | while read f; do
  [ -f "$f" ] && grep -rIlE "sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{20,}|xox[baprs]-|bearer " "$f"
done
# then confirm any "api key"/"token" text hits are descriptions, not values:
grep -nE "api[_-]?key|token|secret" openclaw.plugin.json package.json *.json 2>/dev/null
```

## 2. `.env` MUST be gitignored
```bash
git check-ignore .env        # must print ".env"; empty = DANGER
find . -maxdepth 2 -name ".env*" | grep -v node_modules
grep -nE "\.env" .gitignore  # expect a line like: .env
```

## 3. Large-file guard (>200 KB floods the push / repo)
```bash
git add -A --dry-run | sed 's/^add //' | while read f; do
  [ -f "$f" ] && sz=$(stat -c%s "$f" 2>/dev/null) && [ "$sz" -gt 204800 ] && echo "BIG($((sz/1024))KB): $f"
done
```

## 4. Up-to-date check (avoid rejected/divergent push)
```bash
git fetch origin
git rev-list --left-right --count @{u}...HEAD   # expect "0   0"
```

## 5. Media/agentic-repo artifact ignore (if applicable)
```bash
git check-ignore public/agentic-assets/s0_video_agentic_ph_xxx.png .video-cache.json
# expect both patterns echoed; add to .gitignore if not
```

## 6. Group commits then push
- `fix:` hardening/bugfix · `feat:` new system · `chore:` config/agent files · `docs:` planning docs
- `git add <subset>` per group, `git commit -q -m "..."`, repeat.
- Final: `git push origin main` then `git fetch && git rev-list --left-right --count @{u}...HEAD` → `0 0`.

## Gotchas observed
- `openclaw.plugin.json` had the *word* "API key" only as a description — benign, but always eyeball.
- `.env` was already covered by `.gitignore` line 19 (`.env`) — good; the danger is when a new
  repo's `.gitignore` lacks it. Add `.env`, `.env.local`, `.env.*.local` if missing.
- Generated placeholder PNGs (`public/agentic-assets/*`) accumulate per run; they must be gitignored
  or the commit balloons. `agentic-pipeline/workspaces/*` is ignored but its planning `*.md` docs
  are intended to stay tracked.
