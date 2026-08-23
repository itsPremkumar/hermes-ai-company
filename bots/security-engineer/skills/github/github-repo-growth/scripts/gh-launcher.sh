#!/usr/bin/env bash
# github-repo-growth: secure GitHub MCP launcher.
# Reads the PAT from `gh`'s OS keyring at launch time (NEVER written to a file),
# then execs the official MCP server. Point Hermes config.yaml mcp_servers.github.command here.
set -euo pipefail
GH_BIN="/c/Program Files/GitHub CLI/gh.exe"
TOKEN="$("$GH_BIN" auth token 2>/dev/null || true)"
if [ -z "$TOKEN" ]; then
  echo "gh-launcher: no gh token found (run 'gh auth login')" >&2
  exit 1
fi
export GITHUB_PERSONAL_ACCESS_TOKEN="$TOKEN"
exec npx -y @modelcontextprotocol/server-github "$@"
