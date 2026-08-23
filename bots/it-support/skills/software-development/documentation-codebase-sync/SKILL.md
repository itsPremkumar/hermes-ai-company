---
name: documentation-codebase-sync
title: Documentation ↔ Codebase Sync
description: Audit docs against source code to find and fix gaps.
---

# Documentation ↔ Codebase Sync Workflow

Systematic process to compare a project's documentation against its live source
code and produce correct, comprehensive updates.

## When to Use

- User says "update my documents" or "check docs against code"
- After major code changes (new CLI flags, env vars, features, architecture)
- When adding new example files for a pipeline/CLI system
- Before releases to ensure documentation completeness

## Workflow

### Phase 1: Inventory

```bash
# List all docs
ls docs/

# List all example/config files
ls input/scripts/agentic-script-examples/**/*.json

# Get recent git changes
git log --oneline main -30
```

### Phase 2: Codebase Feature Extraction

Extract every feature that needs documentation coverage:

```bash
# CLI flags from entry points
grep -oP "arg\('([^']+)'|bool\('([^']+)'" bin/agentic-run.ts

# npm scripts from package.json
cat package.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(k) for k in d.get('scripts',{})]"

# Env vars from code
grep -rn "process.env\." src/ --include="*.ts" | grep -oP "'[^']+'" | sort -u

# MCP tools
grep -rn "registerTool\(\s*'[^']*'" src/adapters/mcp/ | grep -oP "'[^']+'" 

# Source module listing
find src/ -name "*.ts" ! -name "*.test.ts" | sort
```

### Phase 3: Cross-Reference Against Docs

For each doc, check:

1. **CLI reference docs** — missing npm scripts, wrong flag names, missing flags
2. **Root README.md + docs/README.md** — stale env var defaults, wrong TTS provider, stale roadmap items, missing links to new docs
3. **Environment docs** — missing env vars, wrong defaults, wrong descriptions
4. **API docs** — missing MCP tools, wrong tool descriptions, outdated examples
5. **Architecture docs** — missing source files, stale directory trees, missing modules
6. **Feature docs** — outdated feature descriptions, wrong TTS/voice defaults
7. **Usage/quickstart docs** — wrong example commands, wrong output paths
8. **Voice/TTS docs** — when default TTS provider changes (e.g. edge-tts → voicebox), update ALL docs that reference TTS defaults: ENVIRONMENT.md, cli-reference.md, usage.md, SETUP.md, ONBOARDING.md, README.md, faq.md, configuration.md, QUICKSTART.md
9. **Troubleshooting docs** — missing new common issues
10. **AGENTIC_SCRIPT_FORMAT.md duplicate** — check BOTH copies (`input/scripts/` and `docs/`) for drift; `input/scripts/` is source of truth

Tag each finding: HIGH (incorrect info), MEDIUM (missing info), LOW (stale but not wrong).

### Phase 4: Fix Priority

**HIGH priority — fix first:**
- Wrong default values (e.g. `TTS_BACKEND` → `TTS_PROVIDER`, `edge-tts` → `voicebox`)
- Wrong output paths (e.g. `agentic-pipeline/workspaces/` → `workspace/jobs/`)
- Wrong env var names (nonexistent vars that cause errors if used)
- Missing 100% coverage on all CLI flags

**MEDIUM priority:**
- Missing MCP tools in API docs
- Stale file tree listings in architecture docs
- Outdated feature comparisons (e.g. roadmap items already implemented)
- Missing example files for feature areas

**LOW priority:**
- Minor wording improvements
- Reorganization suggestions
- Forward-looking roadmap items

### Phase 5: Example File Coverage

When creating/maintaining example files (e.g. pipeline JSON scripts):

1. **Inventory existing examples** — list all current files by category
2. **Map CLI flags to examples** — every flag from every entry point must appear in at least one example
3. **Map source modules to examples** — every feature module should have at least one example
4. **Map content verticals** — different use cases (tech, health, travel, business, etc.)
5. **Create missing examples** — one JSON file per gap, validate after creation
6. **Validate** — all JSON files must parse correctly

```python
# Validation pattern
import json, os
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith('.json'):
            with open(os.path.join(root, f)) as fh:
                json.load(fh)  # throws if invalid
```

### Phase 6: Commit Strategy

Batch commits by category:

```
commit 1: "docs: update core reference docs — CLI, env, usage"
commit 2: "docs: fix architecture/setup docs"
commit 3: "feat(examples): add missing N example files"
```

Always run full JSON validation before pushing example files.

## Key Principles

1. **Exhaustive checking** — check ALL features, not just the main path. Side features (image editing, video editing CLIs, GIF modes, localization) are just as likely to be undocumented.
2. **Verify against actual source code** — don't assume docs are right. Grep the source for the actual flag name, default value, behavior.
3. **Default values matter** — when `TTS_PROVIDER` default changes from `edge-tts` to `voicebox`, it must be updated in every doc that mentions it.
4. **JSON validation is mandatory** — always validate after creating/editing example files.
5. **Subagent for scale** — for 50+ docs or large codebases, delegate analysis to a subagent with specific instructions.

## Related Files

- `docs/cli-reference.md` — CLI commands and flags
- `docs/ENVIRONMENT.md` — env vars reference
- `docs/API.md` — MCP tools API
- `input/scripts/agentic-script-examples/` — pipeline and editing examples
