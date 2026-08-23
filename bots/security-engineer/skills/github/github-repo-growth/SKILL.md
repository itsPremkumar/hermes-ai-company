---
name: github-repo-growth
description: Grow an open-source GitHub repo's discoverability and contributor reach — description, SEO topics, discussions, community health files, releases, issue/PR tracking, and a secure GitHub MCP connection that reads the token from the gh keyring (no token in files). Use when the user wants more stars, contributors, or worldwide visibility for a repo, or wants to wire GitHub MCP/CI/Issues/PRs.
---

# github-repo-growth

Make a public GitHub repo discoverable and trustworthy, and connect it to agentic
tooling (Issues/PRs/Releases/CI) without ever writing a token to disk.

## When to use
- "increase github profile / reach / stars / visibility for this project"
- "connect github mcp", "wire CI/Issues/PRs for this repo"
- "make this repo world-class / production-ready on GitHub"
- "earn more github badges / achievements" → also see **github-achievements** skill
  (badge roadmap, legit triggers, and the fact that badges can't be minted via API).

## The reach levers (highest impact first)
1. **Repo description** — keyword-rich, ≤350 chars. Drives search + shows on every page.
2. **Topics** — up to **20** (GitHub hard-caps at 20; more is rejected). Drives topic pages + search.
   Set them via a SEPARATE call: `gh api repos/OWNER/REPO/topics -X PUT -f names[0]=foo -f names[1]=bar ...`
   (or `--input` a `{ "names": [...] }` JSON). The `PATCH /repos/...` description
   call does NOT accept topics — if you PATCH description then PATCH topics it silently
   no-ops. Build a list of ≤20, then `PUT /topics` once.
3. **Discussions** — `gh api repos/OWNER/REPO -X PATCH -f has_discussions=true`.
4. **Community health files** — CODE_OF_CONDUCT.md, SECURITY.md, .github/ISSUE_TEMPLATE/*,
   .github/PULL_REQUEST_TEMPLATE.md. Signals "maintained" to contributors.
5. **Release** — `gh release create vN --notes ...` at green main. Shows in Releases tab + follower feed.
6. **Issues + labels** — track work; add `good first issue` / `help wanted` to attract contributors.
7. **README** — badges (stars, license, CI, npm), star-history chart, feature matrix. (Usually already good; verify, don't rewrite.)
8. **Out-of-agent reach** (tell the user to do): pin repo to profile, star+share on X/Reddit, add social preview image (Settings → General), enable GitHub Sponsors.

## CRITICAL: install the REAL gh CLI, not the npm package
The npm package `gh` (`npm i -g gh`) is a **broken/old wrapper** — `gh auth login`
crashes with `TypeError: Cannot read properties of undefined (reading 'options')`.
The real GitHub CLI is a **Go binary**. On Windows install the official MSI:
- Download `https://github.com/cli/cli/releases/download/v2.74.0/gh_2.74.0_windows_amd64.msi`
- `msiexec.exe /i "C:\\tmp\\gh-installer.msi" /quiet /norestart`
- Binary lands at `C:\\Program Files\\GitHub CLI\\gh.exe` (NOT x86).
- **Open a NEW shell** after install so PATH updates.

See `scripts/gh-launcher.sh` for the secure MCP bridge and `references/gh-api-quirks.md`
for API gotchas (incl. the Windows `gh.exe` MSYS path bug and the removed `achievements` GraphQL field).

## Secure GitHub MCP connection (no token in files)
The official MCP server `@modelcontextprotocol/server-github` requires
`GITHUB_PERSONAL_ACCESS_TOKEN` and does **NOT** auto-fallback to `gh`. To avoid
writing the token to config/files:
1. User runs `gh auth login` (interactive — agent cannot do this; needs their creds + browser).
2. Create a launcher script that reads the token from the `gh` OS keyring at launch
   and execs the server (see `scripts/gh-launcher.sh`).
3. Hermes `config.yaml` `mcp_servers.github.command` points at the launcher (variable
   reference only, never the literal token). NOTE: Hermes blocks agent edits to
   `config.yaml` — the USER must add the `mcp_servers` block, then restart Hermes.
4. Until the MCP server is wired, `gh` CLI gives the agent the SAME power for a single
   repo (Issues/PRs/Releases/API). Prefer `gh` when MCP isn't connected.

## Windows bash path gotcha
`GH="/c/Program Files/GitHub CLI/gh.exe"` breaks in MSYS bash (space splits it).
Use a function instead:
```bash
ghc() { "/c/Program Files/GitHub CLI/gh.exe" "$@"; }
ghc issue create --repo owner/repo --title "..." --body "..."
```
**BIGGER gotcha (validated 2026-07):** `gh.exe` also rejects MSYS paths passed to
`--input /c/Users/.../file.json` ("system cannot find the path specified") and
multiline `-f content="$VAR"`. Fix: pipe JSON via stdin with `--input -` and base64
file content. Full recipe in `references/gh-api-quirks.md` → "Windows path in bash".

## CRITICAL: multi-account admin on this user's box (rename/settings 404)
`gh` has TWO accounts logged in. `prem-the-dev` (default active) is **READ-ONLY** on
owned repos — repo renames / metadata PATCH / pushes return HTTP 404 ("Could not resolve
to a Repository"). `itsPremkumar` is the OWNER with admin. Switch before any admin op:
```bash
gh auth switch -u itsPremkumar && <rename/patch/push> && gh auth switch -u prem-the-dev
```
Vercel CLI is a SEPARATE account (`premkumar016555`). Full playbook incl. GEO/AEO repo
assets (`llms.txt`, `CITATION.cff`) and Vercel domain limits → `references/repo-seo-geo-aeo.md`.

## User preference (durable)
No email IDs in repo content/contact sections — use the GitHub repo link + social links.
(Full playbook + Vercel limits in `references/repo-seo-geo-aeo.md`.)

## Verify before claiming done
After reach changes, confirm via `gh`:
`gh repo view owner/repo --json description,repositoryTopics` (note: `homepage` is NOT
a valid field there — use `gh api repos/owner/repo --jq '{description,homepage,topics}'`).
For profile/achievement changes, **screenshot the live profile** (browser + vision) —
the `achievements` GraphQL field is gone, so API cannot read earned badges.
