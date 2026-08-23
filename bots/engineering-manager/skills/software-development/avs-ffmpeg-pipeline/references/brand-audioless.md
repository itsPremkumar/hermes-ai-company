# brand.ts applyBrandKit — empirical bug-hunt recipe

Verified 2026-07-28. `src/agentic/operations/brand.ts` `applyBrandKit` had four
defects (B1/B2/B3 + a latent color bug) closed in one commit (`audit/brand-bugs`).
This file is the repro + test recipe so a future session can re-verify without
re-deriving the filtergraph traps.

## The four defects (all in `applyBrandKit`)

- **B1 ordering:** `segments = [...cards, file]` (intro + outro collected into
  one `cards` array, prepended) → concat order `outro → main` (outro FIRST).
  Fix: `segments = [...introCards, file, ...outroCards]`.
- **B2 audio drop:** `concat=n=K:v=1:a=0[outv]` + `-map [outv]` discards source
  audio. AND the audio map was `-map [${mainIdx}:a]` — ffmpeg reads `[1:a]`
  (brackets) as a **filtergraph label**, not input stream #1's audio → "Output
  with label '1:a' does not exist". Fix: `-map ${mainIdx}:a` (NO brackets) +
  `-c:a aac` when `hasAudio`, else `-an`. (Pitfall #59.)
- **B3 temp leak:** the `_brand_*` temp card dir was created and never removed.
  Fix: `try { … } finally { fs.rmSync(tmpDir, {recursive:true, force:true}); }`.
- **Latent color bug:** `rgbExpr` returned `r:g:b` (`31:111:235`); ffmpeg
  `drawbox`/`color` need `0xRRGGBB` → "Invalid 0xRRGGBB[AA] color string: 31".
  Fix: `return '0x' + (6-digit hex)`. (Same family as pitfall #17.)

## Filtergraph traps hit (so you don't repeat them)

1. **Concat must CHAIN labels:** `[v0];[v1];[v2]concat=n=3:v=1:a=0[outv]` is WRONG
   — the `;` separates independent graphs, so only `[v0]` is used and segments
   1,2 are dropped (output = only segment 0, and the main clip's audio input is
   orphaned). Correct: `[v0][v1][v2]concat=n=3:v=1:a=0[outv]` (all labels listed
   together before `concat`). Single segment: rename `[v0]`→`[outv]`. (Pitfall #60.)
2. **`xfade duration=0,offset=0` collapses duration** between clips of different
   lengths (it overlaps the WHOLE prior clip), producing a too-short output.
   Prefer the `concat` *filter* for gapless joins of arbitrary-length clips.
3. **`-map [N:a]` (brackets) ≠ input stream.** Use `-map N:a` (no brackets) to
   reference input file N's audio; brackets mean a filtergraph output label.

## Empirical test recipe (`brand-audioless.test.ts`, 5/5)

The test drives the REAL `applyBrandKit` with an injectable `runner` that ALSO
carries a controllable `probe` (so `hasAudio` is testable without a real
ffmpeg probe path):

```ts
import { applyBrandKit } from './brand.js';
import { runFfmpeg } from './edit.js';

function runnerWithProbe(hasAudio: boolean): any {
  const fn = ((a: string[]) => runFfmpeg(a)) as any;
  fn.probe = async (_file: string) => ({ duration: 0, width: 1280, height: 720, hasAudio });
  return fn;
}
```

Make fixtures under `os.tmpdir()` with `ffmpeg-static` (lavfi `color`/`sine`),
never network:
- audio-bearing source: `ffmpeg -i input/visuals/a.mp4 -i tone.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 out.mp4`
- audio-less source: strip with `-an`.

Assertions that actually catch the bugs (NOT `ok===true` alone — a bool-only
check passes even when ffmpeg crashed because `finalize` swallows the error):
- **B1 ordering:** probe output DURATION ≈ intro+main+outro (1+2+1 = ~4s) AND
  extract a start frame (`-i out -ss 0.3`) → vision confirms "INTRO CARD", and
  an end frame (`-i out -ss dur-0.3`) → "OUTRO CARD".
- **B2 audio kept:** `ffprobe -show_entries stream=codec_type` on the output MUST
  include `audio` when the source had audio.
- **B2-negative (audio-less no-crash):** source `-an` → output has NO `audio`
  stream and `ok===true` (proves the `-map N:a` / `-an` branch works).
- **B3 temp leak:** snapshot `output/_brand_*` dirs before/after → count unchanged.
- **unit:** `buildBrandFilter({name:'X'})` returns a string (no throw).

## Vision confirmation used this session
- start frame: white "INTRO CARD" on solid blue (card color) — proves intro first.
- end frame: white "OUTRO CARD" — proves outro last.
- output `ffprobe`: `video,audio`, duration 5.08s, ~1 MB.

This is the canonical "real-ffmpeg + stream/duration probe + vision" pattern —
a boolean-only or stubbed-fmpeg unit test would have MISSED all four bugs.
