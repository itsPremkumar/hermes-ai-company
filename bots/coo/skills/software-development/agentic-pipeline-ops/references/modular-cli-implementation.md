# Modular Pipeline CLI — Reference Implementation

**Project:** Automated-Video-Generator (`C:\one\Automated-Video-Generator`)
**File:** `src/adapters/cli/agentic-modular.ts`

## Architecture Overview

The modular CLI decomposes the monolithic agentic pipeline into 6 independent subcommands:

```
agentic-modular.ts
├── plan        → parseScript + buildPlan → plan.json
├── visuals     → acquireAssets → render-manifest.json + assets/
├── voice       → generateAgenticVoiceovers → audio/*.wav
├── render      → renderAgenticSlideshow → output/*.mp4
├── edit        → modify single scene → selective re-render
└── list        → workspace inspection
```

## Key Patterns

### 1. Stage Independence via Workspace

Each stage reads/writes the shared workspace at `workspace/jobs/<jobId>/`.

```
workspace/jobs/<jobId>/
├── plan.json              # Stage 1 output, Stages 2-4 input
├── job-meta.json          # Config snapshot (preserves ALL settings)
├── render-manifest.json   # Stage 2 output, Stage 4 input
├── scene-data.json        # Scene metadata
├── audio/                 # Stage 3 output: scene_N_voice.wav
│   ├── scene_1_voice.wav
│   ├── scene_2_voice.wav
│   └── ...
└── assets/                # Stage 2 output: downloaded media
    ├── scene_1.jpg
    ├── scene_2.mp4
    └── ...
```

### 2. Dynamic Imports for Lazy Loading

Each stage function uses `await import(...)` to load its dependencies only when needed:

```typescript
async function runPlan(cliArgs: CliArgs) {
    const { parseScript } = await import('../../lib/script-parser.js');
    const { buildPlan, applyProEdits } = await import('../../agentic/pipeline/plan.js');
    const { AgentBrain } = await import('../../agentic/ai/brain.js');
    // ... stage logic
}
```

This keeps the startup fast and avoids circular dependency issues.

### 3. Scene Editor — Selective Re-render

The edit subcommand modifies only the target scene and optionally re-renders only that segment:

```typescript
// Load plan, modify scene N
const scene = plan.scenes.find((s: any) => s.sceneNumber === sceneNum);
scene.voiceOverride = newVoice;
scene.volumeOverride = 0.8;

// Regenerate TTS for single scene
const singleScenePlan = { ...plan, scenes: [scene] };
await generateAgenticVoiceovers(singleScenePlan, workspace, voice);

// Re-download visual for single scene
const dl = await downloadMedia(url, ws.assetsDir, `scene_${sceneNum}.jpg`);

// Re-render single scene segment
const result = { plan, workspace, manifest: { assets: [sceneAsset] }, voiceovers: { scenes: [sceneVo] } };
await renderAgenticSlideshow(result, { outPath: editOut, crossfadeSec: 0, ... });
```

### 4. Workspace Inspection (`list`)

The `list` subcommand reads `plan.json` and `job-meta.json` to show a comprehensive scene-by-scene breakdown:

```
Scenes (5):
     1. This is a test of the modular pipeline.              [3.0s]
       🖼 technology abstract
       🏷  tr=fade gr=warm
     2. Each stage runs independently.                       [5.0s]
       🖼 computer circuit board
       🏷  kb=false
     3. You can edit single scenes.                          [3.0s]
       🖼 scene_3.jpg
       🏷 en-IN-ValluvarNeural vol=0.8 style=center (cyan)

Stages:
    Plan:     ✅
    Visuals:  ✅
    Voice:    ✅
    Render:   ✅
```

## Pitfalls

### Dynamic Import Paths (relative to caller, not cwd)

All `await import(...)` paths are relative to the source file (`src/adapters/cli/agentic-modular.ts`), NOT the project root or cwd. Use `../../agentic/...` not `../agentic/...`.

### Argument Parsing for Boolean Flags

When `--render false` is passed as a CLI argument, it becomes the STRING `"false"` not boolean `false`. Use `cliArgs.render !== 'false'` or normalize booleans explicitly:

```typescript
const renderEnabled = cliArgs.render !== false && String(cliArgs.render) !== 'false';
```

### DownloadMedia Return Type

`downloadMedia()` from `visual-fetcher.js` returns a `DownloadResult` object, not a string. Extract the `.path` property:

```typescript
const dl = await downloadMedia(url, dir, filename);
const localPath = typeof dl === 'string' ? dl : (dl as any).path || '';
```

## Testing Sequence (verified 2026-07-22)

```bash
# 1. Plan stage
npm run agentic:plan
# → "Plan ready: 5 scenes"

# 2. Visuals stage
npm run agentic:visuals
# → "Acquired 7 candidates, Manifest: 6 assets"

# 3. Voice stage
npm run agentic:voice
# → "Voiceover generated — 5 scene(s)"

# 4. Render stage
npm run agentic:render
# → "Rendered: output/...mp4 (1947 KB)"

# 5. Inspect workspace
npm run agentic:list

# 6. Edit scene 3
npm run agentic:edit --scene 3 --visual "rocket launch" --voice en-IN-ValluvarNeural --volume 0.8

# 7. Full re-render after edits
npm run agentic:render
```
