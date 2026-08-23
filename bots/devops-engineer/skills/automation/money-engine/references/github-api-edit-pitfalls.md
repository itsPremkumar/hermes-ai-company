# GitHub API file-edit pitfalls (learned 2026-07)

When editing repo files via the GitHub REST API (not `git`), these bit us:

## 1. Contents-API PUT silently drops emoji / em-dash / non-ASCII
`PUT /repos/{o}/{r}/contents/{path}` returns HTTP 200 + filename but the edit does NOT
persist when the new content contains `—` (em dash), emoji, or other non-ASCII. Symptom:
a duplicate paragraph appears, or the old content is served. Fix: edit locally and `git push`,
or strip non-ASCII before the PUT.

## 2. raw.githubusercontent.com is CDN-cached (shows STALE content)
After push/PUT it may serve old content (e.g. a duplicate cross-link) for minutes.
AUTHORITATIVE check = git tree, not raw CDN:
`GET /repos/{o}/{r}/contents/{path}` → base64-decode `content`. This reads HEAD.

## 3. RELIABLE path = clone + edit + push
For anything beyond a tiny single-file add (LICENSE blob, one-line tweak), prefer:
```
git clone https://github.com/o/r.git
# edit file
git add <file>; git commit -m "..."; git push origin main
```
Far more predictable than API PUT for READMEs, cross-links, bulk edits.

## 4. Token retrieval (no gh installed)
```
echo -e "protocol=https\nhost=github.com" | git credential-manager get | grep '^password=' | cut -d= -f2
```

## 5. Topics need a SEPARATE endpoint
`PATCH /repos/{o}/{r}` with a `topics` field is IGNORED (returns empty list).
Set separately:
```
PUT /repos/{o}/{r}/topics
Header: Accept: application/vnd.github.mercy-preview+json
Body:  {"names":["ai-agents","open-source",...]}
```
Description + topics = two calls (PATCH for desc, PUT /topics for topics).

## 6. Verify with the git tree, not raw CDN
When confirming a just-pushed change, use the contents-API GET (base64) to avoid false
"stale/duplicate" verification failures.
