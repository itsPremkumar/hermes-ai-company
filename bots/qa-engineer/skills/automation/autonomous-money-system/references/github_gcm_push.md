# Push to GitHub without `gh` CLI

The Windows box has no `gh` installed. Use the cached Git Credential Manager
token + the GitHub REST API instead.

## Get the token
```bash
TOKEN=$(echo -e "protocol=https\nhost=github.com" | git credential-manager get 2>/dev/null | grep "^password=" | cut -d= -f2)
```
(On Windows git-bash, `cut -d= -f2` works; the token is the password field.)

## Create a repo (curl)
```bash
curl -sS -X POST -H "Authorization: token $TOKEN" \
  -d '{"name":"my-repo","description":"...","topics":["ai","automation"]}' \
  https://api.github.com/user/repos
```

## Set description + topics (PATCH + PUT)
```bash
curl -sS -X PATCH -H "Authorization: token $TOKEN" \
  -d '{"description":"..."}' https://api.github.com/repos/itsPremkumar/my-repo
curl -sS -X PUT -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  -d '["ai","automation","self-hosted"]' https://api.github.com/repos/itsPremkumar/my-repo/topics
```

## Push committed code
Normal `git push origin master` works — GCM supplies creds automatically.
Verify a file is live:
```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  https://raw.githubusercontent.com/itsPremkumar/my-repo/master/path/to/file.py
```
(HTTP 200 = live.)

## Pitfalls
- Token from `git credential-manager get` is the **password** field, not the
  whole block. Grep `^password=`.
- Never embed the token in committed files. Use a shell var per command.
