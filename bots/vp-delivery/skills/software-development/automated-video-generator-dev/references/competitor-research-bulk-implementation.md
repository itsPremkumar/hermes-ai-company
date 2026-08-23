# Competitor Research → Bulk Feature Implementation

## Pattern
When the user asks "analyze other video generation projects and borrow features," follow this workflow:

1. **Search & enumerate** — Search for competitor projects (MoneyPrinterTurbo, CapCut, HeyGen, Synthesia, InVideo AI, Runway, Pika, etc.) and list their features.
2. **Classify** — Group features into High/Medium/Low priority by impact vs effort.
3. **Filter** — Skip UI-only features (CLI UX, WebUI preview) unless asked. Skip features that require heavy GPU on the user's 6GB box.
4. **Implement with identity-preserving pattern** — Every new feature:
   - OFF by default, opt-in via env var
   - Graceful fallback chain (e.g., ElevenLabs → SiliconFlow → Edge-TTS)
   - Never breaks the pipeline if dependency is missing
   - Tests that verify graceful degradation when offline
5. **Verify** — Typecheck + lint + new tests + spot-check old tests.

## Import path depth gotcha
When creating files in nested directories, count the `../` carefully:
- `src/agentic/services/` → `../../shared/` (2 levels up)
- `src/agentic/services/tts/` → `../../../shared/` (3 levels up)
- `src/lib/video/` → `../../shared/` (2 levels up)

Wrong depth = `MODULE_NOT_FOUND` at runtime. Always verify by running `npx tsc --noEmit` after creating new files.

## ffmpeg filter string lint trap
- `no-useless-escape` error from `\\,` in template literals — use plain `,` in ffmpeg filter expressions
- `prefer-const` when variable is never reassigned — use `const` not `let`
- `prefer-nullish-coalescing` — use `??` instead of `||` where appropriate

## job-queue auto-processing test pattern
The job-queue auto-processes jobs on enqueue. Tests must NOT assume `queueLength >= 1` after enqueue. Instead:
```typescript
// Wait for auto-processing
await new Promise(resolve => setTimeout(resolve, 100));
// Check completed + failed counts, not pending queue length
assert.ok(status.completedCount + status.failedCount >= 1, 'job was processed');
```

## isGenEnabled() local-first behavior
With local-first AI, `isGenEnabled()` returns `true` even without API keys (ComfyUI fallback). Tests should assert `true`, not `false`.

## Graceful fallback chains (standard pattern)
```
TTS: ElevenLabs → SiliconFlow → Edge-TTS → silence
Image gen: ComfyUI → FLUX3 → API → stock → placeholder
Video gen: CogVideoX → AnimateDiff → FLUX3 → API → stock → slideshow
Stock: Pexels → Openverse → Coverr → Wikimedia → Internet Archive → placeholder
AI: Local ComfyUI → API key → offline placeholder
```

## Feature implementation checklist
For each new feature:
1. Create the module file in appropriate `src/` subdirectory
2. Add exports to `src/agentic/services/` or `src/lib/` index if needed
3. Add env vars to `.env.example` (all optional)
4. Add tests in `tests/` directory
5. Add feature to skill's "New service modules" table
6. Add fallback chain entry if applicable
7. Typecheck + lint + test before push
