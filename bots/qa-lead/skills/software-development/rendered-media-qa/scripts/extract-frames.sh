#!/usr/bin/env bash
# extract-frames.sh — pull frames + contact sheet from a rendered video for
# VISUAL verification (the automated X7..X15 gates do NOT catch caption
# truncation / ghost overlays). Usage:
#   bash scripts/extract-frames.sh <video.mp4> <outdir> [ffmpeg_path]
# Requires ffmpeg-static: FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
set -euo pipefail
VID="$1"; OUT="$2"; FFMPEG="${3:-$(node -e "console.log(require('ffmpeg-static'))")}"
mkdir -p "$OUT"
# Frames at 1s, 5s, 10s (adjust to your video length)
for t in 1 5 10; do
  "$FFMPEG" -y -ss "$t" -i "$VID" -frames:v 1 -update 1 -q:v 3 "$OUT/frame_${t}s.jpg"
done
# Contact sheet: 3x1 grid of evenly spaced frames
"$FFMPEG" -y -i "$VID" -frames:v 1 -vf "select='not(mod(n\,30))',scale=480:-1,tile=3x1" "$OUT/contact-sheet.png" 2>/dev/null || \
"$FFMPEG" -y -i "$VID" -vf "thumbnail,scale=480:-1,tile=3x1" -frames:v 1 "$OUT/contact-sheet.png"
echo "Wrote frames to $OUT"
