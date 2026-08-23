# Document Sync After Code Changes — AVS

When significant code changes land (new CLI flags, env vars, features, refactors), the `docs/` folder (~70 files) drifts from reality. This reference captures the systematic process for bringing docs back in sync.

## Trigger

Use after any of these land on `main`:
- New CLI entry points or flags (bin/ or adapters/cli/)
- New env vars (in config.ts, .env.example, or speech-backend.ts)
- New source modules (pipeline/asset-validators.ts, orchestrator/source.ts)
- Changed default values (TTS_PROVIDER, workspace paths)
- Vendored dependency integration (src/speech/, src/music-system/)
- Multiple audit/hardening commits (brand, palette, plan, etc.)
- Changed output paths or workspace layout

## Process

### Phase 1 — Inventory

```
ls docs//*.md  →  ~70 files
```

Categorize by priority:
1. **Core reference** — CLANGELOG, cli-reference, ENVIRONMENT, usage, QUICKSTART, ARCHITECTURE
2. **Setup** — SETUP, installation, ONBOARDING, configuration
3. **Feature** — MEDIA_VERIFICATION, FREE_VIDEO, VOICEBOX_SETUP, VOICE_CLONING, TESTING
4. **Plan/design** — ARCHITECTURE-MUSIC-SYSTEM, FULL_ARCHITECTURE, SPEC_SUBTITLE_BURNIN
5. **Meta** — FAQ, README, troubleshooting, ROADMAP

### Phase 2 — Codebase Delta Analysis

```
git log --oneline main -40     → recent commits
package.json scripts           → new npm script entries
bin/*                          → new CLI entry points
src/adapters/cli/*.ts          → CLI flag definitions
.env.example                   → new env vars
grep -rn "process.env\." src/  → all consumed env vars
```

Identify:
- New CLI flags (--gpu, --dry-run, --verbose, --chapters)
- Missing npm scripts (agentic:plan, agentic:preview, agentic:mode:*)
- Changed defaults (TTS_PROVIDER default → voicebox, workspace path)
- New modules with user-facing impact
- Any BREAKING changes (path moves, removed features)

### Phase 3 — Systematic Doc Updates

1. **CHANGELOG first** — this is the canonical record. Add every change with user-facing impact.
2. **cli-reference.md** — complete rewrite if many scripts added. Every npm script, every CLI flag.
3. **ENVIRONMENT.md** — add new vars, fix changed defaults, update descriptions.
4. **usage.md / QUICKSTART.md** — update example commands to reflect current CLI.
5. **Cross-reference docs** — SETUP, ONBOARDING, configuration, faq, troubleshooting — check for stale paths, defaults, and feature descriptions.
6. **Feature docs** — VOICEBOX_SETUP, MEDIA_VERIFICATION, etc. — update to match current architecture.

### Phase 4 — Cross-Reference Verification

Check these common staleness patterns:
- **Paths**: `agentic-pipeline/workspaces/` → `workspace/jobs/`
- **Defaults**: `TTS_PROVIDER=edge-tts` → `voicebox`, `VOICEBOX_BACKEND_DIR=voicebox/` → `src/`
- **Module names**: `backend.main` → `speech.main`
- **External paths**: `C:/one/voicebox/` → `src/speech/` (vendored)
- **File listings**: ARCHITECTURE.md tree, FILE_STRUCTURE.md — add new files
- **Test counts**: update in TESTING.md

### Phase 5 — Verify & Push

```
git add docs/
git commit -m "docs: update N documents to reflect latest changes"
git push origin main
```

## Pitfalls

- **Table formatting**: Markdown table rows need exactly `|` delimiters. The `patch` tool can introduce stray `||` prefixes or extra `|`. Always verify the rendered table reads correctly.
- **Path references**: Search for ALL instances of old paths/config files — ADR files may also need updates.
- **New vs updated**: New docs from merged branches (PRODUCTION_*) are already current. Don't re-modify them.
- **Forward-looking plans**: Documents like ARCHITECTURE-MUSIC-SYSTEM.md describe *desired* architecture. Verify which parts are actually implemented before updating.
- **One doc per commit**: When possible, batch related changes into focused commits for clean history.
