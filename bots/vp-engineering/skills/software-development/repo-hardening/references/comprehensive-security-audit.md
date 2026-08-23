# Comprehensive Source-Level Security Audit — Playbook

A **five-layer methodology** for auditing a codebase's security posture, going far beyond `npm audit`.
Derived from a real audit of `itsPremkumar/Automated-Video-Generator` (TypeScript/Node, Express, Electron).

---

## When to use

- User says "run a comprehensive security audit", "check for vulnerabilities", or "find exposed secrets"
- You're doing a pre-launch or pre-deploy security pass
- You've been asked to review a repo's security before adopting / contributing to it

## Prerequisites

- A local clone (or the project is already on disk)
- `npm`, `git` available in PATH

---

## Layer A — Dependency vulnerability scan

```bash
npm audit --omit=dev --json | python -c "
import json,sys
d=json.load(sys.stdin)
v=d.get('vulnerabilities',{})
for name,info in v.items():
    sev=info.get('severity','unknown')
    titles=[x.get('title') for x in info.get('via',[]) if isinstance(x,dict)]
    direct='DIRECT' if info.get('isDirect') else 'transitive'
    fix='fix avail' if info.get('fixAvailable') else 'NO FIX'
    print(f'{sev.upper():>8}  {name}  [{direct}] [{fix}]')
    for t in titles: print(f'        - {t}')
"
```

### 0 vulns? Confirm with a second call
```bash
npm audit --audit-level=critical --json | python -c "import json,sys; d=json.load(sys.stdin); m=d['metadata']['vulnerabilities']; print(f'critical={m[\"critical\"]} high={m[\"high\"]} moderate={m[\"moderate\"]} low={m[\"low\"]} total={m[\"total\"]}'); sys.exit(0 if m['critical']==0 and m['high']==0 else 1)"
```

### When vulns exist → trace transitive deps
```bash
npm ls <offending-pkg>
grep -rn "<offending-pkg-symbol>" src/ --include='*.ts' --include='*.js'
```
If zero callers in source code, the dep is dead code → `npm uninstall <direct-parent>`.

---

## Layer B — Secret / credential scanning in source code

Run all four passes from the repo root:

### Pass 1 — Known API key formats
```bash
for PATTERN in \
  "sk-[a-zA-Z0-9]\{20,\}" \
  "AIza[0-9A-Za-z_-]\{35\}" \
  "AKIA[0-9A-Z]\{16\}" \
  "ghp_\|gho_\|ghu_\|ghs_\|ghr_" \
  "xox[baprs]-" \
  "pk\.\(live\|test\)_"; do
  grep -rn "$PATTERN" src/ bin/ scripts/ --include='*.ts' --include='*.js' \
    --include='*.mjs' --include='*.py' 2>/dev/null
done | grep -v node_modules | grep -v '\.test\.' | sort -u
```

### Pass 2 — Generic credential assignments
```bash
grep -rn -E \
  "(api[_-]?key|apikey|secret|token|password|passwd|credential)\s*[:=]\s*['\"][A-Za-z0-9_!@#$%^&*+=-]{8,}" \
  src/ bin/ scripts/ --include='*.ts' --include='*.js' --include='*.mjs' \
  --include='*.json' --include='*.yaml' --include='*.yml' 2>/dev/null \
  | grep -v node_modules | grep -v '\.test\.' | grep -v 'your_\|placeholder' | head -50
```

### Pass 3 — Private keys and connection strings
```bash
grep -rn -E "-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----" src/ bin/ scripts/ \
  --include='*.ts' --include='*.js' --include='*.pem' --include='*.key' 2>/dev/null

grep -rn -E "(redis|mongodb|mysql|postgresql|postgres)://[^/]+:([^@]+)@" src/ bin/ scripts/ \
  --include='*.ts' --include='*.js' --include='*.json' --include='*.yaml' 2>/dev/null \
  | grep -v node_modules
```

### Pass 4 — Hardcoded fallback / mock credentials
```bash
grep -rn "'mock-key'\|'test-key'\|'placeholder'\|'dummy'" src/ \
  --include='*.ts' --include='*.js' 2>/dev/null
```

### Evaluation
- **Real credential** in source → 🔴 CRITICAL. Rotate immediately. Remove from git history (BFG / `git filter-repo`).
- **Placeholder** (`your_*_here`, `mock-key`) → ⚠️ Acceptable if: (a) documented in a comment, (b) used only as a fallback when no env var is set, (c) doesn't enable auth bypass or privilege escalation.
- **Process.env reference** → ✅ Proper practice. Verify `.env` is in `.gitignore` and was never committed with real values.

---

## Layer C — Git history secret audit

### Was `.env` ever committed?
```bash
git log --all --oneline --diff-filter=A -- '.env' '.env.*' '.env*'
```

### Check the content of the first .env commit
```bash
COMMIT=$(git log --all --oneline --diff-filter=A -- '.env' | tail -1 | awk '{print $1}')
if [ -n "$COMMIT" ]; then
  git show "$COMMIT:.env" 2>/dev/null | grep -E "KEY|TOKEN|SECRET|PASSWORD" | grep -v "^#" | grep -v "your_\|placeholder"
fi
```

### Scan all commits for credential patterns
```bash
git log --all --full-history -p -S "PEXELS_API_KEY" -- . 2>/dev/null | grep -E "^\+\s*(export\s+)?" | grep -vi "your_\|placeholder" | head -20
# Repeat for GEMINI_API_KEY, PIXABAY_API_KEY, YOUTUBE_ACCESS_TOKEN, etc.
```

### Check the very first commit for anything worrisome
```bash
git log --all --reverse --oneline --diff-filter=A | head -1
git show $(git log --reverse --oneline | head -1 | awk '{print $1}') --stat 2>/dev/null | head -30
# Read the .env if it existed in that commit
```

---

## Layer D — Docker / container security review

```bash
cat Dockerfile 2>/dev/null || echo "No Dockerfile"
cat docker-compose.yml 2>/dev/null || echo "No docker-compose.yml"
cat .dockerignore 2>/dev/null || echo "No .dockerignore"
```

### Checklist

| Component | What to verify | Why |
|-----------|---------------|-----|
| **Base image** | Pinned release name + tag, e.g. `node:20-bookworm` not `node:latest` | `latest` breaks on rebuild; `alpine` has musl incompatibility with many native Node modules |
| **Non-root user** | `RUN useradd ... && USER appuser` before `CMD` | Default is root → container breakout = host root |
| **Healthcheck** | `HEALTHCHECK ... CMD` hitting a real app route | Without it, orchestrators can't tell if the app is alive |
| **Sensitive ENV** | No API keys in `ENV` instructions — use `--env-file` or runtime `-e` | ENV is baked into the image layer; anyone with image access sees them |
| **Volume mounts** | `./.env:/app/.env:ro` — note the `:ro` | Prevents the container from modifying host files |
| **COPY order** | `package.json` before source code | Layer caching — dep install only re-runs when deps change, not on every source edit |
| **.dockerignore** | Ignores `node_modules`, `.git`, `output/`, `.env*` | Prevents leaking host secrets and bloat into the build context |
| **Platform pin** | `platform: linux/amd64` in compose | Prevents Apple Silicon ELF mismatch for native binaries |

---

## Layer E — HTTP security headers / web middleware audit

```bash
# Find the Express app setup
grep -rn "res\.set\|res\.header\|app\.disable\|trust proxy" src/ --include='*.ts' --include='*.js' \
  2>/dev/null | head -30

# Find security middleware modules
find src/ -name '*security*' -o -name '*cors*' -o -name '*rate-limit*' -o -name '*local-only*' \
  -o -name '*net-safety*' -o -name '*capabilities*' 2>/dev/null
```

### Full header checklist

```bash
# One-liner to extract all res.set calls from the app setup
grep -A1 "res\.set(" src/app.ts 2>/dev/null || echo "No app.ts found"
```

| Header | Correct value | Risk if missing |
|--------|--------------|-----------------|
| `Content-Security-Policy` | Nonce-based: `default-src 'self'; script-src 'self' 'nonce-{nonce}'` | XSS — inline scripts run unrestricted |
| `X-Content-Type-Options` | `nosniff` | MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` | Clickjacking via `<iframe>` embedding |
| `Referrer-Policy` | `same-origin` | URL leakage across origins |
| `Permissions-Policy` | `camera=(), geolocation=(), microphone=()` | Feature abuse by embedded content |
| `Cross-Origin-Opener-Policy` | `same-origin` | Cross-origin opener isolation (Spectre) |
| `Cross-Origin-Resource-Policy` | `same-origin` | Cross-origin resource side-channel |
| `x-powered-by` | **Disabled**: `app.disable('x-powered-by')` | Server fingerprinting (informs attacker's playbook) |
| `Strict-Transport-Security` | Not needed if HTTP-only local app | But essential if served over HTTPS |

### Code architecture security patterns to check

Read these modules if they exist:

| Module | What to look for | What it defends against |
|--------|-----------------|------------------------|
| `net-safety.ts` / url safety | `isSafeUrl()` blocking private IPs (10.x, 172.16-31.x, 192.168.x, 169.254.x, 127.x, ::1, fc/fd/fe80) | SSRF — blocks internal network probing and cloud metadata exfiltration |
| `local-only.ts` (middleware) | `requireLocalAccess` handler checking `req.ip/socket.remoteAddress` for loopback | Admin endpoint abuse from the public internet |
| `security.ts` (operations) | `safeOutputPath()` rejecting `../` traversal, `redactSecrets()` scrubbing `key=value` from logs | Path traversal attacks, credential leakage in error output |
| `capabilities.ts` | `assertSafeMutationAllowed()` gating write operations behind `ALLOW_UNSAFE_MCP_TOOLS` | Accidental destructive operations from MCP clients |
| `rate-limit.ts` | `createMemoryRateLimiter()` on mutation routes | Brute-force / DoS on form submission endpoints |
| Any CSP header setup | `Content-Security-Policy` with nonces | XSS |
| CORS middleware | Origin allowlist, not `*` | Cross-origin data exfiltration |

---

## Full report template

```
## Security Audit Report — <project>

### npm Dependencies: 🟢 0 vulns
### Secrets in Source: 🟢 None found (or 🔴 N findings — see above)
### Git History: 🟢 Clean (or 🔴 secrets found in history — see Layer C)
### Docker: 🟢 Non-root user, healthcheck, pinned base image
### HTTP Headers: 🟢 CSP + COOP + CORP + XFO + Referrer-Policy all set

### ⚠️ Minor observations (not vulnerabilities)
- Observation 1: <what, why acceptable, what to watch for>
- Observation 2: ...

### Verdict
✅ Pass — no vulnerabilities found. Fixes required: 0.
(or)
🔴 N critical/high findings — see Layer <X> for remediation.
```
