# Offline caption word-timing (syllable heuristic)

Zero-dependency offline fallback for word-paced captions when no word-level
timings exist (non-Edge engine, personalAudio, or tone fallback in tts.ts).

## Why
Edge-TTS returns word boundaries; other paths (tone fallback, custom audio)
land in `fillMissing` / the real-engine no-boundary branch with a single
sentence-length caption block - burned captions then appear all-at-once instead
of word-by-word. No network / no native binary (whisper.cpp) should be required.

## The heuristic (`syllableWordTimings(text, durationMs)` in src/lib/captions.ts)
- Split text into words; estimate per-word ms by syllable count
  (~180 ms/syllable, min 120 ms), distribute across `durationMs` with small gaps.
- Produces N caption segments (one per word/short phrase) with startMs/endMs,
  so the burn-in renders word-by-word.
- Deterministic, fast, no model. True forced-aligner (whisper.cpp / VibeVoice-ASR)
  gives ground-truth boundaries but needs a native binary - noted as optional
  upgrade, not blocking.

## Where it's wired
- `tts.ts fillMissing` (tone fallback) and the real-engine no-boundary branch
  both call `syllableWordTimings` instead of one giant `CaptionSegment`.
- Imported from `../lib/captions.js`.

## Test
`src/lib/captions.test.ts` asserts: segments cover full text, last endMs <= duration,
no overlap, empty text -> [].
