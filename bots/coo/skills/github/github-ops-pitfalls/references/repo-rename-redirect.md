# Repo rename → silent PR redirect (reproduction recipe)

## Setup that triggers it
- Repo `itsPremkumar/agent-search-lite` was renamed to `itsPremkumar/AgentEye`.
- Local clone still has remote `https://github.com/itsPremkumar/agent-search-lite.git`.
- You branch, commit, `git push -u origin feat/...` (succeeds — push follows redirect).
- You run `gh pr create --base master --head feat/... --title ... --body ...`.

## Observed failure
- PR is created as `itsPremkumar/AgentEye/pull/N`, NOT `agent-search-lite`.
- Even `gh pr create --repo itsPremkumar/agent-search-lite ...` and
  `gh api repos/itsPremkumar/agent-search-lite/pulls ...` resolve to `AgentEye`.
- Burned PRs #2, #3, #4 on the wrong name before diagnosis.

## Diagnosis that revealed it
```bash
gh api repos/itsPremkumar/agent-search-lite --jq '.full_name'
# -> itsPremkumar/AgentEye
```
The API returns the NEW name for the OLD slug → rename + 302 redirect confirmed.

## Confirm branch landed correctly
```bash
gh api repos/itsPremkumar/AgentEye/branches/feat/phase-a-robots-guards-lang --jq '.name'
gh api repos/itsPremkumar/AgentEye/pulls?state=open --jq '.[].html_url'
```

## Fix
- PRs are valid on `AgentEye`; close only accidental duplicates.
- Always target `--repo itsPremkumar/AgentEye` (or `export GH_REPO=...`).
- Remind user: README + pyproject homepage/repository still say `agent-search-lite`.

## Why this happens
GitHub never frees old repo names on rename; it issues a permanent redirect.
`gh` (and `curl -L`) follow it. The branch push succeeds against the redirect
target, so the branch "exists" under the new name — but every subsequent PR call
without the canonical name keeps resolving to the new repo, looking like a bug.
