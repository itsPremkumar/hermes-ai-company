# blackdetect loglevel + guard clause fix (2026-08-17)

## Root cause
`detectBlackFrames()` in `src/agentic/media/video-analyzer.ts` always returned empty
because `mppegArgs()` used `-v error` loglevel. The `blackdetect` filter emits its
detection lines (`black_start`/`black_end`/`black_duration`) at the `info` log level.
At `-v error` those lines are suppressed entirely, so the parser never sees any
detections — even on a genuinely black clip.

A secondary guard clause (`start < 0.5 && end > totalDur * 0.95`) was filtering
TRUE POSITIVES — it dropped whole-clip black detections, including a genuinely
black test clip (23.1s black in 23.17s total). The guard was designed to filter
false positives that only occurred at `-v error`, but at `-v info` testsrc produces
zero false positives, so the guard did more harm than good.

## Fix
1. Changed `mppegArgs()` from `-v error` → `-v info`
2. Removed the over-aggressive guard clause entirely

## Verification
- testsrc (moving test pattern): 0 false positives at `-v info` ✅
- Genuinely black clip: correctly detected (23.1s black) ✅
- 24 variety videos: 0 black frames, 0 freeze frames, all pass QA ✅

## Gotcha for future sessions
When debugging ffmpeg filter output that "should be there but isn't":
- Run the filter at `-v info` or `-v debug` to confirm the filter actually emits
- A filter running at `-v error` may produce data that is silently suppressed
- This applies to ANY ffmpeg filter that emits analysis at verbose (not error) level
- Sibling: `volumedetect` also needs `-v verbose` on gyan.dev ffmpeg (see G16 in avs-pipeline-verification)

## Related
- `src/agentic/media/video-analyzer.ts:104-113` (mppegArgs)
- `src/agentic/media/video-analyzer.ts:119-146` (detectBlackFrames)
- `tests/agentic/media/video-analyzer.test.ts` (10 tests, all pass)
- `tests/agentic/media/video-analyzer-blackguard.test.ts` (2 tests, all pass)
