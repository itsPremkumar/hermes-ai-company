# No-`gh` repo create + push via GCM cached token (THIS user)

Verified recipe used 2026-07-14 to publish `itsPremkumar/digital-image-processing-matlab`.
This user has **no `gh` CLI** and an **empty `~/.git-credentials`** (token only in GCM).

## 1. Extract the cached token (silent, no echo)
```bash
TOK=$(printf 'protocol=https\nhost=github.com\nusername=itsPremkumar\n' \
        | git credential fill | sed -n 's/^password=//p')
echo "len=${#TOK}"   # ~40 chars for a classic PAT; sanity check only
```
`git credential fill` returns `protocol/host/username/password`. The `password=` line is
the token. Works headlessly ONLY after the `x-access-token` dual-identity modal is erased
(see `git-credential-manager-windows` Fix A) — before that it hangs.

## 2. Create the repo (auto_init:false so it stays empty for your first commit)
```bash
curl -s -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" \
  -d '{"name":"digital-image-processing-matlab",
       "description":"MATLAB DIP projects: waste classifier + technique demos",
       "auto_init":false,"private":false}' \
  https://api.github.com/user/repos
```
If `auto_init:true`, GitHub adds a README/branch and a later `git push -u origin main`
can be rejected because the remote already has an unrelated `main`. Use `false`.

## 3. Push an existing local repo
```bash
cd /path/to/local/repo
git init -q
git add -A
git -c user.name='prem' -c user.email='premkumar016555@gmail.com' \
    commit -q -m "Initial commit"
git remote add origin https://github.com/itsPremkumar/digital-image-processing-matlab.git
git branch -M main
git push -u origin main      # GCM supplies creds silently
```

## 4. Verify the push (do NOT trust local exit alone)
```bash
curl -s -H "Authorization: Bearer $TOK" \
  https://api.github.com/repos/itsPremkumar/digital-image-processing-matlab/git/trees/main?recursive=1 \
  | grep -oE '"path": "[^"]+"'
```
Returns every tracked file on `main` — concrete proof it landed. Also check `pushed_at`
from `GET /repos/itsPremkumar/<repo>`.

## Pitfalls
- `auto_init:true` + `git push -u origin main` → "failed to push, remote has unrelated
  history". Always `auto_init:false` when pushing an existing repo.
- `git credential fill` hangs (rc=124) in non-interactive shells UNTIL the `x-access-token`
  identity is erased and username pinned (Fix A in the `git-credential-manager-windows` skill).
- Don't embed the token in the remote URL (`https://TOK@github.com/...`) — it persists in
  `.git/config`. Let GCM inject it; pass the token only to `curl` for API calls.
