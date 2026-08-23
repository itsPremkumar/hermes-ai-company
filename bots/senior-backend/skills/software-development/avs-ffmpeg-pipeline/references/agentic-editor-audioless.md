# agentic-editor.ts audio-less guard — empirical test pattern (BUG E2)

The CLI single-task editor (`src/adapters/cli/agentic-editor.ts`) builds
filtergraphs with unconditional `[0:a]`/`[1:a]` references, which crash
("matches no streams") on audio-less inputs (AVS visuals are often audio-less).
The fix (pitfall #50) probes each input via `getMediaInfo(...).streams` and
drops the audio branch when absent.

## Reusable probe idiom

```ts
const hasAudio = Array.isArray(getMediaInfo(input)?.streams)
  && getMediaInfo(input).streams.some((s: any) => s.codec_type === 'audio');
const fc = hasAudio
  ? `[0:v]loop=loop=${n - 1}:size=32767[v];[0:a]aloop=loop=${n - 1}:size=32767[a]`
  : `[0:v]loop=loop=${n - 1}:size=32767[v]`;
// -map the audio label only when present; else '-an'
```

For two-input commands (`transition`, `duck`) probe BOTH; build the audio
filter only when both have audio, else carry the single available track
(`0:a`/`1:a`) or none (`-an`). `duck` falls back to a passthrough of whichever
track exists.

## Testability hook

`agentic-editor.ts` runs `main()` at import time; `main()` safely lists
commands and returns when no subcommand is given, so importing the module in a
test is safe. Export the handler map so tests drive the REAL code:

```ts
export { COMMANDS };
```

## Empirical test (agentic-editor-audioless.test.ts — 5/5 passing)

Pattern: spin up a `fs.mkdtempSync` dir, generate an audio-less video with
`ffmpeg -f lavfi -i color=c=blue:s=320x180:d=3:r=25 -c:v libx264 -pix_fmt yuv420p`
(no `-i` audio → audio-less), then call `COMMANDS['loop']({input, n:'2', output})`
etc. Assert `fs.existsSync(out) && size > 1000`. Real-audio control: generate a
second clip with `-i tone.wav` (sine) + aac so the crossfade path is exercised.

Cases:
1. `loop` on audio-less → valid output (no `[0:a]aloop` crash)
2. `reverse` on audio-less → valid output
3. `transition` between two audio-less clips → valid output (no acrossfade crash)
4. `duck` with audio-less voice (music only) → valid output (no `[1:a]` crash)
5. `transition` between REAL-audio clips → valid output (crossfade path still works)

## Living-proof script (gen-e2-proof.ts, repo root)

Import `COMMANDS`, strip `input/visuals/a.mp4` to an audio-less clone
(`-c:v copy -an`), then run `loop` (n=3), `reverse`, and `transition` (a-noaudio
+ b.mp4 which has audio = mixed case). Produces `output/variety/e2_loop.mp4`,
`e2_reverse.mp4`, `e2_transition.mp4`. Probe a frame (`ffmpeg -ss 2 -frames:v 1`)
and `vision_analyze` to confirm it's a valid non-corrupt frame. The scratch
script is NEVER committed (delete `workspace/tmp/gen-e2-proof.ts` after).

## Gotchas
- Module resolution: a test/scripts file in `workspace/tmp/` fails
  `require('ffmpeg-static')`/import resolution oddly; copy it to the REPO ROOT
  (where `node_modules` resolves) before `npx tsx`, or use absolute import paths.
- `main()` on import reads `process.argv`; running `npx tsx <script>` gives argv
  `node tsx <script>` → no subcommand → `main()` returns safely. Good.
- After edits, re-run the test AND `tsc --noEmit` on the one changed file (scoped
  typecheck) to confirm no `error TS`.
