---
name: media-pipeline-verification
description: Verify ffmpeg / video-editor / audio operations by EXECUTING them against a VARIED input matrix (resolutions × audio-presence × durations) — not just typecheck + narrow unit tests. Use after building or fixing any concat / splice / restitch / render / transcode function, or whenever a change "passes tests" but you haven't actually run the media code. Catches real crashes (dimension mismatch in concat filter, missing audio stream, undefined plan-field access, ffprobe parse misalignment) that single-fixture unit tests hide. Companion to media-pipeline-debugging (stage-isolation) — this skill is about input-variation dogfooding.
---

# Verify media ops with a varied-input matrix

Unit tests that only exercise ONE fixture shape (e.g. 720x1280 portrait WITH audio)
pass green while the real code crashes on landscape, square, or silent input. This
skill is the method to close that gap: generate a small matrix of fixtures and
actually RUN the changed function against each, capturing real ffmpeg stderr.

## When to use
- After implementing/fixing any ffmpeg-based function (concat, restitch, splice,
  render, transcode, trim, mux).
- Before claiming a video-editor feature is "done".
- When a test is green but you suspect untested input variation.

## Method (concrete)
1. Build a fixture matrix covering the real input space:
   - orientation: portrait 720x1280, landscape 1280x720, square 1080x1080, 1080p 1920x1080
   - audio: WITH (`-f lavfi -i sine=frequency=440:duration=N -ac 1`) and WITHOUT (`-an`)
   - durations: 1s (sub-scene edge), 2s, 3s, 6s, 10s
   - Build multi-scene masters via `ffmpeg -f concat -safe 0 -i list.txt -c copy`
     so plan total == master duration (concat-built masters carry ~1s keyframe
     padding, so derive cut points from the PLAN, not the master file).
2. Generate fixtures with `ffmpeg -f lavfi -i color=c=red:s=WxH:d=N` (no network,
   ffmpeg-static only). See references/fixtures.md.
3. CALL the actual module function (not just the CLI) against each fixture; capture
   the real error. A `try/catch` that returns `{ok:false, detail}` can MASK the
   root cause — temporarily log `e.stderr` or run the exact ffmpeg command standalone
   to see the true ffmpeg error line.
4. Assert on AUTHORITATIVE duration (ffmpeg `-i` Duration), not a wrapper that
   ceilings/floors (e.g. `Math.ceil` turned 4.04s→5s and broke comparisons).
5. Fail-safe + bound any NETWORK path with a timeout so it can't hang the command.

## Common crash classes for concat / stitch (and the fix)
- **Hardcoded resolution** → concat filter "dimension mismatch". Probe the master's
  native W/H via ffprobe JSON (NOT line-position parse) and scale BOTH spliced parts
  to it. See references/bug-bank.md.
- **Orientation passed as data but never to the renderer** → the renderer falls back to a
  hardcoded default (e.g. `720x1280` portrait), so a `landscape`/`square` request silently
  renders as portrait. ffprobe still reports a valid (but wrong) video, so this passes
  automated checks. FIX: translate `orientation` → explicit `{w,h}` dimensions and pass
  them into the render opts (e.g. `portrait 720x1280`, `landscape 1280x720`, `square
  1080x1080`). VERIFY VISUALLY (extract a frame, confirm wide/square/tall) — never trust
  ffprobe alone. (AVS bug #7; see references/avs-agentic-verification.md.)
- **Unconditional brand watermark** → a logo overlay runs whenever the logo file merely
  EXISTS, painting a (possibly opaque-background) box in a corner of every video even when
  branding was not requested. FIX: gate the overlay on an explicit opt-in field
  (`if (logoPath && opts.brand)`). VERIFY visually for a corner artifact. (AVS watermark bug;
  see references/avs-agentic-verification.md.)
- **Silent (no-audio) master** → concat filter `[i:a]` "matches no streams". Feed each
  part a finite `anullsrc=channel_layout=mono:sample_rate=44100:duration=X` and map
  `[2*i:v][2*i+1:a]`; add `-shortest` so the endless source can't hang the run.
- **Undefined plan fields** (`searchKeywords`, `voiceoverText`) → `reading 'replace'`
  / `'split'` crash, often AFTER the video already rendered. Guard with `?? []` /
  `String(x ?? '')` at every consumer.
- **ffprobe line-position parse** misaligns on CRLF output (returns height=720,
  codec="1280"). Parse `-of json` by KEY, never by array position.
- **Missing output dir** → ffmpeg "No such file or directory". `fs.mkdirSync(outDir,
  {recursive:true})` before render.

## Rule of thumb
If a media function "passes tests" but you only ran it on portrait+audio, it is NOT
verified. Build the matrix, run it, fix every crash, then add a regression test that
loops the matrix. Reference: references/bug-bank.md (real bugs + fixes from the AVS
editor pipeline).

## node:test mock-API version gotcha (AVS, this env)
A test FILE that opens with `mock.module('./x.js', ...)` (the experimental
`node:test` mock API) CRASHES at module load with
`TypeError: import_node_test.mock.module is not a function` on Node
v22.23.1 in this env — `require('node:test').mock?.module` is
`undefined`. This is ENVIRONMENTAL (Node build lacks the flag / older
`node:test`), NOT a logic bug in the code under test.
DURABLE RULE: when a `*.test.ts` fails with that error,
**(1)** confirm the env first (`node -e "const t=require('node:test');
console.log(typeof t.mock?.module)"` — `undefined` = env incompatibility),
**(2)** do NOT paper over it by rewriting the test (that destroys the
author's intent and hides a real coverage gap).
Treat it as a known-skip, and report it as environmental — same class
as network-host SKIPs. The real logic bugs are the ones that throw
inside a subtest with `AssertionError` / `ERR_ASSERTION`, not at
module load with `mock.module is not a function`.
(Caught this campaign: `src/lib/media-verifier.test.ts` was the only
real lib failure masked by this; the actual fixable logic bug was
`free-music.ts` bundled provider, fixed + 4/4 green.)

## AVS agentic pipeline — two-layer verification
The Automated-Video-Generator (AVS) agentic entry point is `npm run generate:agentic`
(CLI reads `input/scripts/agentic-scripts.json`, an ARRAY of jobs). Verify changes with
TWO layers — a fast offline control-surface matrix, then a real local-asset render:

1. **Control-surface matrix (dryRun)** — build jobs exercising every orientation, voice,
   caption mode, all 19 inline `[Tag:]`s, and top-level config; set `"dryRun": true` so
   `parseScript → buildPlan` runs (validating the whole JSON control surface) WITHOUT
   network/voice/ffmpeg. Expect `✅ DRY RUN OK — N scenes planned`. (dryRun jobs report
   `gate.pass=false` by design — the CLI treats them as completed, not failed; see bug #9.)
2. **Real render proof** — re-run with `localAssets` (no image fetch) + bundled music so
   the full acquire/verify/gate/render path executes and a valid MP4 is produced. Voice
   auto-falls-back (backend fails fast, bug #10). The music-duck pass2 may crash ffmpeg
   with ENOMEM on the gyan.dev Windows build (bug #8) — the code falls back to flat volume
   and the output is still valid. Probe the MP4 with ffprobe to confirm W/H + audio.

Full playbook + the `node:test` (NOT vitest) runner convention: references/avs-agentic-verification.md.
That reference now includes a VISUAL VERIFICATION section (orientation + watermark bugs
caught only by looking at frames) and references/make-perspective-images.md (sharp-based
labeled test-image generator + frame-extraction/vision recipe).

## Motion-FX / per-scene effect verification (PSNR frame-diff)
To prove a per-scene effect (shake, speed-ramp, punch-in, parallax, tint…) actually
changed the output — and ONLY its target scene — use per-time-window `-lavfi psnr`
vs a freshly rendered no-FX baseline (`average:inf` = silent no-op; <30 dB = real
change). Pitfalls: stale baseline with different dims breaks psnr; unit-probe each
applyX() separately to split FX-math bugs from CLI-wiring drops. Full recipe +
recurring bug classes (value-type no-op, wrong setpts ramp math, zoompan d=1 reset,
silent clamps): references/motion-fx-frame-diff.md.

## Re-runnable combinatorial render + visual re-verify (AVS)
The "many combinations → render → assert dimensions → vision spot-check" loop is packaged
as a re-runnable action: `scripts/avs-combo-render.ts` generates a broad
perspectives×orientations×captions×music batch (+ multi-language all-tags STRESS job +
control-surface dryRun), renders `npm run generate:agentic`, asserts ffprobe W×H per
orientation (portrait 720×1280 / landscape 1280×720 / square 1080×1080), and extracts a
late frame per orientation for manual vision inspection. The **re-verify-after-fix rule**
(pre-fix matrix is STALE evidence — re-render the SAME matrix AFTER the fix lands) and the
exact vision question bank that caught the orientation-fallback + watermark-black-box bugs
are in `references/avs-visual-reverify.md`. Run `npx tsx scripts/avs-combo-render.ts` after
any render-path fix; restore `input/scripts/agentic-scripts.json` from its `.bak` afterward.
