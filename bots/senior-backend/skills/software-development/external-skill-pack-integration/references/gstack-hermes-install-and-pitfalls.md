# gstack → Hermes integration: verified commands + evidence

Reproduced live on this Windows/Git-Bash box (username "PREM KUMAR", ~687MB free RAM),
2026-07-16. Commands below are copy-pasteable.

## 1. Bun manual install (official installer FAILS under space-in-username)
```bash
cd /tmp
curl -fsSL -o bun.zip "https://github.com/oven-sh/bun/releases/latest/download/bun-windows-x64.zip"
mkdir -p "$HOME/.bun" && unzip -q -o bun.zip -d "$HOME/.bun"
export PATH="$HOME/.bun/bin:$PATH"        # bun.exe at $HOME/.bun/bin/bun.exe
echo 'export PATH="$HOME/.bun/bin:$PATH"' >> "$HOME/.bashrc"
bun --version                              # → 1.3.9
```
Official `curl -fsSL https://bun.sh/install | bash` errors:
"Failed to download bun ... client returned ERROR on write of 16384 bytes"
(root cause: writes to a `$HOME`-derived path that breaks on the space).

## 2. Clone + generate
```bash
cd ~/.hermes/skills
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git gstack
cd ~/.hermes/skills/gstack
bun install                                  # 339 pkgs, lockfile satisfied → fast
bun run gen:skill-docs --host hermes        # 55 skills, 113 SKILL.md files
```
`./setup --host hermes` only prints guidance — `gen:skill-docs` is the real step.

## 3. EVIDENCE of the partial-port pitfall (Pitfall 2 in SKILL.md)
```bash
# Count skills still hardcoded to ~/.claude (should be ~52, NOT 0):
grep -rl "~/.claude/skills/gstack" ~/.hermes/skills/gstack/*/SKILL.md | wc -l
# → 52

# Count skills that correctly reference ~/.hermes (should be 0 before a patch):
grep -rl "\.hermes/skills/gstack" ~/.hermes/skills/gstack/*/SKILL.md | wc -l
# → 0

# allowed-tools frontmatter still Claude-native (e.g. review/SKILL.md head):
#   allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion
```

## 4. The env-driven escape hatch (why it still works as a reference library)
`bin/gstack-paths` and `bin/gstack-update-check` resolve their root via
`GSTACK_DIR` / `GSTACK_HOME` / dynamic detection — NOT hardcoded. So:
```bash
export GSTACK_DIR=~/.hermes/skills/gstack
export GSTACK_HOME=~/.gstack
```
makes the bin helpers resolve correctly even though SKILL.md bodies say `~/.claude/...`.

## 5. Autonomy-safe subset (Pitfall 3)
Report-only / non-interactive, safe in unattended Hermes cron:
- `/cso`  (OWASP+STRIDE security audit)
- `/qa-only` (bug report, no code changes)
- `/review` with auto-fix OFF

Interactive / AskUserQuestion-gated — DO NOT run unattended:
- `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/autoplan`,
  `/design-review`, `/design-shotgun`, `/design-html` (design choices),
  `/ship` (approval), `/land-and-deploy` (merge+deploy).

## 6. Resource caution
gstack browse pulls Playwright + 22MB ML classifier + Chromium. On low-RAM boxes,
invoke `/qa` / `/browse` sparingly — never inside a tight cron loop.
Pin the version; do NOT `git pull` blind inside an autonomous loop
(fast-moving: daily commits, 400+ open PRs as of install).
