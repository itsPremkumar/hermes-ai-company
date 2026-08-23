# Evaluation checklist & probe recipe

## One-shot probe (bash / git-bash)
Replace OWNER/REPO.

```bash
# Repo stats (no browser needed — browser often times out on these)
curl -sL "https://api.github.com/repos/OWNER/REPO" | python -c "
import json,sys
d=json.load(sys.stdin)
print('stars',d.get('stargazers_count'),'forks',d.get('forks_count'))
print('created',d.get('created_at'),'pushed',d.get('pushed_at'))
print('desc',d.get('description'))
"
# File tree
curl -sL "https://api.github.com/repos/OWNER/REPO/git/trees/main?recursive=1" > tree.json
python -c "import json;[print(t['path'],t.get('size','')) for t in json.load(open('tree.json')).get('tree',[])]"
# README (first 5k)
curl -sL "https://raw.githubusercontent.com/OWNER/REPO/main/README.md" | head -c 5000
```

## Marketplace demand probe (the real test)
The project depends on its OWN marketplace to pay out. Probe it:
```bash
# Try a few likely task endpoints; empty/404 = unverified demand
for ep in "https://api.MARKET.com/v1/tasks?limit=5" "https://api.MARKET.com/tasks" "https://MARKET.com/api/tasks"; do
  echo "-- $ep"; curl -sL -m 12 "$ep" | head -c 200; echo
done
# Is the owner's OTHER repos part of a hype ecosystem?
curl -sL "https://api.github.com/users/OWNER/repos?per_page=30" | python -c "import json,sys;[print(r['name'],'-',r.get('description')) for r in json.load(sys.stdin)]"
# npm download reality
curl -sL "https://api.npmjs.org/downloads/point/last-week/PKG"
```

## Verdict table (fill per project)
| Factor | Project A | Project B |
|---|---|---|
| Core dependency | marketplace X | marketplace Y |
| Marketplace demand | empty/unverified | 85% commission |
| Your cost first | LLM key + ETH | LLM + Stripe + crypto |
| Income proof | none | anonymous quotes |
| Maintenance | abandoned DATE | self-promo |
| Reality | likely net loss | likely net loss |

## Pushing to GitHub WITHOUT gh (user uses cached GCM token)
`gh` is not installed for this user. Use Git Credential Manager's cached token:
```bash
# Extract token (digits only, never echo it)
TOKEN=$(printf 'protocol=https\nhost=github.com\n' | git credential fill 2>/dev/null | awk -F= '/^password=/{print $2}')
# Create repo via API (write JSON to file to avoid quoting/emoji parse errors)
cat > .createrepo.json <<'JSON'
{"name":"aivid-studio","private":false}
JSON
curl -sL -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary @.createrepo.json https://api.github.com/user/repos
rm -f .createrepo.json   # MUST delete before any commit
# Then: git init, commit, remote add, push (token flows via GCM, not in URL)
```
Pitfall: inline JSON with emoji/quotes via `-d` failed with "Problems parsing JSON" — always use `--data-binary @file` or `<<'JSON'` heredoc.
Pitfall: the temp `.createrepo.json` must be removed before `git add -A`, else it ships.
