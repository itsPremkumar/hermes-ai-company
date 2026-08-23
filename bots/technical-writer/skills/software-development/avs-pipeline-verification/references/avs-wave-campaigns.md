# AVS "All-Variety" Continuous Campaign Pattern (Waves A–D)

Condensed recipe for the user's standing mandate: *"edit every possible
variety of video, find/fix bugs, implement any new high-control feature,
verify everything visually, repeat continuously — all driven by
`agentic-scripts.json`."*

## The loop (per wave)
1. **Control-surface audit FIRST.** grep declared job fields vs what
   `compose.ts` consumes (see SKILL.md audit recipe). A declared-but-
   unconsumed control = real feature gap → implement it, don't document.
   This is how `[Transition:]`, `captionTheme`, per-scene captions,
   `paletteFilter`, and `jCutSec` were each turned from dead no-ops into
   real, verified features.
2. **Build a WAVE matrix** as a standalone `input/scripts/waveX-matrix.json`
   (3–4 jobs). Append to `agentic-scripts.json` with a node one-liner
   (keep a `.bak` of the original array first). Each wave exercises a
   NEW feature combo across orientations (portrait/landscape/square) so
   you re-verify dims + the feature together.
3. **Run 2 jobs at a time, background, RAM-safe:**
   `npx tsx src/adapters/cli/agentic-batch.ts --mode compose --job <id> > /tmp/<id>.log 2>&1`
   (run `taskkill //F //IM ffmpeg.exe` before the first of a batch to
   clear stale encoders).
4. **Verify each artifact empirically:**
   - `ffprobe` dims + both streams (expect exact WxH per orientation/aspect).
   - Extract a single frame `ffmpeg -ss 1 -i final.mp4 -frames:v 1 /tmp/x.jpg`
     and `vision_analyze` it (contact sheets LIE — they crop and can
     misread a contact-strip as "landscape"). Always confirm: correct
     orientation, caption fully visible (not clipped), feature visible
     (teal tint, neon text, J-cut lead-in, emoji sticker), no defects.
5. **Fix any bug → re-render only the affected job → re-verify → commit.**
   Keep working tree committed in small feature-wave commits
   (`2c73c3f` transitions+themes, `ac93f81` captions+kinetic+emoji,
   `2d8f063` palette+guards, Wave-D jcut pending). **Never push unless
   the user says "push".**

## Wave A–D feature inventory (what shipped)
- **Wave A** — scene crossfade transitions (`[Transition:]`/`job.transition`
  → xfade filterchain) + `captionTheme` presets (neon/softCard/
  highContrast/minimal/bold) with drop-shadow.
- **Wave B** — per-scene burned captions (`voiceoverText`/`captionText`,
  previously NEVER burned) + auto word-wrap/font-shrink (`wrapCaption`/
  `estimateTextWidth`) + KINETIC karaoke + emoji-sticker infra
  (`renderEmojiSticker` + overlay; visibility limited on Windows — G1).
- **Wave C** — `paletteFilter` → real ffmpeg color filters
  (`buildPaletteFilter`) + `isReadableVideo` FX-chain guard + RAM-safe
  re-encode (`-threads 1 -pix_fmt yuv420p`). Fixed the cinematic-grade
  COMMA bug (G5) and the ffprobe-vs-ffmpeg guard bug (G7) and x264 OOM (G6).
- **Wave D** — `jCutSec` J-cut (`-itsoffset` on video input in amix).

## Next gaps identified (Wave E+ candidates)
- `dialogueVoices` / `voiceSpeed` per-scene wiring in the compose-path
  audio step (currently only plumbed to `single-feature.ts`, not consumed
  where `audios` are mixed).
- `titleCard.subtitle` burn (only `title` is burned today).
- Emoji visibility on Windows — render on a COLORED badge bg (G1) if a
  guaranteed-visible sticker is required.

## Known-good job-shape snippets (copy + modify)
Portrait + neon + kinetic:
```json
{"id":"ex_p","title":"...","topic":"...","script":"Line one. [Visual: x] [Kinetic: on]\nLine two. [Visual: y] [Kinetic: on]","mode":"compose","orientation":"portrait","captionTheme":"neon","kineticText":true,"endCta":"Go","contactSheet":true,"licenseFilter":"cc0"}
```
Square + palette + jcut + progress:
```json
{"id":"ex_s","script":"A. [Visual: a]\nB. [Visual: b]","mode":"compose","orientation":"portrait","aspect":"1:1","paletteFilter":"teal","jCutSec":0.8,"progressBar":true,"captionTheme":"minimal","loopVideo":2,"contactSheet":true,"licenseFilter":"cc0"}
```
Landscape + transitions + grade tags:
```json
{"id":"ex_l","script":"Mtn. [Visual: m] [Grade: warm] [Transition: zoomblur]\nRiver. [Visual: r] [Grade: cinematic] [Transition: fade]","mode":"compose","orientation":"landscape","transition":"zoomblur","captionTheme":"highContrast","sfxOnCut":true,"contactSheet":true,"licenseFilter":"cc0"}
```

## Verification command cheat-sheet
```bash
# dims + streams
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of default=nw=1 workspace/jobs/<id>/compose/final.mp4
# single frame for vision
ffmpeg -y -v error -ss 1 -i workspace/jobs/<id>/compose/final.mp4 -frames:v 1 /tmp/<id>.jpg
# targeted unit tests (NOT full suite — 9 pre-existing offline failures)
npx tsx --test src/agentic/operations/{overlays,caption-wrap,palette-filter,visual-fx,compose-scene-fx}.test.ts src/lib/script-parser.test.ts
# typecheck (SLOW — use timeout 180)
timeout 180 npx tsc --noEmit
```
