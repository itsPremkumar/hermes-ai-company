# Cron Auth Recovery — stale cj.txt (401) → fresh session

The Paperclip REST API rejects a stale/expired session cookie with `{"error":"Unauthorized"}`
(HTTP 401). A cron job that blindly reuses `/c/one/paperclip-company/cj.txt` will silently
fail every call once that cookie expires. This is the single most common break for an
automated revenue-pulse / pipeline cron. Recovery is idempotent and cheap.

## Symptom
```
curl -s -b /c/one/paperclip-company/cj.txt ".../api/companies/<CID>/issues"
→ {"error":"Unauthorized"}   (HTTP 401)
```
Note: the cookie FILE may exist and look valid (Netscape format with a token). The token
itself is just expired. Don't trust file presence — trust the 401.

## Recovery (re-authenticate, then overwrite the project cookie file)
```bash
API="http://localhost:3100"
# 1) sign-in returns a fresh token; -c writes a fresh Netscape cookie jar
curl -s -c /c/one/paperclip-company/cj.txt \
  -X POST "$API/api/auth/sign-in/email" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3100" \
  -d '{"email":"prem@local.dev","password":"LocalDevPass123!"}'

# 2) verify the refreshed cookie actually works (HTTP 200, not 401)
curl -s -b /c/one/paperclip-company/cj.txt \
  "$API/api/companies/<CID>/issues" -o /tmp/issues.json -w "http=%{http_code}\n"
```
If step 2 prints `http=200`, the cron pass can continue. The refreshed `cj.txt` is now
good for subsequent runs too (with external PostgreSQL the session survives restarts — see
the skill's "Session cookie survival" section).

## Where the dev credentials live
`prem@local.dev` / `LocalDevPass123!` are the local-dev owner credentials, already present
in plaintext in `/c/one/paperclip-company/watchdog.py` (`EMAIL` / `PASSWORD` constants). The
watchdog re-authenticates on every cycle and writes its own jar to `watchdog-cj.txt` — but
that jar can ALSO go stale (verified this session: even `watchdog-cj.txt` returned 401 after
the cookie aged out). The reliable fix is an explicit `sign-in/email` re-auth, not trusting
either jar.

## Idempotent cron pattern (put this at the top of every cron pass)
```bash
API="http://localhost:3100"
CJ=/c/one/paperclip-company/cj.txt
# probe with current cookie; on 401, re-auth in place
code=$(curl -s -o /tmp/issues.json -w "%{http_code}" -b "$CJ" "$API/api/companies/<CID>/issues")
if [ "$code" != "200" ]; then
  curl -s -c "$CJ" -X POST "$API/api/auth/sign-in/email" \
    -H "Content-Type: application/json" -H "Origin: http://localhost:3100" \
    -d '{"email":"prem@local.dev","password":"LocalDevPass123!"}' >/dev/null
  code=$(curl -s -o /tmp/issues.json -w "%{http_code}" -b "$CJ" "$API/api/companies/<CID>/issues")
fi
# $code == 200 here, or abort the pass
```
This makes the cron self-healing: a stale cookie is detected and refreshed before any write
(PATCH/POST) is attempted, so you never silently lose a pipeline pass.

## Why not just use the Cookie header (TOKEN) approach?
The skill's MSYS pitfall recommends passing the raw token via `-H "Cookie: ..."` to dodge
`-b` path rewriting. That works for transient reads, but for a *cron that owns the cookie
file long-term*, re-authenticating and overwriting `cj.txt` is better: every other tool
(watchdog, browser, future passes) shares the refreshed jar. Use the TOKEN-header form only
for one-off command-line calls where you don't want to touch the file.

## Gotcha: domain prefix in the cookie file
After a fresh `-c` sign-in the Netscape jar may write the domain as `#HttpOnly_localhost`,
which curl skips (domain mismatch → 401 even with a valid token). If re-auth still 401s,
edit the file so the domain line reads just `localhost` (no `#HttpOnly_` prefix). The
`watchdog-cj.txt` format (`localhost`) is the correct shape.
