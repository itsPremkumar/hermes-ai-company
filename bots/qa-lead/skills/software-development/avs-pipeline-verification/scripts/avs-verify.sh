#!/bin/bash
# avs-verify.sh — empirical VISUAL verification of an AVS final video, no vision
# model needed (DeepSeek box: vision_analyze unavailable). Run per final.mp4.
#
# Usage: bash scripts/avs-verify.sh <video.mp4> [outdir]
#   outdir MUST be a native Windows path (C:/one/...) — /tmp/... fails because
#   native ffmpeg can't open MSYS-mapped /tmp (verified 2026-07-31).
#
# Checks (exit 1 + ⚠ on any failure):
#   - stream structure (dims, codec, fps, SAR via ffprobe)
#   - blackdetect (0 black frames) — NOTE: needs -v info for crop lines; the
#     black_start lines themselves print at error level so grep still works
#   - freezedetect (n=-60dB:d=1.5; slow Ken Burns zooms false-positive at n=0.001
#     → use PSNR/MD5 before trusting, see avs-ffmpeg-pipeline pitfall 57)
#   - volumedetect audio levels (mean ~ -15..-25 dB speech/music healthy)
#   - speech proof: astats zero-crossing rate > 0.05 on any channel
#     (tone fallback = 220Hz sine ~0.01, silence ~0.0 — see G19)
#     PITFALL: astats prints stats at INFO level — must use `-v info`, NOT
#     `-v error`, or the file comes back EMPTY (same family as volumedetect
#     needing -v verbose, G16)
#   - SAR must be 1:1 (setsar=1 bug class, pitfall 70)
#   - per-frame luma stddev at 1/25/50/75/90%: decode 64x64 gray rawvideo,
#     compute stddev in python — < 4.0 = placeholder/swatch (pitfall 75: the
#     old signalstats/metadata YSTD probe is dead on ffmpeg 6.1.1)
#   - 3x3 contact sheet (9 frames at 10-90%, scale 480) for human/vision spot-check
#
# Frames use INPUT seek (-ss AFTER -i) per G8 — output seek returns 0-byte
# files on odd-keyframe streams.
set -u
V="$1"
OUT="${2:-$(dirname "$V")/verify}"
mkdir -p "$OUT"
BASE="$(basename "$V" .mp4)"
FAIL=0

echo "=== $BASE ==="
# --- stream structure ---
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,avg_frame_rate,sample_aspect_ratio -show_entries format=duration -of csv=p=0 "$V" > "$OUT/${BASE}_stream.txt" 2>&1
echo "stream: $(cat "$OUT/${BASE}_stream.txt" | tr '\n' ' ')"

# --- duration ---
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V" | head -1)
echo "duration: ${DUR}s"
DUR_INT=$(printf '%.0f' "$DUR")

# --- black frames ---
ffmpeg -v error -i "$V" -vf "blackdetect=d=0.5:pix_th=0.10" -f null - 2> "$OUT/${BASE}_black.txt"
BLACK=$(grep -c "black_start" "$OUT/${BASE}_black.txt" || true)
[ "$BLACK" -gt 0 ] && { echo "⚠ BLACK FRAMES: $BLACK"; FAIL=1; } || echo "blackdetect: clean"

# --- freeze ---
ffmpeg -v error -i "$V" -vf "freezedetect=n=-60dB:d=1.5" -f null - 2> "$OUT/${BASE}_freeze.txt"
FREEZE=$(grep -c "freeze_start" "$OUT/${BASE}_freeze.txt" || true)
[ "$FREEZE" -gt 0 ] && { echo "⚠ FREEZE: $FREEZE"; FAIL=1; } || echo "freezedetect: clean"

# --- volume ---
ffmpeg -v verbose -i "$V" -af volumedetect -f null - 2> "$OUT/${BASE}_vol.txt"
MEAN=$(grep mean_volume "$OUT/${BASE}_vol.txt" | sed 's/.*: //' | head -1)
MAX=$(grep max_volume "$OUT/${BASE}_vol.txt" | sed 's/.*: //' | head -1)
echo "audio: mean=${MEAN} max=${MAX}"

# --- speech proof: astats zero-crossings over the first 8s ---
# NOTE: astats prints stats at info level; -v error would suppress them.
ffmpeg -v info -i "$V" -t 8 -af astats=metadata=1:reset=0 -f null - 2> "$OUT/${BASE}_astats.txt"
ZC=$(grep -iE "Zero crossings rate" "$OUT/${BASE}_astats.txt" | head -1 | sed 's/.*: //')
echo "speech zcr: ${ZC} (tone fallback ~0.01, silence ~0.0)"
# astats may print per-channel; accept if ANY channel > 0.05
ANY=$(grep -iE "Zero crossings rate" "$OUT/${BASE}_astats.txt" | grep -oE '[0-9.]+' | awk '{if ($1+0 > 0.05) print "yes"}' | head -1)
[ "$ANY" = "yes" ] && echo "speech: real audio detected (any channel)" || { echo "⚠ LOW AUDIO CONTENT"; FAIL=1; }

# --- SAR check (setsar=1 bug class) ---
SAR=$(ffprobe -v error -select_streams v:0 -show_entries stream=sample_aspect_ratio -of csv=p=0 "$V" | head -1)
echo "SAR: ${SAR} (expect 1:1)"
[ "$SAR" != "1:1" ] && [ -n "$SAR" ] && { echo "⚠ NON-1:1 SAR"; FAIL=1; }

# --- per-frame content stddev (placeholder / blank / swatch detection) ---
for T in 1 25 50 75 90; do
  TS=$(echo "$DUR_INT $T" | awk '{printf "%.1f", $1*$2/100}')
  STDOUT=$(ffmpeg -v error -ss "$TS" -i "$V" -frames:v 1 -vf "scale=64:64,format=gray" -f rawvideo - 2>/dev/null | python -c "
import sys
data = sys.stdin.buffer.read()
if not data: print('NOFRAME'); sys.exit()
px = list(data)
n = len(px)
mean = sum(px)/n
var = sum((p-mean)**2 for p in px)/n
print(f'{var**0.5:.2f}')
")
  echo "frame@${T}%: stddev=${STDOUT}"
  if [ "$STDOUT" != "NOFRAME" ] && [ "$(echo "$STDOUT < 4.0" | bc 2>/dev/null)" = "1" ]; then
    echo "⚠ LOW-CONTENT FRAME at ${T}% (placeholder/swatch?)"
    FAIL=1
  fi
done

# --- contact sheet: 9 frames grid ---
i=0
for T in 10 20 30 40 50 60 70 80 90; do
  TS=$(echo "$DUR_INT $T" | awk '{printf "%.1f", $1*$2/100}')
  ffmpeg -y -v error -ss "$TS" -i "$V" -frames:v 1 -vf "scale=480:-2" "$OUT/${BASE}_f${i}.png" 2>/dev/null
  i=$((i+1))
done
ffmpeg -y -v error -i "$OUT/${BASE}_f0.png" -i "$OUT/${BASE}_f1.png" -i "$OUT/${BASE}_f2.png" \
  -i "$OUT/${BASE}_f3.png" -i "$OUT/${BASE}_f4.png" -i "$OUT/${BASE}_f5.png" \
  -i "$OUT/${BASE}_f6.png" -i "$OUT/${BASE}_f7.png" -i "$OUT/${BASE}_f8.png" \
  -filter_complex "[0][1][2][3][4][5][6][7][8]xstack=inputs=9:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0|0_h0+h1|w0_h0+h1|w0+w1_h0+h1" \
  "$OUT/${BASE}_sheet.png" 2>&1 | head -1
echo "sheet: $OUT/${BASE}_sheet.png"

echo "RESULT: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $FAIL
