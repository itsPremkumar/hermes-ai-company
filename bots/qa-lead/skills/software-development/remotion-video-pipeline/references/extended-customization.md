# Agentic Pipeline — Extended Customization Reference

## Per-Scene Inline Tags (All 12)

Parsed from the `script` field by `src/lib/script-parser.ts`.  
Each tag applies only to the scene (sentence) it appears in.  
Tags are stripped from voiceover text before TTS.

| Tag | Values | Effect | Added |
|-----|--------|--------|-------|
| `[Visual: keywords]` | local filename or search keywords | Bind local asset or search stock | Original |
| `[Text: on/off]` | `on`, `off` | Show/hide captions for this scene | Original |
| `[Transition: fade]` | `fade`, `slide`, `zoomblur`, `cut` | Override transition INTO this scene | Phase 1 |
| `[Grade: warm]` | `neutral`, `warm`, `cool`, `cinematic`, `vivid` | Override color grade | Phase 1 |
| `[KenBurns: off]` | `on`, `off`, `true`, `false` | Enable/disable KenBurns zoom | Phase 1 |
| `[Trim: 00:05-00:10]` | `mm:ss-mm:ss` | Trim local video clip | Phase 1 |
| `[Style: top]` | `top`, `bottom`, `center` | Caption vertical position | Phase 2 |
| `[Color: yellow]` | 10 named colors | Caption text color | Phase 2 |
| `[FadeIn: 0.5]` | float (seconds) | Audio fade-in at scene start | Phase 2 |
| `[FadeOut: 0.5]` | float (seconds) | Audio fade-out at scene end | Phase 2 |
| `[Voice: en-GB-SoniaNeural]` | any TTS voice name | Per-scene TTS voice override | Phase 3 |
| `[Music: bgm.mp3]` | filename in `input/visuals/` | Per-scene background music file | Phase 3 |
| `[Volume: 0.8]` | float 0.0–2.0 | Per-scene audio volume override | Phase 3 |

## JSON-Level Fields (All Config)

Applied globally to the whole video. Fields pass through `AgenticCliJob` → `PipelineRequest` → `renderAgenticSlideshow()`.

### Core

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `id` | string | auto | Job identifier |
| `title` | string | **required** | Video title / output filename |
| `script` | string | auto | Custom script with inline tags |
| `topic` | string | title | Fallback when no script |
| `voice` | string | en-US-JennyNeural | TTS voice name |
| `orientation` | `portrait`/`landscape` | `portrait` | Frame aspect orientation |
| `backend` | `agent`/`vision` | `agent` | AI backend |

### Visual Style

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `preset` | string | — | Named visual preset (cinematic, reels, documentary) |
| `format` | string | — | Format preset: shorts, reels, tiktok, square, landscape, explainer, promo |
| `aspect` | `9:16`/`1:1`/`16:9` | — | Override aspect ratio |
| `transition` | string | — | Global transition override |
| `grade` | string | — | Global grade override |
| `kenBurns` | boolean | `true` | Global Ken Burns toggle |
| `vignette` | boolean | `true` | Cinematic edge darkening |
| `kineticText` | boolean | `true` | Animated lower-third text pops |

### Captions

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `captions` | `burned`/`karaoke`/`none` | `burned` | Caption rendering mode |
| `captionTheme` | string | `minimal` | Named theme preset (12 available) |
| `languages` | string[] | — | Extra subtitle language sidecars (e.g. `["es","fr"]`) |

### Audio

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `language` | string | — | Auto-select TTS voice for this language |
| `backgroundMusic` | string | — | Local file in `input/visuals/` for BGM |
| `musicVolume` | number | 0.15 | BGM volume 0.0–1.0 |
| `musicIntensity` | `calm`/`mid`/`energetic` | — | Ducking depth for music |
| `musicQuery` | string | — | Stock music search term |
| `sfx` | boolean | `false` | Enable transition sound effects |
| `jCutSec` | number | — | J-cut: next voiceover leads picture by N seconds |

### Branding

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `intro` | `{title, subtitle?, durationSec?}` | — | Branded title card before first scene |
| `outro` | `{ctaText, showSubscribe?, hashtags?, durationSec?}` | — | Branded CTA card after last scene |
| `brand` | `{watermark?, accent?}` | — | Branding: logo path + accent color |
| Logo auto-detected | from 3 locations | ✅ | `assets/logos/logo-automation.png`, `public/logo.png`, `input/visuals/logo-automation.png` |

### Workflow

| Field | Type | Default | Effect |
|-------|------|---------|--------|
| `hookFirst` | boolean | `true` | Reorder scenes for hook-first |
| `variablePacing` | boolean | `true` | Scientific timing + text-length duration |
| `candidatesPerAsset` | number | 2 | Stock candidates per scene |
| `preferVisual` | `image`/`video` | — | Preferred asset type |
| `dryRun` | boolean | `false` | Plan only, no fetch/render |
| `renderer` | `ffmpeg`/`remotion` | `ffmpeg` | Render engine |
| `maxAttempts` | number | — | Autopilot retry budget |
| `platform` | `tiktok`/`youtube`/`instagram`/`reels` | — | Target platform auto-tailoring |
| `videoType` | `facts`/`tutorial`/`news`/`story`/`product`/`motivational`/`nature` | — | Content type template |

### Asset Binding

| Field | Type | Effect |
|-------|------|--------|
| `localAssets` | string[] | Cycle local files across scenes |
| `videoClips` | string[] | Cycle video clips across scenes |
| `personalAudio` | string[] | Per-scene voiceover files |
| `defaultVisual` | string | Fallback when fetch fails |

## Feature Wiring Map

### Adding a new inline tag (6 touch points)

```
1. src/lib/script-parser.ts   → Scene interface (+ field)
                                parseScriptLocally (+ regex var + match)
                                cleanText chain (+ .replace)
2. src/agentic/types.ts       → ScenePlan (+ field)
3. src/agentic/pipeline/plan.ts → toScenePlans (+ mapping)
4. src/agentic/orchestrator/render.ts → use the field
```

### Adding a new CLI / global option (4 touch points)

```
1. src/agentic/orchestrator/types.ts   → PipelineRequest (+ field)
2. src/adapters/cli/agentic-cli.ts     → AgenticCliJob (+ field)
                                        → req mapping
                                        → render call opts
```

### Per-scene voice override (batch pattern)

`src/agentic/media/tts.ts` — `generateAgenticVoiceovers()`:
1. Group scenes by `voiceOverride || defaultVoice`
2. Call `generateVoiceovers()` per group with that voice
3. Merge all results into a single Map
4. Fallback to tones for any missing scenes

### Per-scene volume override

`src/agentic/orchestrator/render.ts` — segment audio chain:
```typescript
const volOverride = res.plan.scenes[clip.idx]?.volumeOverride;
const volFilter = volOverride && volOverride > 0 && volOverride !== 1
    ? `,volume=${volOverride}` : '';
const af = `[1:a]${afBase}${fadeFilter}${volFilter}[a]`;
```

### Per-scene caption style/color

`src/agentic/orchestrator/render.ts` — segment caption chain:
```typescript
const sceneStyle = res.plan.scenes[clip.idx]?.captionStyle;
const sceneColor = res.plan.scenes[clip.idx]?.captionColor;
const yExpr = sceneStyle === 'top' ? 'h/10' : sceneStyle === 'center' ? '(h-text_h)/2' : defaultY;
const fontColor = sceneColor ?? capColor;
```

## Caption Themes (12 presets)

Resolved by `resolveCaptionTheme(name)` in `src/agentic/config.ts`.
Names: `minimal`, `cinematic`, `neon`, `retro`, `clean`, `bold`, `elegant`,
`playful`, `news`, `tech`, `nature`, `vibrant`.
Each maps to: fontScale, fontColor, bg (rgba), position (top/center/bottom).

## Verification

```bash
npm run typecheck                    # 0 errors
npm run generate:agentic             # exit 0
```
