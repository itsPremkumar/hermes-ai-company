# Example Gap Analysis — Feature vs Example Coverage

Systematically determine which features/flags/options in a codebase are NOT
covered by any example file or config reference. This prevents users from having
features that have no discoverable examples, and catches docs drift.

## When to Use

- User asks for "more useful example scripts" for a system
- You've added new features and need to ensure they have examples
- Before a release — ensure every feature has at least one example
- As a complement to doc-vs-code delta analysis (examples are a different
  surface than docs)

## Core Principle

**Every user-facing flag, mode, and feature should have at least one example
file that demonstrates it.** A feature without an example is as bad as a
feature without documentation — users can't discover how to use it.

## Workflow

### Step 1 — Inventory all CLI flags and features

Start by extracting every flag or field from the authoritative source(s):

**From CLI entry points:**
```bash
# Extract all arg() and bool() calls from agentic-run.ts
grep -oP "arg\('([^']+)'|bool\('([^']+)'" bin/agentic-run.ts | grep -oP "'[^']+'" | tr -d "'"
```

**From job JSON fields:**
Read the AGENTIC_SCRIPT_FORMAT.md or equivalent reference doc for every
configurable field (mode, orientation, quality, gpu, sfx, etc.)

**From script inline tags:**
Extract all `[Tag: ...]` patterns (`[Visual:]`, `[Transition:]`, `[Grade:]`, etc.)

### Step 2 — Inventory all existing example files

```bash
# Count and list all examples
find examples/ input/scripts/agentic-script-examples/ -name '*.json' | sort
```

Categorize them by type:
- **Full demos** — complete ready-to-render jobs
- **Feature demos** — single-feature showcases
- **Modes** — single-stage execution mode configs
- **Inline tag examples** — script files showing tag syntax

### Step 3 — Cross-reference each flag/feature against examples

For each flag/feature from Step 1, check if any example file uses it:

| Feature | Found in examples? | Example file |
|---------|-------------------|--------------|
| `--gpu` | ✅ Yes | `features/16-gpu-quality.json` |
| `--no-ducking` | ❌ No | — |
| `images: true` | ❌ No | — |

**Method:** For each feature, search across all example files:
```bash
# Search for a field across all example files
grep -r '"gpu"' examples/ input/scripts/agentic-script-examples/ --include='*.json'
```

### Step 4 — Identify coverage gaps

Group missing features by priority:

| Priority | Criterion | Example |
|----------|-----------|---------|
| High | CLI flag with no example | `--no-ducking` |
| Medium | Feature field with no demo | `targetLanguages` |
| Low | Niche/edge-case feature | `chromaKeyScenes` |

Also check content vertical gaps (different topic types not represented):
- Have: motivational, educational, product, tutorial, storytelling, tech, health, business, crypto, travel
- Missing: food/cooking, gaming, music, sports

### Step 5 — Create targeted new examples

For each gap, create the minimal example that demonstrates the feature:

```python
example = [{
    "id": "feature-no-ducking",
    "title": "No Ducking Demo",
    "script": "...",
    "noDucking": True,       # The missing feature
    "sfx": False,
    ...
}]
```

**Naming conventions:**
- Full demos: `full-demos/<NN>-<topic>.json` (sequential, descriptive)
- Feature demos: `features/<NN>-<feature>.json` (sequential under features/)
- Modes: `modes/<NN>-<mode>.json`

**When adding a feature with multiple sub-flags** (like `--no-ducking`,
`--no-ken-burns`, `--no-kinetic`), combine them into ONE example file
rather than creating separate files for each.

### Step 6 — Update README

After creating new examples, update the directory README to include:
- New entries in the file tree listing
- A "New in latest" table showing what each new example demonstrates
- Updated coverage count (e.g. "36 → 42 files")

### Step 7 — Validate all JSON

```bash
python3 -c "
import json, os
errors = []
for root, dirs, files in os.walk('examples/'):
    for f in sorted(files):
        if f.endswith('.json'):
            try:
                json.load(open(os.path.join(root, f)))
            except json.JSONDecodeError as e:
                errors.append(f'{f}: {e}')
if errors:
    for e in errors: print(e)
else:
    print('All JSON valid')
"
```

## Pitfalls

- **Don't create example files for CLI-only flags** like `--dry-run` or
  `--verbose` that have no JSON field equivalent — those belong in the
  CLI reference doc, not in example JSON files.
- **Don't duplicate existing coverage.** Before creating a new example, search
  every existing example file for the flag/value you're demonstrating.
- **Some features aren't listable via grep.** Features like `--chapters` or
  `--gpu` may be documented as CLI flags but not as JSON fields. Check both
  the CLI entry point AND the JSON schema/config when doing the inventory.
- **Keep example files focused.** A "kitchen sink" example (all features at
  once) is useful for testing but hard to learn from. Prefer focused examples
  that demonstrate ONE feature clearly.
- **Batch topic generation** is a different pattern from JSON job configs.
  Create a reference file (not a pipeline JSON) showing the CLI commands:
  `batch-topics.json` with command examples for `agentic:generate`,
  `agentic:generate:preview`, `agentic:batch:parallel`.
- **Single-image and single-video editing** commands (`agentic:editor`,
  `agentic:image`) are CLI tools, not pipeline JSON jobs. Create reference
  files showing their CLI usage rather than trying to fit them into the
  pipeline JSON format. Document them in a dedicated `single-edits/`
  directory with their own README section.
