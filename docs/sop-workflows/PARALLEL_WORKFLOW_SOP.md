# IT Company — Parallel Work Workflow (Worktree + Branch + PR + Merge)

This SOP lets multiple sub-agents work in PARALLEL on the same codebase without
clobbering each other, using git worktrees + feature branches + PR + merge review.

## 1. Anchored Repo & Project
- Repo: `C:\c\one\it-company-workspace` (git, `main` branch)
- Hermes Project: `it-company` (id `p_dedf404b`)
- Kanban board: `it-company-ops` (bound to project → deterministic worktree+branch)

## 2. Per-Agent Isolation Rule
Each agent works in its OWN git worktree on its OWN feature branch:
```
git worktree add ../wt/<agent>-<task> -b feat/<agent>/<task>
```
Example: Tech Lead on API task → worktree `wt/tech-lead-api`, branch `feat/tech-lead/api`.

This means:
- Agent A editing `app.py` never conflicts with Agent B editing `app.py` — they're in separate dirs.
- Each branch is independent until merged.

## 3. Workflow Steps (per task)
1. Chief of Staff creates kanban task (`--workspace worktree --project it-company --branch feat/<agent>/<task>`).
2. Assignee claims → `git worktree add` into isolated dir on its feature branch.
3. Agent does work in its worktree only.
4. Agent commits to its feature branch: `git add -A && git commit -m "feat: ..."`.
5. Agent pushes branch: `git push -u origin feat/<agent>/<task>`.
6. Agent opens PR (via GitHub MCP or `<github-account-2>` `gh` CLI): base=`main`, head=`feat/<agent>/<task>`.
7. Reviewer (CTO/Architect) reviews PR → `request-changes` ⇄ fix, or `APPROVED`.
8. On approval: merge PR into `main` (squash or merge). Worktree cleaned: `git worktree remove`.

## 4. Parallel Build (Swarm)
For large features, split into N independent sub-tasks:
- Each sub-task → its own agent + worktree + branch + PR.
- All PRs merge into `main` independently (no cross-dependency).
- If two agents touch the SAME file, they coordinate via Chief of Staff (sequential merge or rebase).

## 5. GitHub MCP (agents file issues/PRs directly)
- MCP server `github` added (stdio: `npx @modelcontextprotocol/server-github`).
- Agents call MCP tools: `create_pull_request`, `create_issue`, `push` (via git), `list_pull_requests`.
- `<github-account-2>` profile holds GitHub credentials for account-separated ops.

## 6. Merge Discipline
- NEVER push directly to `main` from a worktree.
- ALWAYS via PR + review (even for bots — keeps audit trail).
- After merge: delete feature branch + remove worktree.

## 7. Commands Quick Reference
```
# Agent sets up isolation
git -C <workspace-root>/it-company-workspace worktree add <workspace-root>/wt/<agent>-<task> -b feat/<agent>/<task>
# Work, then commit
git -C <workspace-root>/wt/<agent>-<task> add -A && git -C <workspace-root>/wt/<agent>-<task> commit -m "feat: ..."
git -C <workspace-root>/wt/<agent>-<task> push -u origin feat/<agent>/<task>
# Open PR via gh (<github-account-2>) or MCP
gh pr create --base main --head feat/<agent>/<task> --title "..." --body "..."
# After merge
git -C <workspace-root>/it-company-workspace worktree remove <workspace-root>/wt/<agent>-<task>
git -C <workspace-root>/it-company-workspace branch -d feat/<agent>/<task>
```

## 8. Security Merge Gate (MANDATORY)
Every PR into `main` MUST pass Security Engineer review before merge.

1. After the feature PR is opened (step 6), Chief of Staff assigns the PR to `security-engineer` for review.
2. Security Engineer:
   - Reads the PR diff (GitHub MCP `get_pull_request_files` or `git diff main...feat/<agent>/<task>` in the worktree).
   - Runs SAST: `bandit -r <worktree>` (Python), secret scan `grep -rE "(api_key|token|secret|password)\s*=\s*['\"]"` .
   - Posts findings as `FILE:LINE — SEVERITY — issue — fix`.
   - Concludes with EXACTLY one:
     - `SECURITY-APPROVED` → PR may merge.
     - `SECURITY-BLOCKED: <findings>` → PR CANNOT merge until fixed + re-reviewed.
3. A PR WITHOUT `SECURITY-APPROVED` is NOT mergeable — the merging reviewer (CTO/Architect/Chief of Staff) must see the approval comment first.
4. On `SECURITY-BLOCKED`: assignee fixes, pushes, re-requests review; loop until `SECURITY-APPROVED`.

Security Engineer reports to CTO. Critical findings escalate to CTO immediately.

## 9. Quick Security Commands
```
# In the agent's worktree
bandit -r .                      # Python SAST
grep -rEn "(api_key|secret|token|password)\s*=\s*[\"']" .   # secret scan
git diff main...feat/<agent>/<task>   # review diff
```
