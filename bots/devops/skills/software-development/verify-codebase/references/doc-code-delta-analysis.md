# Doc-vs-Code Delta Analysis

Generate a structured, categorized report of everything that has changed in a
codebase since its documentation was written — new CLI flags, env vars, config
options, source files, architecture shifts, and undocumented features.

## When to Use

- User asks "what changed since the docs were written"
- User wants a "comprehensive delta report" comparing source to docs
- You need to assess how out-of-date project docs are
- Pre-requisite before updating docs to match reality

## Core Threat Model

**Generating a plausible-sounding claim about what the docs lack, without
actually checking the source.** The delta must be *empirically verified* against
real source files, not invented from memory or inferred from what "should" be
there. Every claim in the report must cite a source file, line range, or search
result.

## Workflow

### Phase 1 — Map the project surface

Gather EVERY interface between the code and its users/operators in one pass.
Collect these concurrently (they don't depend on each other):

| Surface | What to Read | Key Questions |
|---------|-------------|---------------|
| **Package scripts** | `package.json` `scripts` | All `npm run` commands, their exact `tsx ...` invocation |
| **CLI flags** | `bin/*.ts`, `src/adapters/cli/*.ts` | Every `--flag`, its type (bool/string/number), default value |
| **Entry point args** | The arg-parsing code itself (`process.argv.indexOf`, `arg()`, `parseArgv()`) | Input validation, aliases, defaults |
| **Env vars** | `.env.example`, `src/constants/config.ts`, `process.env.*` greps | Every env var, its default, where it's read |
| **Config schemas** | `src/agentic/config.ts`, any `*.schema.json` | All interface fields, presets, defaults |
| **Source modules** | Directory tree (`find src -type f`) | New directories, new files, renamed/removed modules |
| **Git history** | `git log --oneline -20` | Recent changes in chronological context |

**Method:**
```bash
# Package.json — read with read_file once, extract all scripts
cat package.json | grep -E '"(dev|build|generate|agentic|test|lint|electron|docker|remotion|mcp|batch)' | head -60

# CLI flags — read each CLI entry point and note every --flag
grep -n "\.indexOf\|arg(\|bool(\|args\[" bin/agentic-run.ts | head -30

# Env vars — combine .env.example with grep for process.env
grep -rn "process\.env\." --include="*.ts" src/ | grep -v test | grep -v "\.d\.ts" | sort -u

# Source tree
find src -type f -name "*.ts" | sort
```

### Phase 2 — Read the existing docs

Identify which docs to compare against:
- `docs/cli-reference.md` — CLI flags, scripts, env vars
- `docs/AGENTIC_VIDEO_WORKFLOW.md` — pipeline architecture
- Docs for specific subsystems (e.g. `docs/ARCHITECTURE-MUSIC-SYSTEM.md`)
- `.env.example` (the live one in the root)
- `docs/CHANGELOG.md` (may already list unreleased features)
- `README.md` — top-level claims about features

For each doc, note:
- What it covers (scope)
- What it claims works
- What version / date it references
- Any sections marked "recently added" or "in development"

### Phase 3 — Feature/pattern search

Search the source for features the docs MIGHT be missing. Use targeted grep:

```bash
# GPU acceleration
grep -rn "gpu\|GPU\|nvenc\|amf\|qsv\|hwaccel" --include="*.ts" src/

# Dry-run mode  
grep -rn "dry.run\|dryRun\|DRY_RUN" --include="*.ts" src/

# Preview mode
grep -rn "preview\|PREVIEW" --include="*.ts" src/

# Watchdog / timeouts
grep -rn "AGENTIC_MAX_RUN_MS\|WATCHDOG\|watchdog" --include="*.ts" src/

# Chapters / subtitles
grep -rn "chapter\|CHAPTER\|\.srt\|subtitle" --include="*.ts" src/

# Content gate / placeholder detection
grep -rn "isUniformPlaceholder\|ContentCheckResult\|signalstats" --include="*.ts" src/

# New command modes
grep -rn "render-gif\|render-poster\|render-contact" --include="*.ts" src/

# Honest source labeling
grep -rn "sourceFromUrl\|source.*label\|HONEST" --include="*.ts" src/
```

Also grep for env vars mentioned in source but NOT in .env.example:
```bash
# Extract all process.env references, compare against .env.example
```

### Phase 4 — Cross-reference against docs

For each finding from Phase 1-3, determine doc status:

| Status | Meaning |
|--------|---------|
| ✅ Documented | Mentioned in docs with correct description |
| 📝 Partial | Mentioned but missing details/options |
| ❌ Missing | Not mentioned anywhere in docs |
| 🔁 Changed | Docs describe old behavior that no longer matches |

Build the cross-reference by creating structured comparisons:

```markdown
| Flag | Type | Source Location | Doc Status |
|------|------|----------------|------------|
| `--gpu` | bool | bin/agentic-run.ts:56 | ❌ Missing from docs (partial in CHANGELOG) |
| `--verbose` | bool | src/agentic/orchestrator/render.ts:361 | ❌ Missing |
```

### Phase 5 — Check git log for temporal context

```bash
git log --oneline -30  # Last ~30 commits
```

For each commit, note:
- New features introduced (versus bug fixes)
- Breaking changes
- Any commit that touches files in `docs/` (indicates intentional doc update)

This helps you distinguish between "docs are genuinely stale" versus "this
feature was just added an hour ago and nobody has written docs yet." The
CHANGELOG.md is a useful bridge — it often documents unreleased features
that the user-facing docs don't yet mention.

### Phase 6 — Organize the report

Structure findings by category in this order of importance:

0. **Git-log contextualization (run FIRST, before even reading docs).** Run `git log --oneline -30` and `git diff --stat HEAD~1 HEAD` (or the range since the last known doc update). This instantly tells you:
   - Which docs were already updated in the most recent commits (skip their full re-verification)
   - Which features landed recently that haven't been documented yet
   - Whether there's an ongoing doc-update campaign (multiple docs touched in one commit)
   How to use: grep `docs/` in the `--stat` output. If a commit like `docs: update 12 documents...` exists, those docs are CURRENT — focus effort on the rest.

1. **New CLI flags** — table of flag, type, source file, description
2. **Missing npm scripts** — scripts in package.json not in cli-reference.md
3. **New env vars** — table of var, default, where used
4. **New source files** — new modules with their purpose
5. **Architecture changes** — reorganized directories, split/merged modules
6. **Undocumented features** — any non-trivial capability the docs miss entirely
7. **Changed behavior** — breaking changes (new defaults, different output paths)
8. **Test infrastructure** — new test patterns, test count, coverage
9. **Docs that need updates** — which specific doc files and what's missing

### Phase 6b — Report format (per-doc, with priority)

For each doc file, produce a structured assessment using this format:

```markdown
### `docs/FOO.md` — NEEDS-UPDATE / UP-TO-DATE / STALE

**Issues found:**

| Section/Line | What's wrong | Fix needed |
|---|---|---|
| Line 47 | Missing env var `GPU_ACCEL` | Add: `GPU_ACCEL` — enable GPU-accelerated rendering |
| Line 114 | Old TTS default `edge-tts` | Change default to `voicebox` (vendored in-repo) |

**Recommendation:** Moderate update needed.
```

When many docs are in scope (>5), use this summary table at the top:

| # | Doc | Status | Priority | Action |
|---|-----|--------|----------|--------|
| 1 | ARCHITECTURE.md | NEEDS-UPDATE | High | Add agentic pipeline tree |
| 2 | api-reference.md | ✅ UP-TO-DATE | — | — |
| 3 | installation.md | ⚠️ Minor fix | Low | Update TTS default mention |

Each NEEDS-UPDATE entry must cite **specific line numbers** and **suggested replacement text** so the user can apply changes without re-reading the source. This is the key difference from a vague "this doc is outdated" claim.

### Phase 6c — Multi-doc batch workflow (10+ docs)

When the scope is 10+ documents, process them in waves:

1. **Identify all docs in scope.** `find docs/ -name '*.md' | sort` or the user's explicit list.
2. **Read them in parallel batches** (3-6 at a time, one `read_file` call per doc). This saves rounds vs reading one doc at a time.
3. **For each doc category, verify against the corresponding authoritative source:**
   | Doc category | Verify against |
   |---|---|
   | CLI reference | `package.json` scripts + CLI entrypoint arg parsing + actual binary `--help` |
   | Architecture | Actual directory tree (`find src -type f`) + file purpose headers |
   | API docs | Actual tool registration code (`registerTool('name', ...)`) + route definitions |
   | Environment docs | `.env.example` + `process.env.*` greps across `src/` |
   | Workflow docs | Actual pipeline code (entry→stages→output) |
   | Setup/installation | Run the actual install commands in a terminal; verify paths exist |
4. **Cross-reference git history last.** Check `git log` for recent commits that may have fixed some issues — don't report a known-fixed bug.
5. **Produce a single comprehensive report** with all docs categorized. Start with the summary table, then detailed per-doc sections.

This batch approach saves 3-5 roundtrips compared to processing docs sequentially.

### Phase 7 — Delegated parallel analysis (alternative to Phases 1-4)

When the codebase is large (150+ source files, 20+ recent commits), running
Phases 1-4 sequentially can take 50+ API calls. Instead, **delegate the initial
analysis to a background subagent** while you start reading the docs yourself:

```python
# In the main agent context:
delegate_task(
    goal="Analyze the codebase and produce a structured delta report...",
    context="Project at <path> on branch <name>. Recent changes include..."
)
# While subagent runs, start reading docs in parallel:
read_file(path="docs/cli-reference.md")
read_file(path="docs/ENVIRONMENT.md")
read_file(path="docs/usage.md")
```

**When to use:**
- Codebase has 20+ recent commits worth of changes
- 50+ source files in active directories
- 10+ docs that need comparison
- You need to start working immediately while analysis runs

**When NOT to use:**
- Small codebase (<20 source files) — direct analysis is faster
- The subagent creates a round-trip delay that outweighs the parallelism
- You need exact, per-line citations immediately (subagent summaries are
  summarized — you'll need to verify specific claims yourself)

**How to consume the result:**
1. Read the live transcript (`tail -f <live_transcript_path>`) to track progress
2. When the subagent completes, its summary arrives as a deferred message
3. **Use the subagent output as a checklist, not a source of truth** — verify
   claims about missing docs by reading the actual doc files before patching
4. The subagent may be more thorough on mechanical enumeration (tool counts,
   file lists, grep results) while you focus on semantic accuracy (is the
   description right, not just is the flag listed)

### Phase 8 — Vendor-dependency cross-check (critical for accuracy)

A common doc-vs-code mismatch: **docs describe a dependency as external/optional
when it's actually vendored in-repo.** This session found Voicebox described
as "a separate, locally-run headless TTS engine (MIT)" when it was vendored at
`src/speech/` with an auto-start lifecycle.

**Checklist:**
1. Search for `VENDORED.md`, `vendor/`, or `vendored` markers in the source tree
   (e.g. `find . -name 'VENDORED*' -o -name '.vendor-*' 2>/dev/null`)
2. Check `THIRD_PARTY_LICENSES.md` or `docs/THIRD_PARTY_LICENSES.md` for
   provenance entries that reference in-repo copies
3. Grep the docs for phrases like "separate", "clone", "external service",
   "you need to install", "download from" — each is a candidate for being
   stale if the dependency is now vendored
4. Cross-reference: for any dependency the docs say is external, search the
   codebase for `import`/`require`/`spawn` paths. If the code references
   a local path (`.`/`src/`/`./`) rather than an absolute or env-var path,
   the dependency may be vendored

### Phase 9 — Multi-commit update strategy (for 10+ docs)

When updating 10+ documents, use **focused, scoped commits** rather than one
giant commit. This makes review easier and lets you push partial progress:

| Commit | Scope | Example Message |
|--------|-------|-----------------|
| 1 | Core reference docs | `docs: update CHANGELOG, cli-reference, ENVIRONMENT, usage, QUICKSTART` |
| 2 | Architecture & setup | `docs: update ARCHITECTURE.md, SETUP.md, ONBOARDING.md, faq.md` |
| 3 | Feature-specific docs | `docs: update API.md (+7 tools), PRODUCTION_HARDENING, subtitle spec` |
| 4 | README fixes | `docs: update README.md — Voicebox default, roadmap fixes` |

**Rationale:** Each commit focuses on a coherent set of changes. If a commit
introduces an error, it's easy to revert just that scope. It also lets you
push incrementally while a delegate is still analyzing remaining docs.

### Phase 10 — Verify-by-delegation (final quality gate)

After updating the docs yourself, **dispatch a verification subagent** to check
for remaining gaps. The subagent will independently re-read the updated docs
against the codebase and report anything you missed:

```python
delegate_task(
    goal="Perform a detailed comparison between codebase and documentation...",
    context="I just updated these docs: [list]. Check if any still need updates..."
)
```

**How to use the result:**
- The subagent's findings may overlap with your own work — that's fine
- For each finding it reports as NEEDS-UPDATE, verify the claim against the
  actual doc file (its summary may be based on pre-update content)
- **Apply any genuine gaps the subagent found** that you missed
- This pattern caught 4 additional docs needing updates in one session

### Phase 11 — Pitfalls to avoid

- **Don't trust the docs about what the code does — read the code.** A documented
  flag like `--chapters` may exist in `cli-reference.md` but never be wired in
  the actual entry point. Always verify from source.
- **Don't claim a feature is undocumented without checking ALL the doc files.**
  A flag may be in `cli-reference.md` but described under a different section
  than you expect, or documented only in the `--help` text in the source.
- **Don't confuse CHANGELOG.md with user-facing docs.** The changelog may list
  features the main docs never mention — that's exactly the gap you're looking
  for, not a contradiction.
- **Don't stop at the first doc file.** A system like AVS has multiple docs:
  `AGENTIC_VIDEO_WORKFLOW.md`, `ARCHITECTURE-MUSIC-SYSTEM.md`, `CLI_REFERENCE.md`,
  `README.md`, and subsystem-specific docs. Check them ALL.
- **`search_files` tool may fail on Windows POSIX paths** (`C:/one/...` →
  "The system cannot find the path specified"). Fall back to terminal `grep -rn`
  immediately on the first failure.
- **CLI flags can be defined in arg-parsing, in the `--help` text, or both.**
  Read the actual parsing code (`indexOf`, `arg()`, `bool()` calls), not just
  the `--help` comment block — they often drift apart.
- **Some features are wired ONLY via env vars, not CLI flags.** Always check
  both surfaces.
- **Docs that describe a dependency as "external" may be stale if the
  dependency is now vendored in-repo.** Always check for `VENDORED.md` markers
- **The `patch` tool may double-escape backslashes** in TypeScript/JavaScript
  string literals. After patching a file that contains `\\` in string content,
  verify the actual file content with `read_file` — the escaped backslash count
  may be wrong. Fix with a second targeted patch or direct `write_file`.
- **Subagent summaries are self-reports, not verified facts.** A subagent that
  claims "docs are up-to-date" may have missed stale sections. Always verify
  critical claims by reading the actual doc file.
