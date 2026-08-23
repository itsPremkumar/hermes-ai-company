#!/usr/bin/env bash
# Reusable stdio MCP launcher for an EXTERNAL server that runs under its OWN
# Python/Node venv, registered with Hermes via `hermes mcp add <name> --command bash --args <abs path to this file>`.
#
# Why this wrapper exists (see hermes-mcp-registration SKILL.md):
#   1. Hermes CLI exports PYTHONPATH -> its own venv, which SHADOWS this
#      server's deps and breaks imports. We `unset PYTHONPATH`.
#   2. `hermes mcp add --env ...` gets folded into argv (--args is greedy),
#      so env belongs HERE, not on the add command.
#   3. Resolve paths from BASH_SOURCE so cwd doesn't matter.
set -u

# Resolve this script's directory (works regardless of caller cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Drop any inherited PYTHONPATH so the server's own venv site-packages win.
unset PYTHONPATH

# === EDIT THESE for your server ===
VENV_PY="$SCRIPT_DIR/.venv/Scripts/python.exe"   # or node_modules/.bin/your-server
SERVER_MODULE="your_package.entrypoints.mcp.server"  # python -m <this>
# ================================

# Change into the repo so relative module/asset paths resolve.
cd "$SCRIPT_DIR" || exit 1

# ---- Server environment (set here, NOT via `hermes mcp add --env`) ----
export OPENSPACE_WORKSPACE="$SCRIPT_DIR"
export OPENSPACE_HOST_SKILL_DIRS="C:/Users/PREM KUMAR/AppData/Local/hermes/skills"
export OPENSPACE_CLOUD_MODE="off"   # local-first; set a model+key for task execution
# export OPENSPACE_MODEL="openrouter/tencent/hy3:free"
# export OPENSPACE_LLM_API_KEY=""

exec "$VENV_PY" -m "$SERVER_MODULE" "$@"
