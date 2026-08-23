---
name: avs-agentic-workflow
description: AVS workflow via agentic-scripts.json plus Hermes capture.
---

# AVS Agentic Workflow — end-to-end operating model

Project: `C:\one\Automated-Video-Generator`. The agentic pipeline turns a
`input/scripts/agentic-scripts.json` job array into a rendered, multi-aspect video.
This skill is the **user-facing operating model** — what the system does automatically,
what Hermes (the agent) must drive manually, and what is genuinely missing. It pairs with
`automated-video-generator-dev` (code/architecture) and `avs-pipeline-verification`
(combinatorial test discipline).

## The one-sentence answer to "can it make a video from a topic/website?"
YES. From a single `agentic-scripts.json` job you get: **script → (Hermes-captured website
assets) + auto-downloaded stock images/videos/BGM → vision-verified assets → per-scene
agent editing → full tag control → real Kokoro voice → multi-aspect render.** The ONLY step
not yet auto-triggered from the JSON is **website capture** — that is performed by Hermes
using its OWN browser/computer_use tools (working today, no code change).

## The 8-stage flow (verified against source)

```
STAGE 1  SCRIPT            ✅ automatic (AgentBrain builds hook-first narration)
STAGE 2  WEBSITE CAPTURE   ✅ WORKING — Hermes drives it (browser_navigate +
         browser_vision for screenshots; computer_use capture for window;
         tools/computer-agent gdigrab for screen-record mp4). Files → input/visuals/.
STAGE 3  STOCK DOWNLOAD    ✅ automatic (visual-fetcher: Pexels/Pixabay/Openverse)
STAGE 4  VISION VERIFY     ✅ automatic (media-verifier pass/fail gate)
STAGE 5  PER-SCENE EDIT   ✅ automatic + agent-controlled (scene-edit.ts, agentic:edit)
STAGE 6  TAGS + STYLE      ✅ encoded in agentic-scripts.json
STAGE 7  VOICE             ✅ automatic (src/speech Kokoro; cold auto-starts)
STAGE 8  RENDER + CRITIQUE ✅ automatic (ffmpeg slideshow + 25+ FX plugins + multi-aspect)
```

## What is REAL and verified (do NOT re-litigate)
- **Auto-download images + videos** per scene from `agentic-scripts.json` via
  `src/lib/visual-fetcher/` (Pexels/Pixabay primary; Openverse/Wikimedia keyless fallback).
  With `PEXELS_API_KEY`/`PIXABAY_API_KEY` in `.env` (both SET in this project) → high quality.
  Without keys → still downloads via Openverse (lower relevance/coverage).
- **Auto-download BGM** via `src/lib/free-music.ts` + `music-system` — `musicQuery` field,
  **NO API key needed**. Falls back to a bundled tone if network fails.
- **Vision verification** of every asset via `src/lib/media-verifier.ts`.
- **Per-scene edit one-by-one**: `reorderScenes`/`deleteScene`/`insertScene`/`updateScene`
  (`src/agentic/media/scene-edit.ts`); CLI `agentic:edit --scene N`.
- **Visual/grade/transition/Ken-Burns/J-cut/caption tags** in `src/agentic/types.ts` +
  applied in `render.ts`.
- **Per-scene + global music control**: `musicOverride`/`musicIntensity`(calm/mid/energetic)/
  `volumeOverride`.
- **Real voice (Kokoro)** from `src/speech` — cold auto-starts (`speech-backend.ts` spawns
  `python -m speech.main` from `cwd=src`). Cloned voice needs a GPU Voicebox variant
  (chatterbox_turbo returns HTTP 500 on this CPU-only box).
- **25+ post-render FX plugins**: `src/agentic/plugins/` (motion/overlays/transitions/color/audio).
- **Multi-aspect export** (16:9 / 1:1 / 9:16).
- **Website screenshot + screen-record**: `tools/computer-agent/` (cua-driver + gdigrab).

## The exact command flow
```bash
# 1) edit the job in agentic-scripts.json (or Hermes writes it)
# 2) (Hermes step) capture the site → input/visuals/  [browser/computer_use tools]
# 3) run the pipeline
npx tsx src/adapters/cli/agentic-modular.ts pipeline --file input/scripts/agentic-scripts.json
#    or the older: npm run generate:agentic
# 4) one-by-one edit if needed: npm run agentic:edit -- --scene 3 --set grade=cinematic
# 5) output in output/<job-id>/
```

## Run a DEDICATED job file (backward-compat safe) ✅ prefer this
`src/adapters/cli/agentic-modular.ts` accepts a `--file <path>` flag. **Prefer it over editing
the shared `agentic-scripts.json`** (1600+ lines of example jobs — risky to mutate). Author
your reel as a standalone JSON array and run ONLY it:

```bash
npx tsx src/adapters/cli/agentic-modular.ts pipeline --file input/scripts/sproutern-reel-job.json
# or: npm run agentic:modular -- pipeline --file input/scripts/<your-job>.json
```
Same schema as `agentic-scripts.json`. A known-good Sproutern reel job (7-scene portrait,
local assets, Kokoro af_heart, burned neon captions, intro/outro cards) is in
`references/sproutern-reel-example.md` + `templates/` — copy and modify. Workspace:
`workspace/jobs/<id>/`; output: `output/<id>/`.

## Prepping website screenshots for 9:16 (capture → crop → bind)
`browser_vision`'s full-page screenshot is a TALL strip (e.g. 1350×21525). A 9:16 render
cover-crops the *middle*, missing the hero. **Crop each capture to a ~9:16 top section** first.
- ffmpeg is bundled: `./node_modules/ffmpeg-static/ffmpeg.exe` (NOT on PATH).
- **In-place crop fails** (can't read+write one file) — crop to a temp, then `mv` over.
- Dimension-parse pitfall: `hermes_tools.terminal()` in `execute_code` captures **stdout only**,
  so `ffmpeg -i … 2>&1 | grep` returns nothing there. Either run a **bash script via the
  `terminal` tool** (where `2>&1` reaches grep), or in execute_code do `D=$(ffmpeg -i "$p" 2>&1);
  echo "$D"` and parse the returned string.
- Reusable helper: `scripts/crop_9x16.sh <f1.png> [f2.png] …` crops each to `W × (W*16/9)` top
  section in place. Use it for every batch of captured assets.

Bind with `[Visual: file.png]` inside scene text — pipeline uses `input/visuals/file.png` if
present, else treats the text as stock keywords.

### PITFALL: acquire downloads stock even for local-asset scenes
The `visuals` stage fetches Pexels/Pixabay candidates for **every** scene, including ones with a
`[Visual: file.png]` binding (you'll see `scene_NN/candidate_1.mp4.part` downloading). That is
expected — the local asset is preferred at **render** time via the `localAsset` guard in
`pipeline.ts`. **Always verify the final render shows YOUR screenshot, not stock**: extract
frames (`ffmpeg -ss AFTER -i`) and vision-check. A stock leak means the `[Visual: …]` filename
didn't match a file in `input/visuals/` exactly (case/spacing/path).

### Capture gotcha
Before screenshotting sub-pages, confirm the real slug — guessed paths 404 (e.g. Sproutern
`/interviews` → 404; real list is `/interview-experiences`). A 404 yields a "Lost in the Digital
Universe" frame. Navigate, confirm content, then screenshot.

## RUNTIME TRAPS (verified 2026-07-26 — cost real renders)

### TRAP 1: `pipeline` subcommand HANGS at the gateway/verify stage
The monolithic `pipeline` run has been observed to **stall for many minutes** between the
visuals stage and voice generation — the log prints `✅ Acquired N candidates` then goes
silent (the gateway/verification step blocks; the download itself finished). Symptom is
identical across two independent runs on this box. **Workaround — drive the stages
yourself; they reuse the same `workspace/jobs/<id>/` artifacts:**

```bash
npx tsx src/adapters/cli/agentic-modular.ts plan   --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts voice  --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts render --file input/scripts/<job>.json
```
Voice generation is **per-scene and slow** (a few seconds each on CPU); a 12-scene reel
takes ~2 min end-to-end. Audio is cached per scene, so a re-run of `voice` is fast.
If a `voice` stage reports a scene `generation … did not complete (status=failed)` but the
`.wav` file exists on disk, it's a race in the in-memory status check — the asset is fine;
re-run `voice` and it will say `reused`.

### TRAP 2: `render` needs a manifest; re-binding reads `render-manifest.json`, NOT `plan.json`
The `render` subcommand does **NOT** re-read `plan.json` `localAsset` bindings. It reads
`workspace/jobs/<id>/render-manifest.json` (fallback `scene-data.json`).

**Preferred fix (2026-07-27):** for all-local jobs run `visuals --no-acquire` — it synthesizes
the manifest from `plan.json` localAssets and resolves BGM with NO network acquire. See the
"All-local-asset jobs — `--no-acquire` flag" section below.

If you must hand-edit a single scene's binding (re-bind to a different local file), patch the
manifest's `assets[]` instead of `plan.json`:

```jsonc
// workspace/jobs/<id>/render-manifest.json → assets[] entries
{ "sceneIndex": 2, "kind": "image",
  "localPath": "C:\\one\\Automated-Video-Generator\\input\\visuals\\interview-experiences.png",
  "license": "User-supplied — owner attribution" }
```
Set `kind: "image"` for stills, `kind: "video"` for clips. Then re-run `render`. The
`localAsset` field in `plan.json` ONLY takes effect when the `pipeline`/`plan` stage
writes the manifest — it is ignored on a standalone `render` re-run. (This is why a naive
"edit plan.json then re-render" produced a 5558 KB stock-footage draft while the good
2178 KB screenshot version required the manifest patch.)

### All-local-asset jobs — `--no-acquire` flag (added 2026-07-27)
When every visual is pre-supplied via `[Visual: file]` bindings (Hermes-captured screenshots,
agent-authored Remotion clips, hand-picked stock), run the **local path** instead of the
network `visuals` stage:
```bash
npx tsx src/adapters/cli/agentic-modular.ts plan    --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts voice   --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts visuals --no-acquire --file input/scripts/<job>.json
npx tsx src/adapters/cli/agentic-modular.ts render  --file input/scripts/<job>.json
```
`--no-acquire` synthesizes `render-manifest.json` directly from `plan.json` `localAsset`
bindings + resolves background music (explicit file or `musicQuery`) — **no network acquire,
no gateway, no hand-written manifest**. This removes the old TRAP 2 requirement to edit the
manifest by hand for fresh builds. The `render` subcommand still reads `render-manifest.json`,
so you MUST run `visuals --no-acquire` (or the full `visuals`) before `render`; it will not
re-read `plan.json`. Verified 2026-07-27: an 8-scene all-local job rendered end-to-end via
this path with zero manual surgery.

### Script authoring rule (parser behavior — drives scene count)
- 1 script line → 1 scene by default; the parser sentence-splits on `.?!`, so multi-clause
  em-dash lines (*"Meet AVS — … — MIT licensed."*) **formerly exploded into many scenes** (the
  AVS showcase run produced 14 from 8 → fixed by B1).
- **A line carrying a `[Visual: file]` tag is kept WHOLE as one scene** (B1 fix, 2026-07-27).
  Bind your local asset on the SAME line as the narration. Stage assets into `input/visuals/`
  before `plan` (the parser only sets `localAsset` if the file already exists there).
- `applyProEdits` skips the hook-first reorder when scenes have `localAsset` bindings (B3 fix,
  2026-07-27), so a CTA written last stays last (previously the planner moved it to scene 0).

### Command-flow corrections
- `agentic:modular` reads `--file`. **`agentic:batch` does NOT take `--file`** — it always
  reads `agentic-scripts.json`. Use the modular CLI for single-file jobs.
- `backgroundMusic: "x.mp3"` resolves against **`input/bgm/`**, NOT `input/visuals/`
  (`src/lib/path-safety.ts` → `inputBgmPath`). Dropping the file in `input/visuals/` is a
  silent miss. `musicQuery` (stock, no file) is unaffected.

### CLI JOB-SPEC CONTRACT (cost real iterations 2026-07-28)
`src/adapters/cli/agentic-modular.ts` parses a job file VERY specifically. Getting any of
these wrong silently yields 1 scene, a JSON parse error, or the cryptic
"No approved visuals to render" at the render stage:
- **It reads `job.script`** — a narration STRING with `[Visual: file]` tags (one line = one
  scene). It does NOT consume a `scenes` array you put in the JSON. A job with `scenes` but
  no `script` collapses to 1 scene built from `[Visual: <topic>] <title>`.
  Author the narration in `script`, one `[Visual: <file>]`-tagged line per scene.
- **Top-level MUST be a bare JSON array** `[ {...}, {...} ]`, NOT `{ "jobs": [...] }`.
  The plan loop is `for (const job of jobs)` over the parsed value, so a wrapped object
  throws "jobs is not iterable".
- **`[Visual:]` tags must be BARE filenames resolvable under `input/visuals/`** (e.g.
  `[Visual: a.mp4]` where `input/visuals/a.mp4` exists). The parser sets `localAsset` ONLY
  if `inputAssetPath(tag)` exists (script-parser.ts:303/375/420). An absolute path or a file
  anywhere else → `localAsset = undefined` → the `--no-acquire` stage silently skips the
  scene ("scene N has no localAsset — skipping") → `render` dies with
  "No approved visuals to render." If your asset lives elsewhere, COPY it into `input/visuals/`
  first and keep the tag a bare name.
- Set `hookFirst: false` on a local-asset job to preserve your authored scene order (B3 fix).
- Reusable harness that encodes all of the above + does plan to voice to visuals --no-acquire
  to render and emits a vision grid: `scripts/bug-hunt-harness.mjs` plus
  `references/bug-hunting-workflow.md`.

### Brand-name discipline in reference docs
When authoring a **general-purpose reference doc** (e.g. `AGENTIC_SCRIPT_FORMAT.md` field
reference), do NOT bake the live brand ("Sproutern") into example scripts/tags — use
generic placeholders (`SkillForge`, `career-tools.png`). The skill's own canonical example
(`references/sproutern-reel-example.md`) is exempt because it documents THIS real project;
only docs meant as reusable templates should be generalized. (Pairs with
`brand-safe-doc-authoring`.)

## ONE-BY-ONE AGENT-DRIVEN BUILD (learned 2026-07-27, AVS showcase run)
Full driver recipes (download-one + verify, agent-authored Remotion clip + verify, final-render
grid gate) are in `references/one-by-one-local-asset-recipes.md`. When the user demands "one
asset at a time, verify each before next" (no batch pipeline), the key traps are:

- **tsx import interop trap**: importing project `.ts` modules from a scratch `.mts` script puts
  all named exports under `default`. Fix: `import mod from '../src/...ts'; const { fn } =
  (mod as any).fn ? mod : (mod as any).default ?? mod;`. Probe first with
  `npx tsx -e "import('./x.ts').then(m=>console.log(Object.keys(m)))"` — don't waste retries
  swapping `.js`/`.ts` extensions.
- **One-scene Remotion works great**: `runRemotionController([{index,text,kind,code,durationInFrames}],
  {jobId,maxRetries,fps,width,height,allowFallback:false})` with hand-authored TSX in `code`
  rendered first-attempt for logo/infographic/CTA scenes; output → `input/visuals/<jobId>_s<n>.mp4`.
  Valid `kind` = MotionKind union in `remotion-codegen.ts`
  (kinetic/infographic/hud/diagram/ui/map/particle/procedural/logo/timeline/spectrum/abstract) —
  'intro' is NOT valid.
- **One-asset stock download**: `searchVideos(q, 1, 1, 'landscape')` (limit=1) + native fetch with
  a UA header; 4K Pexels sources are fine (render downscales).
- **Vision on big frames**: `vision_analyze` TIMES OUT on 3840/4096-wide extracted PNGs. Always
  extract with `-vf scale=1280:-1` to jpg before vision-checking.
- **Sentence-split trap — FIXED by B1 (2026-07-27)**: a line carrying `[Visual: file]` is now
  kept WHOLE as one scene, so the 14-scene explosion no longer happens. Still: write each scene
  as one `[Visual:]`-tagged line; the parser sentence-splits un-tagged lines on `.?!`.
- **Scene-order trap — FIXED by B3 (2026-07-27)**: `applyProEdits` skips hook-first reorder when
  scenes have `localAsset` bindings, so author order (CTA last) is preserved. No more manual
  `plan.json` reordering.
- **`render` needs a manifest — FIXED by B2 (2026-07-27)**: run `visuals --no-acquire` to
  synthesize the manifest from `plan.json`; no hand-writing required (see the flag section above).
  For the rare manual re-bind, still edit `render-manifest.json` (TRAP 2).
- **Free-music API**: `src/lib/free-music.ts` exports `resolveFreeBackgroundMusic(query,
  {intensity, durationSec})` (+ providers CcMixterFreeProvider / InternetArchiveProvider /
  OpenLofiProvider / FallbackToneProvider / LocalFreeProvider) — there is NO
  getFreeMusic/downloadFreeMusic. Result `localPath` lands under
  `workspace/cache/free-music/processed/`.
- **Final verification**: extract frames across the whole timeline (~every 8s), xstack them into
  ONE grid image, and vision-check the grid in a single call — confirms scene order, caption
  legibility, and no stock leaks far cheaper than per-frame calls.

## RUNTIME ARTIFACT CONTAINMENT (HARD USER RULE, 2026-07-27 session 2)
ALL runtime artifacts — downloaded/rendered media, agent driver `.mts` scripts, extracted
verification frames, scratch logs, generated job JSON — MUST live under `workspace/`
(git-ignored), **NEVER at the project root**. This was a direct correction this session:
the agent had been writing `tmp_agent_run/` to repo root; user demanded *"everything need
to be create only in the work space folder"* and later *"all the thing i need workspace only
that is correct"*.
- Move `tmp_agent_run/` → `workspace/tmp_agent_run/` (ffmpeg/tsx run fine from there).
- `input/visuals/`, `output/`, `workspace/` are already git-ignored; `workspace/tmp_agent_run/`
  therefore never enters a commit.
- When authoring verification recipes / docs that extract frames or run scratch scripts, write
  to `workspace/tmp_agent_run/`, NOT `tmp_agent_run/`. `AGENT_EXECUTION_GUIDE.md` was corrected
  (9 refs) to use `workspace/tmp_agent_run/`.
- CRITICAL: never create scratch files at repo root (cwd). If a command defaults to cwd,
  redirect its output to `workspace/tmp_agent_run/`.

## VERIFICATION DISCIPLINE (this user insists on empirical proof — honor it)
A "typecheck passes" / "plan exits 0" is NOT proof the system works. The user repeatedly
asked "is this already done?" and "verified?" — prove with REAL runs:
- For voice: kill the backend, run a voice stage cold, grep log for `backend is up`
  (auto-spawned) vs `fallback` (Edge-TTS). See `references/voicebox-auto-start.md`.
- For assets: confirm files exist on disk (`find workspace/jobs/<id> -name 'scene_*_voice.wav'`),
  `ffprobe` them (expect `pcm_s16le 44100Hz mono`).
- For render: extract a frame with `ffmpeg -i final.mp4 -ss N -frames:v 1 out.jpg`
  (**`-ss` AFTER `-i`**, never before — before yields black/undecodeable frames on J-cuts)
  and `vision_analyze` it. Confirm aspect, caption legibility, watermark, no blank emoji.

## COMMIT / PUSH DISCIPLINE (user rule, 2026-07-27 — REINFORCED this session)
When the user approves committing/pushing AVS work, apply this strictly. This was re-affirmed
loudly mid-session (*"okay now ignore all the images and all the error codes the worked
videos generation code only need to be push"*):
- **Push ONLY functional video-generation code.** Stage the source files that change
  behavior (e.g. `src/agentic/...`, `src/lib/...`, `src/adapters/...`) + their tests.
- **Ignore / revert lint-only cleanups.** The user explicitly does NOT want lint-error
  cosmetic fixes bundled into the working-code commit. If you started a lint cleanup,
  `git checkout --` those touched files BEFORE staging. (Confirmed pattern this session:
  4 lint-error files were reverted via `git checkout --` and excluded; only B1/B2/B3 + tests
  were pushed.) Pre-existing lint debt in untouched files is the user's to decide on — do
  not fold it into your feature commit.
- **Never push images / generated media.** `input/visuals/`, `output/`, `workspace/` are
  git-ignored already; `workspace/tmp_agent_run/` (agent driver `.mts` scripts) and generated
  job JSON (`input/scripts/<x>-job.json`) stay untracked — leave them out of the commit.
- **Selective-file commit:** when the user says "commit everything except <file>.md", stage
  every other meaningful change and EXCLUDE only that one file (`git add <list>` with the
  named file omitted). Verified this session: 5 files pushed, `AGENT_EXECUTION_GUIDE.md`
  left uncommitted at user's request.
- **One focused commit**, message matching repo style (`fix: ...`, `feat: ...`,
  `chore: ...`). Then `git push origin main`. The user authorizes the push once the
  working code is verified — do not pause to ask again.
- **Verification gate before push**: the code must have passed `npm run typecheck`
  (always) and a real end-to-end render/vision check where applicable. Lint passing is
  NOT a gating requirement for this user.

## DOC DRIFT & FORMAT-REFERENCE TRAPS (verified 2026-07-27 analysis)

When extending/auditing AVS docs or trusting the format reference, these drift points bite:

### D1 — TWO `AGENTIC_SCRIPT_FORMAT.md` copies DISAGREE; `docs/` is STALE
- `input/scripts/AGENTIC_SCRIPT_FORMAT.md` (1516 lines) is the **current** reference:
  has `[Motion: comp@library]`, `[GenMotion: free-text]` + `autonomousMotion`,
  multi-persona/dialogue (§15), `exportAspects:["4K"]` (§13), full audio-processing (§8.3).
- `docs/AGENTIC_SCRIPT_FORMAT.md` (924 lines) is an **older revision** — it LACKS
  Motion/GenMotion, personas, `exportAspects`, §8.3 audio processing, §11.2 advanced
  transitions. Anyone reading `docs/` gets a crippled mental model.
- **Rule:** treat `input/scripts/AGENTIC_SCRIPT_FORMAT.md` as source of truth. If you
  must cite the format in a doc, link the `input/scripts/` copy or sync `docs/` to it.
  Do NOT author features assuming the `docs/` fields exist.

### D2 — Plugin docs OVERSTATE render-path wiring (verify before trusting)
The format doc §10–§11 + `AGENT_EXECUTION_GUIDE.md` Phase 17 imply ~13 motion/transition/
overlay plugins are live. **As of 2026-07-27 session 2 this was PARTIALLY fixed** — grep
`compose.ts` for CALLS, not just imports:
- **Wired into the ffmpeg render path (per-scene, per `compose.ts:279-340` FX map):**
  `applyParallax`, `applyParticles`, `applyShake`, `applySpeedRamp`, `applyPunchIn`, plus
  `watermark` / `lowerThird` / `progressBar`. These read `shakeByScene` / `speedRampByScene`
  / `punchInByScene` / `parallaxDepthByScene` / `particlesByScene` from the job spec.
- **xfade transition name mappings now LIVE in `compose.ts` (xfade chain, ~line 754):**
  `glitch→pixelize`, `whippan/whip-pan→hblur`, `morphcut/morph-cut→smoothleft`,
  `lightleak/light-leak→fadewhite`, plus `slide→slideleft`, `zoomblur→zoomin`, `cut→fade@0`.
  So `transitionInByScene:{"0":"glitch"}` NOW renders a real blocky glitch transition.
- **STILL present as modules but NOT auto-dispatched from JSON:** `kenBurnsPro`,
  `dynamicCaptions`, `typewriter`, `lightLeak`, `colorWheels`, `filmGrain`, `halation`,
  and the `plugins/*` overlay/transition *files* (compose uses its OWN `buildOverlayPlan`
  for lowerThird/progressBar/captions — the plugin files are separate/dead). `compose.ts`
  does not read `motionByScene` to call the `kenBurnsPro`/`glitch`/etc plugin modules
  directly; it calls the `advanced-fx.ts` functions + uses xfade name mappings.
- **Consequence for job specs:** `shakeByScene`/`speedRampByScene`/`punchInByScene`/
  `parallaxDepthByScene`/`particlesByScene` + `transitionInByScene:{"0":"glitch|whippan|
  morphcut|lightleak|slide|zoomblur|cut"}` are REAL and render. `motionByScene` with
  `kenBurnsPro`/etc is still NOT auto-applied — call that plugin directly or via `agentic:edit`.
- The 25+ plugins ARE real files and DO work when called directly (e.g. via `agentic:edit`
  or a custom driver) — the gap is only the *automatic dispatch* from JSON for that subset.
- VERIFIED this session: `applyShake`/`applySpeedRamp`/`applyPunchIn` produce real MP4s;
  the 4 extended xfade transitions render valid frames (vision-checked blocky/horizontal-streak/
  bright-flash). Source: `src/agentic/operations/advanced-fx.ts` + `compose.ts`.

### D3 — 4K is an Upscale, not native 4K source
`resolveAspectSizes` (`advanced-fx.ts:369`) maps `"4K"→[3840,2160]` and `exportAspects`
scales the BASE render with `scale=…,pad=…`. There is **no native-4K source path** —
Remotion clips and stock are 1080p/lower unless you author them at 3840. For genuinely
sharp 4K, either: (a) author Remotion compositions at 3840×2160, or (b) accept the upscale.
Document this caveat whenever you advertise "4K export".

### D4 — `AGENT_EXECUTION_GUIDE.md` gaps for advanced/local-asset runs
The root workflow guide is 90% accurate but under-documents the BEST path. **Status as of
2026-07-27 session 2:**
- ✅ **ADDED (this session):** `--no-acquire` local-asset path (G1), "1 line = 1 scene"
  authoring rule + author-order-preserved note (G2/G4), `[GenMotion:]` callout as the bespoke
  motion route (G3), 4K-upscale caveat (G6), and the verifiable per-asset + final-grid
  `vision_analyze` snippet (G5) — all present in the working-tree `AGENT_EXECUTION_GUIDE.md`
  (uncommitted; user excluded it from the push).
- ✅ **FIXED (this session):** all 9 `tmp_agent_run/` references → `workspace/tmp_agent_run/`
  (containment rule, Issue 1). The guide now matches the HARD rule that runtime artifacts
  live only under `workspace/`.
- ⚠️ **DEFERRED (Issue 2, not yet fixed in the guide):** Phase 17 still overstates plugin
  wiring — says "all wired into compose.ts lines 279-328". Reality (see D2): motion FX +
  xfade name mappings ARE wired; overlay/transition *plugin modules* are NOT auto-dispatched
  (compose uses its own overlay engine + xfade mappings). Correct Phase 17 wording when you
  next touch the guide: motion plugins wired; overlay/transition plugins exist as modules
  (compose uses its own overlay engine + xfade mappings).
When you update `AGENT_EXECUTION_GUIDE.md`, keep the four added items and fix the Phase 17
overstatement — they make the local-asset "agent does it one-by-one" workflow executable
without manual manifest surgery.

(Verified via grep of `src/agentic/operations/compose.ts` for CALLS not imports, and
`find src/agentic/plugins -name '*.ts'`, on 2026-07-27. The two `AGENTIC_SCRIPT_FORMAT.md`
copies were diffed line-by-line; `resolveAspectSizes` body read from `advanced-fx.ts`.)

## COMBINATION SWEEPS — asset × orientation × feature matrix (proven 2026-08-01)
The user's "try ALL the combinations" mandate has a proven operating pattern:
author a DEDICATED sweep job file (`input/scripts/<sweep>.json`, one job per
combination), run the modular pipeline in the background
(`npm run agentic:modular pipeline -- --file input/scripts/<sweep>.json`),
ffprobe + frame-QA every output, copy the finals to `C:\Users\PREM KUMAR\Downloads`.
For FEATURE sweeps use ALL-LOCAL assets (AI-generated + downloaded images staged
in `input/visuals/` and bound with `[Visual: file]`) so the run is minutes, not
an hour — Pexels 4K video originals can be 100–200 MB each at ~1.8 MB/s, and a
scene with motion keywords downloads 2 such candidates.

### Proven coverage (all rendered, QA-clean; job files: `input/scripts/asset-sweep.json`, `fx-sweep.json`)
- **Assets**: FLUX 3 generated video · AI-generated image (Pollinations `sana`)
  · downloaded stock image (Pexels) · downloaded stock video (Pexels) · every
  mix in ONE video (AI image + stock video + stock image via `[Visual: file]`
  tags for local kinds + untagged lines for planner-chosen stock).
- **Orientations**: 16:9, 9:16, 1:1 (square) — all three proven.
- **Feature surface**: filters (`[Filter: bw|sepia|vintage|blur]`), grades
  (job `grade` + per-scene `[Grade: neutral|warm|cool|cinematic|vivid]`),
  24 transitions (`[Transition: fade|slide|zoomblur|cut|glitch|whippan|morphcut|
  lightleak|wipe|dissolve|circle|...]` + job `transition`), motion (Ken Burns
  on/off, slow-mo/timelapse via `clipSpeedByScene`), overlays (kineticText,
  karaoke/burned captions, progressBar, emojiByScene, lowerThird,
  titleCard/endCta, textOverlayByScene), audio (duckDepth, musicIntensity,
  crossfadeSec, sfx, normalizeLufs, voiceSpeed, loopMusic, ttsStyle),
  structure (hookFirst, variablePacing, sceneOrder, beatSync, loopVideo,
  posterScene, contactSheet), advanced per-scene color (colorTempByScene,
  contrastByScene, saturationByScene, brightnessByScene).

### Pitfalls proven this session
- **Scene length = VOICEOVER length on the modular CLI path.** `minSceneDuration` /
  `maxSceneDuration` / `sceneDurationByScene` are documented but NOT wired into
  `agentic-modular.ts` — a 5-minute video is authored as ~40-word scenes (~16s each),
  not via padding fields. The renderer sizes scenes from
  `manifest.assets[].durationSec`. Full mechanism + recipe:
  `references/voice-duration-and-long-videos.md`.
- **Voice audio cache is text-hash validated (fixed 2026-08-01).** A re-run with a
  CHANGED script used to silently reuse stale short WAVs (40-word lines → 2.5s audio).
  Now `resolveExistingAudio` deletes any file whose `.txt-hash` sidecar doesn't match
  the current text. If re-run audio sounds short, ffprobe the WAVs + sidecars before
  blaming SAPI.
- **`defaultVisual: "image"` is a HINT, not a hard kind lock.** The planner's
  motion heuristics override it — a job declaring images still fetched VIDEOS
  (the "Still Frames" run). To force images, bind local files
  (`[Visual: x.jpg]`); to force videos, use motion keywords. There is NO
  per-scene kind override object — kind flows from `[Visual: file]` bindings +
  planner heuristics only.
- **Mixed kinds in one job work through the NORMAL path** (no `--no-acquire`):
  `[Visual: file]` lines pin local assets, untagged lines get stock per the
  planner. Confirm the mix with `grep '"kind"' workspace/.../render-manifest.json`.
- **`node -e "require('./workspace/...json')"` FAILS on this repo** — package.json
  `main` points at `dist-electron/electron-main.js` (absent), so bare `require`
  of a relative path loads the package and throws MODULE_NOT_FOUND. Use
  `fs.readFileSync('<abs path>', 'utf8')` + `JSON.parse` instead.
- **Job workspaces may NOT be at `workspace/jobs/<id>`** (AGENTIC_WORKSPACES_ROOT
  isolates them) — locate manifests with
  `find . -maxdepth 4 -name render-manifest.json`.
- **freezedetect hits INTENTIONAL stills** (a `[KenBurns: off]` scene, a static
  intro/outro title card) — match the freeze timestamps to the scene map before
  calling a defect (see avs-visual-frame-qa).

### Remotion / motion-graphics path map (exploration handoff)
Full detail + recipes: `references/combination-sweeps.md`. Key facts:
- The modular CLI `render` stage is **ffmpeg-only** (`renderAgenticSlideshow` in
  `orchestrator/render.ts`). `renderer: 'remotion'` branches ONLY in
  `management/autopilot.ts` `autoRunVideo` — which has **no CLI adapter**; drive
  it via a tsx script.
- `renderAgenticWithRemotion` (`orchestrator/remotion.ts`) needs a PipelineResult
  + Chromium (`CHROME_EXECUTABLE` env or `ensureBrowser()`; system Chrome at
  `C:\Program Files\Google\Chrome\Application\chrome.exe` — set the env var to
  skip the ~150 MB browser download).
- The autonomous motion-graphics controller `runRemotionController`
  (`agentic/media/hermes-remotion-controller.ts`) is **template-based codegen**
  (`remotion-codegen.authorRemotionComponent` — no LLM required), 12 MotionKinds
  (kinetic/infographic/hud/diagram/ui/map/particle/procedural/logo/timeline/
  spectrum/abstract), pluggable `visionCheck` hook; output integrates to
  `input/visuals/<jobId>_s<n>.mp4` for `[Visual:]` binding.
- `[GenMotion: …]` / `[Motion: …]` script tags → `extractMotionTags`; job fields
  `autonomousMotion`, `motionByScene`, `motionAutoDecide` exist in config but
  are NOT wired into the modular CLI (drive the controller directly).
- Bulk agentic downloads: `npx tsx src/adapters/cli/agentic-batch.ts --search
  "eagle" --count 10 [--kind video] [--orientation landscape]` →
  `workspace/bulk/{images,videos}/<slug>/`. Single-feature modes
  (`mode: 'download-images'|'download-videos'|'download-music'` + `searchQuery`/
  `downloadCount`) live in `agentic/operations/single-feature.ts`.

## MULTI-SUBAGENT BUG HUNT (technique, 2026-07-28)
When asked to find/fix bugs by generating + visually verifying videos, run parallel
subagent hunters partitioned by subsystem, each using the reusable harness + vision grid.
Full recipe, the voice-backend lock pattern, and the real edit.ts bugs found:
`references/bug-hunting-workflow.md`; harness at `scripts/bug-hunt-harness.mjs`.
Documented in `references/avs-agentic-capabilities.md`. Key points:

### CRITICAL: the CLI `render` stage uses `orchestrator/render.ts`, NOT `compose.ts`
`agentic-modular.ts render` calls `renderAgenticSlideshow` (render.ts). `compose.ts`
(crossfadeSlideshow / audio-mix / particles / anequalizer) is reached ONLY by direct
`composeVideo()` callers. **render.ts has its OWN duplicated ffmpeg filter code** — vintage/sepia
at `render.ts:734-736`, its own xfade chain at `render.ts:547`, its own amix at `render.ts:660/853`.
So fixing a filter bug in `compose.ts` does NOT help the standard CLI pipeline unless the SAME
bug is also fixed in `render.ts`. **Rule: when fixing a ffmpeg filter/class of bug, grep BOTH
files and patch both, or confirm which path the CLI actually uses before claiming the fix works.**
This session the vintage/sepia no-op only actually helped users once `render.ts:734-736` was
patched — the `compose.ts` patch alone was inert for the standard pipeline.

### Real bugs found + fixed this session (2026-07-28, evidence-backed)
- **`edit.ts`** (HIGH): `trimVideo`/`splitVideo` `-c copy` on non-keyframe splits → empty 0-stream
  output that exits 0 → re-encode libx264 + ffprobe duration validate (#1,#2); `interpolateVideo`
  `mode=blend` invalid → `mi_mode=blend` (#3); `changeSpeed` hard-codes `[0:a]` (crashes audio-less
  visuals) + 0.25x slow-mo fails (atempo range) → audio-aware graph + chained atempo (#4,#5);
  `addAudio(mix)` on audio-less video → degrade to replace (#6); `silenceRemove` misleading success
  + A/V desync → fail loud + re-encode (#7); `addProgressBar` defaults 10s → probe real duration (#9);
  `cropVideo` preset non-exact SAR → `setsar=1` (#10); `mergeVideos` silently drops audio → keep when
  all inputs have it, FIXED interleaved concat order `[v0][0:a][v1][1:a]` NOT `[v0][v1][0:a][1:a]` (#11).
  Regression: `src/agentic/operations/edit-regression.test.ts` (10/10, self-seeds ffmpeg fixtures).
- **`compose.ts`**: xfade graph invalid → every transition silently a hard cut (chained `[v{n-1}]`
  link + `;` + `format` on final label); audio-mix invalid when voiceVolume/duck≠1 → silent video
  (track amix labels, feed into amix); particles `[ov]` unmapped → add `-map "[ov]"`; anequalizer
  invalid string → correct `params='c0 f=..:w=..:g=..:t=q:c1 ..'`.
- **`visual-fx.ts` + `render.ts`**: `vintage` (`saturation=` not a filter) + `sepia=0.8` (absent in
  this ffmpeg build) → both no-op (#4, fixed in BOTH with `curves=vintage,eq=saturation=1.2` +
  `colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131`).
- **Audio path**: render crash (`voiceovers.scenes[idx]` on slim fallback shape) — a guard with
  optional chaining already existed at `render.ts:759-766`; re-run renders fine (2.1MB MP4, audible).

### Proof the fixes worked (run this before claiming done)
1. `npm run typecheck` clean (always).
2. `node --import tsx --test src/agentic/operations/edit-regression.test.ts` → 10/10.
3. CLI render a job with `voiceVolume:0.6` + `duckDepth:0.3` + `[Filter: vintage]`/`[Filter: sepia]`
   + `[Transition: glitch|slide|whippan|fade]`. Expect: NO `xfade failed → fallback to concat`
   warning (previously every render logged one), vision confirms vintage=warm / sepia=brown, and
   `ffprobe -select_streams a` shows an audio stream with `volumedetect` mean ~-25dB (NOT silent).
4. Copy deliverable to `C:\Users\PREM KUMAR\Downloads\`.
Full per-area findings: `workspace/bug-hunt/findings_{core,parser,audio,editing}.md`;
consolidated report `docs/AVS_BUG_HUNT_REPORT.md`. See `avs-visual-frame-qa` for objective FX
verification (pixel metrics, not vision alone). `edit.ts` bug-by-bug map + regression pattern:
`references/edit-ts-bug-map.md`.
- Website capture is **agent-driven (Hermes tools), not JSON-triggered**. There is NO
  `capture` field in `agentic-scripts.json` and `tools/computer-agent` is NOT imported by
  the orchestrator (`src/`). If you say "the pipeline captures the website automatically",
  that is FALSE — Hermes does it. (A `capture:[…]` JSON field is a proposed future convenience,
  not required — the working method is Hermes capture.)
- Vision is **verify-only (pass/fail)**, not rank-and-pick from a candidate pool.
- No green-screen / speed-ramp-bound-to-scene / clip in-out trim / keyframe zoom / split-screen
  wired as scene signals yet (ffmpeg-native fixes exist, not yet implemented).
- Cloned voice needs GPU (CPU box → chatterbox 500).
- **Single-image toolbox is MISSING.** Images are treated as *pipeline inputs*, never as
  standalone editable artifacts. Verified against source 2026-07-26:
  - Image→image **format conversion** (png→jpg/webp/tiff): ❌ no code path. `convert.ts`
    handles video/audio only; `agentic-editor.ts` only *extracts* frames (video→image).
    No Sharp/Jimp/ImageMagick dep. (ffmpeg CAN do it but nothing wraps it.)
  - **Image→Video** (standalone still → motion clip): ❌ no command. `render.ts:533`
    does `-loop 1 -i img + zoompan` Ken Burns, but ONLY inside the full `renderAgenticSlideshow`
    pipeline (needs `plan.json`+workspace+script). `convert.ts`/`agentic-editor.ts` have no
    `image2video`/`kenburns` command.
  - **Text/emoji on a SINGLE image**: ❌ not implemented. `agentic-editor.ts` `overlay-text`
    (drawtext) / `overlay-image` (watermark) require a **video** `-i` input. `emojiByScene` /
    `textOverlayByScene` (`cli-job.ts:203`) apply *per scene during render* only.
  - Crop/resize/rotate/adjust (`agentic-editor.ts`) exist but are **video-input** commands;
    they'd run on an image (ffmpeg is format-agnostic) but there's no image-specific UX.
  - **Impl path if asked:** add `agentic-image.ts` (or extend `agentic-editor.ts`) with
    `convert-image`, `image-to-video` (Ken Burns + optional burned text/emoji), `image-text`,
    `image-emoji` — each ~20-40 LOC of ffmpeg wrappers. The render-time image→video machinery
    in `render.ts:484` (zoompan expr) and `cli-job.ts` emoji/text overlays are the reference impls.
- Agent-authored Remotion codegen IS real (proven 2026-07-27): pass hand-written TSX via the
  `code` field to `runRemotionController` — logo/infographic/CTA scenes rendered first-attempt.
  The old claim "no agent-authored codegen, static compositions only" is obsolete.

## The "is this already done?" trap (learned this session)
When documenting a system capability, **verify against source before claiming it exists**.
This session a doc (`hermes-special-integration.md`) described website capture/screen-record
as pipeline features; on inspection `tools/computer-agent/` is real code (cua-driver + gdigrab
screen-record DOES exist — so screen-recording is NOT missing), but it is **agent-run, not
auto-wired into the orchestrator**. The local-asset binding (`[Visual: file.png]` →
`input/visuals/`) and the BGM auto-download ARE automatic. Always separate:
AUTOMATIC (code does it) vs AGENT-DRIVEN (Hermes runs a tool) vs MISSING.

## Voicebox cold auto-start — CRITICAL FIX (2026-07-26)
`src/lib/speech-backend.ts` spawns `python -m speech.main` from `cwd=src` when
`TTS_PROVIDER=voicebox` and no backend is up. It TRIED but the spawned server died instantly
→ silent Edge-TTS fallback. **Root cause:** spawn used `env: { ...process.env, PYTHONPATH: '' }`.
On Windows/venv, blanking `PYTHONPATH` suppresses the venv's `site-packages` discovery when the
module is imported as a package (`from .app import app` → `from fastapi import FastAPI` →
`ModuleNotFoundError: No module named 'fastapi'`), so uvicorn never starts. **Fix:** spawn with
`env: { ...process.env }` (let the in-repo venv resolve its own packages). Full cold-start
proof recipe + `taskkill /F /T` MSYS note in `references/voicebox-auto-start.md`.

**Lesson (reusable):** when a spawned child dies with `No module named X` where X is a venv dep,
suspect a cleared `PYTHONPATH`/`PYTHONHOME` in the spawn env, NOT a missing package. Reproduce
the spawn manually with the SAME env to confirm (manual spawn with inherited env works; with
`PYTHONPATH=''` fails with the exact `No module named 'fastapi'`).

## User preference (embedded from this session)
This user demands **empirical verification, not claims**. Before reporting "X works" or "X is
done", produce REAL evidence: a real render + frame extraction + vision inspection, a live
curl/health check, or a disk-confirmed file. Static checks (tsc, unit exit 0, plan exit 0) are
necessary but NOT sufficient. Also: keep the working doc HONEST about automatic vs agent-driven
vs missing — do not describe agent-driven capture as automatic pipeline behavior.
