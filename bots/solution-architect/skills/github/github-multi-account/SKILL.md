---
name: github-multi-account
description: "Manage multiple GitHub accounts via SSH aliases + gh logins."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Authentication, Git, gh-cli, SSH, Multi-account, Setup]
    related_skills: [github-auth, github-pr-workflow, github-repo-management]
---

# Multiple GitHub Accounts on One Machine

Manage two or more GitHub accounts (e.g. `itsPremkumar` + `prem-the-dev`) on a single laptop without credential pickers or mixed identities. Verified working on Windows/git-bash; the SSH pattern is OS-agnostic.

> Overlaps with the bundled `github-auth` skill (which only has a one-line stub for this). This skill is the detailed, tested implementation. If `github-auth` is later made curator-editable, fold this in.

## When to use
- User says "add my second GitHub account", "manage both accounts", "log into prem-the-dev", "I see a 'Select an account' picker", "Permission denied (publickey)" on a second key.

## Pattern (recommended): SSH key per account + host alias

### 1. Generate a dedicated key per extra account
```bash
ssh-keygen -t ed25519 -C "github-acc2" -f ~/.ssh/id_ed25519_github2 -N ""
cat ~/.ssh/id_ed25519_github2.pub   # HAND THIS to the user to paste at github.com/settings/keys
```
The agent cannot log into the user's second account — the user pastes the public key. On Windows copy to clipboard: `cat ~/.ssh/id_ed25519_github2.pub | clip.exe`.

### 2. Host-alias config (`~/.ssh/config`)
```
# Default -> account #1
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes

# Alias -> account #2 (clone/push with git@github-acc2:owner/repo.git)
Host github-acc2
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github2
  IdentitiesOnly yes
```
`IdentitiesOnly yes` is REQUIRED — without it SSH offers the wrong key first and GitHub returns `Permission denied (publickey)`.

### 3. Per-repo remote + identity
```bash
git remote set-url origin git@github-acc2:prem-the-dev/hammer.git
git -C /c/one/hammer config user.name "prem-the-dev"
git -C /c/one/hammer config user.email "you@users.noreply.github.com"
```
Set `user.name`/`user.email` LOCALLY per repo so commits carry the right identity; the default `github.com` host stays untouched for account #1.

### 4. Separate `gh` login per account (background, browser-approved)
`gh` stores multiple accounts in the OS keyring. Run one `gh auth login` per account in the BACKGROUND so the process survives for the user's browser approval:
```bash
gh auth login -h github.com -p https --web \
  --scopes repo,workflow,gist,read:org,delete_repo
```
Verify both are present and which is active:
```bash
gh auth status
gh api user --hostname github.com     # whoami for the ACTIVE account
gh auth status | grep -i "prem-the-dev"
```
- Target a non-active account: `gh ... --user itsPremkumar` or `gh auth switch`.
- **CRITICAL:** the user must be signed in as the *intended* account when approving the device code at github.com/login/device, or the token attaches to the wrong account.

## Verify WRITE access (push test, then clean up)
Never trust a read test. Prove push works with a scratch branch, then delete it:
```bash
cd /c/one/hammer
T=__access_check_$(date +%s)
SSH="ssh -i '$HOME/.ssh/id_ed25519_github2' -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=8"
GIT_SSH_COMMAND="$SSH" git push git@github-acc2:prem-the-dev/hammer.git HEAD:refs/heads/$T   # expect rc=0
GIT_SSH_COMMAND="$SSH" git push git@github-acc2:prem-the-dev/hammer.git --delete $T            # clean up
```

## Pitfalls (learned the hard way)
- **`ssh -T git@github.com` "Permission denied" is misleading.** It matches the DEFAULT `Host github.com` block (account #1), NOT the `github-acc2` alias. Test the alias: `ssh -T git@github-acc2` or `git ls-remote git@github-acc2:owner/repo.git HEAD`. A correct alias returns `Hi <account2>! You've successfully authenticated`.
- **Embedding tokens in remote URLs creates a stray `x-access-token` credential** in Git Credential Manager, which triggers an interactive "Select an account" picker on every push. The SSH-alias approach above bypasses GCM entirely for git ops — prefer it.
- **Two accounts in GCM + plain `https://github.com/...` remotes = account picker.** Fix: keep SSH alias remotes, and/or `git config --global credential.https://github.com.username <account1>` to pin the default.
- **`gh auth login` dies if run foreground with a short timeout** — the agent shell can't hold it alive for the user's separate browser approval. Run it `background=true` (notify_on_complete) and surface the one-time device code from the process output.

## Quick access-check recipe (copy-paste)
See `references/verify-multi-account.sh` for a script that tests SSH identity + read + write for a given alias/account and cleans up.
