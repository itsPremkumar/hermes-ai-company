# GitHub-Pages Site-Farm Sanitize (private → public) — real technique

From a live port of `itsPremkumar/website-automation` (private, had a committed
GitHub PAT + a third-party Monetag zone ID) → `website-automation-public` (public, clean).

## Pipeline that worked

1. **Clone shallow** (keeps history tiny so amend purges it):
   `git clone --depth 1 <private-url>`
2. **Inventory secrets**: `.env` had `GITHUB_TOKEN=ghp_***` (real, leaked).
3. **Remove from tree + ignore**:
   `rm -f .env` ; `git rm --cached .env` ; add `.env` / `.env.*` (!.env.example) to `.gitignore`.
4. **Purge from history** (shallow, 1 commit):
   `git commit --amend -m "..."` then `git push --force origin <branch>`.
   NOTE: `--amend` only rewrites the single shallow commit. For deep history use
   `git filter-repo --path .env --invalidate-refs`. Force-push is REQUIRED to
   overwrite the remote's old commit that still contains the token.
5. **Scrub third-party IDs**: template `index/post/payment/404.html` hardcoded
   `10403494` (someone else's Monetag zone). Replaced with `YOUR_MONETAG_ZONE_ID`
   placeholder; added `lib/inject.js` that fills title/description/OG/sitemap/robots.txt
   + the Monetag zone from each site's `site-config.json` at deploy time.
6. **Create fresh public repo** via API (`auto_init:false` to avoid merge conflicts),
   add as `public` remote, force-push.
7. **Verify LIVE via API blob decode** (raw CDN lies after force-push):
   ```bash
   curl -s "https://api.github.com/repos/OWNER/REPO/contents/<path>?ref=main" \
     | node -e "const d=JSON.parse(require('fs').readFileSync(0,'utf8'));const t=Buffer.from(d.content,'base64').toString();console.log('old id:',t.split('10403494').length-1,'placeholder:',t.split('YOUR_MONETAG_ZONE_ID').length-1)"
   ```
   Assert: old-ID count = 0, placeholder count >= 1 on EVERY html file incl. 404.

## Gotchas caught in-session
- Missed `404.html` on the first pass (only patched index/post/payment) → re-grep ALL html.
- `raw.githubusercontent.com` served the OLD blob for minutes after force-push → trust the
  API decode, not raw CDN, when re-verifying.
- System flagged my "passed" verify as STALE because I edited html AFTER running `npm test`
  → re-run the test command after the final edit and re-verify live before declaring done.
- Local branch was `main`, remote default `master` → resolve with `git ls-remote --symref`.

## One-liner test that passed
`npm test` = `node --check` on every .js (bot-deploy, deploy-empire-repos,
deploy-single-site, menu, lib/inject). Run it AFTER the last file edit.
