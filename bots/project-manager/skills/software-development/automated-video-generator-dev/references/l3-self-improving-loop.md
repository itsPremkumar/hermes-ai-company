# L3 Self-Improving Loop — READ SIDE IMPLEMENTED (2026-07-25, this session)

The `render-ledger.ts` learning store existed and *wrote* outcomes (autopilot →
`learnFromRender` → `recordRender`), but its read APIs (`bestFor` /
`winningChoices`) were dead code — no planner/brain consumed them, so every
render started cold and `AutonomyLevel:'L3-self-improving'` was a runtime lie.
This session closed the loop.

## What was added (standalone, additive, backward-compat — no old code deleted)
- `src/agentic/management/ledger-prime.ts` (NEW):
  - `primeInputFromLedger(input: Partial<AgenticConfig>, topic: string, file?)` — returns a primed copy of the user's RAW config INPUT, filling only fields the user left open from the ledger. (NOTE: primes the input, NOT the resolved config — see trap below.)
  - `describePriming(input)` — returns the audit string (e.g. `bestFor(near-dup sim=0.50 topic="...")`) or `null`.
  - `NEAR_DUP_SIMILARITY = 0.5` — similarity at/above this ⇒ reuse the whole genome (`bestFor` near-dup); else consensus fill (`winningChoices`).
  - `ledgerPrimingEnabled()` — opt-out via env `AGENTIC_PRIME_LEDGER=0`.
- `src/agentic/management/autopilot.ts` (single guarded call site): `autoRunVideo` calls `primeInputFromLedger` on the raw input BEFORE `resolveConfig`, and emits an `L3 ledger prime: <source>` `AutoRunEvent` when priming fired (observable in the run report / `report.events`).
- `src/agentic/management/ledger-prime.test.ts` (NEW, **15/15 pass** with `render-ledger.test.ts`).

## KEY non-obvious technique — prime the INPUT, not the resolved config
First attempt primed the *resolved* `AgenticConfig` (`resolveConfig(...)` output). It silently did nothing: `resolveConfig` fills EVERY field with a hard default (`aspect ??= '9:16'`, `transition ??= 'fade'`, etc.), so there is never an "open gap" for the ledger to fill. **The correct integration point is the raw user input, before preset/default resolution** — ledger values then win over the preset (because `resolveConfig` layers preset/defaults UNDER the user input: `...preset, ...tpl, ...fmt, ...stripUndefined(input)`). Priming a resolved config is a silent no-op trap. This cost two debug cycles this session.

## Priming logic
1. `bestFor(topic)` → if `topicSimilarity >= 0.5` (near-dup), reuse the whole `choices` genome (orientation/aspect/paletteFilter/captionTheme/transition/hookScene/musicIntensity/voice/preset/videoType).
2. Else `winningChoices(topic)` → consensus (most-common winning value per field across high-scorers ≥ 0.75 score). Also the fallback when `bestFor` returns `null` (its internal threshold 0.34 is stricter than the 0.5 near-dup bar).
3. User-specified input fields ALWAYS win; ledger only fills `undefined` gaps.
4. Empty ledger ⇒ strict no-op (returns input unchanged). Every read/write is `try/catch` — a missing/corrupt ledger degrades to no-op, never breaks a render.

## Empirical proof the loop works (OFFLINE)
Drive `autoRunVideo` TWICE with similar topics, offline via local assets + bundled bgm (Edge-TTS falls back to Windows offline speech — voiceover still succeeds):
```ts
import { autoRunVideo } from '../src/agentic/management/autopilot.js';
import { ledgerStats } from '../src/agentic/management/render-ledger.js';
const base = { backend:'agent', localAssets:['brand_cover.jpg'], backgroundMusic:'ambient_piano.mp3', defaultVisual:'brand_cover.jpg', renderer:'ffmpeg' as const };
// clear ledger first so run1 is a true cold start
await autoRunVideo({ topic:'morning productivity tips', title:'Morning Productivity', ...base }, { renderer:'ffmpeg', learn:true, maxAttempts:2 });
const r2 = await autoRunVideo({ topic:'morning productivity hacks', title:'Morning Productivity Hacks', ...base }, { renderer:'ffmpeg', learn:true, maxAttempts:2 });
console.log(r2.events.some(e=>e.msg.includes('L3 ledger prime'))); // => true on run2
console.log(ledgerStats()); // => {total:2, passed:2, avgScore:1, topics:2}
```
Expected: run1 (empty ledger) ⇒ NO prime event, renders valid MP4, ledger total=1. run2 (similar) ⇒ emits `L3 ledger prime: bestFor(near-dup sim=0.50 topic="morning productivity tips")`, renders valid MP4, ledger total=2/passed=2. (Run in FOREGROUND — a backgrounded pipe printed `stdin is not a tty` and exited early before doing work.)
Local assets present: `input/visuals/brand_cover.jpg` + `input/bgm/__bundled__/ambient_piano.mp3`.

## Edit + verify recipe (proves "make / edit / verify" end-to-end)
Edit a rendered MP4 with the bundled editor (ffmpeg-static backed, `src/adapters/cli/agentic-editor.ts`):
```bash
node --import tsx src/adapters/cli/agentic-editor.ts trim --input output/<job>/<job>.mp4 --start 00:00 --end 00:12 --output workspace/tmp/edited/trimmed.mp4
node --import tsx src/adapters/cli/agentic-editor.ts overlay-text --input workspace/tmp/edited/trimmed.mp4 --text "AVS Demo | @itsPremkumar" --color white --output workspace/tmp/edited/branded.mp4
node --import tsx src/adapters/cli/agentic-editor.ts adjust --input workspace/tmp/edited/branded.mp4 --brightness 0.05 --contrast 1.1 --output workspace/tmp/edited/final_edited.mp4
```
Verify with frames (ALWAYS post-seek, `-ss` AFTER `-i` — see the frame-extract-seek rule):
```bash
node -e "const f=require('ffmpeg-static'),cp=require('child_process');for(const t of [2,6,11]) cp.execFileSync(f,['-ss',String(t),'-i','workspace/tmp/edited/final_edited.mp4','-frames:v','1','-q:v','2',`workspace/tmp/frames/edit_${t}s.png`,'-y'],{stdio:'pipe'});"
```
Then `vision_analyze` each frame with a **literal `C:/one/...` Windows path** (NOT `/c/one/` — the tool mangles MSYS paths to backslash and 404s; documented gotcha). Confirm 9:16 orientation, readable burned caption, and the branding overlay text present.

## Caveats
- `npm run typecheck` may report `src/agentic/orchestrator/render.ts(356,11): error TS2453/TS2451: Cannot redeclare block-scoped variable 'dims'`. This is a **PRE-EXISTING uncommitted WIP change in render.ts** (`git diff` shows ~34 insertions, NOT from the L3 work). It blocks the full `tsc` build but NOT tsx runtime (per-file transpile). Don't chase it as your regression. Verify L3 with `tsx --test` + the driver above, not `npm run typecheck`.
- The normal `npm run generate` / `cli-runner` path bypasses the autopilot, so it never records to the ledger. To exercise learning, drive renders through `autoRunVideo(..., { learn:true })` (or `autoRunBatch`).
