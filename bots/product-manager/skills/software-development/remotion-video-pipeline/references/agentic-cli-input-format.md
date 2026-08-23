# Agentic CLI Wrapper & JSON Input Format

## Overview

The agentic pipeline (6-stage: Plan→Acquire→Verify→Decide→Gate→Render) is exposed
through a **programmatic TypeScript API** (`runAgenticPipeline({ topic, title, ... })`).
This reference documents the **JSON-input CLI wrapper** (`agentic-cli.ts`) that lets
users write a simple JSON file with `[Visual: ...]` tags and run:

```bash
npm run generate:agentic
# or: npx tsx src/adapters/cli/agentic-cli.ts
```

The CLI loads `.env` via `import 'dotenv/config'` so `TTS_PROVIDER`, `VOICEBOX_*`,
and API keys are available to the pipeline.

## File Locations

```
input/scripts/
├── agentic-scripts.json          ← user jobs (same folder as legacy input-scripts.json)
├── agentic-scripts.example.json  ← reference example
```

## JSON Input Format

```json
[
  {
    "id": "my-video",
    "title": "My Cool Video",
    "script": "Scene one text. [Visual: logo.png] [Transition: slide] [Grade: warm]\nScene two text. [Visual: typing code] [KenBurns: off]\nScene three text. [Visual: demo.mp4] [Trim: 00:05-00:10]",

    "orientation": "portrait",
    "voice": "en-US-GuyNeural",
    "language": "english",
    "hookFirst": true,
    "variablePacing": true,
    "backend": "agent",
    "candidatesPerAsset": 2,
    "backgroundMusic": "bgm.mp3",
    "musicVolume": 0.15,
    "topic": "Fallback topic when no script provided",
    "musicQuery": "background corporate"
  }
]
```

### Required fields
- `title` — video title (becomes output filename)
- `script` OR `topic` — if `script` is provided it's used directly with `[Visual: ...]` tag parsing.
  If omitted, the AgentBrain auto-generates a script from `topic`.

### New in this session: Per-Scene Inline Tags

These tags are parsed from within the **`script` field** (alongside `[Visual: ...]`).
They apply only to the scene (sentence) they appear in:

| Tag | Values | Effect |
|-----|--------|--------|
| `[Transition: fade]` | `fade`, `slide`, `zoomblur`, `cut` | Override the transition INTO this scene |
| `[Grade: warm]` | `neutral`, `warm`, `cool`, `cinematic`, `vivid` | Override the color grade for this scene |
| `[KenBurns: off]` | `on`, `off`, `true`, `false` | Disable/enable the KenBurns zoom effect on this image |
| `[Trim: 00:05-00:10]` | `mm:ss-mm:ss` | Trim a local video clip to this time window |
| `[Style: top]` | `top`, `bottom`, `center` | Caption position override (default: bottom) |
| `[Color: yellow]` | `white`, `yellow`, `blue`, `red`, `green`, `cyan`, `magenta`, `black`, `pink`, `orange` | Caption text color override |
| `[FadeIn: 0.5]` | float (seconds) | Audio fade-in duration at scene start |
| `[FadeOut: 0.5]` | float (seconds) | Audio fade-out duration at scene end |

**How it works:**
1. `src/lib/script-parser.ts` matches regexes like `/\[Transition:?\s*(fade|slide|zoomblur|cut)\]/is`
2. The tag is stripped from `voiceoverText` (same pattern as `[Visual: ...]`)
3. Values flow through `Scene.transition/grade/kenBurns/trimStart/trimEnd` → `ScenePlan` → `render.ts`
4. In render: `stylePlan` overrides are applied, so user tags WIN over the auto hash-based style engine

**Example script with all tags:**\n```\nThis scene fades in with warm colors and top captions. [Visual: logo.png] [Transition: fade] [Grade: warm] [Style: top] [FadeIn: 0.3]\nFast cut with vivid colors, center captions in yellow. [Visual: action] [Transition: cut] [Grade: vivid] [Style: center] [Color: yellow]\nKenBurns disabled, audio fades out. [Visual: static-bg.jpg] [KenBurns: off] [FadeOut: 0.5]\nOnly show seconds 5-10 of this video. [Visual: demo.mp4] [Trim: 00:05-00:10]\n```

### New in this session: JSON-level fields

#### `language` — Auto-voice selection

Set a language code (e.g. `"tamil"`, `"hindi"`, `"spanish"`, `"english"`) to
auto-select the correct TTS voice from the `LANGUAGE_DEFAULTS` table in
`src/lib/voice-data.ts`:

```typescript
LANGUAGE_DEFAULTS = {
  tamil:    'ta-IN-PallaviNeural',
  hindi:    'hi-IN-SwaraNeural',
  spanish:  'es-ES-ElviraNeural',
  french:   'fr-FR-DeniseNeural',
  english:  'en-US-JennyNeural',
  // ...
};
```

Only applies when `voice` is NOT explicitly set (explicit voice wins).

#### `backgroundMusic` — Local music file override

Path to a file in `input/visuals/` (e.g. `"bgm.mp3"`). When set, the pipeline
uses this file as background music instead of searching for free stock music.

#### `musicVolume` — Background music volume

Float 0.0–1.0 (default 0.18). Sets `process.env.AUDIO_FULL_LEVEL` which the\nffmpeg ducking filter reads.\n\n#### `intro` — Branded title card\n\nAn object `{title, subtitle?, durationSec?}`. When provided, the renderer\ncreates a branded title card before the first scene. Example:\n\n```json\n\"intro\": {\"title\": \"My Video\", \"subtitle\": \"Open Source • Free • Agentic\", \"durationSec\": 3}\n```\n\n`durationSec` defaults to 3s if omitted.\n\n#### `outro` — Branded CTA card\n\nAn object `{ctaText, showSubscribe?, hashtags?, durationSec?}`. Creates a CTA\ncard after the last scene. Example:\n\n```json\n\"outro\": {\"ctaText\": \"Star on GitHub\", \"showSubscribe\": true, \"hashtags\": [\"#opensource\"], \"durationSec\": 3}\n```\n\n- `ctaText` (required) — call-to-action text\n- `showSubscribe` (optional) — show a subscribe/CTA button\n- `hashtags` (optional) — array of hashtags to display\n- `durationSec` (optional, default 3)

### `[Visual: ...]` tag behavior

| Tag example | File exists in `input/visuals/`? | Result |
|---|---|---|
| `[Visual: logo.png]` | ✅ Yes | `localAsset = 'logo.png'` → local file used |
| `[Visual: github-profile.png]` | ✅ Yes | `localAsset = 'github-profile.png'` |
| `[Visual: ai coding typing]` | ❌ No | `searchKeywords = ['ai','coding','typing']` → stock media fetched |
| `[Visual: demo.mp4]` | ✅ Yes + `[Trim: 05-10]` | Local video trimmed to 5-10s |

### Optional fields (previously documented)
- `orientation` — `'portrait'` (default, 9:16) or `'landscape'` (16:9)
- `voice` — TTS voice name. When `TTS_PROVIDER=voicebox` in `.env`, the voice field
  is ignored and the Kokoro preset profile voice is used instead.
- `backend` — `'agent'` (default, uses free LLM via AgentBrain) or `'vision'`
- `hookFirst` — reorder scenes so the most engaging line opens (default: true)
- `variablePacing` — scientific timing + text-length duration (default: true)
  Now also scales duration to word count: `max(breathing_min, min(words/2.5, 8))`
  So a 50-word scene gets 8s instead of the old flat 5s.
- `candidatesPerAsset` — stock candidates to fetch per scene (default: 2)

## Architecture: CLI → Pipeline Flow

```
agentic-scripts.json
  │
  ▼
src/adapters/cli/agentic-cli.ts
  │  import 'dotenv/config' ← loads .env
  │  maps language→voice (LANGUAGE_DEFAULTS)
  │  passes backgroundMusic, musicVolume
  │
  ▼
src/agentic/orchestrator/pipeline.ts — runAgenticPipeline({ ... })
  │
  ├─ Line 76: script = req.script ?? ...         ← custom script used FIRST
  │
  ├─ buildPlan(script) → parseScript(script)      ← [Visual:...] + new tags parsed
  │    ├── file exists → localAsset = filename
  │    ├── [Transition:] → scene.transition
  │    ├── [Grade:] → scene.grade
  │    ├── [KenBurns:] → scene.kenBurns
  │    └── [Trim:] → scene.trimStart / trimEnd (converted to seconds)
  │
  ├─ Auto-detect input/visuals/ — skips scenes with existing localAsset
  │
  ├─ Acquire → Verify → Decide → Gate
  │    fetchMusic: checks req.backgroundMusic first
  │
  ├─ Voiceover (via voice-generator.ts, respects TTS_PROVIDER)
  │
  └─ render.ts — renderAgenticSlideshow(result, { ... })
       │
       ├─ Per-scene overrides: transition/grade/kenBurns from ScenePlan
       │    WIN over auto hash-based style-engine values
       │
       ├─ Logo watermark: auto-applied via pass3 ffmpeg overlay
       │    Looks for assets/logos/logo-automation.png, public/logo.png,
       │    or input/visuals/logo-automation.png
       │
       └─ Duration: word-count-aware sizing (words / 2.5 wps, min 2s, max 8s)
       │
       ▼
     output/{id}/{title}.mp4 (+ multi-aspect exports + subtitles + archive)
```

## Key Implementation Details

### 1. `script` field on PipelineRequest
- **File**: `src/agentic/orchestrator/types.ts`
- Added `script?: string` before `topic`/`title`.
- When provided, the pipeline skips AgentBrain auto-generation.

### 2. Pipeline respects parseScript-set localAsset
- **File**: `src/agentic/orchestrator/pipeline.ts` (lines 115-135)
- Auto-detect only binds scenes WITHOUT existing localAsset
- This is critical: `parseScript()` sets `localAsset` from `[Visual: logo.png]` → real file.

### 3. Per-scene inline tags in script-parser.ts
- **File**: `src/lib/script-parser.ts`
- Tags are extracted per-line with regex matches, cleaned from voiceoverText.
- Hoisted variables (`sceneTransition`, `sceneGrade`, etc.) so the trailing
  pending-visual-cue scene block can reference them.

### 4. Per-scene override in render.ts
- **File**: `src/agentic/orchestrator/render.ts` (lines ~329-334)
- After `computeStylePlan()`, an overlay loop applies ScenePlan values:
  ```typescript
  for (const sc of stylePlan.scenes) {
      const scene = res.plan.scenes[sc.sceneIndex];
      if (scene?.transition) sc.transitionIn = scene.transition as any;
      if (scene?.grade) sc.grade = scene.grade as any;
  }
  ```
- KenBurns per-scene: checks `res.plan.scenes[i]?.kenBurns` at both xfade and segment paths.

### 5. backgroundMusic override
- **File**: `src/agentic/orchestrator/pipeline.ts` (fetchMusic callback)
- If `req.backgroundMusic` is set and `inputAssetPath(req.backgroundMusic)` exists,
  returns that file directly instead of searching free music.

### 6. Logo overlay (pass3)
- **File**: `src/agentic/orchestrator/render.ts` (after pass2 audio mixing)
- Searches for logo in priority order: `assets/logos/logo-automation.png` →
  `public/logo.png` → `input/visuals/logo-automation.png`
- Runs `ffmpeg -i out.mp4 -i logo.png -filter_complex overlay=W-w*0.12-20:H-h*0.12-20`
- Best-effort: if logo not found or overlay fails, render continues.

### 7. Duration from text length
- **File**: `src/agentic/pipeline/plan.ts` (applyProEdits)
- Blends breathing rhythm (hook=3s, body=5/3, close=5) with word-count:
  ```
  words = voiceoverText.split(/\s+/).length
  wordDur = words / 2.5    // speaking rate
  duration = max(breathing_min, min(wordDur, 8))
  ```

### 8. Language → voice resolution
- **File**: `src/agentic/orchestrator/pipeline.ts` (before buildPlan call)
- `LANGUAGE_DEFAULTS[language]` used when no explicit `voice` set.
- Same table as legacy pipeline.

### 9. musicVolume support\n- **File**: `src/agentic/orchestrator/pipeline.ts` (after buildPlan)\n- Sets `process.env.AUDIO_FULL_LEVEL` which render.ts reads for the ducking filter.\n\n### 10. Intro/Outro cards in render\n- **Files**: `src/agentic/orchestrator/types.ts` (PipelineRequest), `src/agentic/orchestrator/render.ts`\n- `intro` and `outro` are passed through on PipelineRequest as inline objects.\n- In `render.ts`, when `opts.intro` is set, a branded title card is generated (colored\n  background + title text + optional subtitle). Same for `opts.outro` with CTA text + hashtags.\n- Intro/outro cards are rendered as separate ffmpeg segments before/after the scene sequence,\n  then concatenated via concat demuxer.\n\n### 11. Per-scene caption position (Style) and color\n- **Files**: `src/lib/script-parser.ts` → `src/agentic/types.ts` (ScenePlan) → `src/agentic/orchestrator/render.ts`\n- `[Style: top]` maps to `ScenePlan.captionStyle` → controls `yExpr` in drawtext filter:\n  - `top` → `y=h/10` (near top of frame)\n  - `center` → `y=(h-text_h)/2` (vertical center)\n  - `bottom` → default theme y position (default)\n- `[Color: yellow]` maps to `ScenePlan.captionColor` → overrides `fontcolor` in drawtext filter.\n  All 10 named colors are supported: white, yellow, blue, red, green, cyan, magenta, black, pink, orange.\n\n### 12. Per-scene audio fade\n- **Files**: Same path as above + `src/agentic/orchestrator/render.ts` (segment audio chain)\n- `[FadeIn: 0.5]` adds `afade=t=in:st=0:d=0.5` to the per-scene audio filter\n- `[FadeOut: 0.5]` adds `afade=t=out:st=<dur-0.5>:d=0.5` at the end of the scene's audio\n- Both can be combined: `[FadeIn: 0.5] [FadeOut: 0.5]`

## Verification

```bash
# TypeScript
npm run typecheck                          # must be 0 errors

# Lint
npx eslint src/adapters/cli/agentic-cli.ts --no-ignore  # 0 errors, 0 warnings

# JSON validity
python -c "import json; json.load(open('input/scripts/agentic-scripts.json'))"

# Run
npm run generate:agentic                   # exit 0 on success
```

## npm scripts
```json
"generate": "tsx src/cli.ts",                           # legacy pipeline
"generate:agentic": "tsx src/adapters/cli/agentic-cli.ts"  # agentic pipeline
```
