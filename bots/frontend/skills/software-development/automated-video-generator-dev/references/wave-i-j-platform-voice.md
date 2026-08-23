# Wave I–J: `platform`→aspect + `job.voice` default consistency

Condensed learnings from the "find the next ignored control signal" campaign
(2026-07-24). Pair with the SKILL.md "Bug: `platform`…" and "Wave J: `job.voice`…"
sections; this file holds the *mechanics* a future session edits.

## Wave I — `platform` was an AI-only hint, never rendered
- `AgenticCliJob.platform` (`tiktok|youtube|instagram|reels`) was consumed by
  `style-engine.ts` but `compose.ts` ignored it.
- Fix: extracted **`resolveOutputSize(job)`** (pure, exported, module-level in
  `compose.ts`) → unit-tested without the full pipeline. Mapping:
  `tiktok`/`reels`→9:16, `instagram`→1:1, `youtube`→16:9.
- **Test:** `src/agentic/operations/compose-output-size.test.ts` (12 cases).
- **Precedence gotcha (first impl was buggy):** when layering a NEW default
  source onto an existing precedence chain, the new source must NOT override
  an explicit value from an earlier source. The buggy form:
  `asp = job.aspect ?? (job.platform ? MAP[job.platform] : undefined)` let
  `platform` override an explicit `orientation` (test `youtube + portrait →
  720×1280` FAILED, got 1280×720). Correct form:
  `asp = job.aspect ?? (job.orientation ? undefined : (job.platform ? MAP[job.platform] : undefined))`
  — the new source only fills in when BOTH earlier sources are absent.
- **Refactor pitfall:** the first `resolveOutputSize` attempt was placed
  *inside* `composeVideo` as `export function` — illegal; left a missing
  closing brace. A function must go at module level. After refactoring
  `composeVideo`, grep for an `export function` accidentally nested in it.

## Wave J — `job.voice` default was overridden downstream (the real root)
- Symptom: a job with no `voice` died on `en-US-GuyNeural` timeout; even
  setting `voice:'en-US-JennyNeural'` didn't help.
- Naive fix `single-feature.ts:87` (`?? 'en-US-JennyNeural'`) was necessary
  but INSUFFICIENT — the log still showed Guy.
- **Real root:** `runCompose` calls `buildVoiceConfigs({baseVoice: job.voice})`
  then `applyVoiceConfigsToPlan(plan, cfgs)`, which **overwrites `plan.voice`**
  with `cfgs[].voice`. `buildVoiceConfigs` (`voice-intel.ts:59`) hardcoded
  `const base = opts.baseVoice ?? 'en-US-GuyNeural'` → with `job.voice` unset,
  base = Guy, clobbering the Jenny `plan.voice`.
- **Fix:** `voice-intel.ts:59` base → `'en-US-JennyNeural'`. BOTH
  `single-feature.ts:87` and `voice-intel.ts:59` must agree on Jenny.
- **Test:** `src/agentic/pipeline/plan-voice.test.ts` (4 cases: buildPlan
  default/override + buildVoiceConfigs default/override).
- **General rule:** when a hardcoded default "leaks" a failing value, trace
  the full propagation (`buildPlan` → `buildVoiceConfigs` →
  `applyVoiceConfigsToPlan`) to find which assignment WINS. An early default
  can be clobbered by a later `applyXxxConfigsToPlan`. The TTS *timeout* is
  environmental; the *two-disagreeing-defaults* is the durable bug.

## Reusable commit-message pattern for these waves
```
feat(compose): platform drives output aspect (was AI-only hint, never rendered)
fix(voice): root cause — voice-intel defaulted base to en-US-GuyNeural
```
Lead with the USER-VISIBLE behavior change, then the root cause. Reference the
real render proof (e.g. `waveI_tiktok_portrait` → 720×1280) + the new test file.
