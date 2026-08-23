# Adding Custom Script + CLI to an Agentic Pipeline

Case study: adding simple JSON-in + `[Visual: ...]` tag support to the
Automated-Video-Generator agentic pipeline, matching the legacy pipeline's UX.

## The Gap

The legacy pipeline offered `input/scripts/input-scripts.json` → `npm run generate`.
The agentic pipeline had no equivalent — only a TypeScript programmatic API.

## Pattern (4 steps)

### 1. Add `script` field to the Request type

Before (`PipelineRequest`):
```typescript
export interface PipelineRequest {
    topic: string;          // auto-generates script
    title: string;
    localAssets?: string[];
}
```

After:
```typescript
export interface PipelineRequest {
    script?: string;        // ← custom script with [Visual: ...] tags
    topic: string;          // fallback when no script provided
    title: string;
    localAssets?: string[];
}
```

### 2. Check `req.script` first in the pipeline runner

In `runAgenticPipeline()`, before auto-generation:
```typescript
const script =
    req.script ??                                          // ← custom script wins
    (cfg.writeScript ? await cfg.writeScript(req.topic, req.title) : null) ??
    (await bridge.completeJSON<{ script: string }>(...))?.script ??
    writeScriptHeuristic(req.topic, req.title);
```

Then `buildPlan(script, ...)` calls `parseScript()` which handles both:
- `[Visual: logo.png]` → file exists in `input/visuals/` → sets `localAsset`
- `[Visual: ai code typing]` → file doesn't exist → sets `searchKeywords` → stock fetch

### 3. Fix local-asset auto-bind to NOT overwrite `parseScript` results

**Critical bug**: The auto-detect loop was binding local assets to ALL scenes,
overwriting the `localAsset` that `parseScript()` already set from `[Visual: ...]`
tags. This broke the mix of local + stock media.

Before:
```typescript
plan.scenes.forEach((s, i) => {
    s.localAsset = req.localAssets![i % req.localAssets!.length];
});
```

After — only bind to scenes WITHOUT existing `localAsset`:
```typescript
let li = 0;
for (const s of plan.scenes) {
    if (!s.localAsset) {
        s.localAsset = req.localAssets[li % req.localAssets.length];
        li++;
    }
}
```

Same fix needed in the auto-detect (`else`) branch that scans `input/visuals/`.

### 4. Create a simple JSON-in CLI + npm script

Create `src/adapters/cli/agentic-cli.ts` that:
- Reads `input/agentic-scripts.json` (same format as legacy)
- Per job, calls `runAgenticPipeline({ script: job.script, ... })`
- If gate passes, calls `renderAgenticSlideshow()` to produce the final MP4
- Prints output path

Add `package.json` script:
```json
"generate:agentic": "tsx src/adapters/cli/agentic-cli.ts"
```

## Agentic JSON Input Format

```json
[{
  "id": "my-agentic-video",
  "title": "My Video",
  "script": "Intro text. [Visual: logo.png]\nMiddle section. [Visual: ai coding technology]\nFinal call to action. [Visual: rocket launch]",
  "orientation": "portrait",
  "voice": "en-US-GuyNeural",
  "hookFirst": true,
  "variablePacing": true,
  "backend": "agent",
  "candidatesPerAsset": 2
}]
```

- `[Visual: filename.ext]` → local asset from `input/visuals/`
- `[Visual: keyword keyword]` → online stock media fetch
- Script is optional — omit to auto-generate from `topic`+`title`
- `backend: "agent"` uses free LLM; `"auto"` uses standard AI

## Verification

Before shipping:
- `npx tsc -p tsconfig.json --noEmit` → 0 errors
- Run the CLI: `npx tsx src/adapters/cli/agentic-cli.ts` → produces MP4
- Check output for correct mix of local + stock media per scene
- Confirm render produces at least the primary aspect ratio MP4

## Output

Agentic CLI produces more artifacts than the legacy pipeline:
- Main MP4 (9:16 portrait for Reels)
- Multi-aspect exports (16:9, 1:1) via plugin system
- Thumbnails, subtitles (SRT + VTT), metadata
- Publish manifest for multi-platform delivery
- Archive (25+ files including all source assets)

## Quick-start JSON template

Copy `input/agentic-scripts.example.json` to `input/agentic-scripts.json`,
edit the script and title, then run `npm run generate:agentic`.
