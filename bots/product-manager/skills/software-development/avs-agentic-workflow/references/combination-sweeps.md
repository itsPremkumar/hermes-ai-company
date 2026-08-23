# AVS combination sweeps — session detail (2026-08-01)

Two sweeps were run back-to-back to prove the full combination universe of the
Automated-Video-Generator agentic pipeline. All 13 outputs rendered, ffprobe'd,
and frame-QA'd clean (blackdetect=0; the only freezedetect hits were
INTENTIONAL stills — see below).

## Sweep 1 — asset types (`input/scripts/asset-sweep.json`, 5 jobs)

| job id | title | composition | result |
|---|---|---|---|
| stock-images | Still Frames | 2 stock VIDEOS (planner overrode `defaultVisual: "image"`!) | 7.3s |
| stock-videos | Wild Motion | 2 stock videos + SFX | 7.7s |
| ai-canvas | AI Canvas | 2 AI-generated images + Ken Burns + kineticText | 9.6s |
| mashup | Mashup | AI image + stock video + AI image + stock video in ONE video | 15.0s |
| downloaded-images | Downloaded Frames | 2 downloaded stock photos + Ken Burns + kineticText | 7.3s |

Manifest kinds (proves the mix): `grep '"kind"' <job>/render-manifest.json`
→ stock_images 2×video, stock_videos 2×video, ai_canvas 2×image,
mashup 2×image+2×video, downloaded_images 2×image.

Asset recipes (both zero-cost, no key for Pollinations):
- **AI-generated image (Pollinations, model `sana`)**:
  `curl -sL "https://image.pollinations.ai/prompt/<urlencoded prompt>?width=1280&height=720&nologo=true&seed=<N>" -o input/visuals/ai_x.jpg`
  → real 1024×576 JPEG. Verified seeds give stable subjects; `sana` is the free model.
- **Downloaded stock photo (Pexels API, key in `.env`)**:
  `source .env` then
  `curl -s "https://api.pexels.com/v1/search?query=<q>&per_page=3&orientation=landscape" -H "Authorization: $PEXELS_API_KEY"`
  → take `src.original` (full-res 3–6 MB photos, e.g. 5394×3548). Repo helper:
  `scripts/fetch-stock-images.sh` (sources .env, writes input/visuals/stock_*.jpg).

## Sweep 2 — feature surface (`input/scripts/fx-sweep.json`, 8 jobs)

| job id | title | combination tested |
|---|---|---|
| fx-filters | Color Lab | `[Filter: bw]` + `[Filter: sepia]` + `[Filter: vintage]` + grade cinematic + `[KenBurns: off]` |
| fx-transitions | Smooth Cuts | `[Transition: zoomblur]` + `glitch` + `lightleak` + `sfxOnCut` |
| fx-motion | Kinetic | kenBurns + `clipSpeedByScene {0:0.5, 2:2}` (slow-mo/timelapse) + `blurScenes` + vignette |
| fx-overlay | Broadcast | karaoke captions + kineticText + lowerThird + progressBar + emojiByScene + titleCard + endCta + fontColor |
| fx-audio | Soundstage | duckDepth 0.6 + musicIntensity energetic + crossfadeSec 0.8 + sfx + normalizeLufs -14 + voiceSpeed 1.1 + loopMusic + ttsStyle |
| fx-structure | Story | hookFirst + variablePacing + intro/outro cards + sceneOrder + beatSync + loopVideo 2 + posterScene + contactSheet |
| fx-advanced | Studio Grade | grade vivid + filterByScene vintage + colorTempByScene 3500/8000 + contrast + saturation + brightness + textOverlayByScene |
| ultimate | Everything | square 1:1 + AI+downloaded images MIXED + bw/sepia filters + zoomblur + kineticText + burned captions + vignette + sfx + ducking + progressBar + emoji + cinematic + contactSheet |

Runtime tip: feature sweeps with all-local `[Visual: file]` bindings skip the
network visuals stage → full 8-job pipeline (plan+visuals+voice+render) ≈ 10 min
vs ~25+ min with stock downloads. One job in sweep 1 (mashup) pulled a 4K
hummingbird Pexels original: **122 MB+ at ~1.8 MB/s** — don't assume a stall;
check growth with `stat -c "%s" <file>.part` twice ~10 s apart.

## Pitfalls (verified this session)

1. **`defaultVisual: "image"` is a hint, not a lock.** The planner's motion
   heuristics (verbs like "roll beneath", "sprints") choose video regardless.
   The "Still Frames" job fetched stock VIDEOS despite `defaultVisual:"image"`.
   Compensations: (a) bind local stills via `[Visual: x.jpg]`, (b) for stock
   images use the Pexels-image + local-binding path (the Downloaded Frames job),
   (c) accept the planner choice. There is no per-scene kind override object.
2. **`node -e "require('./workspace/.../x.json')"` throws MODULE_NOT_FOUND**
   on this repo: package.json `main` = `dist-electron/electron-main.js`
   (absent), so bare `require('./relative')` tries to load the package entry.
   Use `node -e "const fs=require('fs'); JSON.parse(fs.readFileSync('<abs path>','utf8'))"`.
3. **Job workspaces are not always `workspace/jobs/<id>`** (AGENTIC_WORKSPACES_ROOT
   isolation) — `ls workspace/jobs/ultimate` can 404 while the job rendered fine.
   `find . -maxdepth 4 -name render-manifest.json` to locate the real workspace.
4. **freezedetect flags intentional stills.** Color Lab's freeze at 4.02–9.02 s
   = the `[KenBurns: off]` scene (deliberately static); Story's freeze at
   0.02–2.02 s = the static intro title card. Match freeze timestamps against the
   scene map before reporting defects. (Sibling case — slow Ken Burns flagged by
   freezedetect — is covered in avs-visual-frame-qa with the PSNR proof recipe.)
5. **`[KenBurns: off]` is a real per-scene tag**; `[KenBurns: on|off]` is the
   only motion tag. No `[Still:]`/`[Image:]` tag exists.

## Remotion path map (exploration handoff)

grep-verified facts for the pending "explore remotion + generated motion +
agentic downloading" task:

- **Modular CLI render = ffmpeg only.** `agentic-modular.ts` `render` stage calls
  `renderAgenticSlideshow` (`orchestrator/render.ts`). `job.renderer` is only
  passed into the plan request; nothing in the modular CLI branches on it.
- **`renderer: 'remotion'` branches in `management/autopilot.ts` `autoRunVideo`**
  (line ~440): tries `renderAgenticWithRemotion`, falls back to ffmpeg on error.
  No adapter calls `autoRunVideo` — drive via a tsx script.
- **`renderAgenticWithRemotion`** (`orchestrator/remotion.ts`, export at line 91):
  needs a full `PipelineResult` (`res.plan.title/orientation`,
  `res.workspace.jobId`, `res.manifest.assets[].localPath`); bundles
  `remotion/index.ts` → selects `AgenticVideo` composition → renderMedia per
  aspect. Chromium gate: `CHROME_EXECUTABLE` env or `ensureBrowser()` (20 s
  race) — Chrome is installed at
  `C:\Program Files\Google\Chrome\Application\chrome.exe` (set
  `CHROME_EXECUTABLE` to skip the download).
- **`runRemotionController`** (`agentic/media/hermes-remotion-controller.ts`,
  export at line 153): takes `MotionScene[]` + `ControllerOptions`
  (`jobId`, `maxRetries`, `fps`, `width`, `height`, `visionCheck?`,
  `allowFallback`). Codegen is TEMPLATE-based — `remotion-codegen.ts`
  `authorRemotionComponent` synthesizes .tsx from a `SceneSpec` (NO LLM needed;
  the "agent" path is optional `code` passthrough). 12 MotionKinds:
  kinetic/infographic/hud/diagram/ui/map/particle/procedural/logo/timeline/
  spectrum/abstract ('intro' is NOT valid). Successful output copied to
  `input/visuals/<jobId>_s<n>.mp4` → bind with `[Visual: <jobId>_s<n>.mp4]`.
- **`[GenMotion: ...]` / `[Motion: ...]` tags** → `extractMotionTags`
  (same file, export at line 182): returns `{sceneIndex: tagText}`.
  Config fields `autonomousMotion`, `motionByScene`, `motionAutoDecide`
  (`agentic/config.ts` ~line 300) are NOT dispatched by the modular CLI —
  call the controller directly.
- **Bulk agentic downloads (ad-hoc CLI)**: `agentic-batch.ts` line ~119:
  `--search "eagle" --count 10 [--kind video] [--orientation landscape]`
  → `workspace/bulk/{images,videos}/<slug>/` (via `runBulkImageFetch`).
  Note `agentic-batch` does NOT take `--file` (reads `agentic-scripts.json`).
- **Single-feature modes**: job field `mode: 'download-images' | 'download-videos'
  | 'download-music'` (+ `searchQuery`, `downloadCount`, `sceneIndices`,
  `downloadImagesOnly`, `downloadVideosOnly`) implemented in
  `agentic/operations/single-feature.ts` (`runSingleFeature`), used by
  `agentic-batch.ts` `--mode` path.

## Verification + delivery pattern (user standard)

1. ffprobe every final: h264 1280×720 (landscape) / 720×720 (square) + aac, duration.
2. Frame QA: `blackdetect=d=0.5:pix_th=0.10` and `freezedetect=n=-60dB:d=1`
   → 0 black; freeze hits cross-checked against the scene map.
3. `cp output/<id>/<title>.mp4 "/c/Users/PREM KUMAR/Downloads/<title>.mp4"`.
4. JSON sweep file validated with `node -e "JSON.parse(fs.readFileSync(...))"`
   and a fresh `npm test` (760/750 pass at time of writing) before reporting done.
