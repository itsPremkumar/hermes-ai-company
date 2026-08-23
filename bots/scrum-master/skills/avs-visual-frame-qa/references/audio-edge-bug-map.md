# AVS Audio-Edge + Robustness bug map (2026-07-28)

Scope: audio-less sources, very-short/very-long scenes, inline audio tags,
portrait-into-landscape. Harness: `workspace/bug-hunt/harness.mjs`
(plan → voice → visuals --no-acquire → render). Probes: ffprobe-static,
`ffmpeg -af volumedetect`, vision grid.

## Confirmed REAL bugs

### BUG D1 — `[Volume: N]` inline tag parsed but never attached to scene (HIGH)
- `src/lib/script-parser.ts`: `volumeOverride` (and `voiceOverride`,
  `musicOverride`) are computed into locals (~lines 248/250/252) but the final
  `scenes.push({...})` (~lines 386–414) OMITS `volumeOverride`. So
  `plan.ts:64` (`volumeOverride: s.volumeOverride ? parseFloat(...) : undefined`)
  always gets undefined, and the correct `volFilter` at `render.ts:~803` never
  fires.
- Repro: `parseScript("...[Volume: 0.5]...").scenes[i].volumeOverride === undefined`.
- Expected: per-scene 0.5× gain; volumedetect shows scene NOT quieter.
- NOTE: `fadeIn`/`fadeOut` ARE pushed and DO work — only volume/voice/music
  overrides are dropped at the push. Grep the push object for every parsed local
  to find similar drops.

### BUG C1 — long single scene voiceover truncated by an 8s cap (HIGH)
- `src/agentic/pipeline/plan.ts:222`:
  `s.durationSec = Math.max(minDur, Math.min(Math.round(wordDur), 8));` hard 8s
  ceiling. Also the parser has NO `[Duration: N]` inline tag (`duration` is
  `Math.max(3, Math.ceil(cleanText.length/15))`, then re-capped in plan).
- Repro: a ~60-word/25s-intended single scene renders ~7.9s; voice cut off.
- Expected: long scene drives a ~full-length voiceover, music loops to fill,
  audio≈video within 0.5s.

### BUG C2 — container `format.duration` disagrees with stream durations (MEDIUM)
- For the long-scene render: video stream 7.90s, audio stream 7.94s, but
  `format.duration` = 33.55s (≈ intended un-truncated length). Likely the `-t`
  / music-loop / concat mux in `render.ts` writes a container duration decoupled
  from actual stream content.
- Impact: a naive `ffprobe -show_format` duration gate (audio-vs-video <0.5s)
  FALSE-fails or misleads. Always compare STREAM durations
  (`-show_entries stream=duration`), not just `format.duration`.

## Verified WORKING (regression baselines)
- Audio-less (`-an`) source clips: silent-source guard + `anullsrc` fallback in
  `render.ts` (~line 796) produce a correct mixed voice+music track, no crash.
  volumedetect mean ≈ -26 dB.
- Short 6-scene job with fade/slide/wipe transitions: `blackdetect` = 0 gaps;
  `offsetFor`/xfade `offset=Math.max(0, cursor-xf)` (render.ts:64,556) keeps
  offsets ≥ 0.
- FadeIn/FadeOut envelope: proven with per-window volumedetect —
  FadeIn scene start -33.9 dB → +8 dB after 1s; FadeOut tail drops -24 → -34 dB.
  Parser → `plan.fadeIn/fadeOut` → `render.ts:~797` afade filters correct.
- Portrait (720x1280) source in landscape (1280x720) job: pillarboxed with
  correct aspect, NO distortion (`force_original_aspect_ratio=decrease,pad`,
  render.ts:~824). Confirmed by vision grid.

## Probe recipes that worked
- Per-window envelope: `ffmpeg -ss <t> -t <win> -i out.mp4 -af volumedetect -f null -`
  then grep `mean_volume`/`max_volume`. Sample start / +1s / mid / tail to prove
  fade curves objectively (do NOT trust vision for audio envelope).
- Black-gap check: `ffmpeg -i out.mp4 -vf blackdetect=d=0.05:pic_th=0.98 -an -f null -`
  count `black_start`.
- Duration truth: `ffprobe -show_entries stream=codec_type,duration` (per stream)
  AND `format=duration` — mismatch is itself a signal (see C2).
- Isolated parser probe: `await import('../../src/lib/script-parser.ts')` under
  `npx tsx` (exported `parseScript` is async; import the `.ts` path, not `.js`).
