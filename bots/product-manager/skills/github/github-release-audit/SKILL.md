---
name: github-release-audit
description: Verify a GitHub repo's version and release are correctly set and configured — package.json version matches the latest git tag and published release, the release is a clean stable build (not draft/prerelease), and main isn't carrying unreleased breakage. Use when a user asks "is the latest version set right", "check the release is configured", "verify version X is published correctly", or "audit the release of <repo>".
---

# GitHub Release & Version Configuration Audit

## When to use
- "Check the latest version is properly set/configured"
- "Verify release vX.Y.Z is published correctly"
- "Is the version consistent across the repo?"
- Pre-publish or post-release sanity checks on any open-source repo.
- Side-quest: extracting the *authoritative* list of no-auth / free providers from an AI-gateway repo's source catalog (see companion reference).

## The audit (all via GitHub REST API — no clone needed)

Run these in parallel. The contents API returns `package.json` **base64-encoded** in the `content` field — decode before grepping.

### 1. Repo metadata + latest release
```
curl -s https://api.github.com/repos/<owner>/<repo>
curl -s https://api.github.com/repos/<owner>/<repo>/releases/latest
```
- Release `tag_name` should equal `package.json` version (sans leading `v`).
- `draft: false` and `prerelease: false` → real stable release.
- Note `published_at` and `target_commitish` (should be `main`/`master`).
- Ignore `reactions` / `mentions_count` (noise).

### 2. Decode package.json version
```
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/package.json?ref=main" \
  | python -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())" \
  | grep '"version"'
```

### 3. Tag ↔ release consistency + main drift
```
curl -s "https://api.github.com/repos/<owner>/<repo>/tags"                 # newest tag first
curl -s "https://api.github.com/repos/<owner>/<repo>/compare/vX.Y.Z...main"
```
- `compare` → `status: "ahead"` with `ahead_by: N`, `behind_by: 0` means main has N unreleased commits. **This is normal**, not a misconfiguration — package.json stays at the last released version until the next tag is cut.
- The latest tag's commit SHA should match the release's target commit (no tag/release drift).

### 4. Release asset completeness (desktop / gateway apps)
For Electron/app builds, inspect the release `assets[]`:
- Platform installers (`.AppImage`, `.dmg`, `.exe`, `.deb`, etc.)
- electron-updater manifests: `latest.yml`, `latest-linux.yml`, `latest-linux-arm64.yml`, `latest-mac.yml` (auto-update silently fails without these).

## Verification checklist (verdict)
- [ ] `package.json` version == latest git tag == latest release `tag_name`
- [ ] Release is not draft, not prerelease
- [ ] `target_commitish` = default branch
- [ ] No tag/release SHA drift
- [ ] (if app) full asset matrix + updater manifests present
- [ ] main-ahead-of-tag count noted as "unreleased commits", NOT a defect

## Pitfalls
- **package.json is base64** in the contents API — always decode before grepping.
- **main ahead of latest tag is EXPECTED**, not a bug. Report it as "N unreleased commits on main", never as a misconfiguration.
- `releases/latest` skips drafts/prereleases — if the only release is a prerelease, `latest` 404s. Use `/releases?per_page=5` to see the real newest.
- Unauthenticated GitHub API allows ~60 req/hr/IP. Batch calls; add `Authorization: Bearer <token>` if you hit 403 rate-limit.
- `python3` may be absent on some Windows MSYS/git-bash hosts (use `python`). That's an environment quirk, not a repo issue.
- For free/provider questions: **never trust the README's marketing counts** — read the source catalog (see companion reference). README "90+ free" includes tiers that still need a key or login.

## Companion references
- `references/github-release-audit-recipe.md` — copy-paste curl set + a real interpretation example.
- `references/extract-free-provider-catalog.md` — how to extract the authoritative no-auth / free provider model list from an AI-gateway repo's source catalog (worked example: OmniRoute).
