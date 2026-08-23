#!/bin/bash
# Monitor pipeline progress by checking workspace files.
# Usage: process-monitor.sh <job-directory>
# Shows which phase the pipeline is in based on files present.

jobdir="${1:-workspace/jobs/$(ls -t workspace/jobs/ 2>/dev/null | head -1)}"

if [ ! -d "$jobdir" ]; then
  echo "Usage: $0 <job-directory>"
  echo "No job directory found at: $jobdir"
  exit 1
fi

job=$(basename "$jobdir")
echo "=== Pipeline Progress: $job ==="

# Phase detection (ordered)
[ -f "$jobdir/plan.json" ]           && echo "  ✅ Plan ready" || echo "  ⏳ Planning..."
[ -d "$jobdir/assets/videos" ]        && echo "  ✅ Videos downloaded ($(ls "$jobdir/assets/videos" 2>/dev/null | wc -l) scenes)" || echo "  ⏳ Downloading..."
[ -f "$jobdir/verification/all_checks.json" ] && echo "  ✅ Verification complete" || echo "  ⏳ Verifying..."
[ -d "$jobdir/audio" ]               && echo "  ✅ Voiceover generated ($(ls "$jobdir/audio"/*.wav 2>/dev/null | wc -l) files)" || echo "  ⏳ Voiceover..."
[ -f "$jobdir/approval-manifest.json" ] && echo "  ✅ Gate passed (approved)" || echo "  ⏳ Gate..."
[ -d "$jobdir/render" ]              && echo "  ✅ Render started" || echo "  ⏳ Rendering..."
[ -f "$jobdir/render/${job}.mp4" ]    && echo "  ✅ Render complete ($(du -h "$jobdir/render/${job}.mp4" 2>/dev/null | cut -f1))"
[ -d "$jobdir/archive" ]             && echo "  ✅ Published ($(ls "$jobdir/archive"/*.mp4 2>/dev/null | wc -l) files archived)"

# Check for errors
if [ -f "$jobdir/decisions-report.txt" ]; then
  errors=$(grep -ci "error\|fail\|exception" "$jobdir/decisions-report.txt" 2>/dev/null || echo 0)
  [ "$errors" -gt 0 ] && echo "  ⚠  $errors errors in decision report"
fi

# Disk usage
du -sh "$jobdir" 2>/dev/null | awk '{print "  📦 Job size: " $1}'
echo "========================"
