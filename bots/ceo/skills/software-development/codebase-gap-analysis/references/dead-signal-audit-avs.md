# Dead Control-Signal Audit — AVS worked reference

The AVS project (`C:\one\Automated-Video-Generator`) has a large `AgenticCliJob`
type (`src/adapters/cli/cli-job.ts`) whose fields feed an ffmpeg render pipeline
(`src/agentic/operations/compose.ts`, `overlays.ts`, `single-feature.ts`). Many
fields were declared but silently ignored by the deterministic render path. This
file records the ones found and fixed via the config-field audit (see
`codebase-gap-analysis` SKILL.md → "Declared config-field → actual-consumption
audit"), with the exact fix + verification for each.

## The audit method (reuse)
1. Declared surface: `grep -nE "^\s+[a-zA-Z]+\??:" src/adapters/cli/cli-job.ts`
2. Consumed surface: `grep -oE "job\.[a-zA-Z]+" src/agentic/operations/compose.ts | sort -u`
3. Diff → candidate dead signals. Then trace the real call chain across
   `buildPlanOnly` → `buildPlan` → `buildVoiceConfigs`/`applyVoiceConfigsToPlan` →
   `composeVideo`, because an override downstream can shadow an upstream default.

## Fixes (with precedence contracts)

### `platform` was AI-hint only → now drives output aspect
- Symptom: `platform:'youtube'` rendered 9:16 portrait; only the AI style-engine
  read it.
- Fix: `resolveOutputSize(job)` (extracted pure fn in `compose.ts`) maps
  `youtube→16:9`, `tiktok/reels→9:16`, `instagram→1:1`. Precedence:
  `explicit aspect > explicit orientation > platform-default > portrait-default`.
- Verify: `waveI_youtube_landscape` → 1280×720; `waveI_tiktok_portrait` → 720×1280
  (ffprobe). Unit test `compose-output-size.test.ts` (12 cases) locks the matrix.
- Commit `ed2b7d0` / `a1f692d`.

### `aspect:'square'` / `orientation:'square'` ignored → portrait
- Symptom: only `aspect:'1:1'` matched; `'square'` fell through to 720×1280.
- Fix: accept `'square'` in `compose.ts` + widen the type union across
  `cli-job.ts`, `orchestrator/types.ts`, `agentic/types.ts` Plan+RenderManifest,
  `pipeline/plan.ts`, `acquire.ts`, `register-agentic-tools.ts`, `search.ts`.
- Verify: `waveH_square_stack` → 720×720.
- Commit `308368e`.

### `brand.accent` dead (only Remotion read `accentColor`)
- Symptom: set a brand color in a job → no effect on ffmpeg captions.
- Fix: `buildOverlayPlan` honors `brand.accent` as text color when no
  `captionTheme`/`fontColor` set. Precedence:
  `captionTheme > fontColor > brand.accent > theme default`.
  `drawTextFilter` already converts `#RRGGBB`→`0xRRGGBB` for ffmpeg `fontcolor`.
- Verify: `waveK_brand_accent` (accent `#FF6B35`) → vision confirms orange
  burned captions + lower-third "Brewed by Prem".
- Commit `2ebdf6c` + `a8b5cc2`.

### `voice` default `en-US-GuyNeural` timed out on flaky TTS
- Symptom: unset `job.voice` resolved inconsistently; `en-US-GuyNeural` is the
  voice that fails on a flaky Edge-TTS connection, so the whole voice stage died.
- Fix (two sites, root-cause was downstream):
  - `single-feature.ts` `buildPlanOnly` default → `en-US-JennyNeural` (matches
    `buildPlan`).
  - **Root cause:** `voice-intel.ts:buildVoiceConfigs` defaulted `baseVoice` to
    `en-US-GuyNeural`, and `applyVoiceConfigsToPlan` OVERWROTE the Jenny
    `plan.voice` with Guy. Fixed `voice-intel.ts` base default → `en-US-JennyNeural`.
- Verify: `waveI_tiktok_portrait` logs `Voice: en-US-JennyNeural` and renders
  720×1280; `plan-voice.test.ts` (4 cases) locks both defaults.
- Commit `927b12d` + `fb3899f`.

## Cross-cutting patterns worth reusing
- **Extract resolution into a pure, exported, unit-tested helper** (`resolveOutputSize`,
  `buildVoiceConfigs`) so precedence contracts are regression-safe without a slow
  full render.
- **Verify with a real render + vision_analyze**, not just grep — a field "looks
  consumed" can still be behind a dead branch. One extracted frame asking "is the
  text orange?" is decisive.
- **Windows `execute_code` `node -e` JSON writes can silently not persist** (sandbox
  cwd mismatch). After writing `agentic-scripts.json`, re-read it in a `terminal`
  call to confirm the job exists before rendering; otherwise the render exits
  "No jobs matched filter" and wastes a 60–120s run.
