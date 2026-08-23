# Repo rename under multi-account gh (real session recipe)

## Situation
- Owning GitHub user: `itsPremkumar` (has the repo `sproutern-hermes`).
- Default active `gh` account on the box: `prem-the-dev` (only had `pull`/read perms on the repo).
- Goal: rename `itsPremkumar/sproutern-hermes` -> `itsPremkumar/sproutern-oss`, fix 37 stale
  doc links, set description/homepage/topics.

## Step-by-step (proven)
1. Audit perms BEFORE acting (catches the 404 trap early):
   ```bash
   gh auth status            # shows active account + token scopes
   gh api /repos/itsPremkumar/sproutern-hermes | grep -A5 '"permissions"'
   #   "permissions":{"admin":false,"push":false,"pull":true}  <- read-only!
   gh api /user --jq '.login'   # => prem-the-dev  (NOT the owner)
   ```
2. First rename attempt as read-only account FAILED with a misleading 404:
   ```bash
   gh repo rename sproutern-oss -R itsPremkumar/sproutern-hermes
   # HTTP 404: Not Found   <- looks like "repo missing" but is really "no perms"
   gh api -X PATCH /repos/itsPremkumar/sproutern-hermes -f name=sproutern-oss
   # {"message":"Not Found","status":404}   <- same
   ```
3. Switch active account to the OWNER, mutate, switch back:
   ```bash
   gh auth switch -u itsPremkumar
   gh api -X PATCH /repos/itsPremkumar/sproutern-hermes -f name=sproutern-oss
   # => returns full repo JSON with "name":"sproutern-oss"  OK
   ```
4. Set description + homepage + topics (topics need JSON body via --input -, NOT -f):
   ```bash
   gh api -X PATCH /repos/itsPremkumar/sproutern-oss \
     -f description="..." -f homepage="https://sproutern.dpdns.org"
   # WRONG: gh api -X PUT .../topics -f "names=[...]"  -> empty topics
   printf '%s' '{"names":["nextjs","typescript","open-source"]}' | \
     gh api -X PUT /repos/itsPremkumar/sproutern-oss/topics --input -
   ```
5. Fix stale links in a fresh clone, commit as the owner, push, restore default account:
   ```bash
   gh repo clone itsPremkumar/sproutern-oss /tmp/spr-oss -- --depth=1
   cd /tmp/spr-oss
   git ls-files | grep -E '\.(md|json|yml)$' | xargs grep -Il 'sproutern-open-source' | \
     while read f; do sed -i 's/sproutern-open-source/sproutern-oss/g' "$f"; done
   # also fix any sproutern-hermes repo refs (leave live *.vercel.app URLs untouched)
   git add -A && git commit -m "chore: rename references -> sproutern-oss" && git push origin master
   gh auth switch -u prem-the-dev    # restore user's usual default active account
   ```
6. Verify:
   ```bash
   curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' \
     https://github.com/itsPremkumar/sproutern-hermes
   # 301 -> https://github.com/itsPremkumar/sproutern-oss  OK (auto-redirect works)
   gh repo view itsPremkumar/sproutern-oss --json name,repositoryTopics
   ```

## Key takeaways
- A `gh` repo mutation returning **404** is usually a permission problem, not a missing repo,
  when multiple accounts are present — check `gh auth status` + the `/repos` permissions block.
- Repo rename is non-destructive: old URL 301-redirects, stars/history/clones survive.
- Topics via `gh api` MUST be a JSON array in the request body (`--input -`); `-f names=`
  silently produces empty topics.
- Restore the user's default active `gh` account when done.
