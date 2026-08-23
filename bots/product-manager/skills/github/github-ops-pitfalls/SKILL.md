---
name: github-ops-pitfalls
description: "GitHub gotchas: renamed repos silently redirect PRs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, gh, Pitfalls, Diagnostics, Repo-Rename, PR]
    related_skills: [github-pr-workflow, github-auth]
---

# GitHub Operations Pitfalls

Non-obvious GitHub/gh failure modes that waste 2-3 wasted PRs or a confused
session before you spot them. Contrast with `github-pr-workflow` (the happy-path
PR lifecycle). This skill is for when `gh` "succeeds" but the result is wrong.

## 1. Renamed repos silently redirect PR/create calls (most common)

**Symptom:** git remote is `OWNER/old-name`, but every `gh pr create` and
`gh api repos/OWNER/old-name/pulls` lands the PR on a DIFFERENT repo
(`OWNER/new-name`). You create PRs #2, #3, #4 before noticing they're on the
wrong repo. The branch you pushed "to old-name" actually got stored under
new-name.

**Root cause:** GitHub 302-redirects the old repo name to the new one forever.
`gh` follows the redirect transparently and never warns you.

**Diagnose (single authoritative call):**

```bash
gh api repos/OWNER/old-name --jq '.full_name + " (redirect target)"'
# -> "itsPremkumar/AgentEye (redirect target)"
```

If it prints a name different from what you typed, that's the rename.

**Confirm where your branch/PRs actually went:**

```bash
gh api repos/OWNER/new-name/branches/BRANCH --jq '.name'
gh api repos/OWNER/new-name/pulls --jq '.[].html_url'
```

**Recover (do NOT re-create):**

- The "wrong-repo" PRs are real and correct — they're on `new-name`. Close only
  the accidental duplicates: `gh pr close N --repo OWNER/new-name --comment "..."`.
- Target the canonical name directly to stop hitting the redirect:
  `gh pr create --repo OWNER/new-name ...` or `export GH_REPO=OWNER/new-name`.
- Tell the user the repo was renamed. Their README links, `pyproject.toml`
  `homepage`/`repository` URLs, and any bookmarked PR URLs still say `old-name`
  and will 404/redirect. Recommend keeping the rename (update links) or renaming
  back to the branded name.

See `references/repo-rename-redirect.md` for the full reproduction recipe.

## 2. `gh` default repo ≠ git remote

`gh repo view` / `gh pr create` resolve the "current repo" from `gh`'s own notion
(which can differ from `git remote get-url origin` — e.g. a global `GH_REPO`, a
different default, or the rename redirect above). If calls keep targeting the
wrong repo even with `--repo`, the redirect in #1 is the usual culprit; otherwise
set `GH_REPO` explicitly.

## 3. Active account matters for push/PR

`gh auth status` lists all logged-in accounts; only the one marked
`Active account: true` is used for git operations unless you `gh auth switch`.
A repo owned by `itsPremkumar` but with an active `prem-the-dev` (read-only)
account will 403 on push. Switch first: `gh auth switch -u itsPremkumar`.

## 4. Zero-byte files when bulk-downloading a repo tree on MSYS

When fetching many raw files via a `for p in $(curl ... | ...); do curl -o "$p"; done`
loop on Windows MSYS/git-bash, some iterations can write 0-byte files silently
(the loop's subshell or quoting drops the write). Symptom: `import` fails with
`ModuleNotFoundError` for a module that "exists" (it's 0 bytes). Fix: after the
loop, `find agent_search -name '*.py' -size 0` and re-fetch those explicitly; or
fetch each file with an explicit `curl -sL -w "%{http_code}"` and assert byte count.
(Environment-specific, not a GitHub API issue — recorded here because it blocks
repo inspection that precedes any PR work.)

## When to use this skill

Load it whenever `gh`/`git` "succeeds" but the resulting repo/PR/branch is not
what you expected, or when you're about to open a PR against a repo whose name
you're not 100% sure is canonical.
