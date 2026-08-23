# Hermes-Driven Website Capture + Keyless Download + Opt-In Verify

Durable technique distilled from the 2026-07-26 session where the user asked whether the
agentic pipeline can produce a real video (sproutern / Google style) and how the website
assets get collected. These facts are NOT obvious from the code and were verified live.

## 1. Website capture is HERMES-DRIVEN (working today, not a code gap)

The agentic pipeline does NOT auto-screenshot a URL on its own. The supported, working
method is for **Hermes (this agent) to capture the site using its OWN tools**, then drop
the files into `input/visuals/`. The pipeline binds them via `[Visual: file.png]`.

Tools to use (all real, in this agent's toolset):
- **Screenshots of a page**: `browser_navigate(url)` then `browser_vision(question="full page screenshot")`.
  For long pages, scroll + capture multiple sections. Copy the returned PNG into
  `input/visuals/<name>.png`.
- **Window / app capture**: `computer_use capture(app="Chrome", mode="vision")` for a clean
  window shot. `app="Code"` for code, `app="Windows Terminal"` for CLI, `app="screen"` for desktop.
- **Screen-RECORDING (mp4)**: `tools/computer-agent/demo_record.py` records the desktop via
  ffmpeg `gdigrab` (`-f gdigrab -i desktop`) on Windows. This PROVES the old "no screen-recording"
  claim was wrong — it exists in `tools/computer-agent/`, driven by `cua-driver` + `driver.py`.
  The Python wrapper (`assets.py` / `demo_record.py`) is the real implementation behind the
  `hermes-special-integration.md` doc.
- **Custom HTML to screenshot**: `write_file` an HTML card then `browser_navigate("file:///...")`
  then `browser_vision`. Gives branded title/outro cards with exact colors/fonts/logo.

This works for **ANY website/topic**, not just sproutern. Hermes can capture any public URL;
the stock downloader fills any visual not satisfied by a captured/local asset.

NOTE: a future `capture:[...]` JSON field could auto-fire this, but it is NOT wired into the
orchestrator today (no import of `tools/computer-agent` in `src/`). The agent-driven method
is the supported path.

## 2. Auto-download of images/videos/BGM from agentic-scripts.json

Verified in `src/lib/visual-fetcher/` + `src/lib/free-music.ts`:
- Each scene's `[Visual: keyword]` (or derived `searchKeywords`) drives `fetchVisualsForScene`
  which searches **Pexels** (photos+videos) + **Pixabay** (videos+images), falling back to
  **Openverse/Wikimedia**. Files are downloaded to disk (`download.ts` uses axios + createWriteStream).
- **BGM**: `resolveFreeBackgroundMusic({query})` downloads a free track. **No API key needed.**
- **Keyless still works**: without `PEXELS_API_KEY`/`PIXABAY_API_KEY`, the Openverse/Wikimedia
  fallback still downloads real images + some video (lower relevance, anonymous rate limits).
  The user's `.env` HAS all three keys set, so full Pexels/Pixabay is live.
- A local `[Visual: file.png]` that EXISTS in `input/visuals/` wins; a missing file is treated
  as a keyword and downloaded. (parser: `script-parser.ts` does `localAsset: existsSync ? tag : undefined`.)

## 3. Vision verification is OPT-IN (critical caveat)

`src/lib/media-verifier.ts` + `acquire.ts` (`aiVerifyAsset`) DO verify both images AND videos
(a video frame is extracted via ffmpeg and checked). BUT it only runs when
`aiVerify.verifyOnAcquire` is enabled in config/.env. **Without it, assets skip the check and
flow straight to editing.** Recommend enabling it for the "every image and video verified"
guarantee. Failures trigger a re-fetch (or re-capture).

The current `media-verifier` is **pass/fail** (verify-only), not rank-and-pick. A future
`vision-select` could choose the best from a candidate pool, but that is not built.

## 4. End-to-end flow the user confirmed (documented in repo at docs/AGENTIC_VIDEO_WORKFLOW.md)

script to Hermes captures website (browser/computer_use tools) to pipeline auto-downloads
images/videos/BGM to vision verifies (opt-in) to per-scene edit one-by-one (`scene-edit.ts`,
`agentic:edit`) to tags in JSON to Kokoro voice (auto-starts `src/speech`) to multi-aspect render.
All driven from `input/scripts/agentic-scripts.json`.

## 5. Pitfalls to avoid
- Do not claim "no screen-recording" — `tools/computer-agent/demo_record.py` (gdigrab) does it.
- Do not claim "website capture auto-fires from JSON" — it is agent-driven today.
- Do not claim "every asset is verified" without noting it is opt-in via `aiVerify.verifyOnAcquire`.
- `browser_vision` / `vision_analyze` need literal `C:/one/...` (forward slash) paths, NOT
  `/c/one/...` MSYS paths (mangled to 404). See parent skill PITFALLS.
- `taskkill` on MSYS: use single slash `taskkill /F /T /PID <pid>` (the shell mangles `//F`).
