# AVG: Audio quality debugging (voiceover sounds unclear / noisy)

When the agentic pipeline produces a video where the voiceover narration is
muffled, unclear, or has audible compression artifacts — but the direct TTS
generation (e.g. Voicebox via `/speak`) sounds perfectly clear — the problem is
nearly always in the **ffmpeg render chain's audio encoding**.

## Root cause: default AAC bitrate in segment encoding

The segmented render path (`renderAgenticSlideshow` in
`src/agentic/orchestrator/render.ts`) renders each scene as a separate MP4
segment with ffmpeg. On line 603 the audio codec is specified as:

```typescript
'-c:a', 'aac', '-shortest', '-y', seg,
```

**Without an explicit `-b:a` flag**, ffmpeg's AAC encoder defaults to ~69 kbps
for a mono stream. At this bitrate, voiceover sounds muddy and compressed.

When no music/background audio is found (common with free-music providers), the
segments are concatenated verbatim (`-c copy`) — so the 69k AAC is baked into
the final video.

## Detection recipe

Use ffprobe (or ffmpeg -i) to compare bitrates at three stages:

```bash
# 1. Source WAV from TTS (Voicebox = 384 kbps PCM @ 24 kHz)
ffprobe workspace/jobs/<job>/audio/scene_1_voice.wav

# 2. Individual segment audio
ffprobe workspace/jobs/<job>/render/_seg_<job>_0.mp4

# 3. Final output video audio
ffprobe output/<job>/<job>.mp4
```

If the source is ~384 kbps PCM but the segment / output is ~69 kbps AAC, the
missing `-b:a` flag is the root cause.

## Fix

Add `-b:a 192k` (or higher, e.g. `256k`) to every ffmpeg command line that
encodes AAC audio:

### 1. Segment encoding (line ~603 in render.ts)
```typescript
'-c:a', 'aac', '-b:a', '192k', '-shortest', '-y', seg,
```

### 2. Non-segmented single-pass path (line ~634)
```typescript
...(audioMap.length ? ['-c:a', 'aac', '-b:a', '192k'] : ['-an']),
```

### 3. Music + SFX final pass (line ~667)
```typescript
'-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-y', out,
```

After the fix, segments show ~160-170 kbps AAC and the final output reaches
~167 kbps — a clear improvement from 69 kbps.

## Why this happens only sometimes

- **Music present**: the second pass (lines 651-669) re-encodes the final mix
  with explicit `-b:a 128k` (or `192k` after fix). If music IS found, the
  69k segments get re-encoded and quality improves.
- **No music found**: the `silent` concatenated segments are renamed to the
  output verbatim (line 672-674). The 69k segments become the final audio.
  This is the common case on this project since free-music providers (open-lofi,
  internet-archive) often 404.

## The 24 kHz resample note

Voicebox outputs WAV at 24 kHz / 384 kbps / mono. The pipeline resamples this
to 44.1 kHz via ffmpeg's `aresample=44100` filter (line 597). This upsampling
uses linear interpolation — it doesn't add quality but doesn't degrade it either.
The bottleneck is purely the AAC bitrate, not the sample rate conversion.
