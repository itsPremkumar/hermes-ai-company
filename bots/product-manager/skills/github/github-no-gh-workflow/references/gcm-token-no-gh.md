# GCM token + REST API — full annotated recipe (no `gh`)

Verified on the user's Windows box (no `gh`, no `GITHUB_TOKEN` env var). Auth comes from the Git
Credential Manager cache. Everything below was exercised successfully in a real session.

## 1. Confirm the situation
```bash
command -v gh        # empty → no gh
env | grep -i GITHUB_TOKEN   # empty → no token env var
printf 'protocol=https\nhost=github.com\n' | git credential fill
# prints: protocol=https / host=github.com / username=itsPremkumar / password=****(real 40-char PAT)
```

## 2. Extract token IN-PROCESS (do not use a temp file)
```python
import subprocess, re
out = subprocess.run(['git','credential','fill'],
                     input=b'protocol=https\nhost=github.com\n',
                     capture_output=True).stdout
TOKEN = re.search(rb'password=([^\r\n]+)', out).group(1).decode()
print(len(TOKEN))   # ~40
```

## 3. Create repo
```python
import urllib.request, json
req = urllib.request.Request(
  "https://api.github.com/user/repos",
  data=json.dumps({"name":"omniroute-free-ai-providers",
                   "description":"...","public":True,"auto_init":False}).encode(),
  headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
  method="POST")
d = json.loads(urllib.request.urlopen(req, timeout=60).read())
print(d.get('full_name'), d.get('html_url'))
```

## 4. Create / update a file (Contents API)
- Create: `PUT` with base64 content, no `sha`.
- Update: `GET` first to get `sha`, then `PUT` with `sha`.
- Path can be `docs/x.md` or root `X.md`.
(See `scripts/gh_put_file.py` for a ready helper that does create-vs-update automatically.)

## 5. Push a local git repo (branch gotcha)
```bash
cd mydir
git init -q
git add .
git commit -q -m "init"
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin master      # NOTE: local init → 'master', NOT 'main'
```
If you see `error: src refspec main does not match any` → you pushed `main` but the branch is
`master`. Fix:
```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  -d '{"default_branch":"master"}' https://api.github.com/repos/OWNER/REPO
```

## 6. Verify
```bash
curl -s "https://api.github.com/repos/OWNER/REPO" | python -c "import sys,json;d=json.load(sys.stdin);print(d['default_branch'], d['html_url'], d['size'])"
```

## Security notes
- Never `print(TOKEN)` to chat or logs.
- Don't write `cred.txt` to disk; if you must, delete it immediately after the session.
- The token is a classic PAT cached by GCM; treat it like a password.
