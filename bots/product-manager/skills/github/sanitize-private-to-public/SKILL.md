---
name: sanitize-private-to-public
description: "Port code/docs from a PRIVATE repo into PUBLIC repo(s) while stripping every credential, key, and personal/sensitive detail. Use when a user says 'copy this into the open-source version', 'add the private setup to the public repo', or 'publish this but don't leak secrets'. Enforces a scan-sanitize-scan-verify-live pipeline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [security, secrets, open-source, publishing, sanitization, git]
    related_skills: [github-no-gh-workflow, git-credential-manager-windows]
---

# Sanitize Private → Public (secret-safe porting)

Use when moving files from a **private** repo/account into **public** repo(s) and the user wants
zero credential/PII leakage (they will usually say so explicitly — treat it as a hard requirement
even if they don't). The deliverable is the ported content **plus** proof nothing sensitive shipped.

## The pipeline (do all five, in order)
1. **INVENTORY** — list the private repo's files. Identify (a) the content to port and (b) the
   files to NEVER copy. Never-copy set typically: `.env`, `.env.local`, `.env*`, `.firebaserc`,
   `.mcp.json`, `service-account*.json`, `*-adminsdk*.json`, any `*.pem`/`*.key`, `credentials*`.
2. **STAGE** — copy only the port candidates to a scratch dir. Do NOT copy the never-copy set.
3. **SCAN** — grep the staged tree for secrets AND personal data before touching the public repo:
   ```bash
   grep -rniE 'api[_-]?key|secret|token|password|bearer|private[_-]?key|client_secret|service.?account|AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|vca_[A-Za-z0-9]{8,}|vcr_[A-Za-z0-9]{8,}|-----BEGIN' .
   # plus the USER'S specific PII: email, phone digits, real name, home paths, real team/project slugs
   grep -rniE '<email>|<phone-digits>|<real-name>|C:/one|C:\\\\one' .
   ```
   Distinguish **real secrets** (redact) from **documentation of formats** (`token starts with vca_`,
   `NEXT_PUBLIC_FIREBASE_API_KEY=dummy`) — the latter is safe to keep. Filter false positives with
   `| grep -v 'starts with'` etc.
4. **SANITIZE** — replace what the scan found:
   - Real keys/tokens/service-account JSON → `[REDACTED]` or a placeholder (`your_firebase_web_api_key`).
   - Private local paths (`C:/one/<proj>`) → generic (`/path/to/your/<proj>`).
   - Real account identifiers (team slug like `prems-projects-27978e99`, project IDs, emails, phone)
     → generic tokens (`YOUR_TEAM_SLUG`). These are PII/account-linkage even if not "secret".
   - Ship an `ACCOUNT_SETUP.md` / `.env.example` with **placeholders only** and a note to put real
     values in a git-ignored `.env.local`.
5. **VERIFY LIVE** — after pushing, re-scan the **raw public URLs** (not just local), because that's
   what the world sees:
   ```bash
   curl -s "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/path" | grep -niE '<secret-patterns>'
   ```
   Also confirm the public repo's `.gitignore` already blocks `.env*`, `service-account.json`,
   `*-adminsdk*.json` so the user can't accidentally commit real values later.

## Pitfalls
- **Documentation vs. secret**: don't over-redact. Dummy build values and format descriptions are
  fine and useful; only real live values must go.
- **PII ≠ only API keys**: real team/project slugs, emails, phone numbers, personal home paths are
  sensitive too. Genericize them.
- **Multiple target repos**: when porting to N public repos, they may have different default
  branches — resolve each with `git rev-parse --abbrev-ref HEAD`, don't assume `main`.
- **Scan the staged copy AND the live raw content.** A clean local tree isn't proof; verify what's
  actually served publicly.
- **Clean up scratch dirs and any token temp files** at the end.
- **Committed-token purge (shallow clone)**: `git rm --cached .env` removes the file from the
  tree but leaves the secret in git history — the public repo's old commit still exposes it.
  Fix: on a 1-commit shallow clone, `git commit --amend` rewrites the single commit cleanly,
  then `git push --force origin <branch>` (force is REQUIRED to rewrite the remote commit).
  For deep history use `git filter-repo` instead. Verify the remote no longer has the token via
  the API blob decode (see below), not a local `git log`.
- **Third-party ad / zone IDs are also leakage**: a template may hardcode someone else's Monetag /
  AdSense / analytics ID (e.g. `10403494`). That's not "your" secret but still leaks attribution
  and must be replaced with a per-site config placeholder (`YOUR_MONETAG_ZONE_ID`) filled at
  deploy time by an injector (e.g. `lib/inject.js`). Grep ALL html incl. `404.html` — one
  missed file (e.g. only patching index/post/payment but not 404) is a real leak.
- **Raw-CDN cache lies after force-push**: `curl raw.githubusercontent.com/...` serves a cached
  older blob for minutes after a force-push, so it can show the leaked value as "still present"
  when the repo is actually clean. Authoritative check = decode the API content endpoint:
  `curl -s "https://api.github.com/repos/OWNER/REPO/contents/<path>?ref=<branch>"` →
  base64-decode `content` field → count occurrences. Use that as the source of truth.
- **Re-run verification after the LAST edit, not before**: any edit made after the test run
  invalidates the "passed" status. If you touch files post-test, re-run `npm test` / the
  verification command and re-verify live before declaring done.
- **Retrieved tokens can be dead.** A `.env` token from a private/old repo or a "test
  account" key may be expired — `GET /user` with it returns `401 Bad credentials`. Verify
  liveness BEFORE any deploy/sync, and if it's dead, report honestly (never fabricate a
  successful push). See `github-no-gh-workflow` → "Token verification & API pitfalls".

## References
- `references/scan-patterns.md` — full secret/PII regex bank + false-positive filters used in real runs.
- `references/github-pages-sitefarm-sanitize.md` — concrete technique: private token purge via
  shallow-amend+force-push, third-party ad-ID scrubbing, and API-blob (not raw-CDN) live verify,
  from a real `website-automation` private→public port.
