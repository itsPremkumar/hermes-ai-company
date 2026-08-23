---
name: avs-visual-frame-qa
description: Verify Automated-Video-Generator (AVS) video/image output by extracting frames and inspecting them with vision_analyze — catches REAL visual defects (wrong orientation, watermark glitches, caption language/positioning, overlap, corruption) that typecheck/ffprobe/unit-tests MISS. Use after any change to src/agentic/* render/voice/parser code, or when the user says "verify visually", "check all combinations", "find errors".
---

# AVS Visual Frame QA

Codec/typecheck/unit-test passes are NOT sufficient proof a generated video is
correct. In this project, three real bugs passed every static gate yet were
only caught by looking at the actual pixels:

1. **Orientation ignored** — `landscape`/`square` rendered as portrait
   (720×1280) because the CLI never passed `dimensions` to the renderer.
   `ffprobe` showed a valid 720×1280 MP4 (passes codec check) but it was the
   WRONG aspect. Only a frame inspection revealed portrait-in-a-landscape-job.
2. **Watermark black-box** — opaque logo PNG (rgb24, no alpha) stamped a black
   square in the bottom-right corner of EVERY video. Codec-clean, visually broken.
3. **Caption language mismatch** — hi/ta/fr/de voice jobs rendered ENGLISH
   burned captions (only the SRT sidecar was localized, not the burned caption).

**Rule: "verified" means extracted frames inspected with vision, not just
ffprobe/tsc.**

## Workflow

1. **Render a combinatorial batch** covering the change surface. For AVS use a
   generator script that emits `input/scripts/agentic-scripts.json` jobs across
   orientations × captions × music × perspectives × editing tags × voices. Keep
   it to ~12–47 jobs (each renders ~30–90s; 47 jobs ≈ 40 min — run in
   background with `terminal(background=true, notify_on_complete=true)`).
   - Generate distinct test images with `sharp` (gradient + label) into
     `input/visuals/persp_*.png` so frames are inspectable.
   - Restore `input/scripts/agentic-scripts.json` from `git checkout --` after.

2. **Validate codec/dimensions for ALL outputs** (fast, catches regressions):
   ```ts
   import { execFileSync } from 'child_process';
   const ff = require('ffprobe-static').path;
   // per output dir, main mp4 + variants (_16x9/_1x1/_9x16):
   const dim = execFileSync(ff, ['-v','error','-show_entries','stream=width,height',
     '-of','csv=p=0', f], {encoding:'utf8'}).trim().split('\n')[0];
   // expect: portrait 720,1280 | landscape 1280,720 | square 1080,1080
   ```

3. **Extract frames** for visual inspection (scale=480 to stay small):
   ```ts
   const ff = require('ffmpeg-static');
   execFileSync(ff, ['-y','-ss','1.5','-i',f,'-frames:v','1','-vf','scale=480:-1',
     outPng], {stdio:'ignore'});
   // extract both an early (0.8s) and late (2.2s/3.0s) frame, and one per
   // orientation, to cover intro/caption/transition states.
   ```

4. **Inspect with vision_analyze** — ask specifically:
   - Is the aspect correct for this orientation (fill edge-to-edge, no
     letterbox/pillarbox)?
   - Any grey/dark box artifact in a corner (watermark leak)?
   - Are burned/karaoke captions legible, correctly POSITIONED (top/center/bottom
     per [Style:]), and NOT overlapping baked-in graphic text?
   - For non-English voice jobs: is the burned caption in the TARGET language
     (not English)?
   - Any corruption/glitch/distortion?

5. **Isolate false alarms**: if vision reports a "title/prompt leak" but your
   source images have no text, regenerate one NO-TEXT source image and re-check —
   the vision model often misreads baked-in graphics + captions as leaked text.

## Continuous "variety matrix" campaign (the user's standing mandate)
The user repeatedly asks to "generate all possible varieties of video with
different type combinations, find new bugs, fix them, implement new high-control
features, and verify everything visually — continuously." Encode this as a
repeatable loop, NOT a one-off:

1. **Audit the control surface first.** Diff the `AgenticCliJob` schema +
   `ScenePlan` (parsed from `[Tag:]` inline tags) against what `compose.ts`
   ACTUALLY consumes. Every field that is declared but never called is a latent
   bug AND a feature opportunity. (This session: `[Transition:]`, `captionTheme`,
   and per-scene `voiceoverText` caption were all 100% dead — only title /
   lowerThird / CTA / emoji were burned, and `buildSlideshow` only did hard cuts.)
2. **Append a variety matrix** to `input/scripts/agentic-scripts.json`
   (BACK UP FIRST — `cp` it to `.bak`; restore with `git checkout --` after).
   Cover the combinatorics: orientation × aspect × grade × kenBurns ×
   chroma/blur/stabilize × speed × emoji × progressBar × transition × captionTheme
   × kinetic × loopVideo. Each job = one combination. Run in background 2-at-a-time
   (RAM-safe); wave the jobs (`terminal(background=true, notify_on_complete=true)`).
3. **Verify each artifact empirically** (per Workflow above): `ffprobe`
   dimensions FIRST (catches the silent-squash / wrong-orientation class), then
   `vision_analyze` the contact sheet — confirm captions render in the right
   COLOR/theme, transitions BLEND at seams, no black frames / cut-off text.
4. **When a bug surfaces, fix + add a regression test** (`.test.ts` asserting the
   now-wired behavior), then re-run the affected job to confirm via `ffprobe` +
   vision. Commit locally (never push unless explicitly told "push"/"go").
5. **Repeat.** Each pass should find the NEXT ignored-control gap and close it.
   Keep a running tally of which signals are now live vs still dead.

Key pitfall proven this campaign: **a stale `final.mp4` from a prior run can
mask a fix.** If the audio-mix step fails AFTER the video step, the old
`final.mp4` survives and `ffprobe` reports the OLD dimensions — you'll think
the fix didn't work. Fix: delete any existing `final.mp4` at the start of the
audio stage so a skipped/failed mix can't hide a stale video. Always `stat` the
mtime of `final.mp4` vs the fresh `overlays.mp4` to catch this (same-second
mtime = freshly rebuilt; old mtime = stale).

## The verification TOOL itself: Ollama vs agent `vision_analyze`
A critical, reusable finding (proven 2026-07-27 while building the
mixed-media one-by-one proof):

- The project's built-in `verifyMedia(path, keywords, {vision})`
  (`src/lib/media-verifier.ts`) routes its **vision** check to a **local Ollama**
  (`moondream:latest` @ `http://localhost:11434`). If Ollama is NOT running it
  throws `ECONNREFUSED` and — importantly — the `{vision:{enabled:false}}`
  flag does **NOT** disable the Ollama call (it still fires and returns
  `verdict=undefined`). So `verifyMedia` is **not** a reliable standalone
  visual gate on a box without Ollama.
- **The always-available visual check is the agent's own `vision_analyze`
  tool** (used successfully all session). It does not depend on Ollama.
  Pair it with an offline `ffprobe` (signal-level: resolution/aspect/duration)
  for the real content check.
- **Recommended per-asset loop** (this is the user's standing "verify one-by-one"
  discipline, executable today):
  1. download/generate ONE asset → save
  2. `ffprobe` (or `verifyMedia` offline) → must be 1920×1080 / valid h264
  3. extract ONE frame (`ffmpeg -ss 1 -i asset -frames:v 1 f.png`)
  4. `vision_analyze(f.png, "Does this show <expected>? Any black/corrupt?")`
     → subject must match, no blank/corrupt
  5. **only then** move to the next asset
  Doing it one-by-one (not `searchImages(..., 12, 2, ...)` + bulk verify)
  catches a bad asset AT THE MOMENT it is made, not after 9 others are queued.
- `vision_analyze` CANNOT load MSYS paths (`/c/one/...` → mangled to
  `\c\one\...` and "image file not found"). Pass a **Windows `C:\...` path**
  (forward OR back slashes both work in the `C:` form). If frames were
  extracted under `/c/one/...`, COPY them to a `C:\...` path first.

## Bug-hunt / triage additions (2026-07-28)
- **Confirmed core compose/render bug map** (xfade graph invalid → all
  transitions degrade to cuts; CLI render never calls composeVideo so
  shake/punchIn/speedRamp/parallax/palette silently no-op; audio-mix graph
  invalid when voiceVolume/duck≠1; vintage/sepia filters nonexistent; particles
  unmapped `[ov]`; relative-outDir crash) → see
  `references/core-compose-bug-map.md` for file:line detail, the direct
  composeVideo tsx driver pattern, and harness quirks.
- **Vision text-hallucination + placeholder-acceptance recipes** (pixel
  ground-truth for "is there text here?" and rejecting near-uniform gradient
  placeholders mislabeled as real sources): `references/vision-text-hallucination-qa.md`.
- **Audio-edge + robustness bug map** (audio-less sources, very-short/long scenes,
  `[Volume:]`/`[FadeIn:]`/`[FadeOut:]` tags, portrait-in-landscape) → see
  `references/audio-edge-bug-map.md`. Key finds: `[Volume:]` (and
  voice/music overrides) are parsed but NEVER attached to the scene at the
  `scenes.push({...})` in `script-parser.ts` (fadeIn/fadeOut ARE, so grep the
  push object for every parsed local); a hard 8s cap in `plan.ts:222` truncates
  long-scene voiceovers; and `format.duration` can decouple from stream
  durations (compare STREAM durations, not `format.duration`).
- **Verify audio envelope OBJECTIVELY with per-window volumedetect, never vision.**
  `ffmpeg -ss <t> -t <win> -i out.mp4 -af volumedetect -f null -` at
  start/+1s/mid/tail proves fade curves; vision cannot hear audio.
- **Verify "FX applied" OBJECTIVELY, not by vision alone.** The vision model
  confabulates: shown identical unmodified test patterns, it described the
  requested shake/speed-ramp/zoom/parallax/grade as present. Always pair vision
  with pixel metrics: `signalstats` SATAVG/YAVG on a caption-free crop
  (`crop=W:H:0:100`) for grades, and `tblend=all_mode=difference,signalstats`
  mean YAVG for motion FX (shake raises inter-frame diff). Identical numbers
  A/B = FX no-op regardless of what vision says.
- **`freezedetect` FALSE-POSITIVES on smooth Ken Burns zoom — use PSNR/MD5 to
  prove real motion.** A slow zoom (z 1.0→1.16 over 3 s) shows <0.1%
  per-frame pixel delta, so `freezedetect=n=0.001` flags EVERY animated scene
  as "frozen" (a matrix run reported 4–5 `freezeSegs`/video — looked like a
  catastrophe, was a false alarm). GROUND TRUTH recipe (proven 2026-07-28):
  ```bash
  # two frames 0.5s apart within ONE scene
  ffmpeg -y -ss 1 -i video.mp4 -frames:v 1 a.png
  ffmpeg -y -ss 1.5 -i video.mp4 -frames:v 1 b.png
  # PSNR ~55 dB between adjacent scene frames => REAL motion (true still = ∞)
  ffmpeg -i a.png -i b.png -filter_complex psnr -f null -   # read average:
  # 2s-apart frames: PSNR 27-28 dB => large zoom/pan over time
  # also: md5sum a.png b.png  => DIFFERENT => content changing
  ```
  The freezedetect SPAN is the tell: flagging the exact scene duration
  (0–6s, 6–11s, 11–16s) = slow zoom, NOT a blank still. FIX the QA harness:
  raise threshold to `n=0.02` (2%) and confirm with PSNR. NEVER declare
  "frozen frames" from freezedetect alone — same discipline as the chroma
  byte-size trap (#30 in avs-ffmpeg-pipeline): a miscalibrated metric is not
  proof. Pair with vision_analyze (the motion is visible in consecutive frames).
- **freezedetect also hits INTENTIONAL stills — match timestamps to the scene map
  before calling a defect.** Proven 2026-08-01 (fx-sweep): `[KenBurns: off]`
  scenes are deliberately static for the WHOLE scene duration (Color Lab freeze
  4.02–9.02s = the KenBurns-off scene), and static intro/outro title cards freeze
  for exactly their card duration (Story freeze 0.02–2.02s = the 2s intro card).
  Both are correct renders, not freezes. A freeze whose START+duration lines up
  with a known still element (card `durationSec`, a `[KenBurns: off]` tag) is the
  benign tell; a freeze INSIDE an animated scene is the defect case (then apply
  the PSNR/MD5 proof above).
- **Prove WHICH scenes share visuals with per-scene frame md5s (no vision
  needed) — the CONTENT-IDENTITY check.** When the user reports "same images
  repeated in every video" (or you suspect scene aliasing), extract one frame
  per scene's clip and md5 it:
  ```bash
  for S in 0 1 2 3 4 5 6; do
    ffmpeg -y -v error -i grade_$S.mp4 -frames:v 1 -vf scale=160:90 s$S.png
  done
  md5sum s*.png
  ```
  Identical md5s = the same visual was burned into those scenes. Count
  DISTINCT md5s vs scene count: distinct ≪ scenes = aliasing (e.g. verified
  2026-07-31: a 7-scene video had only 3 distinct md5s — scenes 0&3 and
  1/2/5/6 pixel-identical). Downscaling first makes the md5 robust to
  encoder noise; identical scaled md5s mean identical content, and confirm at
  FULL res (md5 of full frames) before reporting to the user — airtight
  proof. This is the counterpart to freezedetect/PSNR: that pair answers "is
  it MOVING", this answers "is it the SAME PICTURE". Typical root cause in
  AVS: filename collision in the visual fetch layer (every scene's download
  writes `image_001.jpeg` — see avs-ffmpeg-pipeline pitfall #74), not a
  render defect.
- **FIXED 2026-07-31 — the filename-collision root cause is CLOSED in code.**
  `bulk-fetch.ts` now accepts `opts.label` (filename stem, sanitized by the
  exported `sanitizeLabel()`) and `opts.sharedSeen` (a URL-dedupe `Set`
  shared across calls); `single-feature.ts` runCompose passes
  `label: scene_<i>_<kw>` + ONE shared set, so each scene writes
  `raw/scene_0_moon_001.jpeg` … `raw/scene_6_rocket_001.jpeg` and can never
  reuse a URL an earlier scene already picked. Empirical proof (all 6
  campaign videos re-rendered): per-scene md5s went from 3 distinct/7 to
  **7/7 distinct in EVERY video**, with identical duration/audio levels
  (voice/music deterministic). Regression test:
  `src/agentic/operations/bulk-fetch-label.test.ts` (5 cases: unique stems,
  sanitization of spaces/`/`/`\`/`:`; backward-compat default).
  If `distinct ≪ scenes` STILL appears post-fix, check for: (a) a STALE
  pre-fix `final.mp4` (mtime vs the run), (b) a degraded RAM-crash render
  (see avs-pipeline-verification G25 — the 0xC0000142 cascade leaves a
  valid-probing-but-degraded final), or (c) the provider URL pool genuinely
  collapsing (a scene falls back to a teal placeholder — acceptable). Fast
  health check: `ls compose/raw/scene_*.jpeg | wc -l` == scene count = the
  fetch layer is unique; aliasing can no longer occur at the filename level.
- **Vision models HALLUCINATE literal text (especially filenames) onto frames —
  pixel ground-truth must confirm BEFORE you fix anything.** Proven 2026-07-28:
  both the auxiliary vision model AND the agent's own `vision_analyze`
  repeatedly "saw" the string `candidate_1` burned into the CENTER of every
  rendered video. Pixel proof said otherwise: the asset PNG had NO text
  (signalstats center-crop YAVG 70.6 ≈ full-frame YAVG 68.6, no white-text
  brightness spike) and the video frame center was only ~5.77% bright pixels —
  a real white "candidate_1" caption would be far higher. ROOT CAUSE: the
  prompt/context mentioned the filename `candidate_1.png`, so the model
  pattern-matched that literal string onto the pixels. RULES:
  1. NEVER put a filename (e.g. `candidate_1.png`) into a vision prompt — it
     primes the model to "see" it.
  2. When vision reports literal text in an image, DISPROVE it with pixels
     BEFORE acting (same "pixel > vision" discipline as freezedetect/PSNR):
     ```bash
     # (a) center-crop brightness vs whole frame — ~equal => NO text spike
     ffmpeg -hide_banner -i frame.png \
       -vf "crop=iw/3:ih/3:iw/3:ih/3,signalstats,metadata=print:key=lavfi.signalstats.YAVG" \
       -f null -
     #   a real text string spikes the center crop YAVG WELL above the full frame
     # (b) % of bright (text) pixels — real white text is FAR above a few %
     ffmpeg -hide_banner -i frame.png \
       -vf "format=gray,geq='if(gt(lum(X,Y),180),255,0)'" -frames:v 1 bw.png
     ffmpeg -hide_banner -i bw.png -vf signalstats,metadata=print:key=lavfi.signalstats.YAVG -f null -
     #   the printed YAVG on bw.png == % of bright (text) pixels
     ```
  3. If still ambiguous, re-run `vision_analyze` on a tight center CROP with a
     neutral prompt ("is there white text here? answer yes/no only") — but treat
     its answer as suspect until pixel math agrees.
  This generalizes the existing step-5 "title/prompt leak" pitfall: vision
  confabulates text from context; only pixels decide. Full reproduce recipes in
  `references/vision-text-hallucination-qa.md`.
- **Asset-content validation gap: a solid-color gradient placeholder can be
  accepted as a REAL scene visual and mislabeled as a real source.** Proven
  2026-07-28: a matrix run shipped `candidate_1.png` (a near-uniform teal
  gradient from `generateFallbackVisual`, colors `0x1e3a8a:0x0f172a`) for ALL 3
  scenes, with the render-manifest `license` falsely reading "Source:
  openverse/pexels". QA check: cross-check the render-manifest's `license`/
  `source` label against the ACTUAL asset content — reject/skip near-uniform
  images (signalstats YMIN≈YMAX with low spatial variance, or a histogram showing
  one flat color) as non-photo placeholders. A genuine sourced photo has real
  spatial variance (photographic detail), not a flat gradient. Add an
  `isRealPhoto()` guard (reject when signalstats spatial variance < threshold) to
  candidate selection so placeholders fail over to the next source instead of
  shipping as a swatch. Never label a generated placeholder `openverse/pexels` —
  it must read `placeholder` (see `src/agentic/orchestrator/pipeline.ts` source
  labeling at the `fetchVisual` return site).
- A "black frame" in a sparse 2x2 grid can be a scene-boundary/caption-region
  sample, not a real defect — sweep 1-frame-per-second across the whole video
  before declaring black/corrupt frames.
- To prove an ffmpeg filtergraph bug in source, RE-RUN the exact generated
  graph string in isolation against the project's own ffmpeg-static binary and
  quote the parser error — filter-level repro beats reading code.
- **Three concrete AVS checks that catch the bugs found 2026-07-28** (detail in
  `avs-agentic-workflow` `references/edit-ts-bug-map.md`):
  1. **xfade transitions actually render (not hard cuts):** render a job with
     `[Transition: glitch|slide|whippan|fade]`; if `render` logs `xfade failed →
     fallback to concat`, transitions are BROKEN (pre-fix the xfade graph in
     `compose.ts`/`render.ts` was invalid — operands swapped, chain never linked,
     joined with `,`). The fixed graph chains `[v{n-1}]`→`[v{n}]` with `;`
     separators + `format` on the final label. Absence of the fallback warning +
     a successful render = transitions work.
  2. **audio not silently dropped when voiceVolume/duck ≠ 1:** render with
     `voiceVolume:0.6` + `duckDepth:0.3`; run `ffprobe -select_streams a` (expect
     an audio stream) + `ffmpeg -af volumedetect -f null -` (expect mean_volume
     ≈ -25dB, NOT silent). A broken amix graph (labeled `[va]`/`[ma]` outputs not
     fed into amix, joined with `,`) ships a SILENT video.
  3. **vintage/sepia render (not no-op):** `vintage` must be
     `curves=vintage,eq=saturation=1.2` (NOT `saturation=1.2`, which is not a
     filter); `sepia` must be a `colorchannelmixer` matrix (this ffmpeg build has
     NO `sepia` filter). Vision-check: scene looks warm (vintage) / brown-monochrome
     (sepia). Both were silent no-ops pre-fix in BOTH `visual-fx.ts` AND
     `render.ts:734-736` — fix in one file alone is inert for the CLI pipeline.

## Known gotchas
- `agentic-cli.ts` renders only the MAIN mp4 + `_16x9`/`_1x1`/`_9x16` variants;
  verify dimensions on EVERY variant (orientation fix must propagate to all).
- Thumbnails (`*_thumbnail.jpg`) and subtitles (`*.srt`/`*.vtt`) are separate
  artifacts — also spot-check thumbnail cleanliness.
- This zero-cost env has NO translation model configured, so non-English caption
  localization gracefully falls back to English (no regression) — that is
  EXPECTED, not a bug.
- `process(background)` wait clamps at 60s; poll `grep -c "Output:"` on the log
  instead of blocking.
- `workspace/tmp/*.ts` helpers are SCRATCH — never treat them as source edits;
  the system reminder's "changed paths" for them is stale noise.
- **MSYS `bash` for-loop with an inline `ff=...` variable fails (exit 127).**
  Defining `ff=./node_modules/ffmpeg-static/ffmpeg.exe` then using `$ff` INSIDE a
  `for f in ...; do ...; done` (especially piping ffmpeg stderr through `grep`)
  returns exit 127 ("command not found") under MSYS. Same whole-loop
  `2>/dev/null && mv` chains also silently no-op. FIX: write the loop to a `.sh`
  FILE (e.g. `scripts/crop_visuals.sh`) and run `bash scripts/crop_visuals.sh`.
  Keep ffmpeg paths RELATIVE (`./node_modules/...`), NOT absolute `/c/one/...`
  (native ffmpeg.exe mangles MSYS forward-slash paths → "No such file"). Reading
  dimensions inside the script: `DIM=$("$FF" -i "$src" 2>&1 | grep -oE
  '[0-9]+x[0-9]+' | head -1)` then `cut -dx -f1/f2` works reliably.
- **The AVS `pipeline` subcommand HANGS indefinitely** at the "Acquired N
  candidates" line (the gateway/verification stage between visuals and voice
  never returns — seen on the sproutern reel run). Don't block on it: kill it and
  run `voice` + `render` stages separately (`npm run agentic:modular -- voice|render
  --file <job>.json`). `voice` is slow (~10–15s/scene, up to ~2 min for long
  scenes) but reuses completed scenes on re-run, so re-launching is safe. Always
  confirm the mp4 EXISTS (`ffprobe` shows 720×1280) BEFORE any "move/deliver"
  step — the hang leaves no output.
- **`vision_analyze` CANNOT load MSYS paths** (`/c/one/...` → tool mangles
  it to `\c\one\...` with backslashes and fails "image file not found").
  FIX: pass a **Windows `C:\...` path** (forward OR back slashes both work in
  the `C:` form, e.g. `C:\one\automated-video-generator-improvements\qa.jpg`).
  If you extracted frames under `/c/one/...`, COPY them to a `C:\...` path first.
  Do NOT loop on the `/c/one/...` path — it fails every time
  (cost 6 wasted tool calls in one session).
- **ffmpeg `drawtext` gotchas** (broke the overlay chain silently until found):
  - `fontcolor=0xwhite` is INVALID — CSS color NAMES (white, yellow, black)
    must be passed as-is; only prepend `0x` when the value is a HEX code.
  - `enable='gte(t,T-3)'` is INVALID — `T` is not a valid var inside
    drawtext `enable`. Use absolute seconds (`gte(t,3)`) or `between(t,start,end)`.
  - `fontweight` is NOT a valid drawtext option in this ffmpeg build — it
    errors "Option not found" and fails the WHOLE -vf chain (so NO text bakes in).
    Select weight via the BOLD FONT FILE (arialbd.ttf, georgiab.ttf, timesbd.ttf…),
    not a param. Map `fontWeight>=600 → bold file`.
  - Test a full `drawtext`/`-vf` chain via `node -e` array-args BEFORE
    relying on it in compose — a single bad filter in a comma-joined chain
    kills all text.
  - **COMMA inside a single filter string is a filterchain separator.** If a
    grade/palette entry is `'curves=preset=strong_contrast,eq=saturation=0.92'`,
    `filters.join(',')` splits it into two BROKEN tokens
    (`curves=preset=strong_contrast` with no `eq`, then `eq=...` free) →
    corrupt/0-byte output ("moov atom not found"). FIX: one valid filter per
    entry (`eq=contrast=1.15:saturation=1.05`); never a comma inside the string.
    Bit the `cinematic` grade + `vintage` palette this campaign.
  - **`-itsoffset` on the VIDEO input + `-c:v copy` corrupts the TAIL
    frames** (J-cut via `job.jCutSec`: shifting video timestamps while
    copying makes the end undecodeable — seek past the shift point fails).
    FIX: when J-cut active, re-encode video (`libx264 -preset veryfast
    -pix_fmt yuv420p -threads 1` for RAM safety) instead of copy; plain
    copy otherwise (fast, lossless).
  - **`isReadableVideo()`-style guards must call the ffprobe binary, NOT
    ffmpeg.** Calling `ffmpeg -show_entries stream=...` throws (wrong
    binary) → guard always returns false → upstream FX inputs wrongly skipped.
    Use `require('ffprobe-static').path` for any probe.
  - **Emoji stickers DO render on Windows** via `C:/Windows/Fonts/seguiemj.ttf`
    (Segoe UI Emoji, ~12MB, preinstalled). `drawtext` with that font +
    `text='☕'` produces a visible glyph. An earlier "emoji is blank on Windows"
    conclusion was a FALSE ALARM (bad corner-crop verification). Verify the
    emoji with `vision_analyze` on the FULL extracted frame, not a tiny crop.
