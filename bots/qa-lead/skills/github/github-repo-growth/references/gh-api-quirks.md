# gh API quirks (collected during Automated-Video-Generator + profile work)

## Topics: separate endpoint, hard cap 20
- `gh repo edit owner/repo --add-topic x` works, OR
- `gh api repos/owner/repo/topics -X PUT --input topics.json` where
  `{"names":[...]}` — MAX 20 entries, else `Validation Failed: A repository
  cannot have more than 20 topics.`
- Verify: `gh api repos/owner/repo/topics --jq '.names | length'`

## Description + homepage: REST PATCH, not mixed flags
- Use `--input file.json` ALONE (do not mix with `-f`). Mixed `-f` + `--input`
  silently drops fields.
- `homepage` IS valid in REST PATCH body; `description` is too.
- Verify: `gh api repos/owner/repo --jq '{description, homepage, topics}'`

## `gh repo view --json` valid fields
- `description` is valid; `homepage` is NOT a valid GraphQL field for
  `repo view --json` (use REST `gh api` instead). Error: `Unknown JSON field`.

## Discussions enable
- `gh api repos/owner/repo -X PATCH -f has_discussions=true`

## Release at current main
- `gh release create vN --repo owner/repo --title "..." --notes "$(cat <<'EOF' ... EOF)"`
- Tag must not pre-exist (`Release.tag_name already exists` = 422). List first:
  `gh release list --repo owner/repo`; `git tag`.

## Labels
- `gh label create "good first issue" --description "..." --color "7057ff"`
- Re-creating an existing label errors (use --force to update).

## Windows path in bash — CRITICAL `gh.exe` MSYS gotcha (validated 2026-07)
`gh` on this host is a **Windows binary** (`gh.exe`). It does NOT understand
MSYS-style paths (`/c/Users/...`) and does NOT handle multiline `-f` payloads.
Symptoms seen in-session: `--input /c/Users/.../file.json` →
`The system cannot find the path specified`; bare `-f content="$MULTILINE"` →
JSON parse failures; `-f tree[0][mode]=100644` form arrays → `Invalid tree info` (422).

WORKING PATTERN (use this, not file paths or nested `-f`):
1. Put JSON on **stdin via a heredoc / echo pipe**, never `--input /c/...`:
   `echo '{"content":"...","encoding":"utf-8"}' | gh api repos/OWNER/REPO/git/blobs --input - --jq '.sha'`
2. Build each object in a shell variable, chain via pipe so each SHA feeds the next
   (blob → tree → commit → ref → PR). Use `printf '%s' "$VAR" | base64 -w0` for file
   content, then wrap as `{"content":"<B64>","encoding":"base64"}`.
3. For the **Contents API** (single-file create/update) this is cleanest — ONE call
   creates branch+commit:
   `gh api repos/OWNER/REPO/contents/PATH -X PUT -f message=... -f content="$B64" -f branch=NEWBRANCH`
   (note: `branch=` only needed when updating an existing branch; for a new branch it
   may 404 — fall back to the git-data pipeline above).
4. Always `cd` to a simple dir (e.g. `cd /tmp`) before piping, so there is no CWD
   path-translation in play.

## `achievements` GraphQL field is GONE
- `gh api graphql -f query='... achievements ...'` → `Field 'achievements' doesn't
  exist on type 'User'`. GitHub removed it. You CANNOT read a user's current badges
  programmatically. To verify earned badges, screenshot the live profile page
  (browser + vision) and read the Achievements row.
- Don't promise to "list current badges" via API — it's impossible now.

## `gh repo list --json` field names differ from REST
- The GraphQL `repo list --json` uses `stargazerCount` (NOT `stargazers`) and
  `isFork` (NOT `fork`). Wrong field → `Unknown JSON field: "stargazers"`.
- For a quick total-stars sum: `gh repo list OWNER --limit 200 --json stargazerCount,isFork`
  then filter `isFork==false` in python.

## `gh pr merge --merge --delete-branch` (YOLO badge) needs an unprotected branch
- If `main` is branch-protected, the no-review merge fails. Check first:
  `gh api repos/OWNER/REPO/branches/main/protection` → 404 means unprotected (good).
- Workflow that worked: git-data pipeline (blob→tree→commit→ref→PR) then
  `gh pr merge $NUM --repo OWNER/REPO --merge --delete-branch`.

## shields.io stat badges — verify before trusting
- `img.shields.io/github/stars/USER` reports **115** but a manual sum of owned-repo
  `stargazerCount` gives **62** — the badge also includes the profile repo + other
  sources. It IS a real GitHub number, just not "stars received on my code".
  Don't hand-edit it to "fix" the mismatch; it's accurate to shields' definition.
- Dead badge hosts render as BROKEN images on a profile. `visitor-badge.laowi.com`
  is OFFLINE (curl http_status=000) — remove any badge pointing there.
- Verify a badge service is alive: `curl -s -o /dev/null -w "%{http_code}" <url>`
  before adding it to a polished (job-seeker) profile.
