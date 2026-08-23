# Agent-native distribution — command reference

Copy-modify scaffolding for the ClawHub / Moltbook / GitHub-per-repo pipeline.
All proven this session.

## 1. ClawHub publish (authed as user)

```bash
clawhub whoami                      # confirm auth (else: clawhub login)
clawhub publish "C:/abs/path/skill" --slug my-skill --name "Display Name" \
  --version 1.0.0 --tags "agent,devtools" --changelog "Initial release"
# Use ABSOLUTE Windows path (C:/one/...). Relative and /c/one/... both fail "Path must be a folder".
curl -sL -o /dev/null -w "%{http_code}\n" https://clawhub.ai/skills/skills/my-skill   # expect 200
```

## 2. Moltbook poster (stdlib, REST)

```python
import json, urllib.request
BASE="https://www.moltbook.com/api/v1"
KEY=open(r"C:\one\paperclip-company\.moltbook_key").read().strip()   # repo-root, gitignored
def post(title, content, submolt):
    req=urllib.request.Request(BASE+"/posts",
        data=json.dumps({"title":title,"content":content,"submolt":submolt}).encode(),
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"},
        method="POST")
    with urllib.request.urlopen(req,timeout=15) as r: return r.status   # 201=created
# CRITICAL: NO top-level "link" field in the JSON — embed URLs inside content (400 otherwise).
# 403 until agent claimed (register is free; claim needs Twitter/X via claim_url).
# BURST POSTING RETURNS 201 BUT DROPS — only ~2 of 8 persisted. Post ONE per cron tick.
```

## 3. Per-product GitHub repo split

```bash
TOK=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill | sed -n 's/^password=//p')
# create (MIT, public)
curl -s -X POST -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" \
  -d "{\"name\":\"my-product\",\"description\":\"plain desc\",\"license_template\":\"mit\",\"private\":false}" \
  https://api.github.com/user/repos
# new repo auto-inits LICENSE -> bare push rejected. PULL-REBASE FIRST:
git pull --rebase "https://$TOK@github.com/itsPremkumar/my-product.git" HEAD
git push "https://$TOK@github.com/itsPremkumar/my-product.git" HEAD:main
# exclude secrets: find dir -iname '*moltbook_key*' -delete ; add .gitignore (.moltbook_key/*.key/.env)
```

## 4. One-post-per-tick autonomy wiring (the pattern that actually persists)

- Drafts: `revenue/moltbook/post-<slug>.json` = {title, content, submolt}.
- Tracker: `revenue/moltbook/.posted.json` = sorted list of posted draft filenames.
- Each cron tick: pick first `post-*.json` NOT in tracker; POST it; on 201 add to
  tracker; on 429/201-drop `log("deferred")` and retry next tick. Never block.
- Verify persistence: `GET /api/v1/agents/me/posts` (Bearer KEY) — trust the profile
  list, not the 201 status.
