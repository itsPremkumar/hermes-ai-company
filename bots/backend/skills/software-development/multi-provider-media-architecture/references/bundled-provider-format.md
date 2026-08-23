# Bundled Provider — Offline Track Format

## Directory Structure

```
input/bgm/__bundled__/
├── ambient_piano.mp3       # 60s ambient track
├── lofi_chill.mp3          # 60s lo-fi
├── cinematic_drone.mp3     # 60s cinematic drone
├── upbeat_electronic.mp3   # 60s upbeat
├── ambient_nature.mp3      # 60s nature ambient
└── metadata.json           # Track metadata
```

## Metadata Schema

```json
{
  "filename": "ambient_piano.mp3",
  "title": "Ambient Piano",
  "creator": "Procedural",
  "genre": "ambient",
  "mood": ["calm", "meditation", "relaxing"],
  "durationSec": 60,
  "format": "mp3"
}
```

## Critical Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | string | **Yes** | Must match actual file in directory |
| `title` | string | No | Display name; derived from filename if missing |
| `creator` | string | No | Attribution |
| `genre` | string | No | Used for genre-based filtering |
| `mood` | string[] | No | **Property name is `mood` (singular)** — `moods` (plural) silently breaks filtering |
| `durationSec` | number | No | Used by processing pipeline |
| `format` | string | No | File extension (mp3, wav, ogg) |

## Field Name Pitfall

The provider accesses `meta.mood` (singular). If you write `"moods"` in the JSON (plural), `meta.mood` will be `undefined`, and the mood-filtering logic on line 83-85 of `bundled.ts` silently passes all tracks:

```typescript
// bundled.ts line 83-85:
if (query.mood !== 'any' && meta?.mood?.length) {
    if (!meta.mood.some(m => m.toLowerCase() === query.mood)) continue;
}
```

When `meta.mood` is `undefined`, `meta?.mood?.length` is `undefined` (falsy), so the mood filter is **skipped** entirely.

## Generating Bundled Tracks

Use the `scripts/generate-bundled.js` utility with `ffmpeg-static`:

```bash
node scripts/generate-bundled.js
```

The generator:
1. Creates 5 ambient MP3s (piano, lofi, cinematic, upbeat, nature)
2. Each is 60 seconds, 128kbps MP3 (~940KB each)
3. Also creates `metadata.json`
