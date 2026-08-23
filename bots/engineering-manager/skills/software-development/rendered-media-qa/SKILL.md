---
name: rendered-media-qa
description: End-to-end verification of rendered / agentic media-generation systems (video, image, slideshow, AND Remotion comps). Covers ffmpeg eq filter brightness range trap (gradeFilter white-frame fix), asset-level debugging (plan→download→segment→pixel), ffmpeg drawtext escaping, caption wrapping, visual frame verification, Remotion black-frame trap, missing-asset crash, ghost-caption collisions, tsconfig *.tsx blind spot, and Node-22 mock.module test patterns.
---

# Rendered Media QA

Verifying an agentic / rendered-media pipeline is NOT done by automated gates alone.
This skill captures the methodology + the ffmpeg/drawtext-specific traps that bite
every time, learned the hard way across a full production-hardening sweep.

## When to use
- User asks to test/fix/verify "everything" in a video/image generation system.
- You render with ffmpeg and burn captions/subtitles via `drawtext`.
- You dispatch parallel subagents to hunt bugs across subsystems.
- An ffmpeg filter_complex with `enable='between(t\,...)'` regresses after an edit.

## Core methodology: automated gates are NECESSARY but NOT SUFFICIENT
Post-render checks (valid file, duration match, audio present, no black frames,
codec ok, loudness) will ALL pass while the output is visually broken. In one sweep
the X7–X15 gate passed but vision found: (a) burned caption cut off at the right
edge, (b) a semi-transparent GHOST duplicate of the caption overlapping the real one.
**Always do a visual pass**: render → extract frames → `vision_analyze` each.

### Visual verification loop (do this, not just ffprobe)
1. Render the artifact.
2. Extract frames at several timestamps + the contact sheet:
   `scripts/extract-frames.sh <video.mp4> <outdir>` (see scripts/).
   NOTE: extracting a single frame to a bare `.jpg` name (e.g. `f5.jpg`) prints a
   scary-but-BENIGN stderr: "does not contain an image sequence pattern" — the file
   IS still written. Do not treat that warning as an extraction failure.
3. `vision_analyze` on 3–4 frames AND the contact sheet. Ask specifically:
   "Is the caption fully inside the frame (not cut off)? Any ghost/duplicate text?
   Any black/broken frames? Any raw ffmpeg filter code (fontcolor=, enable=between)
   visible as text?"
4. Fix the defect, re-render, re-verify. One render+vision round per fix.

## Remotion component verification (real Chrome render)
If the pipeline has Remotion comps (`.tsx` under `remotion/`), visually verify
them too — not just ffmpeg output. Remotion renders in a headless browser, so it
needs Chrome and a different render path.

- **Chrome is required and usually already present.** On this Windows box:
  `C:/Program Files/Google/Chrome/Application/chrome.exe`. Remotion's chrome-gate
  checks `process.env.CHROME_EXECUTABLE`; export it before rendering or
  `npx remotion render` falls back to a black frame. (The earlier "no Chromium →
  ffmpeg fallback only" assumption was WRONG — Chrome was there all along.)
- **`renderStill` black-frame trap — ROOT CAUSE.** A `remotion still` pass
  RECOPYs `public/` at render start, so an ad-hoc `staticFile('<x>.png')`
  placeholder you dropped into `public/` may NOT be served → black frame, and a
  MISSING image path crashes the whole render (see missing-asset trap below).
  Use `npx remotion render AgenticVideo out.mp4 --props=p.json --frames=0-149`
  (the production `renderMedia` path serves `public/` correctly), then extract
  frames with ffmpeg and `vision_analyze` them. Full recipe in
  references/remotion-visual-verification.md.
- **MISSING-ASSET RENDER CRASH (Remotion) — root cause + correct fix.**
  `staticFile(name)` resolves to a URL fine, but if the file isn't in `public/`
  the URL 404s and `<Img>`/`<Video>` throws
  `EncodingError: The source image cannot be decoded` during encoding, which
  ABORTS the entire composition. Two wrong fixes:
  (a) An in-comp `try/catch` around `staticFile` does NOT catch it — the throw
      is at decode time, not at `staticFile` time.
  (b) You CANNOT import `fs`/`path` inside a Remotion `.tsx` comp — the webpack
      bundle can't resolve Node's `fs` (`Module not found: Can't resolve 'fs'`).
  CORRECT FIX: missing-asset detection + substitution at the **Node pipeline
  layer** (the `renderMedia` caller). For each image/video asset, if the source
  doesn't exist, generate a branded placeholder PNG via the async ffmpeg runner
  (NEVER `execFileSync` — it blocks the event loop on a RAM-starved box) into
  `public/` so `staticFile` resolves it. Music assets: leave silent.
  Regress-test: render a comp with a non-existent scene `localPath` → must
  COMPLETE (exit 0) showing the placeholder, not crash. Details in
  references/remotion-missing-asset-crash.md.
- **Remotion `no-useless-escape` lint errors on ffmpeg drawtext strings are SAFE
  to strip.** In a JS template literal, `\,` (single backslash) is JS-stripped to
  a plain comma before ffmpeg ever sees it — so the lint-flagged `\,` is a
  runtime no-op (byte-identical output). Removing it changes nothing. BUT the
  meaningful ffmpeg escape is `\\,` (double backslash) — preserve those. So when
  fixing `no-useless-escape` in orchestrate drawtext, only delete the SINGLE
  backslash occurrences; keep `\\,` (and `\\\\,`). Verify output is unchanged.
- **Mid-animation frames look broken — NOT a bug.** Springs settle over
  ~15–40 frames; a kinetic title at frame 15 shows only first chars. Render the
  SETTLED frame (intro ~frame 40, outro ~frame 180 for 30fps/60-frame intro)
  before calling a layout bug. Multiple "fragmented title" scares were mid-anim.
- **`@remotion/media-utils` `visualizeAudio` needs a POWER-OF-TWO `numberOfSamples`.** A
  default like `bars=48` (or ANY non-POT caller value) throws
  `TypeError: The argument "bars" must be a power of two. Got: <n>` — which
  ABORTS the entire Remotion render whenever a scene has audio (the
  `VoiceoverWaveform` component crashed every render with an audio track until
  fixed). **Fix:** default `numberOfSamples` to 64 and ROUND any caller value up
  to the nearest power of two (`while ((n & (n-1)) !== 0) n++`) inside the component
  so no caller can crash the render. Regress: render a comp whose scene has audio
  → must COMPLETE, not throw the POT error. (Real fix + regress-test in
  remotion/VoiceoverWaveform.tsx, commit e481264.)
- **`getAudioData(path)` from `@remotion/media-utils` needs `staticFile(path)`.** The
  waveform component receives a `public/`-relative path (e.g.
  `agentic-assets/<job>/s0_audio.wav`). `getAudioData` fetches that as a URL, so a
  bare relative path 404s in-browser and the waveform silently NEVER renders. Wrap
  with `staticFile(audioPath)` (matching the sibling `<Audio src={staticFile(...)}>`),
  with a try/catch so a missing file degrades gracefully. (Real fix in
  remotion/VoiceoverWaveform.tsx.)
- **🔴 CRITICAL: `useCurrentFrame()` inside `<Sequence from={from}>` ALREADY
  returns the LOCAL frame — do NOT subtract `from` again.** When a scene
  component is rendered inside `<Sequence from={from} durationInFrames={...}>`,
  Remotion's `SequenceContext` offsets `useCurrentFrame()` by `from`, so the
  returned value is already local (0-based within the scene). The bug pattern:
  `const local = frame - from;` inside such a component. This **double-subtracts**
  `from` → for the first `from` frames of every non-first scene `local < 0`, so
  `fadeIn = interpolate(local,[0,overlap],[0,1])` clamps to 0 and
  `opacity = min(fadeIn, fadeOut) = 0` → **a black gap at the start of every
  scene after the intro, plus broken crossfade timing.** This slips past
  typecheck/lint and only shows in a real multi-scene render. FIX: `const local = frame;`
  (the frame is already local). VERIFY by rendering a ≥2-scene video with
  crossfade and vision-checking the scene-boundary frames (e.g. t≈1.6s, 2.0s,
  4.6s, 5.0s for a 2-scene 30fps clip) — every frame must show content, NO black
  gap. (Real fix + visual proof in remotion/AgenticVideo.tsx, commit 1bcb745.)
- **ffmpeg `zoompan`/`min()` comma MUST be escaped.** A Ken Burns zoom like
  `zoompan=z=min(zoom+0.0008,1.04):d=1:s=WxH` has an unescaped comma inside
  `min()` — ffmpeg parses the comma as a filter separator, so the filtergraph
  fails to build: `[AVFilterGraph] No option name near '1:s=720x1280'`. The
  comment claiming "comma escaped as '\,'" is a LIE if the source only has one
  backslash. In a JS template literal the runtime string must contain a SINGLE
  backslash: source `min(zoom+0.0008\\,1.04)` (two chars `\\` in source → one `\`
  at runtime). Verify the runtime string with node, never by eye. (Real fix in
  src/agentic/orchestrate.ts:1242, commit 1bcb745.) Same rule applies to ANY
  ffmpeg filter option whose value contains a comma (`min()`, `max()`,
  `between()`-style expressions, color lists): escape the comma as `\,`.
- **Remotion ghost-caption trap (same class as ffmpeg ghost).** If both a static
  `SubtitleOverlay` AND `KaraokeCaptions`/styled caption render the same text
  (both gated on the same segments), you get a faint DUPLICATE. Make them mutually
  exclusive: karaoke/styled when word-timed `captionSegments` exist, else overlay.
- **`tsconfig` `include` MUST list `*.tsx`** or Remotion comps are NEVER
  typechecked — `typecheck` reports 0 while `.tsx` is fully unchecked. Confirm
  `.tsx` is matched. Same for eslint: point it at `src/ remotion/`, ignore any
  `_study/` reference-clone dir (so the MIT study clones don't pollute lint/
  typecheck/parse), and wire `eslint` into CI so latent errors can't ship
  silently. A `test:coverage` script is easy to break: mirror `test:unit` EXACTLY
  but add `--experimental-test-coverage` — it needs `--import tsx` AND the
  remotion test glob (`"remotion/**/*.test.ts"`) AND `--experimental-test-module-mocks`,
  or it dies with `ERR_MODULE_NOT_FOUND`. A bare
  `node --experimental-test-coverage --test "src/**/*.test.ts"` is broken.

## ffmpeg `eq` filter color-grade trap — `brightness` range is [-1.0, 1.0], NOT a multiplier

The `eq` filter's `brightness` parameter has range **[-1.0, 1.0]**, where **0.0 = no change**,
**1.0 = fully white**, **-1.0 = fully black**. Values outside this range are SILENTLY CLAMPED.

**Bug pattern:** `brightness=1.04` or `brightness=1.0` → clamped to 1.0 → the entire frame
becomes **full white**. This happens invisibly: ffmpeg does NOT warn about the out-of-range value.

### Common wrong values (from gradeFilter presets that look correct but aren't)

| Grade    | Wrong value   | Clamped to | Effect | Correct value |
|----------|---------------|------------|--------|---------------|
| warm     | `brightness=1.04` | 1.0    | Full white | `brightness=0.05` |
| vivid    | `brightness=1.0`  | 1.0    | Full white | omit or `brightness=0.0` |
| cinematic| `brightness=0.97` | 0.97   | Near-white | `brightness=-0.03` |
| cool     | `brightness=0.97` | 0.97   | Should be darker, not brighter | `brightness=-0.04` |

### How to detect this
- Video output shows fully white frames in scenes that have content (checked via frame extraction
  and pixel analysis with Python PIL).
- **White/blank pattern follows scene-grading randomization** — if scenes randomly pick
  from a grade pool (e.g. `['warm', 'cool', 'cinematic', 'vivid']`), some scenes are white
  while others have correct content.
- Segment-level analysis: compare per-segment filesizes in the render output. A segment
  with white frames will be much smaller (e.g. 158KB at 282 kb/s) than one with real
  content (e.g. 769KB at 1093 kb/s).

### Recovery checklist
1. Check every `eq=` filter string in the codebase for `brightness` values > 0.3 or < -0.3.
2. Remember: `brightness` is an **offset**, not a multiplier. `brightness=0.0` = original image.
   Small tweaks: +0.05 for slightly brighter, -0.03 for slightly darker.
3. Verify with `ffmpeg` + `Python PIL` frame extraction (see methodology section below).

## Asset-level debugging: tracing white frames from plan → download → segment → pixel

When a rendered video has white/blank frames while the audio and duration are correct,
use this tracing methodology to isolate the root cause:

### Step 1: Check the plan keywords
Read the `plan.json` for each scene's `searchKeywords`. If keywords are off-topic
(e.g. "espresso machine" for a space video), the media fetcher will get wrong assets.
- **Keyword generation bugs**: script/heuristic generators with hardcoded placeholder
  terms (coffee, espresso, barista) are a common pattern in template code that was
  never updated for production.

### Step 2: Verify the downloaded assets
- Check `render-manifest.json` for each scene's asset `localPath`.
- Verify all scene assets have different MD5 hashes (`md5sum` / `certutil -hashfile`).
  **Identical hashes across scenes = only ONE asset was downloaded and copied to all
  scenes.** This means the media API returned the same top result for every keyword
  query, so each scene got the same file.
- Use `ffmpeg -i <asset>` to verify each asset actually has video content (Duration,
  bitrate, codec).
- Extract frames from each downloaded asset to check its actual visual content:
  `ffmpeg -y -ss 0.5 -i <asset.mp4> -vframes 1 -q:v 2 frame.jpg`

### Step 2a: Fix — ensure asset diversity across scenes
When ALL scenes share identical assets, the fix is to use a scene-specific offset
when picking results from the media API:

```typescript
// Instead of always returning videos[0]:
const pickIndex = Math.min(resultIndex, videos.length - 1);
return videos[pickIndex]; // Scene 0→result[0], Scene 1→result[1], etc.
```

Apply this to ALL provider paths:
- **Pexels videos**: `searchVideos(...)` → pick `videos[pickIndex]`
- **Pixabay videos**: `searchPixabayVideos(...)` → pick `videos[pickIndex]`
- **Free video sources**: `freeResults[pickIndex]`
- **Image fallbacks**: `images[pickIndex]`

The `resultIndex` parameter is typically already threaded through the pipeline
(declared as `resultIndex: number = 0`) but was ignored — always defaulting to 0.
The fix is to actually USE it with `Math.min(resultIndex, results.length - 1)`.

### Step 2b: Keyword generation audit
If keywords look off-topic (e.g. "espresso machine" for a space video), check
the heuristic/script keyword generator for hardcoded placeholder terms. Common
pattern: template code with coffee/food/test keywords that were never updated.

### Step 3: Compare render segment sizes and bitrates
The render pipeline typically generates one segment per scene before concatenation.
Check each segment:
```
ffmpeg -i _seg_0.mp4 2>&1 | grep -E "Duration|bitrate"
```
A segment with white frames will have much lower bitrate (e.g. 282 kb/s) than a
healthy segment (e.g. 1093 kb/s) at the same resolution. This instantly identifies
which scenes are broken.

### Step 4: Frame-level pixel analysis
Extract frames at scene midpoints and check average pixel values with Python PIL:
```python
from PIL import Image
img = Image.open(frame.jpg)
avg = img.resize((1,1)).getpixel((0,0))
# White = all channels > 200; dark content = any channel < 150
```

## ffmpeg `drawtext` escaping — the trap that costs hours
Source filter strings are built in TS/JS; ffmpeg receives them after one more
escaping layer. The backslash counts below are what must be in the **.ts source**.

- **`enable='between(t\,${start}\,${end})'` for caption/kinetic drawtext**: needs
  EXACTLY **2 backslashes** in the source (`\\\\,`). 1 → ffmpeg rejects
  "Missing ')' or too many args"; 3+ → also rejected. Verify with a script that
  counts backslashes, never by eye.
- **`buildDuckExpression` duck-term** (`between(t\,s,e)` audio ducking): needs
  EXACTLY **1 backslash** in source. Do NOT "normalize" all `between(t...)` clauses
  to the same count — they differ by path. A global regex over `between\(t` will
  corrupt the duck term and break its unit tests.
- **APOSTROPHE `'` is the single most damaging trap.** The "standard" filtergraph
  escape `'` → `'\''` is **REJECTED by ffmpeg drawtext** — it closes the
  `text='...'` context early, so the ENTIRE remainder of the filter string
  (`fontcolor=...:enable=between(t,3.14,6.00)`) renders as VISIBLE ON-SCREEN TEXT.
  This passes every automated gate and only shows up in visual QA. **Fix: replace
  ASCII `'` with a typographic `'` (U+2019)** in caption text — it renders fine in
  Arial and avoids the single-quote entirely. (`ffmpegDrawtextEscape` MUST use
  `.replace(/'/g, '’')`, NOT `.replace(/'/g, "'\\''")`.) Repro recipe in
  references/ffmpeg-drawtext-escaping.md.
- **`ffmpegDrawtextEscape` converts `\\` → `/`** (see src/lib/ffmpeg-text.ts). So a
  literal `\\n` line break becomes `/n` and ffmpeg will NOT wrap. To wrap a long
  caption: do NOT rely on `\\n`; instead emit ONE drawtext layer per wrapped line,
  stacked via `y = baseY - lineIndex * lineHeight`.
- **Caption wrapping width MUST be measured, not guessed.** Empirically (Arial at
  our render settings) average glyph advance ≈ **0.62 × fontsize**. The old factor
  `frameW*0.82 / (fontsize*0.62)` allows ~10% too many chars/line and OVERFLOWS
  (caption cut off at right edge). Correct, conservative formula:
  `maxChars = floor((frameW - 2*(64+12)) / (fontsize*0.65))` — the `64+12` is 64px
  margin + 12px for the `boxborderw=10` box. Test a known 62-char line at fontsize
  30: it must split, not stay one line. See references/ffmpeg-drawtext-escaping.md.
- **Segmented vs main render path.** The real pipeline renders per-scene segments
  then concats (immune to Windows ~8KB/arg ENAMETOOLONG). Captions are burned in
  the PER-SEGMENT loop, NOT the main `if (captionFile)` vfArgs chain. Both paths
  apply a kinetic lower-third — the MAIN path gates it on `opts.captions === 'none'`,
  but the SEGMENTED kinetic block historically did NOT, producing a GHOST (burned
  caption + kinetic hook stacked). Always mirror the `captions === 'none'` gate in
  BOTH paths. Visual-verify a frame where a kinetic cue fires to confirm no ghost.
- Font: `fontfile='C:/Windows/Fonts/arial.ttf'` on Windows; `-filter_complex` is
  double-escaped in the *segmented* render path vs single in the main path — keep
  the escaping IDENTICAL to a known-working sibling line when editing.

## Parallel subagent bug-sweep (find real bugs fast)
Dispatch 3+ `leaf` subagents, READ-ONLY (return file:line + minimal fix, do NOT edit),
each scoped to a subsystem: (1) HTTP API + MCP server, (2) CLI/classic/batch/export,
(3) security (cred leakage, path traversal, injection, auth bypass, SSRF). They
return findings; you triage, fix only the real ones, then re-run typecheck + tests.
This found RCE (exec→execFile), SSRF (missing isSafeUrl), auth gaps
(/api/agentic unguarded), stream-handler crashes, and path traversal in one pass.

### The two failure modes of an automated gate
1. **Gate passed but output is broken** (covered above) — visual QA catches it.
2. **Gate lies by passing INCORRECTLY (false-positive).** The check's logic is
   too loose, so it green-lights a wrong output. Example from this project: the
   X14 "Output dimensions valid" check was `dimOk = portraitOk || landscapeOk`
   where `portraitOk = h >= w`, `landscapeOk = w >= h` — TRUE for EVERY
   non-zero rectangle, so a portrait request rendered as 720x1280 landscape
   STILL passed. The gate said "valid dimensions" while the aspect ratio was
   wrong. **Fix:** a dimension/format check must compare against the REQUESTED
   size (within tolerance), not against a always-true category predicate.
   General rule: when a gate's pass condition can be satisfied by a degenerate
   input (any non-zero value, `a || b` where one branch is usually true, a
   regex that matches too much), it is a false-positive waiting to happen.
   See references/gate-false-positive.md for the X14 case + the
   content-verifier silent-pass case (below).

### ORIENTATION-IGNORED BUG (new, caught only by visual QA — July 2026 AVS sweep)
A render can produce a **valid, playable MP4 with correct codec/duration/audio**
that is STILL the WRONG aspect because the renderer fell back to a hardcoded
default orientation. Symptom: a `landscape` (16:9) job renders `720x1280`
(portrait), or `square` renders portrait too. `ffprobe` reports width/height fine,
the file "passes" every automated gate, and only a **vision check of the frame**
reveals it's taller-than-wide when it should be wide.
- **Root cause (AVS `agentic-cli.ts` → `renderAgenticSlideshow`):** the CLI built
  the render opts WITHOUT passing `orientation`/`dimensions`, so render.ts used
  its hardcoded `W=720,H=1280` (portrait) default for every job. The orientation
  was parsed into the plan but never reached the renderer.
- **Fix:** map orientation→dimensions in the CLI before calling render and pass
  `dimensions` in opts: `portrait {720,1280}`, `landscape {1280,720}`,
  `square {1080,1080}`. (Real fix in src/adapters/cli/agentic-cli.ts, commit 058c1a7.)
- **Verify:** `ffprobe -show_entries stream=width,height` on the OUTPUT must
  match the requested orientation; THEN `vision_analyze` the extracted frame to
  confirm it actually looks wide/tall/square (codec checks alone miss this).
- **General rule:** any "orientation/aspect/size" field that is parsed but not
  threaded into the actual ffmpeg `-vf scale=W:H` is a latent default-fallback
  bug. Grep for `?? 720` / `?? 1280` hardcoded fallbacks in the render entry.

### WATERMARK / OVERLAY BLACK-BOX DEFECT (new, caught only by visual QA)
A brand-watermark overlay can stamp a **solid black/dark square** in the
corner of every video when the logo asset is **opaque (no alpha channel)**.
The logo PNG (`rgb24`, `pix_fmt` has no `a`) has a solid/dark background;
overlaying it at `W-w*0.12-20:H-h*0.12-20` just pastes that black box. Codec
checks pass; vision reveals the artifact.
- **Root cause (AVS `render.ts` Pass-3 logo overlay):** it applied whenever the
  logo FILE existed, unconditionally — even with no `brand` opt-in, and even when
  the logo was opaque. A `colorkey=black` attempt on a dark-indigo-bg logo
  still left a box (the "background" wasn't pure black), so colorkey is fragile.
- **Fix (two-part):** (a) gate the overlay on `opts.brand` being set (opt-in, not
  every video); (b) before overlaying, `ffprobe` the logo's `pix_fmt` and SKIP
  with a warning if it lacks alpha (`/rgba|argb|graya|:a$|a@/` test). Only
  transparent logos get composited. (Real fix in src/agentic/orchestrator/
  render.ts, commit 058c1a7.)
- **General rule:** any `overlay=`/`[1:v]` watermark step must (1) be opt-in via
  a brand flag, and (2) verify the overlay asset has an alpha channel — opaque
  overlays are never safe. A `colorkey` band-aid on a non-black-bg logo is not
  reliable; skip instead.

### Verification gates can ALSO silently PASS on unparseable AI output
A content-verifier (watermark/NSFW/safety) that calls an LLM/vision model and
then parses the reply must FAIL-CLOSED when the reply is unparseable. The bug:
`parseVerificationResponse` returned `passes:true` on a non-JSON / garbage reply
(a refusal, a "Sure! Here is my thoughts…" non-JSON string). That let a failed
content check silently PASS — defeating the verifier. Fix: route unparseable
output through the same `failClosed` (unavailable) path as a missing backend,
so it returns `passes:false`. Regression test: mock the AI to return non-JSON
and assert the verifier fails closed. (Both the X14 dimension fix and the
fail-closed parse fix landed this project and are covered by tests.)

### SECURITY: path-traversal guard `startsWith(root)` is bypassable
`assertPathWithinProject` using `resolved.startsWith(projectRoot)` with NO
trailing-separator boundary is exploitable: any absolute path whose string
prefix equals `projectRoot` followed by a non-`/` char passes. Concretely a
sibling dir named `<root>_evil` (e.g. `C:\repo_evil\secret.txt` when root is
`C:\repo`) passes the check and can be served/read. FIX: require a path-separator
boundary: `allowed = resolved === projectRoot || resolved.startsWith(projectRoot + path.sep)`.
Separately, a `getViewFile(rawPath)` that accepted an **absolute** `rawPath`
bypassed the `..`-normalize that a relative path gets — REJECT absolute paths
outright (`if (path.isAbsolute(rawPath)) throw`), forcing resolution through the
public-root helper. Regression test: assert `getViewFile('C:\\Windows\\system.ini')`
and `getViewFile('<root>_evil/secret.txt')` both throw, and a legitimate
`public/` file is served. (Real fix in src/infrastructure/filesystem/
local-filesystem.ts, +4 regression tests, commit 1bcb745.)

### SECURITY: verifyMedia fail-open bypasses fail-closed
`verifyMedia()` returned `passes:true` (confidence 10) for an UNSUPPORTED file
extension, `passes:true` (confidence 5) when it could not extract a video frame,
and `passes:true` when it could not read the image — all three SILENTLY PASS,
contradicting the file's documented fail-closed guarantee. FIX: route all three
"verification could not actually run" cases through `unavailableResult(...)`
(which honors `failClosed` → `passes:false`). Regression test: call `verifyMedia`
with an `.xyz` path and a non-existent `.png` under `failClosed:true` and assert
`passes === false`. (Real fix in src/lib/media-verifier.ts, +2 regression tests,
commit 1bcb745.)

### SECURITY: download endpoints need local-only auth
HTTP download endpoints that fetch arbitrary URLs / write files must be guarded
by `requireLocalAccess` (loopback-only) like the rest of `/api`. Routes like
`/video-download/process`, `/social-download/process`, `/free-video/(download|
search|sources)` had NO such guard while siblings did. FIX: add `requireLocalAccess`
to each. (Real fix in src/adapters/http/api-routes.ts, commit 1bcb745.)

### Full 6-bug sweep map + verification recipes
See `references/remotion-ffmpeg-security-bughunt.md` for the complete hit-list
(CRITICAL Sequence double-subtract, zoompan comma crash, path-traversal
boundary, verifyMedia fail-open, music double-prefix, download auth) with exact
locations, fixes, and how to prove each — plus the reusable subagent-sweep recipe.

### Same-video-across-scenes debugging
See `references/asset-diversity-debugging.md` for the three-layer fix pattern
(resultIndex unused → cache-key missing scene index → pool short-circuits
per-scene search) with a full investigation workflow and prevention checklist.

## Black frame detection — the `blackframe` filter parameter trap

Two different ffmpeg/ffprobe filters exist for black frame detection, and mixing them up produces **false positives** that waste hours.

### The trap: `blackframe` vs `blackdetect`

| Filter | Syntax | Proper Use | Common Mistake |
|--------|--------|-----------|--------------|
| `blackframe` | `blackframe=amount:threshold` | `98:15` means "≥98% of pixels must be ≤15/255 luma" | `0.1:30` — a 0.1% threshold flags nearly EVERY frame as black |
| `blackdetect` | `blackdetect=d=dur:pix_th=val` | `d=0.3:pix_th=0.15` means "segments longer than 0.3s where 85%+ of pixels are ≤0.15 luma" | — |

**The bug pattern:** `blackframe=0.1:30` is LITERALLY "if 0.1% of pixels are below value 30", which on a 1080p frame means only ~2K dark pixels are needed — almost all frames qualify. This was used in `trimBlackFrames()` in `src/lib/media-downloader.ts` and caused ALL videos to be detected as "all black".

**Correct detection for verification:**
```bash
# USE THIS — blackdetect with pix_th=0.15 (15% of max luminance):
ffprobe -v quiet -f lavfi -i "movie=${mp4},blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep "black_start\|black_end\|black_duration"

# CORRECT standalone blackframe usage (for frame-by-frame analysis):
ffprobe -v quiet -f lavfi -i "movie=${mp4},blackframe=98:15" -show_entries frame=pkt_pts_time -of csv=p=0 2>&1
```

### The two-parameter fix checklist
1. **In gate checks** (`video-analyzer.ts`): use `blackdetect=d=DUR:pix_th=0.15` — this is correct.
2. **In pre-processing trim** (`media-downloader.ts`, `acquire.ts`): if using `blackframe` to detect leading black for trimming, use `blackframe=98:15` (NOT `0.1:30`).
3. **In verification scripts** (`verify-output.ts`): use `blackdetect` for segment detection, not `blackframe`.

### Where black frames actually come from (and the fix order)
1. **Pexels source videos fade-in** (~0.5-1s of black from a fade-to-black at the start). Fix: call `trimBlackFrames()` AFTER download/copy in the agentic pipeline (`acquire.ts` lines 256-267), not just in the legacy free-video flow. The function must export from `media-downloader.ts`.
2. **Render concat gaps** — black appears BETWEEN scenes when the crossfade filter doesn't overlap correctly. Fix: verify the scene-to-scene transition logic.
3. **Source video is truly dark** (night footage, aurora). Fix: raise `pix_th` to 0.06 for darker content, or accept it.

## Comprehensive output verification script

The `scripts/verify-output.ts` tool performs **31 checks across 8 categories** on any rendered MP4:

| Category | Checks | What It Catches |
|----------|--------|-----------------|
| **1. File Integrity** (F1–F4) | Size > 100KB, not empty, not oversized | Corrupt/crashed renders |
| **2. ffprobe Metadata** (M1–M5) | Format name, duration, bitrate | Unplayable output |
| **3. Video Stream** (V1–V8) | Codec, resolution, FPS, pixel format, aspect ratio | Wrong codec, wrong format |
| **4. Audio Stream** (A1–A4) | Codec, sample rate, channels | Missing/silent audio |
| **5. Video Statistics** (S1–S4) | Corruption check, frame count, loudness | Frozen/stuttering output |
| **6. Black Frame Detection** (B1–B2) | `blackdetect` with `pix_th=0.15` | Black/gap segments |
| **7. Pipeline Logs** (L1–L6) | Workspace assets, manifest, verification | Missing pipeline artifacts |
| **8. Gate Report** (G1) | Reads `gate.json` | Gate-level failures |

### Enhanced: `scripts/batch-verify.ts`

A more comprehensive 32-check verification script that builds on `verify-output.ts`
with better error handling for edge cases:

| Improvement | `verify-output.ts` | `batch-verify.ts` |
|------------|-------------------|------------------|
| Black detection | `blackdetect` (correct) | Same — `blackdetect=d=0.3:pix_th=0.15` |
| Freeze detection | Not included | ✅ `freezedetect=n=0.003:d=0.5` |
| `volumedetect` | Fails to -99dB on bundled ffmpeg | Falls back to gate-verified values |
| `count_frames` | Uses brittle ffprobe flag | Uses stream metadata `r_frame_rate` |
| Manifest check | `startsWith('manifest')` | `includes('manifest')` — catches `approval-manifest.json` etc. |
| Exit code | failCount > 0 | Same — CI-gate friendly |

**Usage:** `npx tsx scripts/batch-verify.ts <path-to.mp4> [job-id]`

The `job-id` parameter (optional) enables pipeline-log checks (P1–P6) by
resolving the workspace path. Without it, pipeline checks are skipped.

### Verify across multiple video types — don't stop at one

A fix that works for one video type (e.g. nature/portrait) might fail on another
(facts/landscape, motivational/portrait with different captions). **Always test
at least 3 video type × orientation combinations** before declaring a fix done:

| Scenario | Type | Orientation | Tests |
|----------|------|-------------|-------|
| Nature scenic | `--video-type` (default) | portrait 9:16 | black frame, freezedetect |
| Educational facts | `--video-type facts` | landscape 16:9 | different caption length, voiceover |
| Motivational quotes | `--video-type motivational` | portrait 9:16 | karaoke captions, energetic music |

In the project this was learned on, the X10 black frame fix was verified across
nature, facts, and motivational types — all 3 passed 32/32 checks with
zero black segments. The fix was **only confirmed robust** after seeing all three
pass.

**Usage:** `npx tsx scripts/verify-output.ts <path-to.mp4> [--verbose]`

The script is self-contained (no project imports) and works on any MP4. It correctly resolves `ffprobe-static` and `ffmpeg-static` paths from bundled packages.

### Visual QA must cover ORIENTATION + WATERMARK too (not just content type)
The two July-2026 AVS defects (orientation-ignored → landscape rendered as
portrait; opaque-logo watermark → black box) both passed every automated gate
and were caught ONLY by rendering many combinations and inspecting frames with
vision. **Mandatory axes for any "verify everything" pass:** orientation
(portrait/landscape/square, confirm OUTPUT dimensions + vision-frame match the
request), watermark on/off (confirm no black box), and the captions
(burned/karaoke/none). Full reproducible loop (asset-gen → combinatorial batch →
frame extract → vision questions → fix → re-verify) in
references/visual-qa-combinatorial.md.

### Building your own verification
When creating a verification script, the critical design rules:
- **Use `blackdetect` NOT `blackframe`** for segment-level black detection (see above).
- **Handle `ffprobe-static` path resolution defensively**: `try { FFPROBE = require('ffprobe-static')?.path; } catch {}`
- **Frame count via `-count_frames`**: parse `r_frame_rate` as fraction (`num/den`), not as a bare number.
- **Loudness via `volumedetect`**: extract `mean_volume` and `max_volume` regex from ffmpeg stderr; check mean > -50 dB and max ≤ 0 dB.
- **Exit code = fail count**: `process.exit(failCount > 0 ? 1 : 0)` so CI gates catch failures.

## Pitfalls (learned painfully)
- **A verification gate can be a FALSE-POSITIVE, not just a false-negative.**
  Audit each check's pass-condition for "always true" branches (see above).
- **Subagent "verification" claims are NOT evidence.** When you fan out
  READ-ONLY bug-hunting subagents, some return reports that *assert* "workspace
  clean and verified-intact" while only running `typecheck`/`npm test` (zero
  dynamic reproduction) — or worse, the delegation owner exits without
  returning anything. TRUST NOTHING: re-confirm every claimed bug AND every
  claimed "clean" area against the actual source / a runtime repro before you
  act (or don't). In one sweep a subagent insisted the VoiceoverWaveform was
  "robust but wrong input" — it had already been fixed two commits earlier.
  The 6 real bugs that DID land all came from treating subagent findings as
  *unverified hypotheses* and proving each (source read + runtime repro for the
  zoompan crash + visual render for the Sequence black-gap).
- **Don't re-wrap an already-absolute path.** When a helper returns a fully
  resolved absolute `localPath` (e.g. `resolveFreeBackgroundMusic` returns
  `<root>/input/music/__auto__/<id>.mp3`), do NOT prepend a relative prefix
  like `music/__auto__/${basename(localPath)}` before passing it to
  `resolveProjectPath('input','music', x)` — that DOUBLE-PREFIXES to
  `input/music/music/__auto__/...` and the file is never found (silently
  skipped). Use the returned absolute path directly. (Real bug in
  src/video-generator.ts:363, commit 1bcb745.)
- **`nul` file corrupts `git add`.** ffmpeg `-f null -` debug runs on Windows
  can leave a file literally named `nul` in the repo root; `git add -A` then
  dies with `error: short read while indexing nul` / `failed to insert into
  database`. The repo index becomes unmodifiable until you `rm -f nul` (and any
  stray `tmp_*.mjs`/`tmp_*.mts` scratch files) AND `git reset -q` to drop any
  staged `nul` before committing. Add `nul` to your mental "always delete before
  commit" list on Windows.
- **`replace_all` can match a function's DEFINITION BODY.** A global replace of
  `writeManifest(x,y)` → `syncManifest()` also rewrote the body of `syncManifest`
  itself, causing infinite recursion ("Maximum call stack size exceeded"). After any
  `replace_all`, re-read the definition bodies it could have touched.
- **Node 22.23.1 `mock.module`**: register ONCE per specifier per process; teardown
  with `mock.restoreAll()`; there is NO `resetModules()`. Single-registration +
  mutable-STATE closure is the correct pattern for 36 adapter tests.
- **tsx caches transpilation** and `npm run test:unit` globs ALL test files into ONE
  process. Module-level state from sibling `mock.module` tests can make a pure
  function's test fail under the glob though it PASSES IN ISOLATION. If a test fails
  only in the full run, run that one file alone to confirm it's a harness artifact,
  not a code bug.
- When fixing a security bug whose tests mock a module (e.g. `child_process` mocked
  with `exec` only), switching to `execFile` requires updating the mock to export
  `execFile` too. Preserve the test's asserted return-shape contract.
- **`execSync` blocks ALL concurrent operations.** In a pipeline with
  `mapWithConcurrencyLimit(concurrency=4, tasks)`, if one task's download path
  calls `execSync` for ffmpeg preprocessing (e.g. `trimBlackFrames` in
  `media-downloader.ts`), the ENTIRE event loop blocks — all other downloads
  and async HTTP fetches freeze until the ffmpeg call finishes. This makes
  concurrent downloads effectively serial during the trim phase. Prefer
  `execFile` with async/await for ffmpeg preprocessing when called inside
  a concurrent batch. Legacy code paths that use `execSync` for ffmpeg work
  fine in isolation but degrade throughput under concurrency.

## Verification gate before claiming "production ready"
`npm run typecheck` clean + `npm run test:unit` green + at least one REAL render
with post-render checks + visual frame verification. Network-dependent tests (e.g.
Wikimedia/MetMuseum live fetches) skip by design — not failures.

## Typecheck=0 is NOT verification — especially for robustness/crash fixes
A fix can typecheck clean AND be unverified. In one sweep a missing-asset
render-crash fix was shipped with only `tsc` green, got flagged for STALE
verification, and had to be revisited: the closure that did the work was extracted
into an exported function, then a REAL regression test was written against it
(actual code + real ffmpeg-static runner) proving the placeholder PNG is created.
**Rule:** for any robustness/crash fix, ADD A UNIT TEST that exercises the actual
code path — do not claim done on `typecheck`/`lint` alone. The user WILL re-verify
and will call out "stale verification" if you didn't run the real thing.

### Testability technique: extract the closure, inject the runner
Robustness logic often lives inside a big function (e.g. the asset-prep loop in
`renderAgenticWithRemotion`). To test it:
1. Extract the loop into an exported `prepareRemotionAssets(res, opts, dir, runFfmpeg)`
   and CALL it from the original function — zero behavior change, just structure.
2. Make the side-effecty runner an INJECTED param (`runFfmpeg`) so the test passes
   a real ffmpeg-static runner (`require('child_process').execFile(ffmpegPath,...)`)
   and asserts the placeholder file lands on disk as a valid PNG (magic bytes
   `89 50 4E 47 0D 0A 1A 0A`). Three cases: missing-image→placeholder-kept,
   present-image→copied-verbatim, missing-music→dropped-silently.
This makes the fix provable without a full Chrome render. Full pattern in
references/verify-robustness-fixes.md.
