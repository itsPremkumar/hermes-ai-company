# Agentic CLI Bridge — Concrete Implementation

Based on the Automated-Video-Generator project (2026-07-21), this reference
covers the exact implementation of a simple JSON-input CLI bridge for an
agentic video pipeline.

## Files Created/Modified

| File | Purpose |
|------|---------|
| `src/agentic/orchestrator/types.ts` | Added `script?: string` to `PipelineRequest` |
| `src/agentic/orchestrator/pipeline.ts` | Custom script used first if provided; auto-detect skips scenes with existing `localAsset` |
| `src/adapters/cli/agentic-cli.ts` | CLI runner — reads JSON → calls pipeline → renders |
| `input/scripts/agentic-scripts.json` | User-facing script input (same folder as legacy `input-scripts.json`) |
| `input/scripts/agentic-scripts.example.json` | Example with docs |
| `package.json` | Added `"generate:agentic"` npm script |

## PipelineRequest — Script field

```typescript
export interface PipelineRequest {
    script?: string;         // custom script with [Visual: ...] tags
    topic: string;           // fallback when no script provided
    title: string;
    // rest unchanged
}
```

## Pipeline priority order (pipeline.ts ~L75)

```typescript
const script =
    req.script ??                                          // custom script first
    (cfg.writeScript ? await cfg.writeScript(req.topic, req.title) : null) ??
    (await bridge.completeJSON(...))?.script ??
    writeScriptHeuristic(req.topic, req.title);
```

## Auto-detect — Only scenes WITHOUT existing localAsset

Changed local asset binding loops from overwriting ALL scenes to only
binding scenes without `localAsset` from `parseScript()`:

```typescript
let li = 0;
for (const s of plan.scenes) {
    if (!s.localAsset) {
        s.localAsset = req.localAssets[li % req.localAssets.length];
        li++;
    }
}
```

## dotenv loading — The #1 silent failure

`npx tsx` does NOT auto-load `.env`. Must explicitly import:

```typescript
import 'dotenv/config';   // FIRST import in runner
```

Without this, `TTS_PROVIDER`, `VOICEBOX_API_URL` are undefined; pipeline falls
through to Edge-TTS → Windows SAPI fallback.

## Gate passes but no video rendered

`runAgenticPipeline()` does NOT render the final MP4. Render must be called
SEPARATELY:

```typescript
const result = await runAgenticPipeline(req, onProgress);
if (result.gate.pass) {
    const finalMp4 = await renderAgenticSlideshow(result, {
        outPath: path.join(outDir, `${title}.mp4`),
        crossfadeSec: 0.3,
        burnCaptions: true,
    });
}
```

## JSON input format (input/scripts/agentic-scripts.json)

Placed in `input/scripts/` to match legacy `input/scripts/input-scripts.json`:

```json
[{
  "id": "avs-agentic-reel",
  "title": "My Video",
  "script": "Scene one. [Visual: logo.png]\nScene two. [Visual: github-profile.png]\nScene three. [Visual: ai voice coding]",
  "orientation": "portrait",
  "voice": "en-US-GuyNeural",
  "hookFirst": true,
  "variablePacing": true,
  "backend": "agent",
  "candidatesPerAsset": 2
}]
```

### Visual tag behavior

| Tag | Behavior |
|-----|----------|
| `[Visual: logo.png]` | File exists in `input/visuals/` → local asset |
| `[Visual: ai coding]` | No matching file → stock keyword search |

### Voice provider routing (voice-generator.ts L362-393)

| TTS_PROVIDER | Route | Server |
|--------------|-------|--------|
| `edge` (default) | Edge-TTS binary | Bundled python |
| `voicebox` | POST /speak with profile+engine | VOICEBOX_API_URL (:17493) |
| `kokoro` | OpenAI-compatible /v1/audio/speech | OPENAI_LOCAL_TTS_URL (:8880) |
| `xtts` | XTTS API server | XTTS_API_URL (:8020) |

For `voicebox`/`kokoro`/`xtts` the `voice` field in the JSON is ignored — the
server uses the profile's preset voice.

### Voicebox/Kokoro .env config

```env
TTS_PROVIDER=voicebox
VOICEBOX_API_URL=http://127.0.0.1:17493
VOICEBOX_ENGINE=kokoro
VOICEBOX_PROFILE_ID=<kokoro-preset-profile-id>
```

Server must be running (`curl http://127.0.0.1:17493/health`). Profile must be
a Kokoro preset profile (voice_type="preset", preset_engine="kokoro").

## Run

```bash
npm run generate:agentic
# or
npx tsx src/adapters/cli/agentic-cli.ts
```
