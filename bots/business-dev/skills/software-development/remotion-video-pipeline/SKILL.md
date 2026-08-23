---
name: remotion-video-pipeline
description: >-
  Develop, enhance, and debug BOTH the Remotion-based agentic video-generation
  pipeline AND the ffmpeg agentic pipeline (the user's Automated-Video-Generator
  repo). Covers the GenMotion autonomous codegen system (12 synthesizer kinds,
  16 library compositions, self-fixing retry loop), Remotion 4 composition
  (transitions, motion graphics, shapes, captions, waveforms), the 6-stage
  ffmpeg agentic pipeline (plan → acquire → verify → decide → gate → render),
  the JSON-input CLI wrapper, per-scene inline editing tags ([Transition:],
  [Grade:], [KenBurns:], [Trim:]), logo overlay, Voicebox/Kokoro TTS
  integration, duration-from-text pacing, and the ScenePlan editing API.
---

# Remotion Video & Agentic Pipeline Development

Recurring class of work for this user: the `Automated-Video-Generator` repo
has TWO parallel pipelines:

1. **Remotion pipeline** — Remotion 4.0.487 compositions with transitions,
   kinetic text, motion graphics, waveforms, shapes. Runs `npx remotion render`.
2. **Agentic ffmpeg pipeline** — 6-stage (plan→acquire→verify→decide→gate→render)
   with JSON-input CLI (`npm run generate:agentic`), Voicebox/Kokoro TTS,
   per-scene inline editing tags, logo overlay, and auto-pacing.

Both share the same `src/lib/script-parser.ts` and same `input/scripts/`
JSON format with `[Visual: ...]` tags.

## Agentic Pipeline Workflow

### JSON input with editing tags

Create `input/scripts/agentic-scripts.json`:

```json
[
  {
    "id": "demo",
    "title": "My Video",
    "script": "Opening scene. [Visual: logo.png] [Transition: slide] [Grade: warm]\nSecond scene. [Visual: coding] [KenBurns: off]\nFinal scene. [Visual: demo.mp4] [Trim: 00:05-00:10]",
    "orientation": "portrait",
    "language": "english",
    "backgroundMusic": "bgm.mp3",
    "musicVolume": 0.15,
    "hookFirst": true,
    "variablePacing": true,
    "candidatesPerAsset": 2
  }
]
```

Then run: `npm run generate:agentic`

### Per-scene inline tags (available in script)

| Tag | Values | Effect |
|-----|--------|--------|
| `[Transition: fade]` | fade, slide, zoomblur, cut | Override transition |
| `[Grade: warm]` | neutral, warm, cool, cinematic, vivid | Override color grade |
| `[KenBurns: off]` | on, off, true, false | Disable/enable zoom for this scene |
| `[Trim: 00:05-00:10]` | mm:ss-mm:ss | Trim local video clip |
| `[Style: top]` | top, bottom, center | Caption position (default: bottom) |
| `[Color: yellow]` | white, yellow, blue, red, green, cyan, magenta, black, pink, orange | Caption text color |
| `[FadeIn: 0.5]` | float (seconds) | Audio fade-in at scene start |
| `[FadeOut: 0.5]` | float (seconds) | Audio fade-out at scene end |
| `[Voice: en-GB-SoniaNeural]` | any TTS voice name | Per-scene voice override |
| `[Music: bgm.mp3]` | filename in `input/visuals/` | Per-scene background music file |
| `[Volume: 0.8]` | float 0.0–2.0 | Per-scene audio volume |

### JSON-level fields

| Field | Type | Effect |
|-------|------|--------|
| `language` | string | Auto-selects TTS voice (e.g. "tamil" → ta-IN-PallaviNeural) |
| `backgroundMusic` | string | Local file in `input/visuals/` for background music |
| `musicVolume` | number | Background music volume 0.0-1.0 |
| `intro` | object | Branded title card: `{title, subtitle?, durationSec?}` |
| `outro` | object | Branded CTA card: `{ctaText, showSubscribe?, hashtags?, durationSec?}` |
| `captionTheme` | string | Caption theme preset (minimal, cinematic, neon, retro, ...) |
| `captions` | `burned`/`karaoke`/`none` | Caption rendering mode (default: burned) |
| `sfx` | boolean | Enable transition sound effects |
| `jCutSec` | number | J-cut: next voiceover leads picture by N seconds |
| `format` | string | Format preset: shorts, reels, tiktok, square, landscape, explainer, promo |
| `preset` | string | Named visual preset (cinematic, reels, documentary, ...) |
| `aspect` | `9:16`/`1:1`/`16:9` | Override aspect ratio |
| `vignette` | boolean | Enable/disable cinematic vignette (default: true) |
| `kineticText` | boolean | Enable/disable kinetic lower-third text (default: true) |
| `musicIntensity` | `calm`/`mid`/`energetic` | Music ducking depth |
| `platform` | string | Target platform for auto-tailoring |
| `videoType` | string | Video content type template |
| `brand` | object | Branding: `{watermark?, accent?}` |
| `renderer` | `ffmpeg`/`remotion` | Render engine |
| `maxAttempts` | number | Autopilot retry budget |
| `languages` | string[] | Extra subtitle language sidecars |
| `kenBurns` | boolean | Global Ken Burns toggle |
| `transition` | string | Global transition override |
| `grade` | string | Global grade override |

### Modular pipeline (independent stage execution)

Run stages **independently** via `agentic-modular.ts` — no need to re-run the full pipeline every time:

| npm script | Stage | What it does |
|------------|-------|-------------|
| `agentic:plan` | Plan | Parse script → build Plan → save to workspace |
| `agentic:visuals` | Acquire | Download visuals using plan |
| `agentic:voice` | TTS | Generate voiceovers (`--scene N` for single scene) |
| `agentic:render` | Render | Render video from existing workspace |
| `agentic:edit` | Edit | Modify a single scene's visual/voice/volume/style/color |
| `agentic:list` | Inspect | Show all scenes with tags, duration, stage progress |
| `agentic:modular` | All | Full pipeline (same as `generate:agentic`) |
| `agentic:reorder` | Reorder | Reorder scenes non-destructively (`--order 4,1,2,3`), then re-render |
| `agentic:critique` | Critique | Director's Critique of the rendered MP4 (black/clip/aspect/caption) |
| `agentic:revise` | Revise | Re-edit a delivered job from change notes (`--auto` to self-heal) |

**Reorder scenes** (writes new order into `plan.json`, renumber `sceneNumber`):
```bash
npm run agentic:reorder --order 4,1,2,3   # must list ALL scene numbers once
npm run agentic:render                     # re-render to apply
```

**Director's Critique** (offline analyzer + opt-in vision; see
`codebase-gap-analysis` `references/worked-example-avs.md` for internals):
```bash
npm run agentic:critique        # prints PASS/NEEDS WORK + per-scene suggestions
npm run agentic:revise --auto   # critique -> auto-apply fixes -> new jobId
```

**Edit a single scene** (no full re-render):
```bash
npm run agentic:edit --scene 3 --visual "rocket launch" --voice en-IN-ValluvarNeural --volume 0.8 --style center --color cyan
npm run agentic:edit --scene 2 --transition fade --grade warm --fade-in 0.3
npm run agentic:edit --scene 5 --ken-burns zoom-in --music bgm.mp3
```
Note: `edit --voice` now re-extracts `captionSegments` from the regenerated audio
(stops caption/audio desync), and renders a contact-sheet PNG next to the clip.

**Inspect workspace state:**
```bash
npm run agentic:list
# Shows every scene, its inline tags, and which stages are complete
```

### Standalone video editor (20 ffmpeg operations)

`agentic-editor.ts` wraps common video editing operations as thin ffmpeg wrappers:

| Command | Example | Operation |
|---------|---------|-----------|
| `info` | `--input video.mp4` | Show codec, resolution, duration |
| `trim` | `--start 00:05 --duration 10` | Cut segment |
| `speed` | `--rate 2.0` | Speed up/slow down |
| `extract-audio` | `--output audio.mp3` | Extract audio track |
| `replace-audio` | `--audio new.wav` | Replace audio |
| `mute` | — | Remove audio track |
| `split` | `--at 00:10` | Split at timestamp |
| `merge` | `--files "a.mp4,b.mp4"` | Concatenate videos |
| `crop` | `--w 720 --h 720 --x 100 --y 50` | Crop region |
| `resize` | `--w 1920 --h 1080` | Scale dimensions |
| `rotate` | `--angle 90` | Rotate/flip |
| `loop` | `--count 3` | Loop clip N times |
| `overlay-text` | `--text "Hello" --color yellow` | Add text/caption |
| `overlay-image` | `--image logo.png` | Add watermark |
| `extract-frame` | `--at 00:02` | Save single frame PNG |
| `thumbnail` | `--at 00:01 --width 320` | Poster frame JPG |
| `blur` | `--strength 5` | Blur frame |
| `adjust` | `--brightness 0.1 --contrast 1.2` | Color correction |
| `reverse` | — | Reverse playback |
| `concat-scene` | `--job avs_job --scene 3` | Extract scene by plan |

All accept `--input` and `--output`. Many accept `--start`/`--end`/`--duration`.

```bash
npm run agentic:editor trim --input output/demo.mp4 --start 00:05 --duration 10 --output output/clip.mp4
npm run agentic:editor overlay-text --input output/demo.mp4 --text "PROMO" --color red --size 72
npm run agentic:editor concat-scene --job avs_demo --scene 2
```

### Logo watermark

Auto-applied from the first existing file found in:
- `assets/logos/logo-automation.png`
- `public/logo.png`
- `input/visuals/logo-automation.png`

Applied via ffmpeg `overlay=W-w*0.12-20:H-h*0.12-20` after audio mixing.

### Duration from text length

`variablePacing` now blends breathing rhythm (hook=3s, body=5/3s) with word-count
proportional timing: `max(breathing_min, min(words / 2.5, 8))`. A 50-word scene
gets 8s instead of the old flat 5s.

Full details in `references/agentic-cli-input-format.md`.

## GenMotion — Autonomous Remotion Codegen

The GenMotion sub-system gives the agent **full Remotion capacity**: it can
write, render, verify, and self-fix any composition from a natural-language
description — no preset templates, no caps.

Three mechanisms:

| Mechanism | How to trigger | What happens |
|-----------|---------------|-------------|
| **Autonomous codegen** | `[GenMotion: description]` in script | Agent writes a new `.tsx` from scratch per scene → renders → vision-verifies → self-fixes (up to 5 retries) → integrates into `input/visuals/` |
| **Pre-built library** | `[Motion: comp]` or `[Motion: comp@library]` | Selects from `remotion-creation/` (16 compositions) → passes data props → renders |
| **Full pipeline render** | `--renderer remotion` | Entire video via `remotion/AgenticVideo.tsx` with A1-A11 features (transitions, grading, karaoke, kinetic text, music ducking) |

### 12 Synthesizer Kinds

`remotion-codegen.ts` auto-generates any of: `kinetic`, `infographic`, `hud`,
`diagram`, `ui`, `map`, `particle`, `procedural`, `logo`, `timeline`,
`spectrum`, `abstract`. All pass the `assertSafeImports` safety gate.

### Retry Diversity (FIXED 2026-07-29)

Retries now pass `variant: attempt` so the synthesizer produces **different**
code on each retry (particle seeds, spectrum phases, procedural offsets).
Without this, failures repeated identically. Also calls `cleanSceneProject()`
before re-bundling to avoid stale cache.

### Key files
- `remotion-codegen.ts` — code author + 12-kind synthesizer (508 lines)
- `hermes-remotion-controller.ts` — controller loop (187 lines)
- `remotion-verify.ts` — signal + vision verification (64 lines)
- `motion-render.ts` — data-driven `[Motion:]` renderer (106 lines)
- `motion-resolver.ts` — tag resolution (91 lines)
- `orchestrator/remotion.ts` — full pipeline render (198 lines)
- `remotion-creation/` — 16 pre-built compositions (+ `remotion/` full pipeline)

Full reference: `references/geomotion-codegen.md` — architecture diagram,
12-kind detail table, known patterns & pitfalls (7 items), library listing.

## "Full-capacity audit" workflow preference (user's expectation)
When working in this repo, the user expects you to:
1. **Check everything end-to-end** before declaring done — not just typecheck +
   unit tests. Grep for all code paths, exercise edge cases, trace the data flow
   from config to render output.
2. **Proactively fix ALL bugs found** — not just the first one. If you find 7
   bugs in an audit sweep, fix all 7 in the same pass.
3. **Make improvements alongside fixes** — if code has dead/weak/brittle areas,
   strengthen them even if the bug was elsewhere. The user said "try to generate
   all new possible code and if you want any improvement means improve that also."
4. **Commit + push after every stable batch** — user authorized auto-commit+push.
5. **Do NOT ask permission for each fix** — the mandate is "check everything,
   fix everything, improve everything." Only pause for truly ambiguous design
   decisions.

## Mandatory Remotion workflow (user-corrected, do not skip)

[Rest of Remotion content unchanged...]

## Verification notes
- `npm test` = `npm run typecheck` **then** `npm run test:unit`. `typecheck` must be
  clean (`tsc -p tsconfig.json --noEmit`) — run it standalone when iterating.
- `npm run test:unit` globs `src/**/*.test.ts`, `remotion/**/*.test.ts`, AND
  `tests/**/*.test.ts`. The runner is Node's **built-in `node:test`** (NOT jest/vitest):
  `node --import tsx --test --test-timeout=120000 ...`. Single file:
  `node --import tsx --test tests/agentic/operations/route.test.ts`.
- In a git worktree the bare `node --import tsx --test` form fails with
  "Cannot find package 'tsx'" (no node_modules symlink). Use `npx tsx --test ...`
  there — full recipe + the mklink path gotcha in
  `references/agentic-pipeline-hardening.md`.
- Remotion helpers that don't need React context (timing mappers, path morph
  strings, shape `make*` path output, `CAPTION_STYLES` list) ARE unit-testable
  — do it. Component JSX that needs the Remotion runtime is only typecheck-verified.
- **Windows `search_files` tool is broken here** (returns `os error 3` on
  `C:/one/...` paths). Grep via `execute_code` + `subprocess.run(["rg","-n",pat,"-n",path])`.
- CLI smoke: `npx tsx src/adapters/cli/agentic-modular.ts help` lists all
  subcommands (plan/visuals/voice/render/edit/reorder/critique/revise/list/doctor/pipeline).
- **Chrome is usually available** — check `C:/Program Files/Google/Chrome/Application/chrome.exe`
  first. Set `CHROME_EXECUTABLE` (project chrome-gate) or pass `--gl` and let
  Remotion auto-detect, then render for real. Do NOT default to "visual
  verification blocked, needs Chrome" — that was a false assumption that let a
  real ghost-caption bug ship untested.
- **`renderStill` is UNRELIABLE for scenes that use `staticFile()`** — Remotion
  recopies the whole `public/` dir at render start, so an ad-hoc placeholder you
  just wrote isn't reliably served; a missing asset crashes the render, an
  unserved-but-present asset renders BLACK with no error. Intro/outro cards (no
  `staticFile`) render fine, masking the problem. **Use `renderMedia` (real
  short video, e.g. `npx remotion render <Comp> out.mp4 --frames=0-149`) then
  extract frames with ffmpeg — that is the production path and it serves assets
  correctly.** Full recipe in `references/visual-verification-real-render.md`.
- When judging a subtle effect (neon glow, small text), **crop+upscale the
  region with ffmpeg before vision_analyze** — a full 1080x1920 downscaled frame
  hides soft glows and the vision model reports "plain text".
- **Timing artifact trap:** kinetic/spring animations are mid-flight in early
  frames. A title that looks "fragmented / missing letters" at frame 15 is just
  still animating — render a SETTLED frame (well after the stagger completes)
  before concluding it's a bug.

## References
- `references/remotion-4.0.487-api.md` — condensed verified API surface.
- `references/license-clean-template-integration.md` — LICENSE verification
  method + safe/unsafe repo findings for this project.
- `references/visual-verification-real-render.md` — Chrome renderMedia loop
  that catches rendering bugs.
- `references/remotion-chrome-windows-troubleshooting.md` — Chrome headless
  timeout on Windows 10: symptom, root cause, attempted fixes, and ffmpeg
  workaround.
- `references/visual-tag-architecture.md` — `[Visual: ...]` tag system:
  how local images AND videos flow through both the legacy (web/CLI)
  and agentic (MCP) pipeline paths identically. Scene interface,
  supported extensions, data flow, and pitfalls.
- `references/agentic-cli-input-format.md` — **Updated this session.**
  JSON-input CLI wrapper (`npm run generate:agentic`). Covers all
  JSON fields, per-scene inline editing tags, logo overlay,
  duration-from-text, backgroundMusic override, and the full
  CLI→plan→acquire→render data flow.
- `references/extended-customization.md` — **New.** Full reference for
  all 12 inline tags, 30+ JSON fields, wiring maps per feature type,
  per-scene voice/volume/color/style override patterns, caption themes,
  and verification commands.
- `references/agentic-pipeline-hardening.md` — **New.** Git-worktree +
  node_modules symlink gotcha, offline fake-injection stage tests, the
  verified **gateway retry bug** + fix, voice integration-test skip pattern,
  modular-CLI voice Workspace parity, console.log→logInfo conversion, and the
  AGENTIC_KEEP_WORKSPACES prune-default RAM note.
