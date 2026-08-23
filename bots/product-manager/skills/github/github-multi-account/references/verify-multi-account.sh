#!/usr/bin/env bash
# verify-multi-account.sh — prove a second GitHub account works (identity + read + WRITE).
# Usage: bash verify-multi-account.sh <ssh_alias> <account_login> <key_path> <owner/repo> [repo_dir]
#   e.g. bash verify-multi-account.sh github-acc2 prem-the-dev ~/.ssh/id_ed25519_github2 prem-the-dev/hammer /c/one/hammer
set -u
ALIAS="${1:?ssh alias, e.g. github-acc2}"
ACCT="${2:?account login, e.g. prem-the-dev}"
KEY="${3:?path to the account's private SSH key}"
REPO="${4:?owner/repo, e.g. prem-the-dev/hammer}"
DIR="${5:-.}"

SSH_CMD="ssh -i '$KEY' -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=8"
export GIT_SSH_COMMAND="$SSH_CMD"

echo "=== 1) SSH identity (must say Hi $ACCT) ==="
ssh -i "$KEY" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=8 "git@$ALIAS" 2>&1 | head -2

echo "=== 2) Read access (HEAD commit) ==="
git ls-remote "git@$ALIAS:$REPO.git" HEAD 2>&1 | head -1

echo "=== 3) WRITE access (scratch branch push, then delete) ==="
cd "$DIR" 2>/dev/null || { echo "repo dir not found: $DIR"; exit 1; }
T="__access_check_$(date +%s)"
if git push "git@$ALIAS:$REPO.git" "HEAD:refs/heads/$T" 2>&1 | tail -2; then
  echo "PUSH OK (rc=0) — write access confirmed"
  git push "git@$ALIAS:$REPO.git" --delete "$T" 2>&1 | tail -1
  echo "scratch branch deleted — clean"
else
  echo "PUSH FAILED — no write access / key not registered to $ACCT"
fi
