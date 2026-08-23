# Opt-in AI verification reusing the agent's OWN model (null-fallback pattern)

Pattern proven in `itsPremkumar/Automated-Video-Generator` (agentic pipeline).
Captured 2026-07-17, hardened same session.

## When to use
User wants AI to verify assets/output (images, video, audio) at any pipeline stage,
but the build must stay ZERO-COST and NO-PAID-KEY. Do NOT add a separate
`visionApiKey` / Gemini / OpenRouter paid path. Reuse the model the agent is
already running on (e.g. `AgentBrain`).

## Hard rules
- **Opt-in only.** Master flag default `false`. When off: zero behavior change,
  zero network, zero cost. Each stage also has its own flag.
- **Null-fallback contract.** Every AI check returns `null` when the model is
  unavailable / offline / rate-limited / not multimodal. Callers MUST fall back
  to existing deterministic signal checks and NEVER block on the model.
- **Augment, never replace.** AI score is AND-ed with signal gates. A `null`
  result lets signal gates decide. AI can reject an asset (e.g. wrong subject =
  "lino vs forest") but cannot un-reject a passing signal check.
- **Reuse the running brain.** Extend the agent's brain with key-free methods
  (vision via the model's own image input if multimodal; audio judged by the
  TEXT model on an available transcript — no audio-decode cost). Never require
  `openRouterKey` for vision; allow a local Ollama vision model too.

## Implementation shape (TS)
```ts
// ai-verify.ts
export async function aiVerifyAsset(
  file, kind: 'image'|'video'|'audio', expectation: string[],
  cfg, brain, transcript?
): Promise<{pass:boolean;confidence:number;reason:string} | null> {
  const av = cfg.aiVerify;
  if (!av?.enabled) return null;
  if (!brain.modelEnabled) return null;          // no model -> signal gates decide
  if (kind === 'image' || kind === 'video') {
    const v = await brain.visionVerify(file, expectation); // null if not multimodal
    if (!v) return null;
    return { pass: v.passes && v.confidence >= (av.minConfidence ?? 6), ...v };
  }
  // audio: judged by TEXT model on transcript; null if no transcript
  if (!transcript) return null;
  return brain.completeJSON?.(system, prompt, schema); // null on failure
}
```

## Wiring (4 opt-in stages)
- **acquire**: after materialising a candidate, call aiVerifyAsset; non-null fail
  -> drop candidate, next source in ladder tried. Pass `cfg`+`brain` via deps.
- **approve**: rides acquire-time check (or a distinct decide-stage gate).
- **edit**: on scene edit with a localAsset file present, score it, record
  verdict on the scene (non-blocking, fire-and-forget `.then().catch()`).
- **render (final)**: extract 1 frame, score as video -> gate X16. Off unless
  `verifyOnRender`. Clean up the temp frame dir.

### PITFALL — X16 silently absent if the extracted frame doesn't exist
The render-stage check extracts one frame with
`ffmpeg -ss 00:00:01 -i mp4 -frames:v 1 frame.jpg` then branches on
`if (fs.existsSync(frame))`. On a video **<=1s long**, `-ss 1` seeks PAST EOF ->
ffmpeg writes **no frame** -> the `fs.existsSync` guard is false -> the `if` body
is skipped and **X16 is never pushed** (no error, no catch -- looks like the
check "vanished"). Real pipeline videos are 15-17s so it works there, but a
short probe/fixture video will make X16 silently absent and you'll waste time
debugging why the check isn't emitted. FIX: seek to a SAFE early timestamp
`00:00:00.5` (always valid), not `00:00:01`. Also: when wiring X16 into
`verifyRenderedVideo`, the new `opts` param must be threaded from the render
caller (`renderAgenticSlideshow`/`renderAgenticWithRemotion` in orchestrate,
`autopilot.ts` passing `cfg.aiVerify`) -- forgetting to pass `opts.brain` means
the `if (opts?.aiVerify?.verifyOnRender && opts?.brain)` guard is false and X16
never runs even on long videos. PROVEN this session: a 1s test video showed
X16 missing; switching to `00:00:00.5` + confirming `opts.brain` threaded made
X16 appear in the gate report.

### PITFALL — tsconfig blind spot hides plugin/render type errors (breaks CI lint)
If `tsconfig.json` `include` is a hand-picked subset (e.g. only `src/agentic`
top-level, excluding `plugins/`, `services/`, `mcp-server/`, `adapters/`), then
`tsc` passes while ESLint's `parserOptions.project` CANNOT resolve the excluded
files -> **CI lint job is RED with parse errors** and **real type errors in
excluded files stay hidden** (e.g. 8 errors in `advanced-transitions.ts`). When
you widen `include` to `src/**` + `remotion/**`, tsc will surface those hidden
errors -- fix them by aligning to the core contract (remove fields the type
lacks, map scene ids correctly, add required `metadata` to filter objects,
type `any`-leak params as `string`). After the widen, re-run `npx eslint src/`
(which was 87 errors -> 0 after the widen + `--fix`). This is the #1 CI-green
fix for this repo. See `remotion-ffmpeg-video` skill `references/ci-typecheck-blindspot.md`.

### RESPONSE DISCIPLINE — stale `[System: unverified]` flag
The verification-gate flag fires on a SNAPSHOT taken mid-turn; it will re-prompt
on files that were ALREADY committed or DELETED (e.g. temp probe scripts removed
with `rm -f` before commit, or a file pushed in the same turn). When it flags
paths you already committed/cleaned: re-run `tsc --noEmit` + `eslint` + the test
suite, show `git status` is CLEAN (or the temp files are GONE), and state the
flag is stale. Do NOT re-edit already-committed code to satisfy a stale flag.
Temp diagnostic scripts (`*.cjs`, `probe*.ts`) you created ARE deletable and
should be removed before commit (Coding guideline). This session confirmed the
flag fired 3x on deleted/committed paths; each time the gates re-passed green and
git status was clean.

## resolveConfig defaults
When `enabled:true` but sub-flags unset, default checkSubjectMatch/watermark/
safety = true, audio checks = false. All stage flags default to the master toggle.

## Test contract (CI stays green, no network)
Mock `AgentBrain` with canned `visionVerify`/`completeJSON`. Assert:
- disabled OR no-model -> null
- vision pass (>= minConf) -> accepted; fail -> rejected
- audio + transcript -> judged; audio + no transcript -> null
- real calls use `npx tsx --test` with node:test (NOT bun:test under tsx).

## Anti-patterns avoided
- Rejecting an AI-verification plan that hard-codes `visionApiKey`/Gemini:
  violates the user's zero-cost rule. A pasted "AI verification plan" doc
  suggested exactly this (paid `visionApiKey`, `gemini`/`openrouter` defaults)
  -- it was correctly rejected; the zero-cost, agent-own-model design was
  built instead.
- AI overriding signal gates: the 9 deterministic gates (X7-X15: size, duration,
  audio, black, freeze, loudness, clip, dims, codec) are CORRECT and proven; AI
  only adds subject-relevance (the one gap signal checks cannot catch).
- Leaving code edits uncommitted: commit + push after tsc=0 + suite green.
