# `edit.ts` bug map (AVS video-edit toolbox) — fixed 2026-07-28

`src/agentic/operations/edit.ts` standalone edit primitives. Every bug below was reproduced by
running the actual function on a real ffmpeg-static clip and confirmed fixed by
`src/agentic/operations/edit-regression.test.ts` (10/10). Each op takes an optional `out` and
returns `{ ok, output, detail }` — NOTE the field is `detail`, NOT `error`.

## Bugs + fixes
| # | Function | Symptom | Root cause | Fix |
|---|----------|---------|-----------|-----|
| 1 | `trimVideo` | output 262 bytes, "Output file does not contain any stream", unplayable | `-ss`/`-to` AFTER `-i` WITH `-c copy` → stream copy can't re-align to non-keyframes, encodes nothing but exits 0 | re-encode `-c:v libx264`; validate duration via ffprobe |
| 2 | `splitVideo` | both parts 262 bytes, empty | same `-c copy` defect | re-encode both parts; validate both |
| 3 | `interpolateVideo` | always fails `Option not found` | filter `minterpolate=mode=blend` — `mode` isn't an option | `minterpolate=mi_mode=blend` |
| 4 | `changeSpeed` | `Stream specifier ':a' matches no streams` on audio-less clip | hard-codes `[0:a]atempo` in the filtergraph | detect audio via ffprobe (`hasAudioStream`); skip audio branch when absent |
| 5 | `changeSpeed` | `Value 0.250000 for parameter 'tempo' out of range` at 0.25x | `atempo` only accepts [0.5,100]; speed clamped to [0.05,10] | chain atempo factors (`0.5*0.5` for 0.25x) via `atempoFilter()` |
| 6 | `addAudio(mix)` | `Stream specifier ':a' matches no streams` when video has no audio | `amix` requires two audio inputs | if source has no audio, degenerate to replace-mode (`[1:a]volume…[outa]`) |
| 7 | `silenceRemove` | `ok=true "silence removed"` but output byte-identical on audio-less input | `-af silenceremove -c:v copy` → desync + no-op on no-audio | fail loud if no audio; re-encode; assert duration changed |
| 9 | `addProgressBar` | bar never fills on 8s clip (defaults totalSec=10) | `totalSec ?? 10` | probe real duration with `probeDurationSec` |
| 10 | `cropVideo` preset | `SAR 5120:5121` (not exact 9:16) | missing `setsar=1` after crop | append `,setsar=1` |
| 11 | `mergeVideos` | output has NO audio track | `concat=n=:v=1:a=0` always drops audio | keep audio when all inputs have it; INTERLEAVED concat order is `[v0][0:a][v1][1:a]` (NOT `[v0][v1][0:a][1:a]`) |

## Helpers added to edit.ts
- `probeDurationSec(file)` — ffprobe duration (null on fail).
- `hasAudioStream(file)` — ffprobe `select_streams a`.
- `atempoFilter(s)` — chained atempo for sub-0.5x / >100x.

## Reusable test pattern
The regression test self-seeds fixtures (no committed binaries): generates a 2s `testsrc2` clip
with ffmpeg-static, a with-audio variant (`-i clip -f lavfi -i sine -c:v copy -c:a aac`), and a
tone mp3. Each op asserts `ok===true` + `fs.statSync(output).size > 1000` + positive ffprobe
duration. Skip cleanly if ffmpeg-static is absent. Run:
`node --import tsx --test src/agentic/operations/edit-regression.test.ts`
