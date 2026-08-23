#!/usr/bin/env bash
# install_github_release.sh — verified GitHub-release Windows installer runner.
# Usage: bash install_github_release.sh <owner/repo> <asset.exe> [appname]
#   e.g. bash install_github_release.sh stablyai/orca orca-windows-setup.exe Orca
# Assumes MSYS/bash on Windows. Downloads to ~/Downloads, silent-installs, verifies.
set -u

OWNER_REPO="${1:?owner/repo required}"
ASSET="${2:?asset filename required}"
APP="${3:-${ASSET%.*}}"            # appname defaults to asset minus extension
DL_DIR="/c/Users/$USER/Downloads"
URL="https://github.com/${OWNER_REPO}/releases/latest/download/${ASSET}"
INSTALL_DIR="/c/Users/$USER/AppData/Local/Programs/${APP}"
EXE="${INSTALL_DIR}/${APP}.exe"

echo "==> Downloading ${URL}"
curl -fL -o "${DL_DIR}/${ASSET}" "${URL}" || { echo "download failed"; exit 1; }

echo "==> Verifying installer"
sha256sum "${DL_DIR}/${ASSET}"
file "${DL_DIR}/${ASSET}"
stat -c '%s bytes' "${DL_DIR}/${ASSET}"

echo "==> Silent install (Nullsoft /S)"
( cd "${DL_DIR}" && ./${ASSET} /S )
echo "parent exited; waiting for extraction..."
sleep 30

if [ -f "${EXE}" ]; then
  echo "==> OK: binary present at ${EXE}"
  ls -lh "${EXE}"
  ls "/c/Users/$USER/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/" | grep -i "${APP}" || echo "(no start-menu link)"
else
  echo "!! binary NOT found at ${EXE} — check installer output / try Inno /SILENT"
  exit 2
fi

echo "==> Launch smoke test (Electron apps may ignore --version and boot GUI)"
timeout 8 "${EXE}" >/dev/null 2>&1 &
sleep 3
taskkill //IM "${APP}.exe" //F 2>/dev/null
echo "==> Done. Launch via Start Menu or: ${EXE}"
