# GitHub REST API editing — Windows/MSYS reliability traps (verified 2026-07-13)

Hard-won lessons from hardening `itsPremkumar/ai-company` (added MIT LICENSE, repo
description, 10 topics, and a README cross-link) entirely via the GitHub REST API on this
Windows/MSYS + uv-Python box. Several API calls **silently fail** — they return 200 with no
error but the change does NOT persist. Use this pattern so future sessions don't repeat the
debugging loop.

## The traps

### 1. Topics PATCH silently drops topics
`curl PATCH /repos/owner/repo` with a `"topics": [...]` field does NOT save topics — it
returns the repo object but `topics` comes back `[]`. Topics have a **separate endpoint**
that needs the preview `Accept` header:
```bash
curl -sS -X PUT "https://api.github.com/repos/$OWNER/$REPO/topics" \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.mercy-preview+json" \
  -H "Content-Type: application/json" \
  -d '{"names":["ai-agents","open-source","self-hosted","automation"]}'
# verify: curl GET /repos/owner/repo | python -c "import sys,json;print(json.load(sys.stdin)['topics'])"
```
Description and license on the PATCH endpoint DO work; only `topics` must go to `/topics`.

### 2. `PUT /contents` for file edits silently fails to persist
Uploading a file via `PUT /repos/owner/repo/contents/README.md` with `content` (base64) +
`sha` returns HTTP 200 + `{"content":{"name":"README.md"}}` with no error — but the file on
GitHub is UNCHANGED (re-fetch shows the old text). Cause: stale `sha` (race) or non-ASCII
em-dash `—` corrupting the base64 payload. **Never trust a 200 from PUT /contents** — always
re-fetch and confirm.
**Reliable fix:** edit via `git`, not the API:
```bash
git clone https://github.com/$OWNER/$REPO.git /tmp/$REPO
# edit with patch / write_file
cd /tmp/$REPO && git add -A && git commit -m "..." && git push origin main
rm -rf /tmp/$REPO
```
This is deterministic; the change is authoritative (after CDN settles). Used successfully to
fix a duplicated README cross-link that the API PUT kept failing to de-dupe.

### 3. `raw.githubusercontent.com` shows STALE content (CDN cache)
After a push, `curl https://raw.githubusercontent.com/owner/repo/main/README.md` can return
the OLD file for **minutes** (CDN propagation lag). This makes verification look like failure
when the push actually worked. **Verify via the API contents endpoint** — it reads the git
tree, not the CDN, so it's authoritative:
```bash
curl -sS -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/contents/README.md" \
  | python -c "import sys,json,base64; c=base64.b64decode(json.load(sys.stdin)['content']).decode(); print('occurrences:', c.count('YOUR_MARKER'))"
```
If the API tree shows the change but raw CDN doesn't, the push succeeded — just wait.

### 4. Token file path doesn't survive the MSYS→uv boundary
Writing the GCM token to `/tmp/ghtoken.txt` then reading it from a `python` subprocess
(`subprocess.check_output(["bash", ...])`) FAILS ("WSL ... execvpe /bin/bash failed" or
FileNotFoundError) because uv-managed Python runs in a different shell context than the MSYS
`bash` that fetched the token. Fixes:
- Pass token via env: `TOKEN=$(echo -e "protocol=https\nhost=github.com" | git credential-manager get | grep "^password=" | cut -d= -f2)` then `GH_TOKEN="$TOKEN" python script.py`, read `os.environ["GH_TOKEN"]`.
- OR write the token to a Windows-path temp file (`C:/one/_tok.txt`), not `/tmp/`.
- OR do the whole call in shell with `curl --data-binary @file.json` (no Python subprocess for the token).

### 5. Em-dash `—` in JSON payloads
Hand-written base64 JSON via shell `printf | base64 -w0` with an em-dash corrupts the payload
→ "Problems parsing JSON" 400. Write JSON to a file (write_file) and POST with
`--data-binary @file.json` instead of inline `-d`.

## Reliable full pattern (verified working)
```bash
TOKEN=$(echo -e "protocol=https\nhost=github.com" | git credential-manager get 2>/dev/null | grep "^password=" | cut -d= -f2)
# description (PATCH works)
printf '{"description":"Your description here"}' > meta.json
curl -sS -X PATCH "https://api.github.com/repos/$OWNER/$REPO" -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" --data-binary @meta.json
# topics (separate endpoint + preview Accept header)
curl -sS -X PUT "https://api.github.com/repos/$OWNER/$REPO/topics" -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.mercy-preview+json" -H "Content-Type: application/json" \
  -d '{"names":["ai-agents","open-source","self-hosted"]}'
# file edits → git clone + push (trap 2), NOT PUT /contents
# verify → API contents endpoint (trap 3), NOT raw CDN
# token → env var or Windows-path file (trap 4); JSON → file + --data-binary (trap 5)
```

## When to reach for this
Any time you need to edit repo metadata (description, topics, license, homepage) or file
contents on a GitHub repo via the REST API from this Windows/MSYS environment — especially
when a "200 OK" doesn't actually change the repo. Prefer `git clone + edit + push` for file
edits; reserve the API for metadata that has no simple git equivalent.
