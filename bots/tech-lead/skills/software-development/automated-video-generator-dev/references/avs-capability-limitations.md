# AVS Capability & Limitation Map (advanced agentic video editing)

Condensed, VERIFIED knowledge bank for the recurring "what can AVS do / what are the
limits / what's missing" class of ask. Every line below was confirmed against the repo
in-session (file:line or direct run), not from memory. Read this BEFORE promising the
user a feature, and before listing "limitations" — at least one prior answer was wrong.

## 1. Asset CAPTURE (Hermes Special Integration) — REAL, two halves
The doc `hermes-special-integration.md` describes a workflow. Reality:

**DONE + automatic (pipeline side):**
- `[Visual: file.png]` → `input/visuals/file.png` binding. `src/lib/script-parser.ts`
  line ~283/314: `localAsset: fs.existsSync(inputAssetPath(tag)) ? tag : undefined`.
  Missing file → falls back to stock keyword. `pipeline.ts` (151-199) won't overwrite a
  scene that already has a `localAsset`. Verified working.
- All referenced docs exist: `docs/CUA_ASSET_COLLECTION.md`, `docs/INPUT_ASSETS_GUIDE.md`,
  `input/scripts/INPUT_FORMAT.md`, `tools/computer-agent/README.md`, `docs/VOICEBOX_SETUP.md`.

**DONE + agent-driven (capture side, executed by Hermes, not auto-triggered by JSON):**
- `tools/computer-agent/src/driver.py` — real `cua-driver` wrapper: `screenshot()`,
  `list_apps()`, `list_windows()`, `window_state()`, `accessibility_tree()`, app launch,
  click/type/scroll/safe-mode secret guard.
- `tools/computer-agent/demo_record.py` — **SCREEN RECORDING to MP4** via ffmpeg `gdigrab`
  (`-f gdigrab -i desktop`). => "screen recording of a website" IS implemented (Windows).
  CORRECTION: an earlier session claimed "no screen-recording exists" — that was WRONG;
  this tool fills it. The only gap: it's a standalone demo script, not yet wired as an
  auto stage in the orchestrator (no `capture:[]` job field that triggers it).
- Browser nav + screenshot: `tools/computer-agent/src/assets.py` (`launch_browser`) +
  `driver.screenshot()`; also Hermes `browser_navigate`/`browser_vision` tools.
- Custom HTML → screenshot → `input/visuals/`: via Hermes `write_file` + `browser_navigate`.

**LIMIT (capture):** no `capture` job field in `agentic-scripts.json` that auto-runs
`tools/computer-agent` before the visual stage. Today I (Hermes) must be explicitly asked
to capture; then files land in `input/visuals/` and the pipeline picks them up automatically.
=> To make it hands-off: add `{ capture: [{url,type:"screenshot"},{app,type:"window"},
{url,type:"record",seconds:8}] }` to `PipelineRequest` → orchestrator calls `computer-agent`
before acquire. Additive, no old code changed.

## 2. EDITING — what's REAL (verified in code)
- Per-scene structural edit one-by-one: `reorderScenes`, `deleteScene`, `insertScene`,
  `updateScene(text/keywords/duration/localAsset)` — `src/agentic/media/scene-edit.ts`.
- Per-scene transition `fade|slide|zoomblur|cut` + `jCutSec` — `types.ts:36,76`.
- Per-scene grade `neutral|warm|cool|cinematic|vivid` — `render.ts` `gradeFilter`.
- Ken Burns zoom-pan (image→motion) — `render.ts:465`, `acquire.ts:141`.
- Caption theme (karaoke/lower-third/etc.) — `captionTheme`.
- 25+ post-render plugins in `src/agentic/plugins/`: motion (ken-burns-pro, parallax,
  punch-in, shake, speed-ramp), overlays (dynamic-captions, lower-third, progress-bar,
  safe-zones, typewriter, watermark), transitions (advanced, glitch, light-leak, morph-cut,
  whip-pan), color (wheels, film-grain, halation, lut-loader), audio (ambience, ducking,
  beat-sync, normalize), genres, platforms (multi-aspect 16:9/1:1/9:16).
- Logo/brand watermark overlay — `render.ts:801-833`. Audio ducking/normalize — `render.ts:690`.
- Real voice from `src/speech` (auto-start fixed this session) — see voicebox bridge ref.

## 3. EDITING — what's MISSING (verified gaps)
| # | Missing | Why | Free fix (all additive) |
|---|---|---|---|
| 1 | Chroma-key / green-screen | zero `chromakey`/`colorkey` in render path | add `chromaKey?` scene signal → `chromakey=color=0x00FF00:similarity=0.12:blend=0.1,despill` in `render.ts` like `grade` |
| 2 | In-clip speed-ramp / slow-mo binding | `speed-ramp.ts` plugin EXISTS but no scene hook; no `setpts`/`minterpolate` in render | bind existing `speed-ramp` plugin to `speed?:number` scene signal (`setpts=PTS/<speed>` + optional `minterpolate`) |
| 3 | Stabilization | no `libvidstab` anywhere | two-pass `vidstabdetect`+`vidstabtransform` behind `stabilize?:true`; needs ffmpeg built w/ libvidstab (ffmpeg-static may lack it → note limit) |
| 4 | Keyframe motion paths | only linear zoompan | extend `render.ts` filter to accept `keyframes?:{t,x,y,z}[]` → multi-keyframe zoompan/rotate/crop |
| 5 | Split-screen / PiP / multi-clip composite | no `hstack`/`vstack`/`blend` in scene path | add `composite` scene type (already partial in `compose.ts`); wire in `render.ts` |
| 6 | In/out clip trim | only `trim=duration`, no in/out | add `inSec`/`outSec` scene fields → `trim=start=..:end=..` |
| 7 | Agent-authored Remotion codegen | static compositions only; no runtime `.tsx` authoring | sandbox-generative component + tsc validation + ffmpeg fallback (see Remotion-codegen plan) |
| 8 | Semantic/narrative critique | critique is metric-only (black frames/aspect/peaks) | after render, extract frames → vision model → "does scene N tell the right story" → auto-revise |
| 9 | Auto-capture trigger from JSON | capture is agent-run manually | add `capture:[]` job field (see §1 limit) |
| 10 | Cloned voice on CPU | chatterbox_turbo `/models/load` 500 on CPU-only box | ENVIRONMENT limit, not code; needs CUDA/ROCm Voicebox variant. Kokoro works. |

## 4. Voice — REAL, with one env limit
- Kokoro (default, `af_heart` etc.) works end-to-end, auto-starts cold (fixed this session:
  `speech-backend.ts` must NOT blank `PYTHONPATH` — see "Voicebox auto-start bug" in SKILL.md).
- Cloned real voice: `cloneVoiceFrom` CREATES the profile but chatterbox_turbo SPEAK fails
  (HTTP 500) on CPU-only. ENV limit — don't chase the 500.
- `voiceSpeed` + `voicePitchSemitones` applied as ffmpeg post-fx (`asetrate`+`atempo`).

## 5. The "research the topic first" gap
- NO web research / scrape / crawl module exists. `AgentBrain` builds the plan heuristic/LLM-only;
  the script is SYNTHETIC (unverified facts, no citations). To add: `src/research/` (search+fetch)
  using free tiers (SearXNG/Ollama/OpenRouter). Vision is verify-only (`media-verifier.ts`),
  NOT rank-and-pick from a candidate pool.

## 6. How to answer "is AVS advanced enough?" honestly
1. Separate AUTOMATIC (pipeline does it) vs AGENT-DRIVEN (Hermes runs it) vs MISSING.
2. Don't claim a module exists from the doc alone — grep the repo (this caught the
   "no screen-recording" wrong claim; `demo_record.py` disproved it).
3. Per-scene editing, voice, motion plugins, watermark, multi-aspect export, asset capture
   (screenshot + screen-record) are REAL. Web-research, vision-select (rank), Remotion
   codegen, chroma-key, in-clip speed-ramp binding, stabilization, keyframes, split-screen,
   in/out trim, semantic critique, auto-capture-trigger are the gaps.
4. Environment limits (not code): cloned voice needs GPU Voicebox; stabilization needs
   libvidstab in the ffmpeg build.
