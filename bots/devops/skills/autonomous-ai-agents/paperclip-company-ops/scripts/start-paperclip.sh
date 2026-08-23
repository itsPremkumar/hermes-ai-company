#!/bin/bash
# start-paperclip.sh  — packaged launcher for the Paperclip server on the Windows/git-bash host.
# WHY this script exists (verified 2026-07-15):
#   - The shipped run-server.bat sets NODE_OPTIONS=--max-old-space-size=8192, which OOM-crashes
#     Node on this ~6GB box. This script uses 4096 (safe ceiling).
#   - Launching tsx via an absolute Windows path from bash FAILS: MSYS mangles C:\one -> C:\cone
#     ('Cannot find module C:\cone\...tsx\dist\cli.mjs'). The relative ../node_modules/.bin/tsx
#     path (run from inside paperclip/server) avoids the mangling.
#   - cmd.exe /c <bat> also fails: MSYS strips backslashes -> 'C:onepaperclip...bat' not found.
#   - WORKING form: run this with terminal(background=true); env exported inline; relative tsx path.
# USAGE (from Hermes terminal tool, background=true):
#   bash /c/one/paperclip-company/start-paperclip.sh
# PREREQ: postgres alive (wmic process where "name='postgres.exe'" > 0)
set -u
cd /c/one/paperclip-company/paperclip/server
export PORT=3100
export HOST=0.0.0.0
export SERVE_UI=true
export BETTER_AUTH_SECRET=paperclip-dev-secret-change-me
export PAPERCLIP_DEPLOYMENT_MODE=authenticated
export PAPERCLIP_DEPLOYMENT_EXPOSURE=private
export PAPERCLIP_PUBLIC_URL=http://localhost:3100
export PAPERCLIP_HOME=C:/one/paperclip-company/data/paperclip
export PAPERCLIP_MIGRATION_AUTO_APPLY=true
export DATABASE_URL=postgres://paperclip:***@localhost:5432/paperclip
export NODE_OPTIONS=--max-old-space-size=4096
# Load OpenRouter key from hermes .env if not already in env (agents 402 without it)
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  OR=$(grep -E '^OPENROUTER_API_KEY=' "C:/Users/PREM KUMAR/AppData/Local/hermes/.env" 2>/dev/null | head -1 | cut -d= -f2-)
  [ -n "$OR" ] && export OPENROUTER_API_KEY="$OR"
fi
exec ../node_modules/.bin/tsx src/index.ts
