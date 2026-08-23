# AVG Agentic System Analysis — Legacy vs Agentic Code Comparison

> Covers `itsPremkumar/Automated-Video-Generator` at `C:\one\Automated-Video-Generator`
> Core finding: The agentic system (`src/agentic/` — 93 files) is a full video production OS layered on top of the legacy pipeline, inheriting `[Visual: ...]` tag support and adding much more.

## System Comparison

| Dimension | Legacy (`src/video-generator.ts`) | Agentic (`src/agentic/`) |
|-----------|----------------------------------|--------------------------|
| **Architecture** | Monolithic: Script→parse→fetch→render | 6-stage: Plan→Acquire→Verify→Decide(Gateway)→Gate→Render |
| **File count** | ~3 core files (~50KB) | ~93 files (~700KB) |
| **Entry points** | `npm run generate` → `cli.ts` → `pipelineAppService` | `runAgenticPipeline()` + 27 ops + plugins |
| **MCP surface** | 4 tool groups (input, job, output, admin) | Same 4 + `registerAgenticTools` + `registerOperationsTools` |
| **AI** | None | `AgentBrain` (free OpenRouter/Ollama), `AgentBackend` ('agent' = Hermes does reasoning) |

## Visual Tag / Local Asset Handling — Both Systems

### Legacy (`src/video-generator.ts` lines 199-224)
- `[Visual: filename.ext]` parsed by `parseScript()` in `src/lib/script-parser.ts`
- Checks `inputAssetPath(filename)` → copies to workspace if exists
- Extension detection → `type: 'video'` or `type: 'image'`
- **Extracts video duration** via `getVideoMetadata()` → sets `videoDuration`
- If file missing → falls back to stock media search

### Agentic (`src/agentic/orchestrator/pipeline.ts` lines 114-134 + `acquire.ts` lines 172-195)

**Two paths (now fixed to respect [Visual: ...] tags):**

1. **`[Visual: tag]` in script** — inherited via `buildPlan()` → calls `parseScript()` same as legacy. Sets `scene.localAsset` when file exists in `input/visuals/`.
2. **`localAssets: string[]` in `PipelineRequest`** — explicit array bound only to scenes WITHOUT an existing `localAsset`
3. **Auto-detection** — scans `input/visuals/` for media files and binds only to scenes WITHOUT `localAsset` (FIXED: previously overwrote all scenes)

**Acquire stage (`acquire.ts` L172-195):**
1. Checks `inputAssetPath(scene.localAsset)` (resolves to `input/visuals/`) → if exists, copies to workspace
2. Extension detection: `.mp4/.mov/.webm/.m4v` → `kind: 'video'`
3. Registers as `AssetCandidate` with source `'local-asset'`
4. Goes through all 6 stages + quality gates (X1-X16)

### ⚠️ Known Code Gaps in Agentic System (as of analysis)

| Gap | Location | Impact | Fix |
|-----|----------|--------|-----|
| **Video duration not auto-adjusted** | `acquire.ts` L172-195 | Scene stays at text-calculated duration; 30s video truncated to 4s | Add `getVideoMetadata()` call + update `scene.durationSec` after copy |
| **MCP `agentic_plan` tool missing `localAssets` param** | `register-agentic-tools.ts` L87-116 | Agent can't pass local assets via MCP stage tools | Add `z.array(z.string()).optional()` to tool input schema |
| **No per-scene trim in/out** | `ScenePlan` type (`types.ts`) | User video can't be trimmed before use | Add `trimIn?: number; trimOut?: number` to `ScenePlan` |
| **No video fit mode** | `ScenePlan` type / `render.ts` | 16:9 video in 9:16 reel gets stretched | Add `visualFit?: 'cover'\|'contain'\|'fill'` + ffmpeg scale/crop logic |
| **No video asset preview in MCP** | `register-agentic-tools.ts` | Agent can't preview downloaded video candidates | Add `preview_asset_video` tool (extract ffmpeg thumbnail) |

### ✅ Resolved in This Session

| Issue | Fix |
|-------|-----|
| **No `script` field on PipelineRequest** | Added `script?: string` to `PipelineRequest` type + `req.script ??` check in `pipeline.ts` |
| **Auto-detect overwrites `[Visual: ...]` localAsset** | Changed `forEach` to loop with `if (!s.localAsset)` guard |
| **No simple CLI for agentic pipeline** | Created `agentic-cli.ts` + `npm run generate:agentic` + `agentic-scripts.json` format |
| **`.env` not loaded in agentic CLI** | Added `import 'dotenv/config'` to `agentic-cli.ts` |
| **Voicebox/Kokoro not wired in agentic** | Set `.env` to `TTS_PROVIDER=voicebox` + correct Kokoro preset profile |

## Platform Detection

Before claiming anything about the codebase:
1. **Always confirm the project path** — user corrected from `job-readiness/Automated-Video-Generator` to `C:\one\Automated-Video-Generator`
2. **Check for `src/agentic/`** — if it exists, the agentic system is present. If not, only legacy exists.
3. **Map the REAL surface** — grep for `server\.(registerTool|tool)\(` and `export.*function` in agentic modules

## MCP Tool Surface (at `C:\one\Automated-Video-Generator`)

From `src/mcp-server.ts`:
- `registerInputTools` — `write_input_script`, `read_input_script`, `delete_input_script`, `validate_input_script`, `upload_asset`, `delete_asset`
- `registerJobTools` — `generate_video`, `get_video_status`, `run_pipeline_command`, `list_jobs`
- `registerAgenticTools` — `agentic_plan`, `agentic_acquire`, `agentic_verify_all`, `list_pending_assets`, `get_asset_preview`, `approve_asset`, `reject_asset`, `replace_asset`, `agentic_gate`, `agentic_render`
- `registerOperationsTools` — 27+ single-task ops (merge, trim, crop, captions, music, etc.)
