# Visual Tag (`[Visual: ...]`) Architecture

## Summary

The `[Visual: filename-or-keywords]` tag is the **primary interface** for specifying per-scene visuals in the Automated-Video-Generator pipeline. It works identically in the legacy (web/CLI) and agentic (MCP) paths — both converge on the same `script-parser.ts` → `video-generator.ts` core.

## Tag Format

```
[Visual: <value>]
```

`<value>` is either:
- **A filename** from `input/input-assets/` (e.g., `my-image.jpg`, `intro.mp4`) — resolves to a local asset
- **A keyword string** (e.g., `tech office blue`, `nature landscape`) — drives stock media search
- If the file exists in `input/input-assets/`, it's used as a **local asset**. If not, the text falls through as **search keywords** for stock media (Pexels → Pixabay → Free Sources → Openverse).

Multiple tags can appear on one line; tags with no narration text between them each produce independent scenes.

## Data Flow

### 1. Script Parsing (`src/lib/script-parser.ts`)

```
[Visual: my-image.jpg]  This is narration text.
   ↓
parseScript() → Scene {
    localAsset: "my-image.jpg"    // set if fs.existsSync(inputAssetPath(tag))
    voiceoverText: "This is narration text."
    searchKeywords: ["my-image.jpg"]  // fallback keywords
    showText: undefined
}
```

Key logic (lines 145-260):
- Regex: `/\[Visual:?\s*(.*?)\]/gis` extracts the tag value
- `inputAssetPath(tag)` builds the full path under `input/input-assets/`
- `fs.existsSync()` check — if the file physically exists, `localAsset` is set
- The `[Visual: ...]` tag text is **stripped** from `voiceoverText` so it never appears in subtitles/TTS
- Tags on their own line (no narration) get `voiceoverText: ''` and default 5s duration

### 2. Visual Resolution (`src/video-generator.ts`, lines 199-224)

When `scene.localAsset` is set:

```
localAsset exists?
  → copy from input/input-assets/<file> → workspace/visuals/<file>
  → detect extension:
      .mp4, .mov, .webm, .m4v → type: 'video' (extract videoDuration via getVideoMetadata)
      .jpg, .jpeg, .png, .webp, .gif → type: 'image'
  → visual = { type, url: "local://<file>", localPath: "public/jobs/<id>/visuals/<file>" }
```

When `scene.localAsset` is NOT set:
- Falls to `fetchVisualsForScene(searchKeywords)` — stock media chain

### 3. Asset Directory

| Path | Purpose |
|------|---------|
| `input/input-assets/` | User places their own images/videos here |
| `input/INPUT_FORMAT.md` | Full documentation with examples |

## Supported Extensions

| Type | Extensions | Behavior |
|------|-----------|----------|
| **Image** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` | Static overlay for scene duration |
| **Video** | `.mp4`, `.mov`, `.webm`, `.m4v` | Plays for its own duration; auto-trim via `trimAfterFrames` (from `getVideoMetadata`) |

## Agentic (MCP) Path

The MCP server (`src/mcp-server.ts`) uses the **exact same** pipeline under the hood. Differences:

| Capability | Legacy (CLI/Web) | Agentic (MCP) |
|-----------|-----------------|--------------|
| Asset placement | Manually copy files to `input/input-assets/` | **`upload_asset`** tool — base64 upload (50MB limit) |
| Script definition | Edit `input/input-scripts.json` manually | **`write_input_script`** tool writes same JSON |
| Script execution | `npm run generate` or web UI | **`generate_video`** tool → `pipelineAppService` → same `video-generator.ts` |
| Asset discovery | `ls input/input-assets/` | **`input://assets`** resource lists files |
| Schema validation | Manual | `videoScriptSchema` (zod) validates `[Visual: query]` explicitly |

**The `[Visual: ...]` tag resolution is 100% identical** — both paths call `parseScript()` → `video-generator.ts`.

## Scene Interface

From `src/lib/script-parser.ts`:

```typescript
interface Scene {
    sceneNumber: number;
    duration: number;
    visualDescription: string;   // "Visual for: <tag>"
    voiceoverText: string;       // Narration (tag-stripped)
    searchKeywords: string[];    // Fallback keywords
    localAsset?: string;         // Set if file exists in input-assets
    showText?: boolean;
    visual?: {
        type: 'video' | 'image';
        url: string;             // "local://<filename>" for local assets
        localPath: string;       // Relative public path
        videoDuration?: number;  // Only for video type
    };
}
```

## Pitfalls

1. **File must exist before parse** — `fs.existsSync()` checks at script-parse time, not at render time. If you `upload_asset` after `write_input_script`, the tag won't resolve as a local asset. Upload assets first.
2. **No symlinks** — the copy in step 2 is a real `copyFileSync`, not a symlink. Large videos double disk usage during the pipeline workspace copy.
3. **Case sensitivity on Windows** — MSYS/bash is case-insensitive for paths but the regex keyword extraction is lowercase-normalized. `my-Image.jpg` and `my-image.jpg` both work on Windows but could break on Linux deploy.
4. **Video durations** — `getVideoMetadata()` uses ffprobe. If ffprobe is missing, `videoDuration` stays undefined and the scene defaults to text-derived duration, which may clip the video.
5. **Tag with no narration** — A bare `[Visual: x.mp4]` that resolves locally will create a 5s scene even if the video is longer. The Remotion composition handles the video trim, but the scene duration in `scene-data.json` won't match.
