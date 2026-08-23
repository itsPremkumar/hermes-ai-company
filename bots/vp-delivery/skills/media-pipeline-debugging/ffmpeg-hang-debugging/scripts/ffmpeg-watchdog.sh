#!/usr/bin/env bash
# ffmpeg-watchdog.sh — run ANY ffmpeg command under a hard timeout and flag a
# runaway encode (ffmpeg copies a stream forever instead of finishing).
#
# Usage:  ./ffmpeg-watchdog.sh <timeout_seconds> <ffmpeg_binary> [ffmpeg args...]
# Example (reproduces the silent-video + amix hang):
#   ./ffmpeg-watchdog.sh 25 "$(node -e 'console.log(require("ffmpeg-static"))')" \
#     -i silent.mp4 -i a.wav -i b.wav -filter_complex "..." -map 0:v:0 -map "[voout]" -c:v copy -c:a aac -y out.mp4
#
# Exit codes:
#   0  -> ffmpeg exited 0 (healthy, or finished before timeout)
#   124 -> timed out = REAL HANG (investigate stderr time= climb)
#   other -> ffmpeg error (not a hang; read stderr)
#
# The script prints the tail of stderr so you can see whether `time=` keeps
# climbing past the source duration (the hallmark of the amix -shortest trap).
set -u
TIMEOUT="${1:-25}"; shift || true
FF="${1:-ffmpeg}"; shift || true
LOG="$(mktemp)"
timeout "$TIMEOUT" "$FF" "$@" 2>"$LOG"
RC=$?
echo "---- ffmpeg stderr tail (watch the 'time=' line) ----"
tail -6 "$LOG"
if [ "$RC" -eq 124 ]; then
  echo "[WATCHDOG] TIMED OUT after ${TIMEOUT}s -> likely a runaway encode (no -shortest?)."
elif [ "$RC" -eq 0 ]; then
  echo "[WATCHDOG] OK (exit 0)."
else
  echo "[WATCHDOG] ffmpeg error (exit $RC), not a hang."
fi
rm -f "$LOG"
exit $RC
