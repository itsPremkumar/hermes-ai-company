# AVG Hardening — Claim Verification & Fail-Closed Pattern

Reusable detail for hardening `itsPremkumar/Automated-Video-Generator` (AVG),
and any AI-dependent content pipeline. Companion to `avg-production-sweeps.md`
and `avg-ai-verify-async.md` under `remotion-ffmpeg-video`.

## 1. Verify every handed-over audit claim (do not trust another AI's list)

A second-AI review of AVG listed ~20 items. Verified each against the code;
several were FALSE. Pattern: `grep`/`read` the cited file+line, confirm the
issue exists, THEN act. False claims that were correctly cancelled/skipped:

| Claim | Reality | Action |
|---|---|---|
| "504 TODO/FIXME debt markers" | `grep -rnE "TODO\|FIXME" src/` -> 0 hits | Cancelled (no fabrication) |
| "Unreachable branch at orchestrate.ts:613" | Legit retry-loop fallback | Skipped |
| "X1-X6 gate IDs retired" (AGENTS.md) | `gate.ts` still has X1-X6 (pre-render holistic gate) | Fixed the DOC, not code |
| "~20 magic env vars" | Actually 81 (`grep -rhoE process.env.[A-Z_]+`) | Documented all categories |
| "diversityPenalty reserved-but-unused" | In `ScoredCandidate` interface + returned | Skipped (shape break) |
| "plugins/ dir exists" (prior issue) | Did not exist | Rejected earlier |
| "no agentic tests" (prior claim) | Integration + ops tests existed | Rejected earlier |

Disposition: TRUE+valuable -> fix with tests; TRUE+risky -> safe slice only,
defer rest; FALSE -> cancel with reason. Never fake a fix.

## 2. Fail-closed AI verification (core reusable technique)

AI-dependent gates (vision subject match, watermark, safety) must FAIL CLOSED.
Old (broken) pattern: AI unavailable -> `passes:true, confidence:5` (silent pass
-> off-topic/unsafe assets ship when Ollama/Gemini is down).

Fixed pattern in `src/lib/media-verifier.ts`:

```ts
// default failClosed = true
export interface VisionCheckOptions { failClosed?: boolean; /* ... */ }

function unavailableResult(reason: string, opts: VisionCheckOptions): VerificationResult {
    if (opts.failClosed) {
        return { passes: false, confidence: 0, reason: `[FAIL-CLOSED] ${reason}` };
    }
    return { passes: true, confidence: 5, reason }; // best-effort only
}

// final-render gate: sample N frames, fail if ANY fails
export async function verifyFinalRender(
    filePath: string, keywords: string[], opts: VisionCheckOptions = {},
): Promise<VerificationResult> {
    const frames = await extractVideoFrames(filePath, opts.sampleFrames ?? 3);
    for (const f of frames) {
        const r = await verifyMedia(f, keywords, opts);
        if (!r.passes) return r; // fail on first bad frame
    }
    return { passes: true, confidence: opts.minConfidence ?? 6, reason: 'ok' };
}
```

Wire into the post-render gate (`gate.ts` X16): when `aiVerify.finalMode ===
'vision'`, call `verifyFinalRender` instead of single-frame. Add `failClosed:
true`. Tests assert the contract (unavailable -> `passes:false`, non-fail-closed
-> neutral pass).

## 3. Single ffmpeg runner consolidation (H2)

6+ divergent ffmpeg callers (`spawn('ffmpeg')` relying on PATH, `execFileSync`
with resolved binary, inconsistent timeouts). Created `src/lib/ffmpeg.ts`:
`ffmpegPath()` (cached resolve of `ffmpeg-static`), `runFfmpeg(args, {timeoutMs,
captureStdout})` (async, SIGKILL-on-stall, throws `FfmpegError`),
`runFfmpegSync`, `ffmpegCanRun()` (real probe). Migrate callers to it; the
`spawn('ffmpeg')` (PATH) variant in `media-verifier.ts` was a latent bug -
fixed to resolved binary. Atomic cache write: write temp + `renameSync` to
avoid corrupt `.video-cache.json` on crash; cap entries (FIFO eviction).

## 4. Bounded-wave execution log (what "complete the full list" looked like)

17 items DONE (verified: typecheck 0 / lint 0 / 366-367 tests / CI green),
4 honestly CANCELLED (L2 any-in-dispatch, L4 sub-project drift, L5 TODO debt,
L7 optional Swagger) with reasons. Committed per wave on feature branches,
merged to main, pushed, CI confirmed. No fake fixes.
