# ffmpeg-hang-repro — exact reproduction (AVS render.test.ts, 2026-08-01)

## Setup (minimal inputs)
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
TMP="C:/one/Automated-Video-Generator/workspace/tmp/repro-$$"
mkdir -p "$TMP"
"$FFMPEG" -f lavfi -i color=c=navy:s=720x1280:d=4 -c:v libx264 -pix_fmt yuv420p -t 4 -y "$TMP/silent.mp4"
"$FFMPEG" -f lavfi -i "sine=frequency=330:duration=2" -c:a pcm_s16le -y "$TMP/a.wav"
"$FFMPEG" -f lavfi -i "sine=frequency=330:duration=2" -c:a pcm_s16le -y "$TMP/b.wav"
```

## HANGING command (the bug)
```bash
timeout 25 "$FFMPEG" -i "$TMP/silent.mp4" -i "$TMP/a.wav" -i "$TMP/b.wav" \
  -filter_complex "[1:a]adelay=delays=0:all=1[vv0];[2:a]adelay=delays=2000:all=1[vv1];[vv0][vv1]amix=inputs=2:duration=longest:normalize=0[vmix];[vmix]apad[vap];[vap]alimiter=limit=0.7:asc=1:level=disabled[voout]" \
  -map 0:v:0 -map "[voout]" -c:v copy -c:a aac -b:a 192k -y "$TMP/voiced.mp4"
# → times out (25s+); NEVER exits.
```

### Observed stderr evidence (the smoking gun)
```
size=       0kB time=00:02:00.76 bitrate=   0.0kbits/s speed= 241x
size=       0kB time=00:06:06.61 bitrate=   0.0kbits/s speed= 366x
size=     256kB time=00:19:58.08 bitrate=   1.8kbits/s speed= 479x
size=    1280kB time=02:02:13.72 ...
```
Video encodes FOREVER because the silent video (no audio track) + `amix duration=longest`
keeps the muxer open. 4h+ of output was observed for a 4-second source.

## FIXED command (added `-shortest`)
```bash
timeout 30 "$FFMPEG" -i "$TMP/silent.mp4" -i "$TMP/a.wav" -i "$TMP/b.wav" \
  -filter_complex "[1:a]adelay=delays=0:all=1[vv0];[2:a]adelay=delays=2000:all=1[vv1];[vv0][vv1]amix=inputs=2:duration=longest:normalize=0[vmix];[vmix]apad[vap];[vap]alimiter=limit=0.7:asc=1:level=disabled[voout]" \
  -map 0:v:0 -map "[voout]" -c:v copy -c:a aac -b:a 192k -shortest -y "$TMP/voiced_fixed.mp4"
# → exit 0, 4.17s MP4, BOTH streams present.
```

### Verified output
```
Duration: 00:00:04.00
  Stream #0:0: Video: h264 (High), yuv420p, 720x1280 [SAR 1:1 DAR 9:16]
  Stream #0:1: Audio: aac (LC), 44100 Hz, mono
```

## Source patch applied
`src/agentic/orchestrator/render.ts` — voice-mix block (segmented path): added
`-shortest` before `-y` in the `runFfmpegSpawn([...])` args.
