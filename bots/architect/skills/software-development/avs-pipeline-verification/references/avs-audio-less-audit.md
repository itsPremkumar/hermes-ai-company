# AVS audio-less `[N:a]` + concat audit (recurring ffmpeg bug class)

## The bug class
AVS's ffmpeg `filter_complex` graphs frequently reference an audio stream
unconditionally (`[0:a]`, `[1:a]`, `[2:a]`). When the actual input has **no
audio track**, ffmpeg aborts with:

```
Stream specifier ':a' matches no streams
```

This is the single most common *silent/late* crash in the editing + render
paths. It is invisible to `tsc` and to the `node:test` unit suite — only a
REAL ffmpeg run (or an `ffprobe` probe) catches it. The same is true for the
related `voiceovers.scenes[idx]` indexing crash (A3) and the concat
label-ordering crash (G12).

## Where it lived (fixed + verified 2026-07-28 audit)
| Module | Site | Fix |
|--------|------|-----|
| `src/agentic/operations/edit.ts` | `changeSpeed`, `addAudio`, `silenceRemove` | probe `hasAudioStream(file)`; skip audio branch when absent |
| `src/agentic/operations/edit.ts` | `mergeVideos` | concat input labels MUST be interleaved per segment: `[v0][0:a][v1][1:a]` (NOT `[v0][v1][0:a][1:a]`) |
| `src/adapters/cli/agentic-editor.ts` | `speed` | `getMediaInfo()` → skip `[0:a]` branch when no audio |
| `src/agentic/operations/silence.ts` | `removeSilence` | probe `hasAudio`; drop `[a]` filter branch when absent |
| `src/agentic/orchestrator/render.ts` | non-segmented pass2 music-mux | probe `silent` for audio; when absent mux music ALONE (no `[0:a]`) |
| `src/agentic/orchestrator/render.ts` | `sceneVoicePath` (A3) | `voiceovers` may be slim `{voiceoverDriven,sceneCount,fallbackUsed}` with NO `scenes[]` → guard indexing |

## G12 — concat label ordering = "Media type mismatch" crash
A `concat=n=K:v=1:a=1` filter needs inputs **interleaved per segment**:
`[v0][0:a][v1][1:a]` — NOT all-videos-then-all-audios `[v0][v1][0:a][1:a]`.
The latter fails with:
```
[AVFilterGraph] Error linking filters
[Parsed_setsar_N] Media type mismatch between the '...' filter output pad 0 (video)
and the 'Parsed_concat_M' filter input pad 1 (audio)
```
This shipped past `tsc --noEmit` AND a boolean-only unit test
(`edit-regression.test.ts` asserted `merge.ok===true` without running ffmpeg)
— only caught when a new test generated two clips, concatenated, and asserted
via `ffprobe` the output was a valid, non-empty mp4. FIX in `edit.ts`
`mergeVideos`: build the concat spec with
`files.map((_, i) => \`[v${i}][${i}:a]\`).join('')`.

## G10/G11 — music/voiceover hang: STATUS CLOSED (corrected 2026-07-28)
Earlier skill text called these "OPEN / NOT yet patched". They are actually
merged and verified:
- G10: `free-music.ts:289` routes the download through `withSignal` (hard-race
  timer in `music-system/providers/base.ts`). Regression: `with-signal.test.ts` (3/3).
- G11: `voice-generator.ts` calls `runPowerShellEncodedAsync` (the async
  tree-killing runner in `voice-engine.ts`, `taskkill /F /T /PID`). Regression:
  `voice-engine.async.test.ts` (2/2).
Re-run those two test files to confirm before touching the code. Do NOT re-fix.

## Audit recipe (re-run after any edit/render-path change)
1. `grep -rn "\[0:a\]\|\[1:a\]\|\[2:a\]" src/` — for each hit, confirm the
   referenced input is GUARANTEED to have audio, OR is guarded by an ffprobe probe.
2. `grep -rn "voiceovers?.scenes\[\|voiceovers\.scenes\[" src/` — any
   unguarded `.scenes[idx]` indexing on a possibly-slim shape is an A3 crash.
3. `grep -rn "concat=n=" src/` — for `a=1` concats, verify input labels are
   interleaved per segment, not all-videos-then-all-audios.
4. Write a `.test.ts` that builds a REAL audio-less clip and drives the
   function; assert it does NOT throw `matches no streams` and the output has
   the expected streams.

## Empirical test pattern (catches what tsc can't)
Generate a synthetic clip with the bundled ffmpeg-static — never touch the
network:
```ts
const ffmpeg = require('ffmpeg-static');
execFileSync(ffmpeg, ['-f','lavfi','-i','color=c=blue:s=640x360:d=3:r=25',
  '-an', '-c:v','libx264','-pix_fmt','yuv420p','-t','3','-y', file]);
```
Then assert `ffprobe` shows a `video` stream and (for audio-less) NO `audio`
stream. For a before/after proof, run the OLD graph (expect crash) then the
NEW guarded graph (expect valid output) in the same test. This is how the real
`mergeVideos` concat bug + the `[0:a]` crashes were caught (`edit.test.ts`,
`sibling-audio-guard.test.ts`).
