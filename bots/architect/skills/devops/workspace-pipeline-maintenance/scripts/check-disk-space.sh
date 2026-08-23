#!/bin/bash
# Quick disk space check for pipeline workspace maintenance.
# Exits 0 (OK) if >=5GB free, 1 (WARN) if <5GB, 2 (FAIL) if <1GB

avail=""
if command -v df &>/dev/null; then
  raw=$(df -h /c/ 2>/dev/null | awk 'NR==2{print $4}')
  avail=$(echo "$raw" | sed 's/[A-Za-z]//g')
  unit=$(echo "$raw" | sed 's/[0-9.]//g')
  case "$unit" in
    G|g) ;;  # already GB
    M|m) avail=$(awk "BEGIN{printf \"%.1f\", $avail/1024}");;
    T|t) avail=$(awk "BEGIN{printf \"%.1f\", $avail*1024}");;
  esac
fi

if [ -z "$avail" ]; then
  # Fallback: wmic
  avail_bytes=$(wmic logicaldisk where "Caption='C:'" get FreeSpace /value 2>/dev/null | grep -oP '\d+')
  [ -n "$avail_bytes" ] && avail=$((avail_bytes / 1073741824)) || avail=0
fi

echo "C: free = ${avail}GB"

if [ "$(echo "$avail < 1" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
  echo "FAIL: <1GB free — clear old jobs: rm -rf workspace/jobs/job_178461*/"
  exit 2
elif [ "$(echo "$avail < 5" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
  echo "WARN: <5GB free — consider cleaning old jobs before starting"
  exit 1
fi
echo "OK: sufficient disk space"
exit 0
