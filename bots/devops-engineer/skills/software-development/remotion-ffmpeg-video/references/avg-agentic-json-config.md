# Agentic JSON Config Fields — Wiring Reference

> How the `agentic-scripts.json` fields flow through the pipeline (language, backgroundMusic, musicVolume, duration-from-text).

## Field Wiring Map

```
agentic-scripts.json  →  agentic-cli.ts  →  PipelineRequest  →  pipeline.ts  →  plan.ts / render.ts
```

### `language` → voice auto-selection

- **JSON:** `"language": "tamil"` (no `voice` field)
- **CLI (agentic-cli.ts):** Passes `req.language = job.language`
- **Pipeline (pipeline.ts):** Resolves `LANGUAGE_DEFAULTS[req.language.toLowerCase().trim()]` → e.g. `"ta-IN-PallaviNeural"`
- **Only when `req.voice` is NOT set** — `voice` takes priority
- **Import:** `import { LANGUAGE_DEFAULTS } from '../../lib/voice-data.js'`

```typescript
const resolvedVoice =
    req.language && !req.voice
        ? LANGUAGE_DEFAULTS[req.language.toLowerCase().trim()]
        : req.voice;
// Then pass resolvedVoice to buildPlan({ voice: resolvedVoice ?? 'default' })
```

### `backgroundMusic` → local file override

- **JSON:** `"backgroundMusic": "my-song.mp3"`
- **Pipeline (pipeline.ts fetchMusic callback):** Before calling `resolveFreeBackgroundMusic()`, check `inputAssetPath(req.backgroundMusic)`
- **Resolution:** `inputAssetPath(...)` → `input/visuals/<filename>`
- **If found:** Return a single-item track array (skips stock music search entirely)
- **If not found:** Warn and fall through to normal `resolveFreeBackgroundMusic`

```typescript
if (req.backgroundMusic) {
    const bgmPath = inputAssetPath(req.backgroundMusic);
    if (fs.existsSync(bgmPath)) {
        const normalized = normalizeAudio(bgmPath);
        return [{
            url: '', localPath: normalized || bgmPath,
            source: 'local', license: 'CC-BY (user provided)', licenseUrl: '',
        }];
    }
}
```

### `musicVolume` → render duck level

- **JSON:** `"musicVolume": 0.15`
- **Pipeline (pipeline.ts):** Sets `process.env.AUDIO_FULL_LEVEL = String(req.musicVolume)` before render
- **Render (render.ts):** Reads `AUDIO_DUCK_LEVEL` (speech-active) and `AUDIO_FULL_LEVEL` (silence) — both env vars
- **Default (unset):** duck=0.06, full=0.18

```typescript
if (req.musicVolume != null) {
    process.env.AUDIO_FULL_LEVEL = String(req.musicVolume);
}
```

### Duration from text length (plan.ts `applyProEdits`)

- **Location:** In the `variablePacing` block of `applyProEdits()`
- **Algorithm:** Blend breathing minimum + word-count ideal

```typescript
// Start with breathing/minimum duration
let minDur = /* hook=3, body=5/3, close=5 */;

// Duration from text length (~2.5 words/sec speaking rate)
const words = (s.voiceoverText || '').split(/\s+/).filter(Boolean).length;
const wordDur = words / 2.5;

// Blend: at least the breathing minimum, at most 8 seconds
s.durationSec = Math.max(minDur, Math.min(Math.round(wordDur), 8));
```

**Speaking rate:** 2.5 words/second (empirical; matches typical TTS output)
**Min:** 3s (hook) / 2s (any scene)
**Max:** 8s (capped to prevent one scene dominating)
**Example:** 5-word scene → 2s → blended with minDur=3 → 3s. 50-word scene → 20s → capped at 8s.

## ⚠ Common Pitfall: `.env` Not Loaded

When creating a NEW standalone CLI entry point for an existing pipeline:

```typescript
// BAD: .env is NOT loaded because pipeline.ts doesn't import dotenv
npx tsx src/path/to/new-cli.ts

// GOOD: import 'dotenv/config' at the top of the CLI entry
import 'dotenv/config';
```

The existing pipeline's main code (`pipeline.ts`, `video-generator.ts`) does **not** import `dotenv` — it reads `process.env` and expects the caller to have loaded it. The legacy `cli.ts` works because the import chain passes through `config.ts` which calls `dotenv.config()`. A new entry point must explicitly load dotenv.

**Fix:** Add `import 'dotenv/config'` as the first import in your CLI runner.

## PipelineRequest type (types.ts)

Add new fields to the `PipelineRequest` interface:

```typescript
language?: string;
backgroundMusic?: string;
musicVolume?: number;
```

## AgenticCliJob type (agentic-cli.ts)

Add matching fields to the CLI interface for type safety + JSON schema documentation.
