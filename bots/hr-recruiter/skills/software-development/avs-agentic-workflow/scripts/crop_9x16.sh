#!/bin/bash
# crop_9x16.sh — crop full-page website screenshots to a 9:16 top section, in place.
# Usage:  scripts/crop_9x16.sh input/visuals/sproutern-hero.png [more ...]
# Requires the bundled ffmpeg: ./node_modules/ffmpeg-static/ffmpeg.exe
# NOTE: ffmpeg cannot read+write the same file, so we crop to a temp then mv over.
set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
FF="./node_modules/ffmpeg-static/ffmpeg.exe"
for src in "$@"; do
  [ -f "$src" ] || { echo "skip (missing): $src"; continue; }
  dim=$("$FF" -i "$src" 2>&1 | grep -oE '[0-9]+x[0-9]+' | head -1)
  W=$(echo "$dim" | cut -dx -f1)
  H=$(echo "$dim" | cut -dx -f2)
  CH=$(( W * 16 / 9 ))
  [ "$CH" -gt "$H" ] && CH=$H
  tmp="${src%.*}_9x16.png"
  "$FF" -y -i "$src" -vf "crop=${W}:${CH}:0:0" "$tmp" >/dev/null 2>&1
  mv -f "$tmp" "$src"
  echo "$(basename "$src") -> ${W}x${H} cropped to ${W}x${CH}"
done
echo "ALL DONE"
