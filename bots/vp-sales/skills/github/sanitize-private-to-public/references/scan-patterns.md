# Secret / PII scan pattern bank

Patterns proven in real private→public porting runs. Combine into one `grep -rniE '...'`.

## Secret token/key patterns
```
api[_-]?key
secret
token
password|passwd
bearer
private[_-]?key
client_secret
service.?account
AIza[0-9A-Za-z_-]{20,}        # Google / Firebase API key
sk-[A-Za-z0-9]{20,}           # OpenAI-style
ghp_[A-Za-z0-9]{20,}          # GitHub PAT
vca_[A-Za-z0-9]{8,}           # Vercel MCP access token
vcr_[A-Za-z0-9]{8,}           # Vercel refresh token
prj_[A-Za-z0-9]{10,}          # Vercel project id
team_[A-Za-z0-9]{10,}
-----BEGIN                     # PEM/private key block
```

## PII / account-linkage patterns (genericize, not necessarily "secret")
```
<user-email>                   # e.g. someone@gmail.com
<phone-digits>                 # e.g. 93455 / +91...
<real-name>
C:/one|C:\\one                 # private local paths
/c/one
<real-team-slug>               # e.g. prems-projects-27978e99
<project-id>
```

## False-positive filters (these are SAFE to keep — don't redact)
Append to the grep to drop documentation-of-format matches:
```
| grep -v 'starts with'                       # "token starts with vca_"
| grep -vE '=dummy|=your_|=YOUR_|REDACTED'    # placeholders
| grep -v '.env.example'                      # example env files (placeholders)
```

## Sanitization replacements that came up
- `C:/one/sproutern` → `/path/to/your/sproutern`
- Vercel team slug `prems-projects-27978e99` → `YOUR_TEAM_SLUG`
- Firebase web config values → `your_firebase_*` placeholders
- Service-account JSON → `{"type":"service_account", "...": "REDACTED"}` in docs; real file git-ignored

## Never-copy file set (exclude at STAGE, verify blocked by .gitignore)
```
.env  .env.local  .env*  .firebaserc  .mcp.json
service-account*.json  *-adminsdk*.json  *.pem  *.key  credentials*
```

## Live-verification (post-push)
```bash
# BRANCH differs per repo — resolve it, don't assume main
curl -s "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/FILE" \
  | grep -niE '<secret+PII patterns>' | grep -v 'starts with'
# empty output = clean live
```
