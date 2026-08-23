---
name: oss-fork-evolution
description: Revive, update, or evolve a stalled/under-maintained open-source project by forking it, syncing to live upstream, and using GitHub Actions CI as the remote build/verify gate when your local machine can't compile it. Also covers the "is this repo actually dead?" maintenance-health check (last commit on main vs open-PR activity) that prevents wrong "it's abandoned" conclusions. Use when the user says "evolve this project", "it's not developed anymore", "fork and improve X", "the main branch is stale", "update this repo to current", or wants to contribute to / breathe life into an OSS project they can't build locally.
---

# OSS Fork Evolution

## When to use
- User asks to "evolve", "update", "revive", "continue development of", or "fork-and-improve" an OSS repo.
- User claims a repo is "dead / not developed" — **VERIFY before acting** (Step 0).
- Local box cannot build the project (missing toolchain, <8GB RAM, low disk) but you still need to prove it compiles/tests → use the repo's own CI as the gate.

## Step 0 — Maintenance-health check (is it REALLY dead?)
A frozen `main` does NOT mean abandoned. Verify with the GitHub API (not README claims):
1. Last commit on the default branch: `GET /repos/{o}/{r}/commits/{branch}` → `.commit.author.date`.
2. Open PRs and their `updated_at`: `GET /repos/{o}/{r}/pulls?state=open&per_page=100&sort=updated`. If PRs were updated recently, the project is alive — just not merged.
3. Whether those PRs are merged: `GET /repos/{o}/{r}/pulls/{n}` → `.merged_at`. If `null` and `state=="open"`, they're unmerged backlog.
**Pitfall:** the user's premise is frequently WRONG. In a real session, "after launch this project was not developed" was false — `main` frozen at v0.6.9 (May) but 39 open PRs with July activity. Report both facts; don't parrot the premise.

## Step 1 — Stale-fork rescue
If the user's fork has diverged from upstream (its `main` predates current upstream), rescue it safely:
```bash
git clone --depth 1 <fork>
cd <repo>
git remote add upstream <upstream>
git fetch upstream
git branch legacy-fork-main main          # preserve old fork work
git reset --hard upstream/main            # fast-forward fork to current upstream
git push origin legacy-fork-main          # keep old work safe
git push --force origin main              # align fork main with upstream
```
The `legacy-fork-main` branch is the rollback; never force-push it.

## Step 2 — CI-as-build-gate evolution (no local toolchain)
When you can't `cargo build` / `pnpm install` locally (no toolchain, low RAM/disk):
1. Ensure the fork has a working CI workflow triggering on `pull_request`:
   `GET /repos/{o}/{r}/contents/.github/workflows` and `GET /repos/{o}/{r}/actions/permissions` (expect `enabled:true`).
2. Branch off upstream main: `git checkout -b evolve`.
3. Merge a candidate upstream PR (verify it's safe/isolated FIRST):
   `git fetch upstream pull/<N>/head:pr<N>` then `git merge --no-edit pr<N>`.
   Inspect the diff (`git diff main pr<N>`) BEFORE merging — prefer small, self-contained PRs (e.g. a model/catalog addition) for the first green checkpoint.
4. Push and open a PR to YOUR OWN fork's `main`:
   `gh pr create --repo <you>/<r> --base main --head evolve`.
   This triggers the 3-OS Actions CI (check + test) on GitHub's runners — your real verification.
5. Watch `gh run list --repo <you>/<r>` / `gh pr checks <n>`. CI green = the consolidation compiles & tests pass remotely.

## Pitfalls
- **README/LICENSE/version claims are unreliable.** Verify license via API (`license.spdx_id`; Rust repos are often dual MIT+Apache but README says "MIT only"). Internal benchmark numbers in README may contradict CLAUDE.md — treat as marketing.
- **Don't trust "X is the major hub" from memory.** Pull live star/last-push data for the whole category before ranking (see `references/worked-example-openfang.md`).
- **"List only" requests:** when the user asks for "a complete list only", output the catalog (name / stars / lang / last-push) without the deep-analysis narrative; they request depth separately if wanted.
- Force-push only the fork's `main` AFTER creating the `legacy-fork-main` safety branch.

## References
- `references/worked-example-openfang.md` — full command transcript + verified facts from a real session (OpenFang v0.6.9 stale-fork rescue, PR #1267 merge into `evolve`, CI-gate PR). Reuse the exact recipes.
