#!/usr/bin/env bash
# sync_audit.sh — scan a directory tree of git repos and report unsynced state.
# Usage:  bash sync_audit.sh /path/to/repos
# Requires: git, python3 (for the GitHub cross-check, optional).
set -u
ROOT="${1:-.}"
echo "=== LOCAL SYNC AUDIT: $ROOT ==="
for d in $(find "$ROOT" -maxdepth 2 -name .git -type d 2>/dev/null | sed 's#/.git##'); do
  repo=$(basename "$d"); cd "$d" 2>/dev/null || continue
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  # ahead (local commits not on remote)
  if git rev-parse --abbrev-ref @{u} >/dev/null 2>&1; then
    ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null)
  elif [ -n "$branch" ] && [ "$branch" != "HEAD" ] && git rev-parse "origin/$branch" >/dev/null 2>&1; then
    ahead=$(git rev-list --count "origin/$branch..HEAD" 2>/dev/null)
  else
    ahead="NO-UPSTREAM"
  fi
  # behind (remote has commits local lacks) — only if we have an origin/<branch>
  if [ -n "$branch" ] && [ "$branch" != "HEAD" ] && git rev-parse "origin/$branch" >/dev/null 2>&1; then
    behind=$(git rev-list --count "HEAD..origin/$branch" 2>/dev/null)
  else
    behind="?"
  fi
  uncomm=$(git status --porcelain 2>/dev/null | wc -l)
  # classify
  if [ "$ahead" = "NO-UPSTREAM" ]; then
    flag="NO-REMOTE-UPSTREAM"
  elif [ "$ahead" != "0" ] && [ "$ahead" != "?" ] && [ "$behind" != "0" ] && [ "$behind" != "?" ]; then
    flag="DIVERGED"
  elif [ "$ahead" != "0" ] && [ "$ahead" != "?" ]; then
    flag="AHEAD/UNPUSHED"
  elif [ "$uncomm" != "0" ]; then
    flag="DIRTY"
  fi
  if [ "${flag:-}" ]; then
    echo "[$flag] $repo | br=$branch | ahead=$ahead | behind=$behind | uncommitted=$uncomm"
  fi
  cd "$ROOT" 2>/dev/null || cd /
done
echo "=== (repos with no line above are clean & in sync) ==="
