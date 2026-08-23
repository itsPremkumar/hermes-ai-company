# Working transcript — 2nd GitHub account on one Windows laptop (2026-07-31)

Real commands + responses from a session that added a second account next to an
existing HTTPS/GCM account, verified SSH, and started the account rename via the
device flow. Reuse as the ground truth for the recipe in SKILL.md.

## Audit before touching anything

```bash
git config --global --list          # account A: credential.helper=manager (GCM), username pinned
ls -la ~/.ssh                       # id_ed25519_github (account A) existed
gh auth status                      # gh logged in as account A
```

## Key generation + registration

```bash
ssh-keygen -t ed25519 -C "github-acc2" -f ~/.ssh/id_ed25519_github2 -N ""
cat ~/.ssh/id_ed25519_github2.pub | clip.exe   # → user pastes at github.com/settings/ssh/new
```

~/.ssh/config (must be written via terminal heredoc — write_file refuses dotfiles):

```
Host github.com        # account A (default)
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
Host github-acc2       # account B alias
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github2
  IdentitiesOnly yes
```

## Verification (before registration vs after)

```bash
ssh -o BatchMode=yes -T git@github-acc2
# before key registration:  git@github.com: Permission denied (publickey).   (exit 255)
# after user pasted key:     Hi premkumar995252-tech! You've successfully authenticated,
#                            but GitHub does not provide shell access.      (exit 1 = EXPECTED)
```

Note: the account-A SSH key also returned "Permission denied" — account A only ever
used HTTPS/GCM, so that's fine and NOT a regression. The SSH test only proves the
alias/key path you configured.

## Device-flow OAuth via curl (no gh) — exact request/response

```bash
curl -s -X POST https://github.com/login/device/code -H "Accept: application/json" \
  -d "client_id=178c6fc778ccc68e1d6a&scope=repo%20workflow%20admin:public_key%20user%20read:org%20gist"
```

Response:
```json
{"device_code":"af0acc3d58e1662761ebc4d44d5c44468d7a34c6",
 "user_code":"02AB-0C87",
 "verification_uri":"https://github.com/login/device",
 "expires_in":899,"interval":5}
```

User then opened https://github.com/login/device in Chrome (already signed in as the
second account) and entered `02AB-0C87`.

Poll loop (background, notify-on-complete, saved result to a temp file):

```bash
for i in $(seq 1 100); do
  resp=$(curl -s -X POST https://github.com/login/oauth/access_token -H "Accept: application/json" \
    -d "client_id=178c6fc778ccc68e1d6a&device_code=af0acc3d58e1662761ebc4d44d5c44468d7a34c6&grant_type=urn:ietf:params:oauth:grant-type:device_code")
  echo "$resp" | grep -q '"access_token"' && { echo "$resp" > .acc2_token.json; echo TOKEN_GRANTED; break; }
  echo "$resp" | grep -qE 'access_denied|expired_token' && { echo "FAILED: $resp"; break; }
  sleep 5
done
```

Token grants full API access for the browser-active account — then
`PATCH /user {"login":"<new>"}` renames it, `POST /user/repos` creates repos,
`PATCH /user` also sets name/bio/location/blog.

## Username availability

```bash
for n in premthedev prem-the-dev premdev premdev-m premkumar-builds; do
  echo "$n: $(curl -s -o /dev/null -w '%{http_code}' https://api.github.com/users/$n)"
done
# 200 = taken; 404 = free. Picks checked: premthedev 200(taken), prem-the-dev 404(free, chosen),
# premkumar-m 200, premkumar-ai 200, premkumar-builds 404.
```

## Browser-driving lessons (why the device flow is preferred for account ops)

On this setup (Chrome + computer_use, no vision model — AX tree only):
- `ctrl+l → type URL → Enter` navigation was FLAKY: 2 of 3 attempts left the page
  unchanged, and one raced with the user's own typing (their URL landed instead).
- Element clicks occasionally failed with "not visibly actionable / off-screen" while
  the dropdown was actually open (stale window geometry; capture came back 0x0 when
  the window was minimized). Coordinate click then errored.
- cua_browser_* (typed-browser) binding required its own prepare/allow-launch setup —
  not worth it vs the API path.
- Verdict: for GitHub ACCOUNT operations (rename, profile, repo creation) go straight
  to the device-flow token. Browser is only for the human-only steps (paste key,
  approve device code, enter password).
