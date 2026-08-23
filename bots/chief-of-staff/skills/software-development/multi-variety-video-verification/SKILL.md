---
name: multi-variety-video-verification
description: Generate and verify all video type/formats in the agentic pipeline, then run 32-check batch verification on each output.
---

# Multi-Variety Video Verification

Generate every video **type** (nature, facts, motivational, tutorial, cinematic, educational) across every **format** (portrait 9:16, landscape 16:9, square 1:1) and run comprehensive 32-check verification.

## Prerequisites

- Pexels API key in `.env` (`PIXABAY_API_KEY=...` for video)
- ffmpeg-static / ffprobe-static installed
- `scripts/batch-verify.ts` present (32-check suite)

## Steps

### 1. Generate Core Types
Run each independently (Pexels rate-limits, allow 2-5 min per job):

```bash
# Type 1: Nature
npx tsx bin/agentic-run.ts --topic "aurora borealis" --title "Aurora" --orientation portrait --renderer ffmpeg --quality low --backend heuristic --video-type nature

# Type 2: Facts/Explainer
npx tsx bin/agentic-run.ts --topic "black holes" --title "Explained" --orientation landscape --renderer ffmpeg --quality low --backend heuristic --video-type facts

# Type 3: Motivational
npx tsx bin/agentic-run.ts --topic "never give up" --title "Keep Going" --orientation portrait --renderer ffmpeg --quality low --backend heuristic --video-type motivational

# Type 4: Tutorial
npx tsx bin/agentic-run.ts --topic "how to ride bicycle" --title "Learn to Ride" --orientation landscape --renderer ffmpeg --quality low --backend heuristic --video-type tutorial

# Type 5: Cinematic
npx tsx bin/agentic-run.ts --topic "city lights night" --title "City Nights" --orientation landscape --renderer ffmpeg --quality low --backend heuristic --video-type cinematic

# Type 6: Educational
npx tsx bin/agentic-run.ts --topic "photosynthesis" --title "How Plants Eat" --orientation landscape --renderer ffmpeg --quality low --backend heuristic --video-type educational
```

### 2. Run 32-Check Verification on Each Output
```bash
npx tsx scripts/batch-verify.ts "workspace/jobs/<job_id>/render/<job_id>.mp4" "<job_id>"
```

### 3. Check Multi-Format Exports (if platform-export plugin active)
Tutorial type auto-generates: `_16x9.mp4`, `_1x1.mp4`, `_9x16.mp4` exports.
```bash
npx tsx scripts/batch-verify.ts "workspace/jobs/<job_id>/render/<job_id>_16x9.mp4" "<job_id>"
npx tsx scripts/batch-verify.ts "workspace/jobs/<job_id>/render/<job_id>_1x1.mp4" "<job_id>"
```

### 4. Scan for Runtime Console Errors
```bash
for j in workspace/jobs/job_*/; do
  if [ -f "$j/decisions-report.txt" ]; then
    warns=$(grep -ci "warn\|timeout\|retry\|fallback\|error\|exception" "$j/decisions-report.txt" 2>/dev/null || echo 0)
    echo "$(basename $j): $warns warnings"
  fi
done
```

## Verification Checklist (32 Checks)

| Section | Checks |
|---------|--------|
| File Integrity | exists, >50KB, <500MB |
| ffprobe Metadata | readable, duration, bitrate |
| Video Quality | h264, 360p-4K, 12-60fps, yuv420p, std AR |
| Audio Quality | stream, AAC/MP3, ≥22kHz, ≥mono |
| Corruption | no decode errors |
| Black Frames | blackdetect, no segment >0.5s |
| Frozen Frames | freezedetect, no freeze >1s |
| Audio Loudness | non-silent, no clipping, reasonable LUFS |
| FPS | valid FPS, standard rate (24/25/30) |
| Pipeline Logs | workspace, plan, candidates, manifest, decision, assets |

## Known Issues

- **Pexels rate limiting**: 2-5 min per job, do not run >3 concurrently
- **Edge-TTS network fallback**: Occasional fallback to Windows offline speech (graceful)
- **4K source videos**: Verification takes longer on 4K Pexels sources; output is always downscaled to 720p
- **Black frame trim**: Uses `blackdetect=d=0.3:pix_th=0.15` (NOT deprecated `blackframe`)

## Pitfalls

- Pexels API key (`PIXABAY_API_KEY`) is used for both images AND videos — different from Pixabay Audio (which returns 403)
- Do NOT run `render` and `acquire` concurrently on the same job directory
- `batch-verify.ts` must be run with `npx tsx`, not `npx ts-node`
- Windows: `volumedetect` filter may not be available in bundled ffprobe; falls back to gate-verified values
