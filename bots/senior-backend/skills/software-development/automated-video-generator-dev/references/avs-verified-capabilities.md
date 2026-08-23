# AVS — Verified Capability Map & Audit Methodology

Condensed from an empirical audit (July 2026). Every claim below was checked
against the repo with `grep`/`find` + a real cold-run, NOT from memory/README.
Pair with the user's standing rule: **"verified" = real evidence, never claims.**

## 0. Audit methodology (do this before answering "can it do X?")
1. `grep -rln` the claimed feature in `src` + `tools` (e.g. puppeteer, chromakey,
   eval(, registerRoot). Zero hits = not implemented.
2. `cd /c/one/Automated-Video-Generator` then inspect (MSYS quirk: use
   `/c/one/...` POSIX paths in `search_files`/`find`; `C:\...` fails).
3. For runtime claims, do a COLD run: kill any running speech server
   (`taskkill /F /T /PID <pid>` — note single slash on Windows; `//F` gets
   mangled by bash to `/F` and fails), then run the stage and watch logs.
4. Prove voice/visual output with `ffprobe` + frame extraction + vision_analyze.

## 1. What is REAL and working (verified)
- **Script → MP4 pipeline**: `agentic-scripts.json` → AgentBrain plan →
  visuals → voice → ffmpeg/Remotion render → multi-aspect export. Real.
- **Per-scene structural edits**: `reorderScenes/deleteScene/insertScene/
  updateScene` in `src/agentic/media/scene-edit.ts`. Real.
- **Per-scene signals**: `transition` (fade|slide|zoomblur|cut), `grade`
  (neutral|warm|cool|cinematic|vivid), `kenBurns`, `jCutSec`, `captionTheme`.
  Bound in `render.ts`.
- **Local asset binding**: `[Visual: file.png]` → `input/visuals/file.png` if
  it exists, else falls back to stock keyword. `src/lib/script-parser.ts` +
  `pipeline.ts:151-199`. Real.
- **Stock image+video download**: Pexels/Pixabay/Openverse via
  `src/lib/visual-fetcher/`. Downloads to disk (`download.ts` axios+writeStream).
  **Keyless fallback works** via Openverse (no API key) — but lower video
  coverage/relevance; Openverse rate-limited anonymous.
- **BGM download**: `musicQuery` → `resolveFreeBackgroundMusic` (`src/lib/
  free-music.ts`, `src/music-system`). **No API key needed.** Per-scene
  `musicOverride/musicIntensity/volumeOverride` supported.
- **Voice (src/speech)**: Kokoro works end-to-end; backend **auto-starts cold**
  once the PYTHONPATH bug (see §3) is fixed. Cloned voice (`chatterbox_turbo`)
  creates the profile but returns HTTP 500 on CPU-only → needs CUDA/ROCm variant.
- **25+ post-render plugins**: motion (ken-burns-pro, parallax, punch-in, shake,
  speed-ramp), overlays (dynamic-captions, lower-third, watermark), transitions
  (glitch, light-leak, whip-pan), color (film-grain, halation, lut-loader),
  audio (ducking, beat-sync, normalize), genres, platform-export. Real.
- **Hermes Special Integration / `tools/computer-agent/`**: REAL code, not just
  docs. `driver.py` wraps cua-driver (screenshot, list_apps/windows, click/type).
  `demo_record.py` screen-records desktop → mp4 via ffmpeg `gdigrab`. `assets.py`
  does browser launch + screenshot capture. Drives Chrome/Edge headless.

## 2. What is ASPIRATIONAL / NOT built (verified gaps)
- **No autonomous web research**: zero search/scrape/crawl code. AgentBrain is
  heuristic/LLM-only; script facts are synthetic (not fetched/cited).
- **No website image-file ripping**: `tools/computer-agent` only *screenshots*
  the rendered page; it does NOT extract `<img src>` / `og:image` and download
  the site's raw asset files. ~30-line `rip_site_images(url)` would close it.
- **Vision = verify-only, not select**: `media-verifier.ts` is pass/fail
  (`verificationPasses`). No rank-and-pick from a candidate pool.
- **No runtime Remotion codegen**: `remotion/` has rich primitives
  (motion-effects, path-morph, kinetic-text, VoiceoverWaveform) but rendering
  uses STATIC compositions; no agent-authored `.tsx` registration. Default
  agentic render is ffmpeg slideshow.
- **No advanced video edits**: zero `chromakey/colorkey/despill`, `vidstab`,
  `minterpolate`, `hstack/vstack/blend` in scene path. Speed-ramp plugin EXISTS
  but isn't bound to a scene signal yet.
- **No auto-capture stage from JSON**: capture is agent-run manually (Hermes
  tools or `tools/computer-agent`), not auto-triggered by a URL field in
  `agentic-scripts.json`.
- **No semantic/narrative critique**: `revise` is metric-only (black frames,
  aspect, peak dB), no LLM frame review.

## 3. Key fix discovered (worth reusing)
- **Speech backend auto-start was broken on Windows**: `src/lib/speech-backend.ts`
  spawned the backend with `env: { ...process.env, PYTHONPATH: '' }`. Blank
  PYTHONPATH broke venv `site-packages` discovery → `speech.main` couldn't import
  `fastapi` → spawned server died → silent Edge-TTS fallback. FIX: remove the
  `PYTHONPATH: ''` override (`env: { ...process.env }`). Now cold-start works
  (~2s) and logs `[SPEECH-BACKEND] backend is up` then
  `[VOICE-CTRL] voiceover generated via speech backend`.
- Verification pattern: kill server (health→000), run `voice` stage, confirm
  log shows spawn→up→generated.

## 4. Advanced-editing roadmap (free = ffmpeg-native, no new deps)
- **Wave A (highest value, free)**: add scene signals `chromaKey` (chromakey+
  despill), `speed` (reuse existing `speed-ramp` plugin → setpts), `inSec/outSec`
  (trim), `keyframes` (multi-point zoompan). All in `types.ts`+`render.ts`+
  `acquire.ts`+`plan.ts`+`scene-edit.ts`. Prove with real render + frame inspect.
- **Composite**: scene type carrying 2 assets → hstack/vstack/overlay in
  `compose.ts`/`render.ts`.
- **Stabilization**: gate on `libvidstab` presence in ffmpeg-static; if absent,
  document limit (don't fake).
- **Auto-capture stage**: `capture:[{url|app,type,seconds}]` in job → orchestrator
  calls `tools/computer-agent` before visuals.
- **Semantic critique**: post-render frame extract → vision → auto-revise.
- **Remotion codegen**: sandbox `tsc --noEmit` + ffmpeg fallback for invalid
  components. Heaviest; only if plugins hit a ceiling.

## 5. User-verification style (embed in any AVS answer)
User repeatedly asks "am I correct?" — they want empirical confirmation, not
description. Before claiming a feature exists: grep the repo, or run it. State
explicitly: "verified in code at <file:line>" or "gap: no code found".
