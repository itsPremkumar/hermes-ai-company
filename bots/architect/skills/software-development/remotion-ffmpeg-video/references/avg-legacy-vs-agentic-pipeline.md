# Legacy vs Agentic Pipeline: Automated-Video-Generator

> Session: 2026-07-21 — Deep code analysis comparing both systems at `C:\one\Automated-Video-Generator`.

## Architecture Overview

| Aspect | Legacy Pipeline | Agentic System |
|--------|----------------|---------------|
| **Location** | `src/video-generator.ts` (1 file, ~21KB) | `src/agentic/` (~93 files, ~700KB) |
| **Stages** | Script → Parse → Fetch → Render | Plan → Acquire → Verify → Decide (Gateway) → Gate → Render |
| **Gates** | None | X1–X16 quality checks (duration, black frames, freeze, audio clipping, dimensions, codec, AI vision) |
| **AI** | No AI | AgentBrain (free OpenRouter/Ollama) for script writing, hook detection, pacing, music derivation |
| **MCP surface** | 4 tool groups (input, job, output, admin) | Same 4 + `registerAgenticTools` + `registerOperationsTools` (27+ single-task ops) |
| **Plugins** | None | 25+ plugins (audio, color, motion, overlays, transitions, genres, platforms) |


## Local Asset Handling — Critical Path Information

### Where the code looks for assets

**`INPUT_ASSETS_DIR = 'visuals'`** in `src/lib/path-safety.ts`:
```typescript
export const INPUT_ASSETS_DIR = 'visuals';
export const INPUT_ASSET_ROOT = resolveProjectPath('input', INPUT_ASSETS_DIR);
export function inputAssetPath(...segments: string[]) {
    return resolveProjectPath('input', INPUT_ASSETS_DIR, ...segments);
}
```

**Resolution**: `resolveProjectPath('input', 'visuals')` → **`input/visuals/`**

### ⚠️ Critical Pitfall: `input/input-assets/` vs `input/visuals/`

Both pipelines ultimately call `inputAssetPath()` which resolves to `input/visuals/`. 
If you place assets in `input/input-assets/`, the **legacy pipeline will NOT find them**.

**Legacy pipeline**: Asset must be at `input/visuals/<filename>`. Referenced via `[Visual: filename.ext]` in script.

**Agentic pipeline**: Has TWO mechanisms:
1. `[Visual: filename.ext]` in auto-generated script → calls `parseScript()` → calls `inputAssetPath()` → **input/visuals/**
2. `PipelineRequest.localAssets: string[]` → copies from `input/input-assets/` to workspace directly (BYPASSES `inputAssetPath()`)

So for the agentic system's `localAssets` mechanism, use `input/input-assets/`. For the legacy `[Visual: ...]` tag, use `input/visuals/`. For the agentic system's `[Visual: ...]` tag, use `input/visuals/`.

### Verification: `continue` in acquire.ts

In `src/agentic/pipeline/acquire.ts` (around line 172):
```typescript
if (scene.localAsset) {
    const srcPath = inputAssetPath(scene.localAsset);  // ← checks input/visuals/
    if (fs.existsSync(srcPath)) {
        // Copies local file, pushes candidate, then:
        continue;  // ← Skips stock fetch entirely
    }
    // File missing → falls through to stock fetch below
}
```

If the file is in the wrong directory (`input/input-assets/` instead of `input/visuals/`), `fs.existsSync` returns false, the local asset is **silently skipped**, and stock media is fetched as fallback. The `plan.json` will show `localAsset` set but the `candidates.json` will show `source: "placeholder"` instead of `source: "local-asset"`.


## How to Run Each Pipeline

### Legacy Pipeline

1. Place local assets in **`input/visuals/`**
2. Write input script in **`input/scripts/input-scripts.json`** (JSON array format)
3. Run: `npm run generate` (runs `tsx src/cli.ts`)

Input format:
```json
[{
  "id": "my-video",
  "title": "Video Title",
  "script": "Scene one text. [Visual: logo.png]\nScene two text. [Visual: screenshot.png]",
  "orientation": "portrait",
  "voice": "en-US-GuyNeural",
  "showText": true,
  "language": "english"
}]
```

Edge-TTS voice generation runs via bundled portable Python (`portable-python/Scripts/edge-tts.exe`).

### Agentic Pipeline (MCP tools)

Exposed via MCP in `src/adapters/mcp/register-agentic-tools.ts`:
- `agentic_plan` — builds the plan from topic/title + localAssets
- `agentic_acquire` — fetches/downloads assets
- `agentic_verify_all` — verifies each asset
- `list_pending_assets`, `get_asset_preview`, `approve_asset`, `reject_asset`, `replace_asset`
- `agentic_gate` — runs quality gate
- `agentic_render` — renders the final video

### Agentic Pipeline (direct TypeScript)

```typescript
import { runAgenticPipeline } from './src/agentic/orchestrate.js';

const result = await runAgenticPipeline(
    {
        jobId: 'my-job',
        topic: 'Topic description for auto-generated script',
        title: 'Video Title',
        orientation: 'portrait',
        voice: 'edge',
        localAssets: ['logo.png', 'screenshot.png'],  // ← from input/input-assets/
        hookFirst: true,
        variablePacing: true,
    },
    console.log,
);
```

Run with: `npx tsx run-agentic-reel.ts`


## Known Render Performance

| Pipeline | Scenes | Total Time | Output Size | Voice Quality |
|----------|--------|-----------|-------------|---------------|
| Legacy | 8 scenes, 34s video | ~2 min | 2.61 MB | Edge-TTS (real voice) |
| Agentic | 3 scenes, 13s plan | ~5+ min (render >300s, timed out) | N/A | Edge-TTS → SAPI fallback |

The agentic pipeline has more overhead due to:
- 6-stage pipeline with quality gates
- Plugin system initialization (25+ plugins)
- AI Brain LLM calls (script generation)
- Stock media fetch with multiple providers (12s timeout per keyword)
- Complex render manifest construction


## Voiceover Providers (in priority order)

Chain in `src/lib/voice-generator.ts`:
1. **Edge-TTS** (bundled `portable-python/Scripts/edge-tts.exe`) — default, needs network
2. **Windows SAPI** (offline speech) — fallback when Edge-TTS unreachable
3. **Voicebox** (local GPU) — via `TTS_PROVIDER=voicebox` in `.env`
4. **Kokoro** (local) — via `VOICEBOX_ENGINE=kokoro`
5. **XTTS** — via `api-tts-provider.ts`
6. **Sine-tone fallback** — when all voice engines fail

The agentic pipeline's `generateAgenticVoiceovers()` in `src/agentic/media/tts.ts` uses the same chain via `generateVoiceovers()`.


## Key Gaps in the Agentic System

From analysis, the agentic system is more advanced structurally but has these gaps vs legacy:

1. **Video duration not auto-adjusted**: When a local video asset is bound, `acquire.ts` doesn't extract duration via `getVideoMetadata()` (legacy does this at `video-generator.ts` L219-222)
2. **MCP agentic_plan missing localAssets param**: The tool schema doesn't expose `localAssets` (add as `z.array(z.string()).optional()`)
3. **No per-scene trim in/out points**: `ScenePlan` lacks `trimIn`/`trimOut` fields
4. **No video fit mode**: `ScenePlan` lacks `visualFit` ('cover' | 'contain' | 'fill')
5. **No agentic scene editor**: `scene-editor.ts` is legacy-format only
6. **No asset caching**: Redownloads every run
7. **Render timeout**: Complex ffmpeg pipeline can take >5min for simple reels


## The `[Visual: ...]` Tag: Available in Both Systems

Parsed by the same `parseScript()` in `src/lib/script-parser.ts`:
```typescript
const visualMatches = [...line.matchAll(/\[Visual:?\s*(.*?)\]/gis)];
```

The agentic pipeline calls `parseScript()` during `buildPlan()`, so `[Visual: ...]` tags in the auto-generated or user-provided script work identically. Additionally, the agentic system has `localAssets` in `PipelineRequest` for direct file binding without tags.
