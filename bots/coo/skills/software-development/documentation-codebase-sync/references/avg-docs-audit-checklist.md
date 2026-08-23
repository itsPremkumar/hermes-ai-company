# Session-specific reference — AVG Docs Audit (2026-07-29)

## Checklist for Each Document

When auditing documentation, run through this checklist per doc:

### CLI Reference (`cli-reference.md`)
- [ ] Every npm script from `package.json` listed (use `grep -oP '"[^"]+": "tsx|node' package.json`)
- [ ] Every CLI flag from `bin/agentic-run.ts` listed (use `grep -oP "arg\('([^']+)'"`)
- [ ] Every env var with correct default value
- [ ] Exit codes documented and match code
- [ ] TTS env var names correct (e.g. `TTS_PROVIDER` not `TTS_BACKEND`)

### Environment Reference (`ENVIRONMENT.md`)
- [ ] Every `process.env.X` in source has a row
- [ ] Default values match source code defaults
- [ ] New features' env vars added (e.g. `GPU_ACCEL`, `AGENTIC_MAX_RUN_MS`)
- [ ] TTS provider default accurate

### API / MCP Docs (`API.md`)
- [ ] Count tools registered in source vs documented
- [ ] Missing tools added (`agentic_revise`, `agentic_critique`, etc.)
- [ ] Default provider mentions reflect current code (Voicebox, not Edge-TTS)

### Example Files
- [ ] Every CLI flag from every entry point covered by at least one example
- [ ] Every source module/feature area represented
- [ ] JSON files all validate
- [ ] README accurately lists all files
- [ ] Side tools (image editor, video editor) have examples too

## Common Pitfalls

1. `TTS_BACKEND` env var does NOT exist — the actual var is `TTS_PROVIDER`
2. `TTS_VOICE` env var does NOT exist — use `VOICEBOX_ENGINE` instead
3. `VOICEBOX_CLONE_DIR` does NOT exist — use `VOICEBOX_PROFILE_ID` instead
4. Default TTS is now `voicebox` (vendored in-repo), NOT `edge-tts`
5. Output path is `workspace/jobs/<jobId>/`, NOT `agentic-pipeline/workspaces/`
6. GPU acceleration is CURRENT (v5.x), NOT future roadmap
7. Check SINGLE-EDITING CLIs too (`agentic:editor` and `agentic:image`), not just pipeline
