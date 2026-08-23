---
name: avs-empirical-bug-hunt
description: Empirical bug-hunt loop for the AVS video pipeline.
globs:
  - "src/agentic/**"
  - "src/lib/**"
  - "src/music-system/**"
  - "src/adapters/**"
alwaysApply: false
---

# AVS Empirical Bug Hunt

## When to use
The user asks to **find and fix bugs**, **hunt bugs across subsystems**, **generate videos and visually verify**, **continuous bug fixing**, or any **audit → fix → verify** task on the Automated-Video-Generator repo. The goal is a crash-free, artifact-free, empirically-verified pipeline maintained in a loop — not one-off spot fixes.

## The continuous loop (this is the deliverable shape)
1. **Build a COMBINATION MATRIX** of feature combos to cover exhaustively: orientation (9:16 / 1:1 / 16:9) × transition (slide/xfade/glitch/whippan/fade/morphcut/lightleak) × filter (bw/vintage/sepia/blur/noir/sunset/cyberpunk) × motion-FX (shake/speedRamp/punchIn/parallax) × music/SFX/voice variants × captions/wordpop/emoji/ken-burns/chroma × parser edge cases (long-line/CJK/duplicate-tag/missing-file) × stress (8-scene, 1.5s scenes, 25s scene, audio-less sources). Track in `workspace/bug-hunt/MATRIX.md` so coverage is exhaustive, not random.
2. **Dispatch N parallel TRIAGE-ONLY subagents** (max **3 concurrent** + queue the rest). Each owns a feature cluster, renders REAL videos via the harness, and writes `findings_<cluster>.md` with: `file:line`, repro job, observed vs expected, severity, harness-reproduced evidence. **Subagents MUST NOT edit source** — triage only. They render + vision/ffprobe-verify and report.
3. **Main agent** reads findings → fixes in source → **empirically re-verifies** (vision grid + ffprobe) → **commits + pushes IMMEDIATELY per stable fix batch**. One commit per logical fix group; never let verified fixes dangle uncommitted.
4. **Continue waves** until the matrix is exhausted, then produce a final verified showcase video, copy to `C:\Users\PREM KUMAR\Downloads\`, and update the bug-hunt report.

## Hard rules (from the user — non-negotiable)
- **"verified" MUST be empirical.** Extract REAL frames (`ffmpeg -ss <t> -i V` — `-ss` AFTER `-i`) + `vision_analyze`; static `tsc`/unit tests miss visual defects (black frames, no-op FX, distortion). Frame-inspect before declaring done.
- **Commit + push after EVERY stable bug-fixed code batch.** User authorized auto-commit+push. Each stable fix = its own commit.
- **NEVER delete/modify old code** — build standalone + backward-compat shim.
- **All runtime scratch under `workspace/`** (git-ignored). Never write to system TEMP. `workspace/`, `input/visuals/`, `output/` are git-ignored — commits stay source-only.
- **CONCURRENCY HAZARD (2026-08-01):** MULTIPLE Hermes sessions may edit the SAME source file (e.g. `src/agentic/orchestrator/render.ts`) at once. A sibling agent committed a complementary fix (`f09c04a`, `-shortest` on the voice-mix block) mid-session — independent of but adjacent to this session's zoompan fix. **Before pushing:** `git log --oneline -8` for foreign commits; if any exist, `git pull --rebase` (MERGE, don't clobber) and re-run `npm run typecheck` on the merged tree. Don't assume your unpushed commits are the only change to that file.
- **UNIQUE LOG PATH per run.** A reused log path (e.g. `workspace/tmp/w5.log`) collects STALE `RENDER_EXIT=137`/`RENDER_EXIT=1` lines from KILLED prior runs, so grepping the log mid-run shows a fake failure even when the current run is fine. Use a UNIQUE log path per run (e.g. `w5_grades_only.log`, `w5dbg4.log`) and trust the FINAL line + the actual `output/<job>/` dir, not a mid-log error. The background-process "exit code 1" notice from an OLD run is stale — match the PID/session to the current one.

## Empirical verification recipe
See `references/verification.md` for the exact ffmpeg/vision/ffprobe commands (frame-grid, ffprobe duration+audio-sync, volumedetect RMS). The reusable harness lives at `workspace/bug-hunt/harness.mjs` (contract in that reference); a condensed grid-builder is in `scripts/make_grid.mjs`.
- **Feature-correctness probe (no vision model):** `scripts/frame_probe.py <video.mp4> [t1 t2 ...]` extracts frames as rawvideo and reports per-frame yellow/white-pixel % so you can PROVE a filter/overlay actually burned (e.g. title card at t≈1s → white% > 1; `[Filter: bw]` → R≈G≈B). Pairs with `references/avs-segmented-render-trap.md` (G30) for the global-overlay post-concat fix.

## AVS architectural pitfalls (recurring, verify these first)
- **Grade presets are a silent-no-op trap (W5-1).** `style-engine.ts` `gradeFilter`
  only mapped `warm/cool/cinematic/vivid/neutral`; `noir/sunset/cyberpunk` (declared
  in INPUT_FORMAT.md) fell into `default` → neutral `eq`, and job-level `grade` was
  never even forwarded into `computeStylePlan`. Any NEW grade enum added to
  INPUT_FORMAT.md MUST be (a) added to the `GradeKind` union + `GRADES` pool AND
  (b) given a real filter string in `gradeFilter`, or it renders as nothing. Also
  avoid `format=gray`/`colorbalance` in grades — they force a slow/unoptimized
  colorspace path on ffmpeg-static CPU; use `hue=s=0` (grayscale) / `hue=h=...`
  (tint) which stay in YUV. Full repro in `references/avs-fx-pitfalls.md` (W5-1).
- **`zoompan` = INFINITE ENCODE HANG + OOM (W5-2).** `zoompan`'s `d` is OUTPUT
  FRAMES PER INPUT FRAME, not a duration. With `d=1` on a still image, zoompan
  emits 1 frame, the downstream `trim=duration=<dur>` can't stretch it, and ffmpeg
  loops forever (multi-hour encode, stuck at `render 0%`, ffmpeg CPU-seconds
  climbing past ~300 for a <3s scene). CAPTURE recipe (when a render hangs at 0%):
  temp-edit `runFfmpegSpawn` to log the segment cmd on `DEBUG_FF`, run, kill after
  ~20s, `grep '\[ffmpeg\]' log` → look for `zoompan...d=1`. **THE FIX THAT ACTUALLY
  SHIPS:** do NOT just bump `d` — `d=${Math.round(dur*25)}` STILL OOMs (zoompan
  buffers ALL `d` frames ≈ 180MB for a 2.6s/25fps scene and SIGKILLs the 6GB box,
  observed `RENDER_EXIT=137` at 346MB free). Replace `zoompan` ENTIRELY with a
  streaming `scale`+`crop` pan (no frame buffer, no loop, no OOM) at EVERY site:
  default kenburns → `scale=${Math.round(W*1.04)}:${Math.round(H*1.04)}:force_original_aspect_ratio=increase,crop=${W}:${H}:x='(iw-${W})*(t/${dur})':y='(ih-${H})*(t/${dur})'` (the `tpad=stop_mode=clone:stop_duration=${dur}` BEFORE it provides the timed stream so `t` advances); punchIn → `scale=${Math.round(W*punch)}:${Math.round(H*punch)}:...:crop=...:x='(iw-${W})*(1-(t/${dur}))':y='(ih-${H})*(1-(t/${dur}))'` (zooms from `punch`→1); keyframes → `scale='iw*(${expr})':'ih*(${expr})':force_original_aspect_ratio=increase,crop=${W}:${H}:x='(iw-${W})/2':y='(ih-${H})/2'`. Full repro + verified fix in `references/avs-fx-pitfalls.md` (W5-2).
- **Voice-mix `amix duration=longest` on an AUDIO-LESS `silent` video = SECOND
  infinite-encode class.** The segmented path's final music pass runs
  `[0:a][a]amix=inputs=2:duration=longest...` where input 0 is the concatenated
  `silent` video (no audio track when no scene had voiceover). `duration=longest`
  waits on the video's (nonexistent) audio → the muxer copies the video stream
  forever (observed 4h+ for a 4s source; `render.test.ts` timed out at 79%).
  FIX: append `-shortest` to that mux (caps output at the video length). Symptom
  differs from the zoompan hang: this one shows `time=` climbing in the PASS2/voice
  mux ffmpeg stderr WHILE the SEGMENTS completed fine. Always add `-shortest` to any
  mux whose audio is `duration=longest` against a possibly-audio-less input.
- **CLI `render` calls `renderAgenticSlideshow` (orchestrator), NOT `composeVideo`.** FX that `composeVideo` applies (shakeByScene / speedRampByScene / punchInByScene / parallaxDepthByScene) are **silently dropped on the CLI path**. The `agentic-modular.ts` `runRender` pre-process (BUG M3) only applies them to **video** assets and SKIPS images — so image-based CLI jobs get zero motion. Fix: forward the four fields into `renderAgenticSlideshow` opts and apply them as **filtergraph strings inside the segmented per-scene chain** (`segAdv` in `render.ts` at ~line 863) so they work on images + videos uniformly. Shake = `scale=W+2a:H+2a:force_original_aspect_ratio=increase,crop=W:H:x='…':y='…'`; punchIn = `zoompan`; parallax = horizontal `crop` pan; speedRamp = `setpts=PTS/k,minterpolate`. **SAR trap (G70):** these filters reset sample aspect ratio after the base chain's `setsar=1` → SAR `12160:12159` breaks concat. Re-pin `,setsar=1` at the END of `segAdvStr`.
- **Multilingual captions = tofu for non-CJK scripts (W3-1, 2026-08-01).** `pickFontArg` in `render.ts` only special-cased CJK (msyh.ttc / NotoSansCJK), so Hindi/Devanagari, Tamil, Arabic rendered as boxes on Arial. Fix: detect Indic/Arabic codepoint ranges (`U+0600-U+06FF`, `U+0900-U+097F`, etc.) → `C:/Windows/Fonts/Nirmala.ttf` (Win) / `NotoSansDevanagari` (Linux), mirroring the CJK branch. Proven: Nirmala draws Hindi 'सूर्य' = 214 real glyph px (not tofu). Note: this is the SAME trap class as the CJK fix — any new script block needs its own font fallback added to `pickFontArg`, or it tofus.
- **`renderAgenticSlideshow` ALSO has TWO internal branches** — `if (segmented)` (DEFAULT, used unless `AGENTIC_SEGMENTED=0`) and `else` (non-segmented). Global overlays (title card / lower-third / end CTA / progress bar) appended to the pre-branch `vfArgs` / `videoMap` are consumed ONLY by the non-segmented branch and are **SILENTLY dropped on the default path** (no ffmpeg error, just 0% text pixels on probe). Burn global overlays as a single post-process pass on the concatenated `silent` video instead. Full root-cause + fix + repro: `references/avs-segmented-render-trap.md` (G30). Reusable feature-probe: `scripts/frame_probe.py` (yellow/white-pixel % per frame — proves filters/overlays actually burned when vision_analyze is unavailable).
- **`backgroundMusic` resolution:** `inputBgmPath(name)` → `input/bgm/<name>`, but bundled tracks live in `input/bgm/__bundled__/`. Check both, prefer `__bundled__`.
- **Voiceover indexing:** `sceneVoicePath` matched by positional index, not `sceneIndex` → a missing scene narration shifted to the WRONG visual. Match by `sceneIndex`.
- **Kokoro per-scene voice** (e.g. `af_bella`) was treated as a VoiceBox profile id → 404. Provision a preset profile via `resolveProfileId(engine, voice)` (auto-provisions by voice name).
- **`sceneVoicePath` guard** already present at `render.ts` — a "crash on voiceovers" report may be a stale finding; re-render to confirm before fixing.
- **Silent segment guard:** a failed segment can pass `fs.existsSync` with a 0-byte file and get silently dropped at concat — require ffmpeg success + plausible size, fail loud.
- **Windows emoji font** is `C:/Windows/Fonts/seguiemj.ttf` (Segoe UI Emoji); Linux uses Noto Color Emoji. Burn via drawtext with the font, no `fontcolor` (emoji carry own color).
- **SFX gated on music:** `opts.sfx` was ignored when no music bed was present — cut-SFX are independent; build the SFX layer whenever `opts.sfx` is on and mix even without music.
- **Duration is VOICEOVER-driven; plan `durationSec` is only an ESTIMATE.** Real speech WAV length sets `scene.durationSec` (`pipeline.ts:580`; `agentic-modular.ts` via `estimateAudioDurationSafe`); the plan's default `durationSec` (8s) is a guess. The renderer read **plan-first in FOUR separate consumers** — a 5-min script renders exactly `19×8=152s` if any one of them clobbers: (1) `agentic-modular.ts` voiceScenes `s.durationSec || 4`; (2) `render.ts` asset loop overwriting `v.durationSec` with plan; (3) `durOf()` `plan.scenes[i].durationSec || a.durationSec || 4`; (4) segmented branch `dur:` `res.plan.scenes[i]?.durationSec ?? a.durationSec ?? 4`. **Grep recipe:** `grep -n "durationSec" src/agentic/orchestrator/render.ts src/adapters/cli/agentic-modular.ts` and confirm EVERY consumer is asset-first (`a.durationSec ?? plan ?? 4`). The bug re-clobbered 3× because each fix only covered one consumer — fix the class, not the site.
- **Voice cache MUST be text-hash validated.** `resolveExistingAudio` reused ANY existing WAV >1000B with no text match → a re-run with a LONGER script silently kept the old short narration (2.1–2.9s WAVs) → 158s video instead of ~300s. Fix: `.txt-hash` sidecar written at all 4 synthesis paths (Kokoro/Voicebox/XTTS/SAPI); reuse only when stored hash == `hashText(cleanText)`, else delete + re-synthesize. Confirm a hit by comparing plan-text hash to the sidecar AND checking the WAV mtime is old.
- **Segmented render path NEVER mixes voice by itself.** Segments are video-only; the `-c copy` concat carries NO audio stream; the final music pass probes `silentHasAudio` → false → plays the music bed ALONE (audio = music length, e.g. 59.9s while video is 291.5s). Fix: after concat, attach the voiceover mix (per-scene `adelay` at each scene's start time → `amix inputs=N:duration=longest:normalize=0` → `apad` → limiter; `-c:v copy`, audio aac) so `silent` becomes voice-bearing; the music pass then ducks under `[0:a]` narration. **CRITICAL (bug #8, 2026-08-01): that voice-attach pass MUST end with `-shortest`, or drop the `apad`.** `amix=duration=longest` ends at the last delayed WAV (~345s), but `apad` then pads the audio INFINITELY — without `-shortest` the mux never stops: observed 7-min runaway (`time=07:06` at 620× speed, file size plateaued ~28MB, then `ffmpeg failed (exit 1)`). `-shortest` stops the mux at the video length (video is the shortest stream). Also give EVERY intermediate write `-y`: the `-c copy` concat has no `-y`, so a leftover `_av_<jobId>.mp4` from a killed run makes it prompt `File ... already exists. Overwrite? [y/N]` → answers N on non-TTY stdin → "concat failed" AFTER all segments rendered (~7 min wasted). Clean `_av_*`/`_seg_*`/`_concat_*` leftovers before re-running after a crash/kill.
- **Audio amix MUST be `duration=longest` + `apad`, NEVER `duration=shortest`** when narration spans longer than the music bed — `shortest` cuts the voiceover to music length and the `-shortest` mux flag then truncates the whole video. Apply in ALL branches: music+sfx, music-only, sfx-only, and the flat-volume fallback.
- **Filtergraph string-building trap:** joining only the output LABELS of chained filters (consumers) without the producing filter strings yields `Invalid stream specifier: vv0` / "matches no streams". Labels must be preceded by the producers: `vDelays.join(';') + ';' + vDelays.map(labels).join('') + 'amix=...'`. Validate the assembled graph string with a tiny node script (count `adelay` occurrences vs `[vv` label count) BEFORE launching a ~6-minute render cycle.
- **Long-render iteration technique (2026-08-01):** (a) run the `render` subcommand ALONE (`npx tsx src/adapters/cli/agentic-modular.ts render -- --file X.json`) to skip plan/visuals/voice (~2 min saved per loop) once `workspace/jobs/<id>/` has plan.json + render-manifest.json + audio; (b) patch `main().catch` to print `e.stack` (first 8 lines) for real stack traces instead of just `e.message`; (c) a `ReferenceError: X is not defined` that appears IMMEDIATELY after saving a patch, passes `tsc --noEmit`, and passes an isolated module probe (`npx tsx -e "import('./src/.../X.js').then(m=>console.log(typeof m.fn))"`) is a tsx transform-cache race on the just-saved file — rerun once before deep investigation (observed: `computeStylePlan is not defined` vanished on rerun).
- **`job.voice` may be an object** (`{backend, voice}`) on the agentic path → `voice.split` crashed in `voice-generator.ts`; coerce defensively.
- Full inventory this session produced is in `references/avs-fx-pitfalls.md`.
- Cross-entry-point ID normalization, edit-command workspace shape, and missing output-dir (3 bugs, 2026-07-29) in `references/avs-cross-entry-point-shape-consistency.md`.

## Windows / MSYS tooling gotchas (cost real time — see `references/windows-msys-gotchas.md`)
- `read_file` with absolute `/c/one/...` MSYS paths **intermittently fails** ("system cannot find the path"). Use `search_files` with RELATIVE paths (`src/...`) or `terminal` `grep` with the quoted path.
- `.mjs` is ESM → `require is not defined`. Use `import { createRequire } from 'module'; const require = createRequire(import.meta.url);`.
- `patch` may emit `error TS6053: file not found` for the file being edited — **pre-existing/false positive**, ignore.
- To `import()` an absolute Windows path: `pathToFileURL('C:/...').href`.
- Run a `.mts`/`.ts` repro with `node --import tsx <file>`.

## Flaky-test vs real-bug isolation (critical — see `references/flaky-isolation.md`)\nWhen a repro test fails but the **raw ffmpeg command works**, do NOT ship a fake fix. Bisect: (a) call the real function in a loop 5× — if it's reliable in isolation, the bug isn't in that function; (b) reproduce the exact ffmpeg args raw via `execFileSync` and probe; (c) diff two repro scripts that disagree (input filenames, `stdio:'ignore'` vs `'pipe'`, preceeding probe calls). A flaky harness probe is a TEST artifact, not a pipeline bug — make the test robust (add a settle delay / re-probe) rather than pretend the source was broken.\n\n**Concrete decision rule (from the BUG A6 / A5 episode, 2026-07-28):** A test that probes ffmpeg output with `out.split('\\n').includes('audio')` FALSE-FAILS on Windows because ffprobe emits **CRLF** line endings (`audio\\r` ≠ `audio`) — see `avs-ffmpeg-pipeline` pitfall #48. The product code (`addAudioTrack` + its `audioStreamPresent` guard) was CORRECT; the failing test was a buggy fixture, not a pipeline bug. The trap: it's tempting to "fix" the source so the test goes green, but that manufactures a fake fix. **Procedure:** (1) capture the function's actual ffprobe output (the `audioStreamPresent` helper already trims CRLF → returns true while the test's un-trimmed probe returns false); (2) conclude the source is fine and the TEST is wrong; (3) fix the test's parse (add `.trim()`), delete any stale duplicate repro test you created while investigating. Never commit a source change solely to satisfy a CRLF-sensitive probe. Same family: a stale/duplicate `*.test.ts` you wrote during triage may shadow a real, already-passing test — prefer the committed `audio-track-audioless.test.ts` over a hand-rolled `audio-track-repro.test.ts`.\n\n**Inline-tag ingestion pitfall (verify parser ↔ render end-to-end).** Feature tags the SCRIPTS accept must each be (a) parsed in `src/lib/script-parser.ts`, (b) stripped from caption/voiceover text so they don't leak into TTS, and (c) propagated through `plan.ts → ScenePlan → render.ts` (the modular render path, which is what the CLI actually uses — not `compose.ts`). Confirmed gaps closed 2026-07-28: `[Filter: bw|vintage|sepia|blur|grayscale|mono]` (was unparsed + leaked; now `Scene.filter` → `sp.filter` grade chain), `[Transition: glitch|whippan|morphcut|lightleak|…]` (regex only allowed fade|slide|zoomblur|cut → silently dropped the rest), `exportAspects:['4K']` (threw in `ASPECT_DIMS` and the throw was swallowed → zero exports; fix: add `'4K'→3840x2160`, widen the `Aspect` type, skip+warn on unknown), and `paletteFilter` (never forwarded from the CLI to `render.ts` → no grade applied; fix: forward `job.paletteFilter` and apply `buildPaletteFilter()` to every scene). **Grep recipe for any new knob:** the field name must appear in `cli-job.ts` + `agentic-modular.ts` (forward) + `render.ts` (consume) — if it's missing in any one of the three, it's a silent no-op. Also add the tag to the `cleanText` strip list so it never reaches captions.

## Verification bar before commit
- `npm run typecheck` clean (0 errors).
- Targeted unit/regression tests green (e.g. `node --import tsx --test src/agentic/operations/edit-regression.test.ts`).
- At least one real render + vision grid confirming the fix (and a ffprobe check for audio/affected streams).
- `git status --short | grep -vE "workspace/|input/visuals|output/"` shows only intended source + tests.
