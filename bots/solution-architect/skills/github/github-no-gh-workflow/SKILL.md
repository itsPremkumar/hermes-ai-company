---
name: github-no-gh-workflow
description: "Operate GitHub (create repos, push files, set default branch, update docs) on a host where `gh` CLI is absent and only a cached Git Credential Manager token exists. Drives the REST API directly from the Windows box."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [GitHub, Git, CredentialManager, Windows, REST-API, No-gh]
    related_skills: [github-repo-management, github-auth]
---

# GitHub — No-`gh` Workflow (cached GCM token + REST API)

Use this when `gh` is **not installed** and there is **no `GITHUB_TOKEN` env var** (this Windows box).
Auth is in the **Git Credential Manager** (Windows Credential Manager), retrievable via
`git credential fill`. You then drive the GitHub **REST API** with a Bearer token.

> Overlaps conceptually with the bundled `github-repo-management` skill (which prefers `gh` or a
> `GITHUB_TOKEN` env var). That one is protected and doesn't cover the GCM-token path, so this skill
> captures the box-specific recipe. Curator may consolidate later.

## When to use
- `command -v gh` is empty AND `echo $GITHUB_TOKEN` is empty.
- You need to create a repo, push a local dir, create/update a file (incl. under `docs/`), or set the
  default branch — all via API.

## Golden rule: extract the token IN-PROCESS
Never shell out to `git credential fill > cred.txt` and read the file in a *different* shell call.
The temp file may not persist across MSYS shell calls / path mismatches, and you'll silently get an
empty token → "Bad credentials". Extract it inside the **same Python process** that calls the API.

```python
import subprocess, re
out = subprocess.run(['git','credential','fill'],
                     input=b'protocol=https\nhost=github.com\n',
                     capture_output=True).stdout
TOKEN = re.search(rb'password=([^\r\n]+)', out).group(1).decode()
# ~40-char classic PAT; use as header:  Authorization: Bearer <TOKEN>
```

## Environment gotchas (this box)
- **Use `python`, not `python3`.** `python3` is absent (use `python` → 3.11).
- **`git init` makes branch `master`, not `main`.** `git push -u origin main` fails with
  `error: src refspec main does not match any`. Two clean fixes:
  - **Preferred:** push the current HEAD to `main` explicitly:
    `git push -u origin HEAD:main` (creates the `main` branch remotely), then the local branch
    tracks `origin/main`. Then set the default branch to `main` via API (below).
  - **Or:** push `master`, then `PATCH /repos/{owner}/{repo}` with `{"default_branch":"master"}`.
- **GitHub rejects any file >100 MB *in history* (not just the working tree).** A 250 MB demo
  video committed locally will make `git push` fail (or silently be rejected by GitHub's
  pre-receive hook). Fix BEFORE committing: compress the media so the largest blob is well under
  100 MB (target <10 MB for headroom). Use the bundled `imageio-ffmpeg` (no system ffmpeg needed):
  ```python
  import imageio_ffmpeg, subprocess, os
  ff = imageio_ffmpeg.get_ffmpeg_exe()   # installs a working ffmpeg binary on demand
  subprocess.run([ff,"-y","-i","Assets/video.mp4","-vf","scale=1280:-2",
                  "-c:v","libx264","-crf","30","-preset","medium",
                  "-c:a","aac","-b:a","96k","Assets/demo.mp4"])
  ```
  Then `git rm --cached Assets/video.mp4`, add `Assets/video.mp4` to `.gitignore`, commit only
  `demo.mp4`. See `references/github-100mb-limit.md` for the full recipe.
- The token is a secret: never print it, never commit `cred.txt`, delete temp copies after use.

## Core operations

### Create a repo
Drive the API from **Python `urllib`**, NOT inline `curl -d '{json}'`. On this box the MSYS
`curl` mangles inline JSON and returns `Problems parsing JSON` (HTTP 400) even when the JSON is valid.
```python
import json, urllib.request, subprocess
# token extracted IN-PROCESS (golden rule)
out = subprocess.run(['git','credential','fill'],
                     input=b'protocol=https\nhost=github.com\n', capture_output=True).stdout
TOKEN = out.split(b'password=')[1].split(b'\r\n')[0].decode()
payload = {"name":"pdf-chatbot","description":"...","private":False,"auto_init":False}
data = json.dumps(payload).encode()
req = urllib.request.Request("https://api.github.com/user/repos", data=data, method="POST")
req.add_header("Authorization", f"Bearer {TOKEN}")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req, timeout=25) as r:
    body = json.loads(r.read().decode())
print("created:", body.get("html_url"))
```
Use the same Python-urllib shape for `PATCH` (default branch), `GET` (verify), and `PUT` (Contents API).
Reserve `curl --data @-` (heredoc) only for the PR-creation case noted below.

### Create OR update a file (Contents API)
`PUT /repos/{owner}/{repo}/contents/{path}` with base64 content.
- **Create:** omit `sha`.
- **Update:** first `GET` the file, take its `sha`, then `PUT` with `sha` included.
- Works for any path incl. `docs/free-ai-providers.md` or a root `ZERO_INVESTMENT_SETUP.md`.
Reusable helper: `scripts/gh_put_file.py` (handles create-vs-update + base64 + Bearer auth).

### Clone + push a whole repo over HTTPS (embedded token)
When you need to modify many files (not one-off Contents API PUTs), clone with the token embedded,
commit, push, then scrub the token from the remote URL:
```bash
git clone -q "https://itsPremkumar:${TOKEN}@github.com/OWNER/REPO.git" localdir
# ...edit files, git add/commit...
cd localdir && git push origin "$(git rev-parse --abbrev-ref HEAD)"
git remote set-url origin "https://github.com/OWNER/REPO.git"   # remove token from stored URL
```
Pitfalls: (a) each repo may have a different default branch — use `git rev-parse --abbrev-ref HEAD`,
don't assume `main`/`master`; (b) don't hardcode a dir→repo name map wrong (e.g. `sp_oss`→`oss`);
resolve the real repo name explicitly before `set-url`.

### Create / open a Pull Request
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/{owner}/{repo}/pulls" \
  --data @- <<'PAYLOAD'
{"title":"...","head":"your-branch","base":"main","body":"..."}
PAYLOAD
```
**MSYS/curl gotcha — `--data @file` FAILS to read the file on this box.** Both
`--data @/tmp/pr_body.json` and `--data-binary @/path` error with
`curl: option --data: error encountered when reading a file`, even though the file
exists and `python -c "json.load(open(...))"` proves it's valid JSON. The MinGW curl
build cannot open the data-file path (space-in-username `/tmp` symlink resolution, or a
path-escaping quirk). **Workaround: pipe the JSON via stdin with `--data @-`** (above).
Heredoc + `--data @-` is the only form that reliably worked here. Do NOT write the body
to a file and point `@` at it.

To capture the response, redirect stdout: `... > /tmp/pr_resp.txt 2>&1`, then parse with
python (`json.load(open(r'C:/Users/PREM KUMAR/...pr_resp.txt'))`). Note a `pr_body.json`
written by `write_file` to `/tmp` resolves to `\\tmp\...` (outside the MSYS workspace) —
another reason to skip the file and use the heredoc.

### Set default branch
`PATCH /repos/{owner}/{repo}` with `{"default_branch":"master"}`.

### Verify a push
`GET /repos/{owner}/{repo}` → check `default_branch`, `size`, `html_url`.

## Pre-push safety gate (run BEFORE every `git push`)
This box has a `.env` with live provider keys and several agent/editor config files that
frequently embed secrets. Never push blind. Gate order:
1. **Secret scan** across staged + untracked source (no live values):
   ```bash
   git add -A --dry-run | sed 's/^add //' | while read f; do
     [ -f "$f" ] && grep -rIlE "sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{20,}|bearer |xox[baprs]-" "$f"
   done
   ```
   Also check config files individually: `openclaw.plugin.json`, `*.json`, `*.md`, and confirm any
   "api key"/"token" hits are descriptions only, not values.
2. **`.env` must be gitignored.** `git check-ignore .env` must print `.env`. If empty → DANGER, add
   `.env`/`.env.*` to `.gitignore` before committing. The Pexels key lives in `.env` here.
3. **Large-file guard:** nothing >~200 KB should be staged (downloads, models, media):
   ```bash
   git add -A --dry-run | sed 's/^add //' | while read f; do
     [ -f "$f" ] && sz=$(stat -c%s "$f") && [ "$sz" -gt 204800 ] && echo "BIG: $f"
   done
   ```
4. **Up-to-date check** so the push isn't rejected/divergent:
   `git fetch origin && git rev-list --left-right --count @{u}...HEAD` → expect `0 0`.
   (For Remotion/ffmpeg media repos, generated artifacts like `public/agentic-assets/*`,
   `agentic-pipeline/workspaces/*`, `.video-cache.json` must be in `.gitignore` or the push floods
   with junk. Verify with `git check-ignore` per pattern.)
5. **Group commits logically** (fix / feat / chore / docs) rather than one giant dump — easier to
   review and to `git revert` a bad class later.

## Token verification & API pitfalls (from real runs)
- **Dead tokens are common.** A token pulled from an old/private `.env` (or a "test account" key the user says is "for testing only") may be **expired/revoked**. Before any write, verify it's live:
  `curl -s https://api.github.com/user -H "Authorization: Bearer $TOKEN"` → `200` + `login`. A `401 Bad credentials` means it's dead — **report that honestly and do NOT fake a successful deploy/sync**. Re-prompt the user for a fresh PAT.
- **Contents API `PUT` needs the REAL default branch.** If you pass `branch:"main"` but the repo default is `master`, you get `{"message":"Branch main not found"}`. Resolve first:
  `curl -s .../repos/{owner}/{repo} | node -e "let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>console.log(JSON.parse(s).default_branch))"` — then set `branch` to that value. Same trap as `git push -u origin main` on a `master` repo.
- **Don't read a bash var inside `node -e` via `process.env` unless exported.** `PAT=$(git credential fill …)` is NOT exported, so `'Bearer '+process.env.PAT` is empty → `401`. Either `export PAT=…` first, or interpolate the shell value directly into the JS string: `'Authorization: Bearer '+'$PAT'`. Cleanest is still the golden rule — extract the token IN-PROCESS inside the same node/Python that calls the API.

## References
- `references/gcm-token-no-gh.md` — full annotated recipe + every gotcha from real use.
- `references/pre-push-safety.md` — pre-push secret/.env/large-file/up-to-date checklist (run BEFORE every push).
- `references/github-100mb-limit.md` — GitHub's 100 MB history limit + compress media with bundled imageio-ffmpeg.
- `scripts/gh_put_file.py` — put a local file into a repo via Contents API (create/update aware).
