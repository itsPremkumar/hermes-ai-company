# AVS agentic pipeline — end-to-end verification playbook

How to verify the Automated-Video-Generator (AVS) agentic pipeline after a change,
WITHOUT network-heavy/full renders being the only proof. Two layers.

## Layer 1 — Control-surface matrix (fast, offline, no voice/network)
The CLI `npm run generate:agentic` (→ `src/adapters/cli/agentic-cli.ts`) reads
`input/scripts/agentic-scripts.json` (an ARRAY of jobs). Build a matrix of jobs, each
exercising a cluster of editing varieties, and set `"dryRun": true` on them. dryRun runs
`parseScript → buildPlan` (so every inline tag + top-level field is parsed and mapped into
the plan) then returns early with `gate.pass=false` by design — NO asset fetch, NO voice,
NO ffmpeg render. This is the cheapest proof that the JSON control surface is wired.

Coverage to assert in the matrix:
- **orientations**: portrait (9:16), landscape (16:9), square (1:1) — set `orientation`
  and confirm the `_1x1`/`_16x9`/`_9x16` output variants appear with correct W/H.
- **voices/languages**: `en-US-*`, `en-GB-*`, `en-IN-*`, `es-ES-*` (multi-language job).
- **captions**: `burned`, `karaoke`, `none`.
- **all 19 inline `[Tag:]`**: Visual, Text, Transition, Grade, KenBurns, Trim, Style, Color,
  FadeIn, FadeOut, Voice, Music, Volume, CaptionTheme, Sfx, JCut, Vignette, Kinetic,
  MusicIntensity — put several per scene.
- **top-level config**: preset, videoType, platform, brand, renderer, maxAttempts, aiVerify,
  pruneWorkspaces, brain, agent, defaultVisual, hookFirst, variablePacing, backend,
  candidatesPerAsset, musicVolume, localAssets (array of filenames → auto-bound, no fetch).
- A dryRun job should print `✅ DRY RUN OK — N scenes planned, Xs` (see bug #9).

Run: `npx tsx src/adapters/cli/agentic-cli.ts` from repo root.

## Layer 2 — Real render proof (validates the ffmpeg output path)
dryRun does NOT exercise acquire/verify/gate/render. To prove the actual MP4 is produced:
- Use `"localAssets": ["github-profile.png", "logo-automation.png"]` (existing files in
  `input/visuals/`) so NO network image fetch happens.
- Voice falls back automatically: the vendored torch/kokoro venv is RAM-prohibited here, so
  the backend fails fast (bug #10) → Edge-TTS → (if Edge-TTS network blocked) Windows offline
  speech. Either way voiceovers complete; render proceeds.
- Background music auto-selects a bundled track from `input/bgm/__bundled__/*.mp3` even when
  `backgroundMusic:""` — so the music-mix pass2 ALWAYS runs (this is where bug #8 lives).
- Expect the per-caption duck expression to crash ffmpeg (bug #8) and the code to fall back
  to flat volume; the output MP4 is still valid.
- Probe the result with ffprobe: assert `codec_type=video` W/H matches orientation and
  `codec_type=audio` duration ≈ plan duration. Example:
  `node -e "const{execFileSync}=require('child_process');const p=require('ffprobe-static').path;console.log(execFileSync(p,['-v','error','-show_entries','stream=codec_type,width,height,duration','-of','csv=p=0',F],{encoding:'utf8'}))"`

Real renders are SLOW (voice ~10-30s + per-scene ffmpeg). Run them in background
(`terminal(background=true, notify_on_complete=true)`) and poll the log for
`🎬 Output: .../<id>.mp4` and `Summary: N completed, 0 failed`.

## 🔴 VISUAL VERIFICATION — codec/ffprobe checks are NOT enough (learned this session)
A render can pass every automated check (ffprobe shows valid 720x1280 video + audio,
file size > 100KB, no errors) while being VISUALLY WRONG. Two real bugs shipped past
ffprobe-only checks and were caught ONLY by looking at frames:

- **BUG #7 — orientation ignored (landscape/square rendered as portrait).** ffprobe
  reported a clean `720x1280` video and the render "passed" — but a LANDSCAPE job had
  been rendered as portrait because `agentic-cli.ts` called `renderAgenticSlideshow`
  WITHOUT passing `orientation`/`dimensions`, so render.ts fell back to its hardcoded
  `720x1280` default. **Fix:** map orientation → dims in the CLI
  (`portrait 720x1280`, `landscape 1280x720`, `square 1080x1080`) and pass
  `{ orientation, dimensions }` into `opts`. Always VISUALLY confirm: extract a frame
  and ask the vision tool "is this wide (landscape) / square / tall (portrait)?"
- **BUG — unwanted watermark "grey square" in every video.** Vision flagged a dark
  square in the bottom-right corner of EVERY frame. Root cause: `render.ts` Pass-3
  logo overlay ran UNCONDITIONALLY whenever `input/visuals/logo-automation.png` existed
  (the file simply being present triggered it), overlaying a logo PNG that has an
  OPAQUE BLACK background → a black box in the corner. **Fix:** gate the overlay on
  `opts.brand` (opt-in, matching the documented `brand` control-surface field):
  `if (logoPath && opts.brand)`. Pass `brand: job.brand` from the CLI.

### Visual verification loop (do this AFTER any render change)
1. Extract 2 frames (early + late) per video with ffmpeg:
   `ffmpeg -y -ss <t> -i <video.mp4> -frames:v 1 -vf scale=480:-1 <out>.png`
   (scale keeps native aspect so a 16:9 source stays wide — if the extracted frame is
   portrait when you asked for landscape, orientation is broken).
2. `vision_analyze` each frame with specific questions:
   - "Is the image WIDE (wider than tall, edge-to-edge, no big black bars)?" (landscape)
   - "Is it a SQUARE (equal W/H)?" / "Is it TALL portrait?" (orientation check)
   - "Any dark/grey square artifact in a corner?" (watermark check)
   - "Is the burned caption fully inside the frame (not cut off)? Any ghost/duplicate text?"
3. Generate distinct, LABELED test images so frames are inspectable — see
   `references/make-perspective-images.md` (sharp-generated gradient + bold label per
   scene; lets you confirm the RIGHT perspective image is shown per scene).
4. Fix the defect, re-render, re-verify. One render+vision round per fix.

**Rule:** after ANY edit to the render/orientation/watermark/caption path, run the
visual loop on at least one portrait + one landscape + one square job before claiming done.

See `references/make-perspective-images.md` for the sharp-based labeled test-image
generator (10 distinct perspective images) and the frame-extraction + vision recipe.

## Test runner convention (IMPORTANT — easy to get wrong)
AVS `*.test.ts` files use **Node's built-in `node:test`** (import `test from 'node:test'`,
imports use `.js` extension per NodeNext ESM). They are NOT vitest files.
- WRONG: `npx vitest run src/.../foo.test.ts` → "No test suite found".
- RIGHT: `npx tsx --test src/.../foo.test.ts` (tsx provides the TS loader; Node's runner
  executes the `node:test` suites).
- The repo's `*.test.ts` split into two groups:
  - `src/agentic/ai/style-engine.test.ts`, `src/lib/script-parser.test.ts`,
    `src/adapters/cli/agentic-cli.test.ts` → run with `tsx --test`.
  - `src/agentic/pipeline/{acquire,gate,gateway,verify}.test.ts` → run with `tsx --test`.
- Full feature suite: `npx tsx --test src/agentic/ai/style-engine.test.ts src/lib/script-parser.test.ts src/adapters/cli/agentic-cli.test.ts src/agentic/pipeline/*.test.ts`
  → 36 pass / 0 fail (as of this writing).
- The BROAD `src/**/*.test.ts` full suite has ~8 pre-existing ENV-only failures
  (`mock.module is not a function` on Node 22.23.1 in http/mcp/media-verifier tests; live
  voice venv; network image providers) — these are environmental, not regressions. Use the
  targeted `tsx --test` command above to verify your changes.

## Workspace / RAM discipline (AVS-specific)
- node_modules is a symlink in each git worktree → `mklink /D node_modules <main>/node_modules`.
- Keep only Hermes + the AVS process alive; kill RAM hogs. Do NOT install torch/kokoro venv
  (breaches the ~800MB RAM budget) — the voice stage is designed to skip/fallback.
- All generated files stay inside the project root (output/ + workspace/); never write to
  system TEMP.
