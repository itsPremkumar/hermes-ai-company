---
name: avs-ffmpeg-pipeline
description: >-
  FFmpeg / compose-pipeline pitfalls and VERIFIED filter+encode recipes for the
  Automated-Video-Generator (AVS) agentic video project. Load this whenever
  you touch src/agentic/operations/compose.ts, compose-scene-fx.ts,
  overlays.ts, sfx.ts, single-feature.ts, src/agentic/orchestrator/render.ts,
  src/adapters/cli/agentic-editor.ts,
  or any ffmpeg filtergraph/encode in AVS. Captures the recurring failure
  classes that cost hours: comma-inside-a-filter-string corruption, wrong probe
  binary in guards, x264 OOM on low RAM, J-cut -itsoffset + -c:v copy tail
  corruption, stale-final masking fixes, drawtext color-emoji on Windows, -ss
  seek order, agentic-editor CLI arg mismatches, and the terminal
  lowercase-l-renders-as-x display glitch. Also covers subtitle export
  (SRT/VTT), chapter marker injection, and the verbose ffmpeg debugging flag.
  Pair with avs-pipeline-verification /
  avs-visual-frame-qa for the render-then-vision-check loop.
---

# AVS ffmpeg / Compose-Pipeline Pitfalls & Recipes

Every editor knob in AVS must be driven by `input/scripts/agentic-scripts.json`
(backward-compat: new code + optional params, never delete old paths). After any
change, render a real job, extract a frame, and `vision_analyze` it — static
checks miss real visual defects (orientation, caption clipping, grade tint).

## When to load
- Editing `compose.ts` / `compose-scene-fx.ts` / `overlays.ts` / `sfx.ts`.
- A generated `final.mp4` is corrupt, blank, wrong-sized, or a feature is
  "silently ignored" (declared in cli-job.ts but never consumed).
- Building a new Wave of variety jobs (transitions, grades, palettes, captions,
  J-cut, sfx, outro).

## Verified filter strings (use these exact forms)
See `references/compose-ffmpeg-pitfalls.md` for the full table + node-spawn
test snippet. `references/avs-resilience-network.md` has the retry + offline-
placeholder + music-fallback recipe for flaky media fetch. Key ones:
- bw/mono/grayscale: `format=gray`
- sepia: `colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131`
  (the `sepia=` filter is NOT compiled into ffmpeg-static 6.1.1 — silently no-ops/fails)
- vintage: `curves=vintage,eq=saturation=1.2`
  (old forms `curves=vintage:saturation=1.2` and `curves=vintage,saturation=1.2`
  are INVALID — `saturation` is not a curves option nor a filter; verified 2026-07-28)
- cinematic grade: `eq=contrast=1.15:saturation=1.05`  (NO comma)
- teal palette: `colorbalance=bs=0.14:gs=0.05:rs=-0.10,eq=saturation=1.25`
  (comma OK here — it is the WHOLE filtergraph wrapped in `[0:v]…[v]`)

## Pitfalls (the expensive ones)
1. **Comma inside a single filter string.** `filters.join(',')` treats a
   comma as a filterchain separator. `curves=preset=strong_contrast,eq=…`
   splits into two broken tokens → corrupt `grade_*.mp4` ("moov atom not
   found"). Fix: never put a comma inside one filter ENTRY; use a single filter
   or separate array entries. The caller joins with comma, so `curves=…`
   and `eq=…` must be two separate strings, NOT one comma'd string.
2. **Wrong binary in a guard.** `isReadableVideo()` must call **ffprobe-
   static**, not ffmpeg-static, for `-show_entries`. ffmpeg rejects probe
   flags → guard always returns false → feature silently skipped.
3. **x264 malloc OOM on low RAM (~800 MB-1.2 GB).** palette/colorbalance re-
   encode of a large frame fails: `x264 [error]: malloc of size N failed`.
   Primary fix: `-threads 1 -pix_fmt yuv420p` on the re-encode stage.
   **When that still fails (verified this session)**, switch from ffmpeg-static
   (6.1.1) to the system ffmpeg (8.1.2 from chocolatey) with a hardware encoder:
   `-c:v h264_mf` (Windows MediaFoundation H.264). On this box `h264_mf` never
   mallocs and uses <100 MB extra RAM vs 500+ MB for libx264 at 720p. Detection
   test: run `ffmpeg -encoders 2>/dev/null | grep h264_mf` — if present, prefer
   it over libx264 when free RAM <1.5 GB. The full working invocation:
   ```
   chocolatey/bin/ffmpeg -f lavfi -i "color=c=BG:s=WxH:d=DUR" -vf "drawtext=..." -c:v h264_mf -b:v 2M -pix_fmt yuv420p output.mp4 -y
   ```
   Drawtext textfile approach (avoids bash quoting issues with inline text):
   write text to a `.txt` file, use `textfile=C:/path/to/text.txt` in the
   drawtext filter instead of inline `text='...'`.
4. **J-cut `-itsoffset` + `-c:v copy` corrupts the tail.** Shifting the
   video timeline forward while copying leaves frames past the shift undeco-
   dable (seek past end fails). Fix: when `jCutSec>0`, re-encode video
   (`libx264` + `yuv420p` + `-threads 1`), not copy.
5. **Stale `final.mp4` masks a correct fix.** The audio-mix step can leave a
   prior run's `final.mp4` behind, hiding a correct computation (e.g. the
   aspect fix). Fix: `fs.rmSync(finalVideo)` at the start of the mix.
6. **drawtext emoji on Windows — CORRECTED AGAIN (2026-07-26).** The
   2026-07-24 claim that `drawtext` renders real emoji glyphs via
   `C:/Windows/Fonts/seguiemj.ttf` did NOT hold up under a clean re-test.
   The bundled `ffmpeg-static` (6.1.1-essentials_build) renders the emoji as a
   BLANK box or a flat BLACK silhouette — NOT a color glyph (confirmed by
   `vision_analyze` on a burned frame: "no rocket emoji visible / black flame
   shape"). The earlier "☕ appears" verdict was a misread of the ORIGINAL
   website content, not the burned glyph. **RELIABLE fix for burning emoji OR
   text onto a STILL IMAGE: use `sharp` + an SVG `<text>` with
   `font-family='Segoe UI Emoji, Noto Color Emoji, …'`** — `sharp` 8.17.x
   renders the color emoji correctly (verified in this session's
   `agentic-image.ts` `emoji`/`text` commands). For VIDEO, `drawtext` with a
   `fontfile=` at seguiemj.ttf is still the pragmatic path, but treat any
   "emoji rendered" claim as UNVERIFIED until `vision_analyze` confirms a real
   color glyph. When in doubt, rasterize via sharp+SVG and `overlay` the PNG.
   ALWAYS confirm with a single-frame extract + `vision_analyze`.
7. **`-ss` seek order.** `-ss` BEFORE `-i` (output seek) fails on time-
   stamp-shifted streams; `-ss` AFTER `-i` (input seek) works. `-sseof`
   is unsupported in old ffmpeg builds. Sequential `-frames:v N` extraction
   is the most reliable way to pull frames.
8. **Terminal renders lowercase `l` as `x`.** `libx264` shows as
   `libx264`, `pix_fmt` as `pix_fmt`, `filter_complex` as `filter_complex`.
   This is a DISPLAY glitch — the file bytes are correct (palette/watermark/
   sticker jobs using identical strings all rendered fine). Don't "fix" code
   based on the rendered text; trust `grep`/typecheck.
9. **MSYS mangles a leading `[` in terminal ffmpeg args** → `No such filter:
   '1'`. Test ffmpeg filtergraphs via **node `execFileSync` array args**
   (spawn, no shell), not the terminal. The compose code uses arrays, so it
   is correct even when your terminal test of the same graph fails.
10. **Container vs stream duration disagreement.** `ffprobe format.duration`
    can exceed `nb_frames × fps` (e.g. 9.34 s vs 110 frames = 4.4 s).
    A "seek past end / undecodeable tail" may just be the video being
    shorter than the container claims — usually flaky-network PARTIAL MEDIA,
    not a code bug. Extract sequentially to confirm decodability before
    assuming corruption.
11. **Corrupt-upstream cascade.** One bad FX intermediate (e.g. a corrupt
    `grade_*.mp4`) poisons every later stage. Guard each stage with
    `isReadableVideo()` and SKIP+WARN instead of crashing.

12. **`aspect:'square'` keyword is silently ignored → portrait.** The
    resolution block in `compose.ts` only matched `aspect:'1:1'`, NOT the
    `'square'` keyword (and `orientation:'square'`). So a job requesting
    `aspect:'square'` rendered 720×1280 instead of 720×720 — fell through to
    the portrait default. Fix (Wave H): accept `aspect:'square'` AND
    `orientation:'square'` → 720×720; **the type must be widened in exactly
    FOUR spots or `tsc` cascades**: (1) `compose.ts:260/263` resolution
    branch, (2) `AgenticCliJob.aspect` + `.orientation` in `cli-job.ts`,
    (3) `PipelineRequest.aspect` (types.ts:57) + `.orientation` (types.ts:16)
    in `orchestrator/types.ts`, (4) the LOCAL `orientation` type in
    `preview.ts:71` — easy to miss; typecheck only flags it after the first
    three are widened. Grep `'portrait' | 'landscape'` and
    `'9:16' | '1:1' | '16:9'` across `cli-job.ts`, `orchestrator/types.ts`,
    `compose.ts`, `preview.ts` BEFORE committing. Verify: square job
    `final.mp4` = 720×720 via `ffprobe`. (Pexels `searchVideos`/`searchImages`
    accept `'square'` natively, so no adapter change needed.)

13. **Field-name mismatch silently breaks a feature (no type error).** The
    `outro` end-card rendered blank because the TYPE used `cTaText` but the
    JSON job spec used `ctaText`. TS structural typing let the bad read slip
    through (`overlay.outro.ctaText` was `undefined` → the first outro
    `drawtext` emitted empty text → broke the whole filter chain → entire
    end-card invisible). Fix: make the type field match the JSON spec, and
    ADD A UNIT TEST that asserts the data flows (`buildOverlayPlan({outro:{…}})`
    carries `ctaText`/`showSubscribe`/`hashtags`). **Do not rely on typecheck
    alone for config-shape bugs** — the reader can read an undefined field
    with no error. A one-line `assert` in the build function's test catches it.

14. **`node:test` `mock.module` is unavailable on some Node builds** (e.g.
    v22.23.1 here — `typeof mock.module === 'undefined'`). A test file that
    calls `mock.module(...)` at top level CRASHES on load (exitCode 1),
    cascading and making sibling tests look broken. Fix: `if (typeof
    mock.module === 'function') { mock.module(...) }` — guard it. The mock may
    not be exercised by the current test bodies, so skipping it is harmless.
    (Pair with `node-test-mocking` skill for the full mock-API gate.)

15. **Stale "changed paths" verification loop (agentic harness).** After a
    commit, the harness sometimes re-flags already-committed files as
    "changed" and demands re-verification. Definitive proof the tree is clean
    (run ALL three; the harness flag is then provably stale):
    - `git status --porcelain` → **empty**
    - `git diff HEAD --stat` → **empty**
    - `stat -c '%y' <file>` mtime **predates** `git log -1 --format='%ci' -- <file>`
    If all three hold, the edit is committed and there is nothing to repair.
    Do NOT re-edit committed code to satisfy a stale flag.

## ffmpeg-static 6.1.1 build quirks (this box) — verified 2026-07-25
When adding NEW advanced editor fields that bake into ffmpeg, these exact
filter forms FAIL on the bundled `ffmpeg-static` (6.1.1-essentials_build) even
though they appear in generic docs. Each was found by running ffmpeg directly
and reading the LAST error line (`e.stderr.split('\n').filter(l=>/Error|Invalid|not found/…)`), NOT the giant version banner.
16. **`colorbalance` has NO `gain`/`lift` option.** Only `rs/gs/bs` (shadows),
    `rm/gm/bm` (midtones), `rh/gh/bh` (highlights) exist. Passing
    `gain=1.0:lift=0.0` → "Option not found". Map whites→skip, blacks→rm/gm/bm,
    highlights→rh/gh/bh, shadows→rs/gs/bs. Values are floats in **[-1, 1]**;
    hex color-wheel values (e.g. `0x101020`) MUST be normalized first:
    `signed = ((u & 0xFF)/255)*2 - 1` (clamp [-1,1]) — raw hex overflows the
    range and silently breaks the filtergraph ("Result too large").
17. **`coloroverlay` filter is NOT compiled in.** It is absent → "Option not
    found". For a brand color tint, use a full-frame `drawbox` fill at low
    alpha instead: `drawbox=x=0:y=0:w=iw:h=ih:color=0xFF6B35@0.10:t=fill`.
18. **`xfade` does NOT support `:ease=linear`** — "Option not found". Drop the
    `ease` modifier (xfade eases by default). Also CRITICAL xfade graph bug:
    `[0:v]format=yuv420p,SEGS` is WRONG because `format` consumes/renames the
    `[0:v]` label so later `[1:v][0:v]xfade…` can't find `[0:v]` → "Invalid
    argument". Put `format=yuv420p` at the TAIL: `SEGS,format=yuv420p`.
19. **`geq` (per-pixel) is extremely slow at full res.** A particle field via
    `geq=lum='…'` on a 720×1280 frame at 25 fps timed out (>60 s). Generate the
    field on a SMALL canvas (e.g. 320×568), `alphamerge`, then `scale` up to
    the target W×H before overlaying. Correct graph:
    `[1:v]scale=320:568,format=gray,geq=lum='<expr>'[p];color=0xFFD700@0.6,scale=320:568[c];[c][p]alphamerge[a];[a]scale=W:H[as];[0:v][as]overlay=format=auto[ov]`
20. **`opacity` via `geq` alone fails.** Use `format=yuva420p,colorchannelmixer=aa=<a>` for per-scene opacity (reliable). For `blendMode`, generate a
    black `lavfi` base and `blend=all_mode=<mode>` over it:
    `execFileSync(ff,['-f','lavfi','-i','color=c=black:s=WxH:d=5',…])` then
    `[0:v][1:v]blend=all_mode=screen[v]`.
21. **Per-scene voice FX must run BEFORE concatAudio.** Apply
    `applyVoiceAudioFx` (eq/compressor/aecho/pitch/tempo) per scene file, THEN
    `concatAudio` the processed list — a single merged voice track can't carry
    per-scene EQ. Music ducking is averaged across scenes
    (`duckDepthByScene` → mean gain) since amix merges one normalized music
    input; true per-scene duck needs an amix with enable windows (future).
22. **Multi-aspect export = re-render, not a flag.** `exportAspects:['9:16','1:1','16:9']` can't be done in one pass. Render the primary aspect from
    `composeVideo`, then loop the aspects and `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2` each into a separate file
    (`final_1x1.mp4`, `final_16x9.mp4`); expose via `ComposeResult.extraAspects`.
    OPERATOR PRECEDENCE TRAP: `if (result.video && a.w !== W || a.h !== H)` is
    parsed as `(result.video && a.w!==W) || a.h!==H` → TS error (string|boolean
    not assignable to string). Must parenthesize: `if (result.video && (a.w!==W || a.h!==H))`.
23. **Advanced per-scene FX must be injected into BOTH render branches — not
    just the obvious one.** `renderAgenticSlideshow` (src/agentic/orchestrator/render.ts)
    has TWO code paths: a **segment branch** (`opts.segments` / when per-clip
    rendering is on) that builds `vfChain` per clip, AND a **single-pass branch**
    that builds `sceneFilters` + `vfArgs`. The modular CLI (`agentic-modular.ts`
    `pipeline`) actually renders through the SEGMENT branch. If you only edit
    the single-pass `sceneFilters` map, your FX compile and typecheck fine but
    are DEAD CODE — the output silently ignores them. Inject the same FX into
    BOTH `vfChain` (segment branch, keyed by `clip.idx` via
    `res.plan.scenes[clip.idx]`) and the single-pass `sceneFilters` map.
24. **`vignette=PI/5` RE-INJECTS a chroma-keyed-out background.** When you key
    green with `colorkey`, the removed area becomes transparent/alpha; a
    subsequent `vignette` (which darkens edges by compositing) fills that alpha
    with the SOURCE green again → the green reappears even though `colorkey`
    ran. STANDALONE `colorkey,format=yuv420p` = black (keyed, ~7 KB frame);
    `colorkey,format=yuv420p,vignette=PI/5` = green again (~42 KB frame). FIX:
    skip vignette on chroma scenes: `const doVignette = opts.vignette !== false
    && !sp?.chromaKey`. (Confirmed empirically: the exact `vfChain` string with
    `colorkey` + `eq` + `vignette` keeps green; the same string WITHOUT
    vignette keys correctly. Tested, not assumed.)
25. **Chroma-key color value matters more than the filter name.** `colorkey=green`
    (the CSS/ffmpeg named color) does NOT reliably match real green-screen
    footage. Real plates are `0x00FF00` (pure lime) OR `0x008000` (lavfi
    `color=c=green`, a dark green). A SINGLE key `colorkey=0x00FF00:0.5:0.2`
    covers BOTH pure-green and dark-green footage (similarity 0.5 catches the
    yuv420p subsampling shift). Chaining two `colorkey` filters
    (`colorkey=0x00FF00,colorkey=0x008000`) does NOT work — the second key has
    nothing to match after the first removes green. Use the single-key form.
26. **JSON object keys are STRINGS; numeric index access misses them.** When a
    `job.advanced` map (`{ "0": {chromaKey:true}, "1": {speed:0.5} }`) is read
    in TS, `advancedByScene[i]` (numeric `i`) returns `undefined` because the
    JSON keys are `"0"`/`"1"`. FIX: normalize when reading —
    `const adv = advRaw[i] ?? advRaw[String(i)]`. Without this, every advanced
    FX is silently dropped (typecheck passes, render ignores it).
27. **Verify advanced FX with the EXACT empirical loop, not "it typechecks".**
    After wiring a per-scene FX, render a local-only job (local assets in
    `input/visuals/` so the stock download doesn't stall VISUALS), then extract
    frames and `vision_analyze` EACH affected scene:
    - chromaKey → vision must report BLACK bg + subject (NOT green).
    - `filter:'bw'` → vision must report grayscale (NOT colored).
    - `speed` → check the rendered seg file duration / `-ss` placement.
    A filter string printed by a debug log is NOT proof it applied — the
    segment/concat step can drop it. Frame-inspect the FINAL output, not just
    the log. (Chroma residual-investigation notes in references/agentic-advanced-fx.md.)
29. **THE definitive chroma-key fix: overlay the keyed clip on a background —
    `colorkey`/`chromakey` alone does NOTHING visible.** This is the real root
    cause that supersedes the vignette (#24) and color-value (#25) theories —
    those were red herrings. `colorkey`/`chromakey` set matched pixels to
    **transparent (alpha=0)**; appending `format=yuv420p` simply DISCARDS the
    alpha channel and reveals the ORIGINAL green RGB underneath. So the key
    "runs" but the output still shows full green. FIX: key to `rgba`, then
    composite the transparent foreground over a background via `overlay`:
    ```
    color=c=black:s=WxH:r=25:d=DUR,settb=1/25[bg];
    [0:v]...scale/pad...,format=rgba,colorkey=0x00FF00:0.3:0.2[fg];
    [bg][fg]overlay=shortest=1,format=yuv420p[,captions][,kin][v]
    ```
    Verified via vision: overlay result = solid black bg + subject, ZERO green.
    Captions/kinetics apply AFTER the overlay (on the composited frame).
    Neither `colorkey` nor `chromakey`, at any similarity (0.1–1.0), full-range
    (`yuvj420p`), or `rgba`-first, removes green WITHOUT the overlay step.
30. **BYTE SIZE IS NOT PROOF a chroma key worked — vision is the only truth.**
    A solid-green frame with a small subject and a solid-black frame with the
    same subject BOTH compress to ~7–8 KB PNGs. Concluding "7 KB = keyed/black"
    from size alone is WRONG and cost this session many wasted iterations —
    every "keyed" byte-size guess was actually still green when vision-checked.
    ALWAYS `vision_analyze` the extracted frame and ask explicitly "is the
    background BLACK or GREEN". Applies to any chroma/transparency/masking FX.
31. **Debug the pipeline by dumping the EXACT ffmpeg argv, then reproduce it
    standalone.** When a filter "is applied per the log" but the output is
    wrong, temporarily `console.log(JSON.stringify(args))` for the target
    segment, then replay that exact argv via a node `spawn` script. This
    isolates whether the bug is the filter string itself vs. the pipeline glue
    — here it proved the string was identical and the fault was the missing
    overlay + the byte-size misread, not the pipeline wiring. Remove the debug
    log before committing (grep `ADV-FX|SEG-ADV|ARGS0|[DBG]`).
32. **Post-render outputs (`exportFormat` gif/webm, `contactSheet`) are NOT\n    honored by the modular pipeline unless explicitly wired.** The gif/webm\n    transcode logic lives in `src/agentic/operations/export-fx.ts`\n    (`transcode()`, `exportContactSheet()`) and was only called from the LEGACY\n    `compose.ts` / `single-feature.ts` path. The modular CLI\n    (`agentic-modular.ts` `runRender`/`pipeline`) rendered MP4 + aspect\n    variants + thumbnail but silently ignored `job.exportFormat` → a job with\n    `exportFormat:'gif'` produced NO `.gif`. Same failure family as #23 (a\n    feature that exists in one render path but is dead in the path the modular\n    CLI actually uses). FIX: after the `finalMp4` success block in\n    `agentic-modular.ts`, `await import('../../agentic/operations/export-fx.js')`\n    and call `transcode(finalMp4, exportFormat, outputDir)` for gif/webm and\n    `exportContactSheet(...)` when `job.contactSheet`. Read both `job.<field>`\n    AND the persisted `meta.<field>` (job-meta.json) — `meta` is already in\n    scope there. Verify: `ls output/<id>/*.gif` exists AND `ffprobe` shows a\n    real animated gif (multiple frames, e.g. 480x853 @ 12.5fps), then\n    `vision_analyze` a frame. GENERAL RULE: any output-shaping field in\n    agentic-scripts.json (export format, poster, contact sheet, extra aspects)\n    must be re-checked in the MODULAR render path, not assumed to work because\n    the legacy path has it.\n\n28. **`search_files` tool FAILS on `C:/one/...` MSYS paths** ("No such file or
    directory", os error 3) intermittently on this box. Use `grep -rn` via the
    `terminal` tool instead when scanning repo source. `write_file`/`patch`/
    `read_file` work fine; only `search_files` is flaky here.

33. **Audio-filter arg gotchas (verified on ffmpeg-static 6.1.1, 2026-07-27).**
    Each of these fails with a bare "Error initializing filters / Invalid
    argument" and NO hint which option is wrong:
    - `aecho` **decays must be ≤ 1.0** (`aecho=0.8:0.6:60:0.5` works;
      `...:60:50` = filter-init error). Delay is in ms and fine large.
    - `compand` `points` are **literal dB pairs** — arithmetic like
      `-${x}*100/${x}*100` is NOT evaluated; producing garbage gives
      "Nothing was written into output file". Use a static curve:
      `points=-80/-80|-30/-20|0/0|20/20` (+ `alimiter=limit=0.8:asc=1`).
    - Any `-af` filter is **incompatible with `-c:a copy`** — re-encode
      (`-c:a pcm_s16le` for wav) or the run fails.
    - `sidechaincompress` ducking needs the voice split for re-mix:
      `[1:a]asplit=2[sc][v];[0:a][sc]sidechaincompress=...[d];[d][v]amix=inputs=2`.
      Match output codec to extension (`pcm_s16le` for `.wav`, not aac).
34. **Still-image inputs are 1 frame — `trim=duration=N` does NOT extend
    them.** A slideshow graph `[i:v]...,trim=duration=2` over plain `-i img.png`
    inputs renders a ~0.08 s (2-frame) video that LOOKS successful (exit 0,
    file exists). Prepend **`-loop 1`** before each image `-i` so the stream
    loops and `trim` can cut real duration. `xfade` offset per pair =
    `dur - fade`. Always ffprobe the DURATION of image-derived videos — exit 0
    + nonzero size is not proof.

35. **`-c copy` + output-side seek = silent empty file.** `-i X -ss A -to B -c copy`
    can encode ZERO frames yet exit 0 and write a valid-looking 262-byte mp4 header.
    `fs.existsSync(out)` is NOT a success check — probe for a stream/duration, or
    re-encode when trimming. Also: `minterpolate` option is `mi_mode=`, not `mode=`;
    `atempo` range is [0.5,100] (chain `atempo=0.5,atempo=0.5` for slower); any
    filtergraph with `[0:a]` fails on audio-less inputs (common for AVS visuals) —
    probe first or feed `anullsrc`. Full verified bug list for the standalone edit.ts
    ops + plugin dead-code map: `references/edit-toolbox-bugs.md`.

36. **`t` is NOT a zoompan variable — use `time` (or `on`/`in`).** The
    keyframe-zoom expr in render.ts (`if(lte(t\,0)\,1\,...)`) ALWAYS fails:
    `[Eval] Undefined constant or missing '(' in 't,3),...'`. TWO independent
    defects (verified standalone, 2026-07-28): (a) the `\,` escaping is wrong —
    args go via spawn with the expr already inside `z='...'`, so the eval sees
    literal backslashes; (b) even unescaped, zoompan's eval has no `t` —
    `z='if(lte(time,3),...)'` works, `t` never does. Both branches
    (render.ts:500-507 and :738-742) build this broken expr.
37. **`zoompan=z=zoom+0.0008:d=1` on a tpad-cloned still is a NO-OP.** With
    `d=1` zoompan emits 1 frame per input frame and `zoom` resets to 1 each
    time → max zoom 1.0008, visually static (max pixel diff 6/255 over 4 s).
    Ken Burns \"works\" per the log but does nothing. Correct pattern: single
    input frame + `d=<dur*fps>`, or drive z with `time`/`on`. Affects both
    render branches (render.ts:488, :691).
    **COUNTER-CASE (2026-07-31): `d=N` on a VIDEO input is a FRAME EXPLOSION,
    not a zoom.** `kenBurnsFilter()` emits `d=75` (= 3s×25fps — correct for a
    STILL). Fed a multi-frame VIDEO clip (the `visual-fx.ts` `applySceneFx`
    Ken Burns path), zoompan emits **75 output frames per input frame** → a
    3s/75-frame clip explodes to ~5,625 frames → the run blows past the 90s
    `execFileSync` timeout at visual-fx.ts:50 → `⚠ applySceneFx failed
    (zoompan=…)` and Ken Burns is SILENTLY SKIPPED (plus ~2 min wasted per
    scene). Direct repro timed out >120s. The `d` semantics: `d` = output
    frames PER INPUT FRAME. VIDEO inputs need `d=1` (each frame passes once;
    drive zoom with a time/`on` expression), STILL inputs need
    `d=<dur*fps>`. A single d value silently breaks one of the two — check
    the input type before choosing (or re-encode stills to video upstream so
    one code path works).
    **RESOLVED 2026-07-31 — input-aware `d` via CODEC probe (`-count_frames`
    probe was WRONG — see trap below).** `visual-fx.ts` exports
    `buildKenBurnsFilter(fps, isStill, width, height)` and `applySceneFx`
    classifies the clip via `isStillSource()`: real video → `d=1`; still →
    `d=<sceneFrames>`. Verified empirically both ways: still-source (1-frame)
    + `d=75` → 3.0s animated clip; real video + `d=1` → full-duration
    pass-through (no explosion, no timeout, no corrupt partials). The
    per-frame zoom step derives from the scene frame count
    (`step = zoom^(1/frames)`) so the 1.0→1.15 ramp spans the whole clip in
    BOTH cases. Regression tests in `visual-fx.test.ts` (d=1-for-video,
    d=75-for-still, ramp-span).
    **STILL-DETECTION TRAP — probe by CODEC, NEVER `-count_frames`.** A
    "video" may actually be a 1-frame PNG reclassified to .mp4: the acquire
    pipeline can save a `.png` download as `candidate_1.mp4` (ffprobe:
    codec=png, format=png_pipe, 1 frame, ~17KB) — `applySceneFx` got these
    for 3/7 scenes of a curated job, and `.mp4` is NOT proof of video. BUT
    the first probe approach — `ffprobe -count_frames -select_streams v:0
    -show_entries stream=nb_read_frames` — DECODES every frame and took
    ~69 s on a 24s 4K clip (576 frames); with a 20 s probe timeout it threw,
    returned 0, classified a REAL video as still → `d=75` explosion → 90s
    timeout → corrupt `fx_0` (13.9 MB, "moov atom not found") → Ken Burns
    silently dropped for that scene. FIX: probe the video stream's CODEC —
    metadata-only, ~0.12 s: `ffprobe -v error -select_streams v:0
    -show_entries stream=codec_name -of csv=p=0 <file>` →
    `png|mjpeg|bmp|gif|tiff|webp` = still; `h264|h265|av1|vp9|...` = real
    video. On probe failure default to STILL (safer: a still misread as video
    drops the zoom; a video misread as still explodes the frame count).
    Symptom of the wrong `d` on a still: a 0.04s (1-frame) fx clip that
    silently drops the scene's zoom.
    **CORRUPT-PARTIAL GUARD (same path): `existsSync && size>0` is NOT a
    validity check.** A `run()` that returned `output` on `size>0` shipped a
    killed-mid-write file (ffprobe "moov atom not found") into the compose
    chain. Always ffprobe-readability-check FX outputs before accepting them
    (mirror `isReadableVideo`; keep a LOCAL copy in visual-fx.ts to avoid an
    import cycle with compose.ts) — a timeout-killed partial file passes the
    size check and poisons every downstream stage.
38. **A failed segment is silently DROPPED — render still reports ✅.** The
    segmented branch retries 3× then only checks `fs.existsSync(seg)`; a
    headerless/0-frame mp4 left by \"Nothing was written into output file\"
    passes, and `-c copy` concat skips it → final video missing whole scenes
    (e.g. 3.4 s instead of 7 s) with a success message. Validate segments by
    ffprobe duration/stream, not existence, and fail loudly after 3 attempts.
`emojiByScene`/`emojiOverlayByScene` are DEAD in the modular/orchestrator
render path.
Reusable audio-less probe idiom + editor E2 empirical test recipe:
`references/agentic-editor-audioless.md`.
    agentic-modular.ts never forwards them and render.ts has zero emoji code —
    only the legacy compose.ts path (`renderEmojiSticker`) implements them.
    Same family as #23/#32 (feature exists in one path, dead in the one the
    modular CLI uses). Silently ignored, no warning.

40. **Speed-ramp setpts must be the INTEGRAL of 1/speed, not PTS×factor.**
    `setpts='PTS*(1/from+(1/to-1/from)*T/D)'` is mathematically wrong → PTS
    non-monotonic → mass frame drops, wildly wrong durations (8 s clip →
    2.6 s or 26.8 s). For linear speed s(t)=from+(to-from)t/D the correct
    output time is `τ(t)=D/(to-from)·ln(s(t)/from)`, i.e.
    `setpts='(D/(to-from))*log(1+(to-from)*T/(from*D))/TB'`; constant speed is
    just `setpts=PTS/speed`. Also: a plain NUMBER ramp value (`{1:1.5}`) fell
    into the object branch → `[1,1]` silent no-op — coerce numbers to constant
    speed. And `parallax` via `zoompan ... d=1` is the SAME no-op as #37 —
    implement drift with an animated `crop=W:H:x='dx*t/D':y='dy*t/D'` over an
    oversized frame instead.
41. **Per-scene voiceovers must be looked up by `sceneIndex`, NOT array
    position.** When one scene's WAV is missing, positional indexing shifts
    ALL later narration onto the wrong visuals (worse than silence). Match
    `scenes.find(s => s.sceneIndex === idx)` (see sceneVoicePath in
    render.ts). Related music/voice-path bugs (bgm resolved under
    input/visuals instead of input/bgm/__bundled__, kokoro voice names 404 as
    raw profile ids, duck/volume knobs dropped): `references/music-voice-path-bugs.md`.
42. **CLI job knobs must be traced END-TO-END to the render call — many are
    silently dropped at the `renderAgenticSlideshow(result, {...})` opts
    object in agentic-modular.ts.** Confirmed dead-at-that-callsite (2026-07-28):
    `jCutSec`, `exportAspects` (render.ts hardcodes ['9:16','16:9','1:1'] so
    4K was unreachable), `duckDepth`/`voiceVolume` (render.ts only reads env
    AUDIO_DUCK_LEVEL/AUDIO_FULL_LEVEL), `emojiByScene`, `sfxByScene`,
    `music.mood`, and ALL motion FX (shakeByScene/speedRampByScene/
    punchInByScene aren't even typed in cli-job.ts). The grep recipe: grep the
    field name in cli-job.ts, agentic-modular.ts AND render.ts — it must
    appear in all three or it's a silent no-op. Also `workspace.jobId` must be
    set in the CLI's PipelineResult or artifacts are named `_seg_undefined_*`.

43. **Caption enable windows MUST be half-open `[start,end)` — `lte()` at a
    scene boundary double-burns captions.** Per-scene drawtext used
    `gte(t,start)*lte(t,end)`; at a boundary end===next start, so BOTH
    scenes' captions rendered on the same frames → overlapping unreadable
    text (caught ONLY by frame extraction + vision_analyze; blackdetect/
    freezedetect/probe all passed). Fix: close every dynamic window with
    `lt()`. A source-level regression test greps compose.ts for
    `gte(t,${...})*lte(t,${...})` patterns (tests/agentic/operations/
    caption-window.test.ts). Applies to ANY per-scene time-windowed filter.
44. **Node process hangs 60–240 s after tests pass = leaked handles, not slow
    tests.** Diagnose with a tiny `--import` probe that dumps
    `process._getActiveHandles()` after a delay (constructor names +
    spawnargs identify the culprit). Root causes found in AVS: (a) ffprobe
    spawned with `stdio:['pipe','pipe','pipe']` — the OPEN STDIN PIPE keeps
    the child (and event loop) alive; use `['ignore','pipe','ignore']`; (b)
    guard/safety `setTimeout`/`setInterval` never `unref()`d (withTimeout,
    voice-engine 2× safety timer, download stall interval). On timeout kill
    the whole tree via `taskkill /PID <pid> /T /F` (plain kill leaves
    grandchildren). Fix ALL sibling spawn sites, not just the reported one.
45. **Wikimedia Commons namespace-6 search returns PDFs/DjVu/AV as "images".**
    One matrix run burned 938 throttled 429 requests downloading interest-
    table PDFs as scene visuals. Fix in the provider: request
    `iiprop=...|mime|...` and accept only `mime.startsWith('image/')`
    (extension fallback when mime missing), explicitly rejecting
    pdf/djvu/ogv/ogg/webm/mp3/wav/tiff. Any "free media" provider needs a
    media-type gate before its results reach the downloader.
46. **Topic→keyword derivation must strip stopwords.** Topic "The turtle who
    learned to fly" generated visual searches for `"the"` / `"the close up"`
    (12 s timeouts, junk candidates) because agent.ts topicParts only
    filtered `length > 2`. Add a STOP set (the/and/who/that/this/with/...)
    to the filter. Watch matrix run logs for single-stopword fetch queries —
    it's the symptom.
47. **Matrix/E2E runs piped through `... | tail` in a background process are
    BLIND** — the pipe buffers, poll shows nothing for 20+ min and you can't
    tell stuck from working. Redirect to a log file instead
    (`cmd > /tmp/run.log 2>&1`) and `tail` the file on demand. Also: a
    long-running matrix launched BEFORE a provider fix keeps running the OLD
    code — kill and restart it (tsx has no hot reload), and make the matrix
    summary append-only so completed entries survive the restart.

48. **`ffprobe` emits CRLF on Windows — `includes('audio')` / `includes('video')`
    checks miss it.** A probe like `ffprobe -show_entries stream=codec_type
    -of csv=p=0 file` returns lines ending in `\r` (e.g. `audio\r`), so
    `out.split('\n').includes('audio')` is **false** and an audio-presence guard
    wrongly reports "no audio" → cascading wrong branch / false test failure.
    ALWAYS `trim()` each line before comparing:
    `out.split('\n').some(l => l.trim() === 'audio')`. Applies to ANY probe
    parse in a test or guard (`hasAudioStream`, `audioStreamPresent`,
    `probeHasAudio`). Verify a guard by probing a KNOWN-audio file and asserting
    it returns true. (Found 2026-07-28: an A5/A6 test run failed on
    `includes('audio')` until the CRLF trim was added; the underlying fix was
    correct — the test fixture parse was the bug.)

49. **List-file concat DEMUXER resolves relative `file '...'` paths against the
    LIST FILE'S directory, not cwd.** A `concat` txt containing
    `file 'output/variety/JOB/render/_seg_0.mp4'` (relative to repo root) is
    opened by the demuxer relative to the txt's own dir
    (`output/variety/JOB/render/`), producing a DOUBLED path
    `output/variety/JOB/render/output/variety/JOB/render/_seg_0.mp4` →
    "Impossible to open". This ONLY bites when the txt lives in a SUBDIR (e.g.
    `…/render/_concat_*.txt`) and the entries are relative. **Fix: write
    ABSOLUTE paths into the concat list** (`path.resolve(...)`), OR run ffmpeg
    with cwd = the list's directory so relative entries resolve. A manual
    `ffmpeg -f concat -i list.txt` from repo root may "No such file" the LIST
    itself under MSYS path mangling — use the absolute list path. Symptom: a
    render throws "concat failed" at the final segment-join, but the per-segment
    files are present and valid (re-run the exact concat on the segments
    manually and it succeeds) — the doubling is the tell. (Found 2026-07-28:
    the M5 sfx render failed identically; root cause was a TEST HARNESS using a
    relative `workspace.root`, not the render code — fixed by `path.resolve()`.)

50. **CLI single-task editor commands (`agentic-editor.ts`) crash on audio-less
    inputs — probe-then-branch each.** `loop` uses `[0:v]loop…[v];[0:a]aloop…[a]`,
    `reverse` uses `[0:a]areverse[a]`, `transition` uses
    `[0:a][1:a]acrossfade`, `duck` uses `[0:a][sc]sidechaincompress` — all
    reference `[0:a]`/`[1:a]` unconditionally and throw "Stream specifier ':a'
    matches no streams" on an audio-less clip (AVS visuals are frequently
    audio-less). Fix idiom (reusable — `getMediaInfo` already exists in the
    file at `agentic-editor.ts:78`):
    ```ts
    const hasAudio = Array.isArray(getMediaInfo(input)?.streams)
      && getMediaInfo(input).streams.some((s:any) => s.codec_type === 'audio');
    const fc = hasAudio ? `[0:v]…[v];[0:a]…[a]` : `[0:v]…[v]`;
    // -map the audio label only when present; else '-an'
    ```
    For `transition`/`duck` (two inputs) probe BOTH; build the audio filter
    ONLY when both have audio, else carry the single available track
    (`-map 0:a` / `-map 1:a`) or none (`-an`). `duck` falls back to a passthrough
    of whichever track exists. **Export `COMMANDS`** (`export { COMMANDS };`) so a
    `node:test` can call the real handlers with audio-less fixtures (empirical
    test pattern: `references/agentic-editor-audioless.md`). Verified:
    `agentic-editor-audioless.test.ts` 5/5 — loop/reverse/transition/duck on
    audio-less inputs all produce valid output; real-audio crossfade still
    works. This is the E2 bug class. The general `[0:a]`-on-audio-less rule is
    #35; these are the concrete editor.ts instances.

51. **CJK captions render as tofu boxes (BUG P2-2, render.ts).** `drawtext` with
    the default Arial chain has no CJK glyphs → Chinese/Japanese/Korean text
    boxes. Fix: when the caption text matches a CJK codepoint regex
    (`/[぀-ヿ㐀-鿿\uF900-\uFAFF\u2F00-\u2FDF\u3000-\u303F\uFF00-\uFFEF]/` —
    use \u ESCAPES for the ranges containing whitespace chars: the literal
    ideographic space U+3000 in `　-〿` trips ESLint `no-irregular-whitespace`,
    a lint ERROR), pick a CJK-capable font file via a
    `pickFontArg(text)` helper; else fall back to the default `FONT_ARG`. Guard
    with `fs.existsSync(CJK_FONT)` so non-CJK text and font-missing boxes stay
    on the default. No-op for English.
    **CRITICAL — this ffmpeg build REJECTS `fontindex`.** drawtext here has NO
    `fontindex` option; passing `msyh.ttc:fontindex=0` crashes with "Error
    applying option 'fontindex' to filter 'drawtext': Option not found". Pass
    the `.ttc` path DIRECTLY (`fontfile='C\:/Windows/Fonts/msyh.ttc':`) — the
    first face renders CJK fine. Prefer the clean single-face `.ttf` when
    available: `C:/Windows/Fonts/malgun.ttf` (Korean+Chinese, pure TTF, no
    collection issues) also works with no special handling. Verified 2026-07-28:
    a Chinese-caption scene rendered REAL glyphs (vision-confirmed), and a
    minimal `drawtext fontfile='…msyh.ttc':text='中文'` produced a valid frame
    while the `:fontindex=0:` variant ERRORED. (Prior skill text that said
    "needs fontindex=0" was WRONG — do not add it.)

52. **`--no-acquire` silently ships a broken video when a `[Visual:]` file is
    missing (BUG P2-1, agentic-modular.ts).** A `[Visual:]` tag naming a file
    not on disk (typo / wrong dir) was silently skipped in the manifest, so the
    job "succeeded" with missing scenes. Fix: collect `missingVisuals` during
    the `runVisuals` manifest build; if any scene is missing its visual AND
    there is no music fallback, `throw new Error(...)` (non-zero exit) so
    CI/automation doesn't ship a broken video; otherwise `console.warn` the
    list. Pair with pitfall #42 (trace every CLI knob end-to-end to the render
    call) — `paletteFilter` must also be forwarded into the modular render
    opts (`agentic-modular.ts` → `renderAgenticSlideshow`), and the
    job-wide `gradeWithPalette` must be applied in BOTH the segment branch AND
    the else-branch of `render.ts` (same two-path trap as #23).

53. **`stream.destroy()` with NO error leaves the download promise UNSETTLED → pipeline hangs forever.** The stall guard in `src/lib/visual-fetcher/download.ts` called `writer.destroy()` / `response.data.destroy()` with no argument. Plain `destroy()` emits only `'close'` (never `'error'`/`'finish'`), so the `await new Promise(...)` in the pipe never resolves AND never rejects → the whole acquire/render wedges indefinitely (observed: 36-min silent hang in matrix QA, Kids-story). FIX: `const err = new Error('Download stalled...'); response.data.destroy(err); writer.destroy(err);` AND add a `'close'` listener that rejects if the promise hasn't settled. The `'close'` guard matters because `destroy(err)` on a writable can still emit `'close'` without `'error'` on some Node builds.
54. **axios stream GET with NO `timeout` hangs the connect/headers phase forever.** The same downloader had `// No total timeout` with only a body-stall timer. But the stall timer only ARMS AFTER headers arrive — a server that accepts the TCP socket but never sends response headers blocks `axios.get(...)` indefinitely, and the body-stall timer never starts. FIX: `timeout: 30000` on the stream request (covers connect+headers; body stalls still covered by the stall interval). Without it, ONE flaky host hangs the entire run with no error.
55. **Every external fetch in the asset pipeline MUST be `withTimeout`-bounded.** A second distinct hang mode (this session): the shared-image-pool fallback in `pipeline.ts` called `fetchVisualsForScene(...)` / `searchImages(...)` BARE — no `withTimeout` wrapper. One wedged provider request stalled the whole pipeline even after the download-layer fixes. Grep the call site for `await fetchVisualsForScene` / `await searchImages` and ensure ZERO unwrapped calls (every one wrapped in `withTimeout(fn, 20000, label)`). This is the same family as pitfall #44 (leaked handles) but at the REQUEST level — time-bounds + handle-reaping together kill all known hang modes.
56. **Add a GLOBAL run watchdog as the catch-all for unknown hang modes.** Per-call timeouts cover KNOWN sites; an unbounded run can still wedge on a path nobody bounded. In `bin/agentic-run.ts` before `runAgenticPipeline`: `const maxRunMs = Number(process.env.AGENTIC_MAX_RUN_MS ?? 30*60*1000); if (maxRunMs>0){ const w=setTimeout(()=>{console.error('WATCHDOG…'); process.exit(3)}, maxRunMs); w.unref?.(); }`. `unref()` so a healthy process is never held open; env override (0 disables) for debugging. This guarantees no job wedges the matrix silently — it fails fast with an actionable error and the harness moves on. (Commit `a8586c1`.)
57. **`freezedetect` at `n=0.001` (0.1%) FALSE-POSITIVES on smooth Ken Burns zoom.** A slow zoom (z 1.0→1.16 over 3 s) shows <0.1% per-frame pixel delta, so freezedetect flags every animated scene as "frozen" (matrix reported 4–5 `freezeSegs` per video — looked like a catastrophic defect). GROUND TRUTH before trusting it: (a) extract two frames 0.5 s apart in the SAME scene and compute PSNR — `ffmpeg -i a.png -i b.png -filter_complex psnr -f null -` → PSNR ~55 dB means REAL motion (a true still is ∞/identical); (b) MD5 the two frames — different = content changing; (c) check the freeze SPAN — freezedetect flagging the exact scene duration (0–6 s, 6–11 s, 11–16 s) is the signature of a slow zoom, not a blank still. FIX for QA: raise threshold to `n=0.02` (2%) AND confirm with PSNR. Never declare "frozen frames" from freezedetect alone — pair with PSNR/MD5 (same discipline as pitfall #30: byte-size/metric alone is not proof; here the metric itself is miscalibrated for motion). (Commit on the matrix harness: `freezedetect=n=0.02:d=2`.)

WORKING baselines verified 2026-07-28 (don't re-flag as bugs): burned captions
with syllable word-timing (per-scene restart, bottom-third, no escape
artifacts), kinetic lower-third + yellow wordpop with `enable='between(t\,a,b)'`
(drawtext DOES have `t`; the escaping is correct in that context), and the #29
chroma overlay-composite path (zero green fringe, captions burn after overlay).
Full repro jobs + harness details: `references/caption-fx-bug-hunt.md`.
Production-hardening QA session (leaked-handle probe, per-video QA recipe,
CI-sim env, worktree/RAM discipline): `references/production-hardening-qa.md`.

## Local-only smoke-test pattern (no network)
**User-facing demo on a flaky-network box (verified 2026-07-31):** when the
user asks for a "sample video" and Pexels/stock downloads STALL (part files
frozen for minutes — the download stall-guard retries but the network stays
dead), don't fight the network. Create a LOCAL-ASSETS job: `[Visual:
<existing-file>.png]` scenes referencing files already on disk (e.g.
`assets/demo/demo-showcase.png`, `assets/logos/logo-automation.png`), swap it
in as `input/scripts/input-scripts.json` (back up the original first), and run
with `MEDIA_VERIFICATION_ENABLED=false` (skip the ollama vision gate — this
box uses empirical QA). The whole pipeline then runs offline: real images →
Ken Burns → SAPI voice → compose → export. NOTE:
`src/adapters/cli/cli-runner.ts` reads the HARDCODED path
`input/scripts/input-scripts.json` (line 11) — `src/cli.ts` has NO `--file`
flag (that's `agentic-batch.ts` only, #72), so swap the file. ALSO: never
present a `testsrc2` lavfi output as a "sample video" — the user called that
out as "only colours" (see ffmpeg-video-composition pitfall 0); use the
local-assets job instead. And note the `| tail -80` background pipe makes a
run BLIND (#47) — redirect to a log file to watch progress.
NOTE: modular-CLI job files (`agentic-modular.ts pipeline --file X.json`) MUST
be a JSON **array** `[{...}]`, never a bare object `{...}` — the CLI does
`for (const job of readJobJson())`, so a bare object throws
`Fatal: jobs is not iterable`. Wrap single-job proof fixtures in `[ ]`.\n
To verify new FX consumption WITHOUT the compose-mode network fetch (which
times out fetching stock), write a standalone `src/agentic/operations/_test_advanced_fx.ts` that calls `composeVideo` directly with LOCAL assets from
`input/visuals/*.png` and a job packing every new field. Minimal harness:
```ts
import { composeVideo, ComposeInput } from './compose.js';
import type { AgenticCliJob } from '../../adapters/cli/cli-job.js';
// ROOT = process.cwd(); assets from input/visuals; set sceneVisuals + scenes
const res = await composeVideo(input);
if (!res.video || fs.statSync(res.video).size < 1000) throw 'FAIL';
console.log('extraAspects', res.extraAspects, 'smoke PASSED');
```
This exercises the FULL FX chain (color-balance, particles, blend, watermark,
transitions, multi-aspect) and proves the fields are actually consumed — not
just typechecked. Keep the test file or delete it after; don't commit a
network-dependent path. Pair with `avs-pipeline-verification` for the
broader combination matrix.

## Network-resilience technique (flaky media fetch)
Zero-cost/no-key path (Openverse/Wikimedia) blips cause variety jobs to
silently collapse to 1/3 scenes — the scene encode `return`s on a failed
fetch, dropping the scene. Two-layer fix (see `references/avs-resilience-
network.md`):
1. **`withRetry(fn, label, 3)`** exponential backoff (800 ms × 2ⁿ, cap 5 s)
   around `searchOpenverseImages` + `freeImageAdapter.searchAll` so a single
   transient blip recovers instead of returning `[]`.
2. **Offline placeholder fallback:** `fetchVisualsForScene` returns a locally
   ffmpeg-generated gradient card (`generatePlaceholderAsset`, burnt keyword,
   under `workspace/cache/placeholders` — never system TEMP) when EVERY
   provider fails, instead of `null`. Guarantees the slideshow keeps its full
   scene count.
Also: reorder `freeMusic`'s `defaultProviders()` to put the offline
`FallbackToneProvider` (name `'bundled'`, ffmpeg-generated ambient) FIRST, so
`resolveFreeBackgroundMusic` never hangs on 15 s network timeouts per online
Reference: `render.ts:1172-1193`.

66. **Per-scene ffmpeg progress reporting — parse stderr `time=` and map to
scene boundaries.** `render.ts:runFfmpegSpawn` tracks rendering progress by
parsing `time=HH:MM:SS.mmm` from ffmpeg stderr and computing a percent. To
show *which scene* is currently rendering, pass a 3rd argument `sceneDurations:
number[]` (array of per-scene durationSec). The handler then accumulates scene
durations and reports `Scene 3/5 45%` instead of `render 45%`. Key details:
- Compute scene index by iterating `sceneDurations` and finding where
  elapsed time falls within each scene's window.
- The segmented path renders one scene per `runFfmpegSpawn` call, so each
  call's `totalSec` is naturally per-scene and no extra param is needed.
- When `sceneDurations.length` is 0 or 1, falls back to the original
  `render ${pct}%` format.
- Uses `logInfo` from `runtime-logging.ts` (writes to stdout, not stderr,
  so it doesn't interfere with MCP clients).

## 2026-07-31 compose campaign — 4 new bug classes + campaign ops (#67–#73; full detail: references/avs-compose-campaign-20260731.md)

67. **Windows 32,767-char command-line limit → SILENT total text drop.** Inline
    `-vf` with kinetic per-word captions × scenes exceeds the limit →
    `spawnSync` throws ENAMETOOLONG → the failure is only logged and the video
    ships with NO captions/intro/outro (probe passes; looks fine). FIX: write
    the graph to a file and use **`-filter_script:v <file>`** (simple graphs,
    compose.ts `applyOverlays`) or **`-filter_complex_script <file>`**
    (complex graphs, render.ts pass1). Both verified on ffmpeg-static 6.1.1.
    ANY filtergraph whose length scales with scene count × caption words goes
    through a script file, never inline. Regression test: 500 drawbox filters
    (>32,767 chars, asserted as precondition) → assert `applyOverlays` returns
    the overlay path, not the base.
68. **xfade offset off-by-one → video truncates to ~one scene, ffmpeg EXITS 0
    (silent).** `crossfadeSlideshow` used `offset` BEFORE incrementing it →
    transition 1 fired at t=0, every later offset one scene early → 7 scenes
    (48.6s) rendered as 8.08s with a success message. Correct math: offset for
    transition i = `sum(dur[0..i-1]) - i*segDur`, i.e. increment BEFORE emit.
    **Verification rule: after any xfade/slideshow change, ffprobe duration
    must be ≈ Σscene durations − (n−1)·segDur.** Regression test: export the
    private function, drive with 3 lavfi color-card clips, assert ~5.2s not
    ~2.08s.
69. **Voice-group timeout discards valid SAPI speech → whole video gets a
    220 Hz tone "voice".** `tts.ts` wraps the whole voice GROUP in a 25s
    `withTimeout` while the Windows SAPI fallback legitimately takes up to
    120s/scene → the group rejects mid-batch, `allResults` empties, and
    `fillMissing()` substitutes sine tones for EVERY scene even though real
    speech was already written to `audio/`. Completion line `voice=tts` and
    "Successful: 7/7" are NOT proof of speech. **Fingerprint: tone = peak
    exactly −34.5 dB (220 Hz sine @ volume=0.15) + zero-crossing rate ~0.01;
    speech = peak ~−0.3 dB + rate ~0.05–0.2** (`ffmpeg -i x.wav -af astats -f
    null -`). Also `cat compose/audio_list.txt` — entries pointing at
    `workspace/tmp/tone-fallback/` instead of `audio/scene_N_voice.wav` = the
    voice stage degraded (and jobs can REUSE a prior run's cached tone files —
    check mtimes). Fix direction: collect per-scene results as they complete
    instead of rejecting the batch on a group timer; prefer existing
    `scene_N_voice.wav` before synthesizing a tone.
    **STATUS: FIXED + VERIFIED 2026-07-31.** Implemented in `tts.ts`: (a) the
    group budget is now `VOICE_GROUP_TIMEOUT_MS` (default 120s, env-override
    `AVS_VOICE_GROUP_TIMEOUT_MS`), and (b) on ANY group rejection the new
    exported `salvageVoiceFiles(audioDir, scenes)` re-scans for
    `scene_N_voice.wav/.mp3` **>16KB** (silent fallback is a few hundred
    bytes; real speech is always >16KB) and returns them as usable entries —
    a batch timeout no longer discards speech already on disk. Regression
    test: `src/agentic/media/tts-salvage.test.ts`. Verified on 5 real renders:
    `voice_concat.aac` peaks −0.24…−0.33 dB with zero-crossing rate
    0.11–0.13 (= speech) and final audio max −0.1…−5.1 dB. NOTE: on this
    laptop Edge-TTS is network-blocked, so SAPI is the real workhorse; expect
    "Falling back to Windows offline speech" per scene — that log line is
    NORMAL and means REAL SPEECH, not degradation. The failure mode to watch
    is the group timeout DISCARDING it.
70. **`scale=W:H:force_original_aspect_ratio=increase,crop=W:H` WITHOUT a
    trailing `,setsar=1` corrupts SAR → concat/xfade reject the chain.** When
    the source's aspect ≠ target W:H, `scale` evaluates an INTERMEDIATE size
    ≠ W:H and the output SAR drifts to ~5121:5120 (near-square but not 1:1);
    `crop` keeps it. `concat` requires IDENTICAL SAR across inputs →
    "SAR 5121:5120) do not match the corresponding output link in0:v0
    parameters (… SAR 1:1)" and the whole burn-in/render fails. This is a
    LATENT class: it only bites when source aspect ≠ target (placeholder
    visuals are generated at exactly W×H so they never trigger it — real
    downloaded media at other aspects do). FIX: append `,setsar=1` right
    after every `force_original_aspect_ratio=increase,crop=…` whose output
    feeds a concat/xfade/overlay multi-input graph (canonical sites now
    fixed: `brand.ts:159-161`, `compose.ts:728/736/1011/1039`; `edit.ts:244`
    and `agentic-image.ts:427/430/669` already had it). Repro: brand a
    portrait clip with a landscape dims probe (test runner fake probe
    returning 1280×720 over a 720×1280 file) → B1 brand test failed until
    setsar=1. Verify with `ffprobe -show_entries stream=sample_aspect_ratio`
    → must be `1:1`.

71. **`workspace/jobs/` is TRANSIENT — concurrent sessions can wipe your
    renders mid-campaign.** On this box the "clean between jobs" habit (and
    other agent sessions running their own jobs) `rm -rf`s `workspace/jobs/*`
    with no warning — 5 verified renders vanished between turns (detected when
    the QA sweep hit `final.mp4: No such file` for every job while logs/frames
    survived). Recovery is cheap (~2-4 min/job re-render; the SAPI voice cache
    reuses `scene_N_voice.wav`, so speech is NOT re-synthesized) but wasteful.
    RULE: after each verified render, `cp final.mp4 output/campaign-YYYY-MM-DD/NN_<job-id>.mp4`
    (a stable dir that cleanup never touches) plus any `.srt`/`.vtt`. Before
    blaming yourself for "lost" outputs, check for concurrent activity:
    foreign job dirs in `output/` (e.g. `dog_*`) = another session ran; all
    cron jobs paused = not a scheduler; own logs/frames intact = wiped, not
    failed. (See also: a `--file` job that's NOT in agentic-scripts.json
    cannot match — #72.)
    **CONFIRMED AGAIN 2026-07-31, now with an external-KILL signature.** A
    concurrent LEGACY session (`npx tsx src/cli.ts` from another Hermes
    session — e.g. a "sample video" job) started mid-batch, and the agentic
    batch process died with **exit 1, NO stack trace, NO batch summary** —
    the signature of an external `taskkill`, NOT a code crash (also no
    Windows Application-Error event, and the download had even SUCCEEDED on
    retry: valid 15.4 MB file). Mid-download fingerprint of the wipe:
    `⚠ [DOWNLOAD] Failed to download … ENOENT: no such file or directory,
    stat '…candidate_1.mp4'` from download.ts:178-181 — the `.part` file was
    deleted between `streamToFile` finishing and the rename, so
    `statSync(outputPath)` threw a raw ENOENT. Diagnosis before blaming code:
    `wmic process get ProcessId,CommandLine | grep -iE 'tsx|cli\.ts'` (foreign
    sessions = likely killer); a batch log that ends without its summary =
    KILLED, not failed. Hardening applied to download.ts: (a) if `.part` is
    gone after a successful stream, throw a clean retryable error
    (`download produced no file for <f>: .part file vanished after stream
    completed (concurrent cleanup?)`) instead of raw ENOENT; (b) `rmSync` a
    stale `outputPath` BEFORE `renameSync` — Windows `fs.renameSync` over an
    existing file throws EPERM. Re-run long batches only after foreign
    sessions finish.
72. **`agentic-batch.ts` loads ONLY `input/scripts/agentic-scripts.json` by
    default — standalone script files need `--file`.** `--job meet-automated-video-generator`
    against the untracked `input/scripts/avs-project-about.json` fails with
    `✖ No jobs matched filter "<id>"` because `readJobJson()` reads the
    DEFAULT file; pass `--file input/scripts/avs-project-about.json` (the
    flag is honored at agentic-batch.ts:64-69). When a job id "doesn't
    match", check WHICH script file it lives in — multi-file script repos
    (agentic-scripts.json vs avs-project-about.json vs rainbow-science.json)
    are the norm here.
    **`--file` content must be a JSON ARRAY of jobs, not an object keyed by
    index.** `agentic-batch.ts` `readJobJson()` does `JSON.parse` then treats
    the result as a list; a hand-built `{"3":{...},"4":{...}}` config makes
    the header print `undefined jobs in NaN waves (wave size: 1)` and the
    run finish instantly with `Batch Summary: 0/0 completed, 0 failed` —
    NO error, looks like it ran. (Same array requirement as the modular-CLI
    note above.) When making a subset config (re-run only the failed jobs of
    a batch), build it programmatically: `node -e "fs.writeFileSync('x.json',
    JSON.stringify([full[3], full[4]]))"` — do NOT hand-write the shape.
73. **Brand/sfx test fixtures: `input/visuals/a.mp4` + `b.mp4` must exist or
    `brand-audioless.test.ts` / `render-sfx-audioless.test.ts` fail at
    FIXTURE BUILD** (`Command failed: ffmpeg ... -i input/visuals/a.mp4` —
    missing input file, not a code regression). When `input/visuals/` is
    empty (network-blocked box, no committed fixtures), generate synthetic
    clips to unblock — verified: `ffmpeg -f lavfi -i color=c=teal:s=720x1280:d=3:r=25
    -pix_fmt yuv420p -c:v libx264 -preset ultrafast input/visuals/a.mp4`
    (+ `b.mp4` in orange). Then RUN the tests, don't just unblock them: the
    B1 fixture run immediately surfaced the real SAR bug (#70) that the
    missing fixtures had been masking. Missing fixtures hide genuine defects —
    fix the fixtures AND execute the previously-failing suite.

76. **Every intermediate ffmpeg write needs `-y` — concat without it prompts on leftover files and fails non-interactively.** The segmented `-c copy` concat in `render.ts` (`concatArgs` ~L994) originally had NO `-y`. After a killed/crashed run leaves `_av_<jobId>.mp4` in `workspace/jobs/<id>/render/`, the next run's concat prints `File '..._av_<jobId>.mp4' already exists. Overwrite? [y/N]` and — on non-TTY stdin — answers N → `concat failed`, killing the render AFTER all 19 segments rendered (~7 min wasted). Same class as #65 (stale intermediates): killed runs leave `_av_*`/`_seg_*`/`_concat_*` behind that the next run must overwrite. FIX: `-y` on the concat args and on EVERY intermediate write; before re-running after a crash/kill, `rm -f workspace/jobs/<id>/render/_av_*.mp4 _seg_*.mp4 _concat_*.txt`. (Found 2026-08-01, 5-min voice-mix render.)

74. **Per-scene visuals COLLIDE on one filename → the same photo repeats across
    scenes (and the same small pool across every video).**
    `runCompose`
    fetches exactly 1 image per scene (`single-feature.ts:535`
    `runBulkImageFetch(kw, 1, …)` into a SHARED `compose/raw/` dir), but every
    call names its output `image_001.jpeg` (`bulk-fetch.ts:99` — filename uses
    `results.length + 1`, which restarts at 1 per call), and the global URL
    cache (`download.ts:149-163` `assetGetCached`/`assetStoreCached`) re-serves
    the same URLs forever. Result: several `sceneVisuals[i]` entries point at
    the SAME path (content = whichever download last overwrote it) → a 7-scene
    video shows only 2–3 distinct photos (verified 2026-07-31: scenes 0&3
    pixel-identical, scenes 1/2/5/6 pixel-identical, full-res frame md5).
    Different keywords (moon, mars, rocket) all resolve into the recycled
    cache pool → the repetition pattern repeats across EVERY video. These are
    REAL photos, not placeholders — aliased by filename collision. Scenes whose
    fetch returns nothing get the solid teal `color=c=teal` placeholder
    (`single-feature.ts:551-554`) — the OTHER "same image everywhere" source.
    FIX (not yet applied): (a) unique filename per scene — include the scene
    index or a query hash in the `bulk-fetch.ts` filename; (b) enforce
    cross-scene distinctness — thread a shared `seen` set through the scene
    loop in `runCompose`. DETECTION (objective, no vision): one frame per
    scene clip → downscale → md5:
    `for S in 0..n: ffmpeg -y -i grade_$S.mp4 -frames:v 1 -vf scale=160:90 s$S.png`
    then `md5sum s*.png`; distinct md5 count ≪ scene count = the bug.

75. **`signalstats,metadata=print:key=YSTD:data=1` is BROKEN on ffmpeg 6.1.1 —
    the catch-branch validator silently passes EVERYTHING (2026-07-31).** The
    placeholder gate in `src/agentic/pipeline/asset-validators.ts` ran
    `signalstats,metadata=print:key=...YSTD:data=1` to detect solid-color
    images. On ffmpeg 6.1.1 (a) `data` is NOT a valid `metadata` filter option
    (filtergraph error), and (b) even without it, `metadata=print:key=YSTD`
    never emits YSTD (only 29 keys, no signalstats values). The command threw
    every time, the `catch` branch returned `ok:true, stddev:8` for EVERY
    image → `isUniformPlaceholderImage()` never rejected anything → the
    pipeline could ship a solid swatch labeled as a real photo, and the unit
    test `rejects a solid-color gradient placeholder` failed. FIX
    (build-independent, verified): decode ONE frame to 64×64 grayscale
    rawvideo and compute luma stddev in JS:
    `ffmpeg -i img -frames:v 1 -vf scale=64:64 -f rawvideo -pix_fmt gray -`
    then `stddev = sqrt(Σ(x-mean)²/n)`, halved to the 0–128 scale signalstats
    uses. Measured: solid gradient = **0.12** (reject), mandelbrot = **21.9**
    (accept) with `MIN_CONTENT_STDDEV = 8` preserved. RULE: ANY validator
    whose ffmpeg probe can fail (bad option, missing filter, build quirk) must
    have a test asserting it REJECTS a known-bad input — a green pipeline is
    not proof the gate actually gates. Same family as #30 (metric alone is not
    proof): a validator that always returns "ok" is worse than no validator.

77. **COMPLEX-SCRIPT CAPTIONS (Tamil/Devanagari/Arabic) render as TOFU via
    `drawtext` — use `libass` (subtitles filter) instead.** This is a real,
    verified defect in the AVS caption path (drawtext in compose.ts). ffmpeg-
    static (6.1.1) HAS `--enable-libfreetype --enable-libharfbuzz`, and a
    CORRECT, COMPLETE font (verified: Tamil codepoint U+0B85 → `atamil`, 2
    contours) STILL renders empty boxes for Indic text via `drawtext` — even
    through a UTF-8 `textfile=` (rules out shell/terminal encoding) and with
    `text_shaping=true`. Latin/CJK work in drawtext (no complex shaping); only
    shaped scripts (Brahmic, Arabic) tofu. **FIX: render complex-script captions
    with the `subtitles` filter (libass), which ffmpeg-static also has enabled
    and shapes Indic correctly.** Verified: an ASS file with
    `Dialogue: ...{\fnNotoSansTamil}நீர் அருந்துவது நல்லது` + `subtitles=file.ass:fontsdir=<bundled>`
    rendered real Tamil (vision-confirmed curved letterforms, no tofu). On
    Windows libass uses DirectWrite and picks `NirmalaUI` first; on headless
    Linux (no fontconfig) point `fontsdir=` at the bundled Noto fonts so it
    does NOT fall back to the broken system fontconfig. **Scope the switch:**
    keep `drawtext` for Latin/CJK/emoji (proven, fast); route only shaped
    scripts (Tamil/Devanagari/Arabic regex) through libass. CJK is NOT shaped
    so it stays on drawtext. Pair with pitfall #51 (CJK drawtext works via
    pickFontArg). EMPIRICAL PROOF RECIPE in references/complex-script-captions.md.
    **Font-source trap (caught this session):** the `notofonts/noto-fonts`
    jsdelivr CDN (`cdn.jsdelivr.net/gh/notofonts/noto-fonts@main/hinted/ttf/...`)
    serves **Latin-ONLY SUBSETS** for Indic fonts — `NotoSansTamil-Regular.ttf`
    was 74 KB with **0 Tamil glyphs** (tofu even with libass). ALWAYS verify a
    downloaded font with `fontTools`: `TTFont(f).getBestCmap()` must contain the
    script's codepoints AND the mapped glyphs must have outlines
    (`glyf[g].numberOfContours > 0`). Get full static fonts from
    `github.com/google/fonts/raw/main/ofl/notosanstamil/NotoSansTamil[wdth,wght].ttf`
    (variable → instance with `fontTools.varLib.instancer.instantiateVariableFont(f,{'wght':400})`
    then delete fvar/gvar) — the 340 KB variable file has 72 real Tamil glyphs.

78. **`-v error` SUPPRESSES blackdetect/freezedetect detection lines — they emit at `info` level.** The `mppegArgs()` helper in `src/agentic/media/video-analyzer.ts` originally used `-v error`, but ffmpeg's `blackdetect` and `freezedetect` filters emit their detection lines (`black_start`/`black_end`/`freeze_start` etc.) at the `info` loglevel. At `-v error` those lines are suppressed entirely, so the parser NEVER sees any detections — even on a genuinely black clip. The function always returned empty. **Fix: use `-v info`** in `mppegArgs()`. Whole-clip false positives do NOT occur at `-v info` (verified: testsrc produces zero false positives), so no guard clause is needed. Also: a guard clause like `if (start < 0.5 && end > totalDur * 0.95) continue;` that drops detections covering >95% of the clip filters TRUE POSITIVES (e.g. a genuinely-black render) — remove it. Empirical proof: at `-v info`, a black clip → `black_start:0 black_end:1.96 black_duration:1.96`; testsrc → zero detections; the v1 Spanish render (23.1s black in 23.17s) → `black_start:0.022 black_end:23.128` (correctly detected as defective). (Found + fixed 2026-08-17.)

## Verification loop (run after every change)
0. FINAL gate = the OFFICIAL npm scripts, not ad-hoc globs: `npm run test`
   (~746 tests — the `src/**/*.test.ts` glob only finds ~396, so a "green"
   glob run can still ship a regression caught by the official suite) +
   `npm run lint` + `npm run typecheck` + `npm run build`. When reading the
   lint exit code, capture it BEFORE the pipe:
   `npm run lint 2>&1 | tee lint.log; echo ${PIPESTATUS[0]}` — bare `$?`
   after a pipe is the LAST command's (tail), always 0. Pre-existing lint
   errors (empty `catch {}`, `\-` in a char class, literal U+3000 in a regex)
   are one-line fixes — fix them so the gate is actually green.
1. `npx tsc -p tsconfig.json --noEmit`  (Windows: timeout ~150 s)
2. `npx tsx --test src/agentic/operations/*.test.ts src/lib/script-parser.test.ts`
3. Render: `npx tsx src/adapters/cli/agentic-batch.ts --mode compose --job <id>`
4. Probe dims: `ffprobe -select_streams v -show_entries stream=width,height`
5. Extract frame (input seek): `ffmpeg -i final.mp4 -ss <t> -frames:v 1 f.jpg`
6. `vision_analyze` the frame: caption fully visible? grade tint correct?
   orientation right? no black frames / cut-off text?

## Commit discipline
- Backward-compat only; commit locally; **PUSH only after explicit
  "push"/"go"** (user rule). Working tree must be clean before declaring done.
- One commit per feature-wave; reference the agentic-scripts.json job id(s).
- **Dangling-uncommitted-fix recovery (this box, recurring).** A prior session
  often leaves MANY verified fixes uncommitted on `main` (A5/A6/M5, palette,
  filter-narrowing, editor E2, P2-1/P2-2, brand B1/B2/B3, …). When you
  `git worktree add` from `main` and commit a SINGLE file, then `git checkout --`
  + merge, the OTHER uncommitted files remain on `main` and keep re-surfacing
  (they were never in the worktree's branch). **Symptom:** after a "clean"
  merge, `git status` still shows `render.ts` / `agentic-modular.ts` / `types.ts`
  / `script-parser.ts` modified. **Fix:** when several unrelated fixes dangle at
  once, gather them ALL into one worktree at once (`cp` each changed file into
  the worktree, `git add` all, one commit), then merge — don't peel them one
  file per worktree. Use the three-criteria clean check (#15) to prove `main` is
  hours at a prior session. Verified 2026-07-28-30. The audio-less fixes (A5/A6/E2) and the
  editor E2 / brand B1-B3 tests are the canonical template for this recovery.

58. **`brand.ts` `applyBrandKit` multi-defect class (B1/B2/B3 + color, 2026-07-28).**`
    The brand-kit burn-in (`src/agentic/operations/brand.ts`) had FOUR defects,
    all closed in one commit (`audit/brand-bugs`):
    - **B1 ordering:** `segments = [...cards, file]` → the outro card ran BEFORE
      the main video. Fix: `[...introCards, file, ...outroCards]` so the concat
      chain is intro → main → outro.
    - **B2 audio drop:** `concat=n=K:v=1:a=0[outv]` + `-map [outv]` silently
      discarded the source audio. Plus the audio map was `-map [${mainIdx}:a]` —
      ffmpeg reads `[1:a]` (brackets) as a **filtergraph label**, not input
      stream #1's audio → "Output with label '1:a' does not exist". Fix:
      `-map ${mainIdx}:a` (NO brackets) + `-c:a aac` when `hasAudio`, else `-an`.
    - **B3 temp leak:** the `_brand_*` temp card dir was never removed. Fix:
      `try {…} finally { fs.rmSync(tmpDir, {recursive:true, force:true}); }`.
    - **Latent color bug:** `rgbExpr` returned `r:g:b` (`31:111:235`); ffmpeg
      `drawbox`/`color` need `0xRRGGBB` → "Invalid 0xRRGGBB[AA] color string: 31".
      Fix: return `0x` + 6-digit hex. (Same family as #17.)
    Verified: `brand-audioless.test.ts` 5/5 — ordering (duration ≈ intro+main+
    outro + vision-confirmed INTRO/OUTRO card text at start/end), audio preserved
    on audio-bearing source, audio-less source no-crash, temp dir count unchanged,
    filter unit. Repro recipe: `references/brand-audioless.md`. The `-map [N:a]`
    (bracket → filtergraph label) vs `-map N:a` (input stream) trap is GENERAL.
59. **`-map [N:a]` (brackets) is a FILTERGRAPH LABEL, not an input stream.**
    `-map [1:a]` tells ffmpeg to use a filtergraph output named `1:a`; when no
    such label exists → "Output with label '1:a' does not exist". To reference
    the AUDIO STREAM of INPUT file #1, use `-map 1:a` (NO brackets). Inverse of
    the `-map [outv]` (filtergraph label, WITH brackets) case — brackets = label,
    no brackets = input stream. Easy to confuse when you have BOTH a filtergraph
    AND want to carry an input stream through. (GLITCH: a single segment built
    via the concat filter leaves the scaled label as `[v0]`; `-map [v0]` works
    because `[v0]` IS a (final) filtergraph label — but `-map [0:a]` where `0:a`
    is an input stream would wrongly be read as a label. Prefer `0:a` form.)
60. **Concat *filter* must CHAIN all segment labels together — `;` separates
    graphs.** `[v0];[v1];[v2]concat=n=3:v=1:a=0[outv]` is WRONG: the `;` makes
    each a separate graph, so only `[v0]` is consumed and segments 1,2 are
    dropped (and any `-map N:a` for the main clip is then orphaned → B2-style
    error). Correct: `[v0][v1][v2]concat=n=3:v=1:a=0[outv]` (all labels listed
    CONTIGUOUSLY before `concat`). Single segment: rename `[v0]`→`[outv]` rather
    than leaving it unreferenced. Also: `xfade` with `duration=0,offset=0` between
    clips of different lengths OVERLAPS the whole prior clip → output collapses to
    the shorter clip's length; use the `concat` *filter* for gapless joins of
    arbitrary-length segments. (Pair with G12: the interleave rule
    `[v0][0:a][v1][1:a]` is the OTHER concat-label mistake — different cause,
    same "label ordering" family.)

61. **Verbose ffmpeg flag (`opts.verbose`) — log every ffmpeg command to stderr
    before executing.** In `renderAgenticSlideshow`, `runFfmpegSpawn` prints
    `[ffmpeg] <binary> <args>` when `opts.verbose` is true. The same pattern
    applies to `execFile`-based concat calls and the chapter-remux pass. This
    formalises the ad-hoc debug-log approach from pitfall #31 (dump exact argv)
    into a reusable option. Add to any new ffmpeg-wrapper function. See
    `render.ts:469-471` (runFfmpegSpawn), `render.ts:873-874` (concat), and
    `render.ts:1119-1121` (chapter remux) for the canonical three-spot
    implementation.

62. **SRT/VTT subtitle export alongside the final output.** After the final
    video (`.mp4`) is written, generate `<out>.srt` and `<out>.vtt` from the
    same `captionSegments` data used for burned captions. Key details:
    - Timing offsets include the intro card duration (when present).
    - Each visual has `.captionSegments?: {text, startMs, endMs}[]` — word-timed
      cues when available, else a single cue from the scene's `voiceoverText`.
    - Pass through `chunkCues()` (merges micro-segments, enforces min 500 ms).
    - VTT format is identical to SRT except the millisecond separator is `.`
      (dot) instead of `,` (comma), and the file begins with `WEBVTT`.
    - Write ONLY when at least one cue exists (`if (cues.length)`).
    - The SRT/VTT export lives after the logo-overlay section and before
      `writeOutputArtifacts`, so the files are alongside the truly final mp4.
    Reference implementation: `render.ts:1053-1084`.

63. **Chapter markers via ffmpeg ffmetadata.** Inject MP4 chapter markers from
    scene `voiceoverText` (first 60 chars) without re-encoding:
    - Build a temp `.txt` file in ffmetadata format:
      ```
      ;FFMETADATA1
      [CHAPTER]
      TIMEBASE=1/1000
      START=<startMs>
      END=<endMs>
      title=<scene title>
      ```
    - Remux: `ffmpeg -i <out> -i <metadata.txt> -map_metadata 1 -codec copy -y <tmp>`
      then rename `<tmp>` → `<out>`.
    - Intro card becomes chapter 0 (if present); each visual/scene gets its own
      chapter. Last chapter gets a 60 s fallback end since total duration is
      approximate at that point.
    - Clean up the temp metadata file in `finally`.
    - Verbose flag prints the chapter-remux argv.
    - Graceful failure: catch errors, `warn` and skip rather than crash.
    Reference implementation: `render.ts:1086-1136`.

64. **GPU encoder auto-detection (nvenc/amf/qsv) — probe ONCE, not per-encode.**
    When `opts.gpu` is true, detect the best HW encoder via
    `execFileSync(ffmpeg, ['-encoders'], {timeout:10000})` and check
    `encoders.includes('h264_nvenc')` → `h264_amf` → `h264_qsv` in that order.
    **Cache at module level** so probing runs exactly once per process.
    Three changes per encode call-site (render.ts three of them):
    - Prepend `-hwaccel auto` **before** real video `-i` inputs (not lavfi
      synthetic sources) for GPU-assisted decoding.
    - Replace `-c:v libx264` with `-c:v GPU_ENCODER`.
    - Append encoder-specific extra args: nvenc → `-preset p7` (highest quality),
      amf → `-quality speed`, qsv → none.
    - Fall back to `libx264` (CPU) when no HW encoder found or `gpu` is false.
    **Important:** The `-hwaccel auto` flag only helps decode; HW encode quality
    at a given bitrate is usually slightly below libx264 `-preset medium` —
    tradeoff is speed (3–10× faster) vs file size at same quality. Verified
    pattern in `render.ts:400-430` (detection), `render.ts:465-466` (makeCard),
    `render.ts:895-897` (segment branch), `render.ts:944-948` (single-pass branch).

65. **Auto temp cleanup of stale intermediate render files — prevent disk bloat.**
    Each `renderAgenticSlideshow` call creates `_av_*`, `_seg_*`, `_concat_*`,
    `_intro_*`, `_outro_*` files in `outDir`. While the current run cleans its own
    intermediates after concat, aborted/crashed runs leave orphans that accumulate.
    Fix: add a best-effort cleanup block before `writeOutputArtifacts` that scans
    `outDir` for files matching these prefix patterns and deletes any with
    **mtime older than 24 hours**:
    ```ts
    const cleanupPatterns = ['_av_', '_seg_', '_concat_', '_intro_', '_outro_'];
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    for (const f of fs.readdirSync(outDir)) {
      const matched = cleanupPatterns.some((p) => f.startsWith(p));
      if (!matched) continue;
      const fpath = path.join(outDir, f);
      try {
        const st = fs.statSync(fpath);
        if (st.isFile() && st.mtimeMs < cutoff) fs.rmSync(fpath, { force: true });
      } catch { /* skip unreadable */ }
    }
    ```
    Log when >0 files removed. Never fail the render on cleanup error.
    Placed **after** chapter markers and **before** writeOutputArtifacts so the
    final output is not affected. Do NOT clean files younger than 24h — current
    render may still need them. Reference: `render.ts:1172-1193`.

