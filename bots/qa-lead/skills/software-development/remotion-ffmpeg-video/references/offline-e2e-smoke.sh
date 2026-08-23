#!/usr/bin/env bash
# offline-e2e-smoke.sh — reproducible offline end-to-end smoke test for the
# Automated-Video-Generator agentic pipeline on a RAM-starved Windows/MSYS box.
#
# WHAT IT DOES
#   1. Generates 6 local 720x1280 JPG fixtures via ffmpeg-static (no network).
#   2. Runs the agentic pipeline fully offline (P44 short-circuit: --local-assets
#      + P24 flags) so it exercises the WHOLE path (acquire -> verify -> gateway
#      -> voiceover -> render -> X7-X15) WITHOUT any network/Edge-TTS/music hang.
#   3. Prints the [STAGE] markers so a hang is pinpointable (P46), and the
#      post-render gate result.
#
# WHY
#   This is the deterministic gate that proves the P45 sync-ffmpeg fixes hold:
#   before the fixes the run hung at EXIT=124 right after music resolution;
#   after them it reaches "Rendered" + GATE PASS. Run it after ANY edit to the
#   media path (asset-checks, video-analyzer, gate, free-music, visual-fetcher).
#
# USAGE
#   PEXELS_API_KEY="<key>" bash references/offline-e2e-smoke.sh
#   (OPENVERSE_ENABLED=false is set inside; pass --aspect 9:16 or 1:1 as $1)

set -u
ASPECT="${1:-1:1}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
cd "$REPO_ROOT" || exit 1

export OPENVERSE_ENABLED=false
PEXELS_API_KEY="${PEXELS_API_KEY:-REDACTED}"

FF="$(node -e 'console.log(require("ffmpeg-static"))')"
mkdir -p input/input-assets
for i in 1 2 3 4 5 6; do
  "$FF" -y -f lavfi -i "color=c=green:s=720x1280:d=3,drawtext=text='IMG$i':fontcolor=white:fontsize=80:fontfile=C\\:/Windows/Fonts/arial.ttf:x=(w-text_w)/2:y=h-text_h-120" -frames:v 1 "input/input-assets/img$i.jpg" >/dev/null 2>&1
done

ASSETS="img1.jpg,img2.jpg,img3.jpg,img4.jpg,img5.jpg,img6.jpg"
timeout 160 npx tsx bin/agentic-auto.ts \
  --topic "morning coffee routine" --title "Coffee" \
  --no-sfx --local-assets "$ASSETS" --max-attempts 1 --aspect "$ASPECT" \
  2>&1 | grep -iE "\[STAGE\]|GATE PASS|GATE FAIL|Rendered|EXIT|error|Cannot|spawnSync|timed out"
echo "EXIT=${PIPESTATUS[0]}"
