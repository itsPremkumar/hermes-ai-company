---
name: codebase-onboarding
description: Analyze and remember an unfamiliar large codebase.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [codebase, onboarding, architecture, memory, analysis, clone]
    related_skills: [codebase-gap-analysis, verify-codebase, source-audit]
---

# Codebase Onboarding & Remember

Use when a user asks you to "analyze / understand / remember my project or repo", after you clone a repo you'll work in repeatedly, or when you need a working mental model of an unfamiliar large codebase before making changes.

## When to use
- "clone the latest version of my X project and analyze + remember it"
- "onboard me to this codebase" / "explain how this repo is structured"
- You've just cloned (or are sitting in) a repo and will work in it across sessions.

## Workflow (cheap-first, then empirical)
1. **Establish ground truth — do NOT blindly re-clone.**
   - `git remote -v`, `git branch -a`, `git status`.
   - `git fetch --all --prune`, then find the newest branch by committer date:
     `for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | sed 's#origin/##'); do echo "$(git log -1 --format='%ci' origin/$b)  $b"; done | sort -r | head`
   - If `main` is already the newest and local is up to date, *say so* — don't re-clone over a working tree. Only `git pull --ff-only` if behind.
2. **Map structure cheaply (avoid reading every file).**
   - Read the manifest: `package.json` (scripts/bin/deps), `pyproject.toml`, `Cargo.toml`, `go.mod` — reveals entry points + toolchain.
   - List the source tree: `find src -type f | sort` (or the repo's main dir). Skim names to see layering.
   - Read the project's own curated orientation docs if present: `llms.txt`, `README.md`, `AGENTS.md`, `SKILL.md`, `.cursor/rules/*`. These are high-ROI summaries — read them before source.
3. **Follow the golden path, not everything.**
   - Trace ONE feature end-to-end: entry point → orchestrator/controller → data model (`types.ts`/`models.py`) → config surface → renderer/composer.
   - Multi-pipeline repos: identify each pipeline's entry and how they share core libs.
4. **Empirically verify the tree compiles (proves it's current, not stale/broken).**
   - Node/TS: `npm run typecheck` (or `tsc --noEmit`). Run in background if slow.
   - Python: `pytest -q`. Go: `go build ./...`. Rust: `cargo build`.
   - A clean compile is your evidence that the remembered map describes a real, current tree.
5. **Persist a COMPACT architecture map to memory.**
   - Module responsibilities, dual/multi-pipeline layout, key file pointers (entry → orchestrator → config), and the verify command.
   - Keep it under ~700 chars. Consolidate into ONE entry; the memory store caps at ~2200 chars total. Do not dump transcripts or task narrative.

## Pitfalls
- **Re-cloning over a working tree** wastes state and can clobber local work. Verify freshness with fetch+compare first.
- **Reading every file** burns context. Target entry points + types + config; follow one golden path.
- **Memory size cap (~2200 chars total).** If near the cap, use `replace` to *consolidate* an existing entry; an `add` (or an overflowing `replace`) that exceeds the limit is rejected. Trim operational notes into one tight entry.
- **Don't capture transient errors as durable rules** — setup failures, missing binaries, session-specific hangs are not memory/skill material.
- **Don't commit/push** unless the user explicitly asks — onboarding is read + remember only.

## Verification
- The remembered map must match what `typecheck`/`build` confirms: a compiling tree. If the build fails, fix or note it before claiming "remembered".

## Support
- `references/onboarding-commands.md` — copy-paste command recipes for steps 1–4.
