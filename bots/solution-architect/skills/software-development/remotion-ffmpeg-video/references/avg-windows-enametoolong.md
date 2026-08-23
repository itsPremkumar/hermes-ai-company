# AVG Windows `spawn ENAMETOOLONG` + dotenv-placeholder retry storm

Two real, reproducible Windows runtime failures found while running 10 agentic
videos end-to-end (no API keys, offline, tones fallback). Both are now fixed in
the Automated-Video-Generator repo; this note records the root cause + fix so a
future session recognizes them instantly.

## Failure 1 — `spawn ENAMETOOLONG` on the render step

### Symptom
`renderAgenticSlideshow` (single-pass path) crashes with
`spawn ENAMETOOLONG` when the scene count grows (e.g. 7+ scenes). The gate
passes; voiceover completes; ffmpeg spawn dies.

### Root cause
The caption-burn loop emits **one `drawtext` filter per WORD** because the
fallback caption generator (`syllableWordTimings`) and a TTS word-aligner produce
*word-level* `captionSegments`. With ~15 words × 7 scenes that is ~105 `drawtext`
filters, each ~200 chars, all concatenated into ONE `-filter_complex` argument.
On **Windows**, a single command-line argument over ~8 KB (or the total command
line near the limit) triggers `ENAMETOOLONG` from `child_process.spawn`.

Also: the **segmented** render path used the `subtitles=` filter (libass), which
is broken on the bundled static Windows ffmpeg build (renders the clip black).

### Fix (merged to main, commit be88fa5)
1. `mergeWordsToLines()` — collapse word-level segments into **line-level**
   captions (<=7 words/line), so the drawtext count drops ~15x. Used in BOTH the
   single-pass and segmented burn loops.
2. Default to **segmented rendering** (`segmented = process.env.AGENTIC_SEGMENTED
   !== '0'`) — each scene is an independent ffmpeg process with a tiny filter,
   inherently immune to the arg-length limit, plus retry isolation.
3. Replace the broken `subtitles=` filter in the segmented path with **drawtext**
   burn (segment-relative time, starts at 0).

### Detection recipe (reuse)
If a render crashes only at higher scene counts, suspect arg-length. Quick check:
count drawtext filters in the composed `-filter_complex`. If > ~30, merge words.
Also: if `ffmpeg-static` lacks `-filter_complex_script` (old builds don't),
segmented rendering is the right fallback — don't try to write the filtergraph to
a file.

## Failure 2 — Voicebox retry storm (dotenv re-injects placeholder)

### Symptom
With no real TTS profile, every video hangs ~90s before producing audio: a 40s
backend-spawn wait + a 30s x 3 HTTP retry **per scene**.

### Root cause
`runAgenticPipeline` resolves `VOICEBOX_PROFILE_ID` from `.env` via dotenv.
The repo `.env` ships a **placeholder** value
(`VOICEBOX_PROFILE_ID=<your-voicebox-profile-id-here>`). Running with
`env -u VOICEBOX_PROFILE_ID` unsets it for the shell — but dotenv **re-injects
the placeholder from the file**. So `speakVoicebox` sees a "profile", tries to
spawn the backend (fails: module path), then does a doomed 30s x 3 `/speak`
retry per scene before falling back to tones.

### Fix (merged to main, commit be88fa5)
- `ensureBackend()` and `speakVoicebox()` now treat the placeholder (and any
  value containing `your-voicebox-profile-id`) as **"not configured"** -> return
  false / throw immediately -> fast tone fallback (no spawn, no HTTP retry).

### Detection recipe (reuse)
If you see repeated `[VOICEBOX-LIFECYCLE] backend exited (code 1)` +
`did not become ready in 40s; falling back` in logs, the profile id is a
placeholder (or the backend dir is wrong). Grep logs for
`your-voicebox-profile-id` — if present, it's the placeholder trap, not a real
config error.

## Companion fixes in the same sweep
- `runAgenticPipeline(req, onProgress)` — 2nd arg is a **progress callback
  function**, NOT an options object. Passing `{ bridge }` throws
  `TypeError: onProgress is not a function`. Pass `(p) => {...}` or `undefined`.
- Added `bin/batch-10.ts` (`npm run batch:hardening`) — a 10-variety sweep that
  **ffprobe-verifies every output** (video+audio streams, duration, dimensions)
  so silent corruption is caught. This is the regression net for the render path.
