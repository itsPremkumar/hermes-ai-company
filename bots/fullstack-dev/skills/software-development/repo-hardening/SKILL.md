---
name: repo-hardening
description: Full improvement pass on a codebase — dependency vulnerability remediation (npm audit root-cause), dead-code removal, repo binary hygiene on Windows, fast integration tests, and README placeholder cleanup. Trigger when the user asks to "complete", "improve", "harden", "finish", or "clean up" a project, or wants a code review turned into concrete fixes.
---

# Repo Hardening — Full Improvement Pass

A repeatable playbook for taking a working-but-rough repo to a cleaner, safer, contributor-ready state. Derived from hardening `itsPremkumar/Automated-Video-Generator` (TypeScript/Node, Electron, Remotion video pipeline): took it from **29 npm vulnerabilities → 0** and **53 → 57 tests** with real binary dedup and README fixes.

## When to use
- "Complete / improve / harden / finish / clean up this project"
- "Review this repo and fix the issues"
- A user hands you a "production-grade autonomous loop" prompt that says
  `while(!ProductionReady)` — treat it as BOUNDED SWEEPS, not a literal infinite
  loop (see below).
- Pre-launch or pre-deploy hardening pass

## Bounded-sweep model (for "make it production-ready" autonomous prompts)
A prompt like "loop until production-ready, never stop" will OOM a 6 GB box and
stall on a flaky network if taken literally. Run it as **discrete, verified
sweeps** instead:
1. Pick ONE subsystem (correctness → error-handling → security → docker → CI →
   docs → testing). Do NOT rewrite everything at once.
2. Read the code, find REAL bugs (not assumed ones), fix the highest-impact with
   tests.
3. Gate: `npm run typecheck` = 0 errors AND `npm run test:unit` green.
4. Commit on a feature branch → merge to `main` → push (`gh`/git). Report what
   was verified vs blocked (network/Docker/RAM stated honestly — never fake a pass).
5. Stop the sweep when that subsystem has no remaining critical/high issues.
   Move to the next. Do not loop forever; the user reviews between sweeps.
This matches the user's standing preference: verify at green checkpoints,
commit+push each sweep, be honest about what the environment blocked.

## Verify review-claims BEFORE executing (a handed-over audit is not gospel)
When the user pastes a "review/audit/plan" produced by ANOTHER AI (or even a
prior session) and says "do all of this", do NOT blindly execute every item.
**Verify each claim against the actual code first** — treat the list as
HYPOTHESES, not facts. For each item: grep/read the cited file+line, confirm
the bug/issue actually exists, and mark it TRUE / FALSE before acting.

Concrete false claims seen in a real second-AI audit of this repo (all were
stated as real but were NOT):
- "504 TODO/FIXME debt markers" → `grep -rnE "TODO|FIXME" src/` returned **0**.
  Cancelled the item, did not fabricate cleanup.
- "Unreachable branch at orchestrate.ts:613" → it was a legitimate retry-loop
  fallback, not dead code. Skipped.
- "X1–X6 gate IDs retired" (in AGENTS.md) → `gate.ts` clearly still had X1–X6
  alive as the pre-render holistic gate. The doc was wrong; fixed the DOC, not
  the code.
- "~20 magic env vars" → actually 81; documented all categories.
- "diversityPenalty reserved-but-unused" → it was in the `ScoredCandidate`
  interface AND returned; removing it would break the shape. Skipped.

Disposition rule per item: TRUE+high-value → fix with tests; TRUE+risky
(refactor that could break the render path) → do the safe contained slice and
defer the rest with a reason; FALSE → **cancel/defer, document why**, never
fake a fix. This matches the user's standing bar: "distrusts unverified claims,
demands actual test/verify, not just announce."

## Honest deferral vs. fake-fix (the user explicitly values this)
The goal "complete the full list" means COMPLETE THE HONEST ITEMS, not force a
change for every line. When an item is:
- inaccurate (claim false, see above),
- a low-value/risky refactor whose blast radius (e.g. Remotion render
  components) isn't worth the destabilization this pass,
- an optional add-on that conflicts with a standing constraint (e.g. adds a
  runtime dep against the ZERO-COST rule),
→ mark it **cancelled** in the todo list with a one-line reason, and state it
explicitly in the final report. Do NOT leave it "pending" forever and do NOT
pretend it was done. A report that says "4 items honestly cancelled with
reasons, 0 fake fixes" is a SUCCESS, not a failure.

## Fail-closed verification (AI-dependent gates must not silently pass)
Any check that depends on an external AI/LLM backend (vision verify, content
moderation, subject match) MUST fail **closed**: when the backend is
unavailable, unparseable, or times out, the check returns `passes:false`
(confidence 0, reason "[FAIL-CLOSED] …"), NOT a silent `passes:true`. A
silent-pass lets off-topic/unsafe assets through whenever Ollama/Gemini is
down — the worst failure mode. Implement with a `failClosed` option (default
true); the best-effort (non-fail-closed) branch is only for explicitly
non-blocking checks. Reusable pattern: see
`references/avg-hardening-claims.md` (verifyFinalRender + unavailableResult).

## Bounded-wave execution for multi-item hardening lists
For a list of N items (Tier-1..Tier-N), execute in **contained waves**, not one
giant diff:
- Group by risk: safe/contained first (declare dep, unify util, wire redact,
  doc fixes), then feature (H7/M8), then refactors behind tests (H1/H2),
  then risky large refactors last.
- **Commit per logical group** on a feature branch → merge → push → confirm CI
  green. Never leave a big uncommitted pile across the session boundary.
- Re-run the full gate (`typecheck` + `lint` + `format:check` + `test:unit`)
  after EACH wave. One green wave at a time.
- Keep a single source-of-truth todo list; mark completed/cancelled honestly.

## The `verification_evidence` harness verdict is UNRELIABLE
When a tool returns a `verification_evidence: { status: "passed" }` block, it
can report "passed" EVEN WHEN the underlying command emitted errors (e.g.
typecheck showed 46 errors but the harness said passed). TRUST THE RAW COUNT:
`npm run typecheck 2>&1 | grep -c "error TS"` → 0 is pass, anything else is fail.
Same for tests: parse the real `# pass / # fail / # skipped` lines, not the
harness summary.

## Sequence (each step re-verifies the build)

### 0. Analyze before touching
- Prefer the **local working copy** if present (it may hold uncommitted fixes); otherwise `git clone --depth 1`.
- Inventory: file tree (`find . -not -path '*/node_modules/*'`), language breakdown (GitHub API `languages` or `tokei`), `package.json`, README, `git log`, bus-factor (distinct authors).
- Run existing test + typecheck suites FIRST to establish a green baseline.

### 1. Security — multi-layer audit (highest leverage)

A comprehensive security audit covers **five layers** — not just npm deps. Run all the commands below and cross-reference findings.

#### Layer A — Dependency vulnerability scan

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

- `npm audit fix` — clears the easy ones.
- For remaining criticals/highs marked "No fix available": they are almost always **transitive** inside a deprecated lib (e.g. `request` → SSRF). Find the ONE **direct** dependency pulling them in:
  `npm ls <offending-pkg>` and inspect the JSON above for `isDirect: true`.
- If that direct dep is **dead code** (verify with `grep -rn` — zero callers), remove it: drop from `package.json` + `npm uninstall`. Re-audit → often **0 vulnerabilities**.
- Bump top-level framework deps to latest minor (e.g. Remotion `^4.0.0` → `4.0.487`) in case transitive versions improved.
- **Re-verify**: `npm run typecheck` AND full `npm run test:unit` must stay green.

#### Layer B — Secret / credential scanning in source code

Scan for hardcoded API keys, tokens, passwords, private keys, and connection strings. Use multiple regex passes for depth:

```bash
# API keys + tokens (OpenAI, Google, AWS, GitHub, Stripe, Slack)
grep -rn \
  -e "sk-[a-zA-Z0-9]\{20,\}" \
  -e "AIza[0-9A-Za-z_-]\{35\}" \
  -e "AKIA[0-9A-Z]\{16\}" \
  -e "ghp_\|gho_\|ghu_\|ghs_\|ghr_" \
  -e "xox[baprs]-" \
  -e "pk\.\(live\|test\)_" \
  src/ bin/ scripts/ --include='*.ts' --include='*.js' --include='*.mjs' \
  2>/dev/null | grep -v node_modules | grep -v '\.test\.' | head -50

# Password / secret / generic credential patterns
grep -rn \
  -e "\(api[_-]?key\|apikey\|secret\|token\|password\|passwd\|credential\)\s*[:=]\s*['\"][A-Za-z0-9_]\{8,\}" \
  -e "-----BEGIN.*PRIVATE KEY-----" \
  -e "redis://.*@" \
  -e "mongodb.*://.*:.*@" \
  src/ bin/ scripts/ --include='*.ts' --include='*.js' --include='*.mjs' \
  --include='*.json' --include='*.yaml' --include='*.yml' \
  2>/dev/null | grep -v node_modules | grep -v '\.test\.' | head -50

# Hardcoded fallback values that look like credentials
grep -rn "'mock-key'\|'test-key'\|'placeholder'" src/ \
  --include='*.ts' --include='*.js' 2>/dev/null | head -10
```

**Evaluation rubric:**
- **Real credential in source** → 🔴 CRITICAL — rotate immediately, remove from history (BFG/filter-repo).
- **Placeholder value** (`your_*_here`, `mock-key`) → ✅ acceptable if fallback is documented and doesn't enable auth bypass.
- **Process.env reference** → ✅ proper practice — verify the actual `.env` file is in `.gitignore` and was never committed.

#### Layer C — Git history secret audit

Check whether credentials were ever committed (even if later removed):

```bash
# Was .env ever committed?
git log --all --oneline --diff-filter=A -- '.env' '.env.*'

# Scan all commits for credential patterns
git log --all --full-history -p -S "PEXELS_API_KEY\|GEMINI_API_KEY\|ghp_" \
  -- . 2>/dev/null | grep -E "^\+\s*(export\s+)?" | grep -vi "your_\|placeholder" | head -20

# Check the first commit for any secrets
git log --all --oneline --diff-filter=A --diff-filter=A -- '**/.env*' '**/*.secret*'
```

**What's okay:**
- Initial commit only had `.env` with placeholder values (`your_pexels_api_key_here`)
- `.env` was added to `.gitignore` before real credentials were ever stored

**What's not okay:**
- Real API keys anywhere in git history → redact with `git filter-repo` or `bfg --replace-text` immediately
- `.env` NOT in `.gitignore` before real credentials were added

#### Layer D — Docker / container security review

```bash
# Check image for: non-root user, healthcheck, env var leakage, base image
cat Dockerfile
```

Checklist:
| Check | What to look for |
|-------|-----------------|
| **Non-root user** | `RUN useradd ... && USER appuser` — without this the container runs as root |
| **Healthcheck** | `HEALTHCHECK ... CMD` — should hit a real route, not just `curl localhost` |
| **Base image** | Prefer pinned release (e.g. `node:20-bookworm`) over `latest` or `alpine` (musl breaks native modules) |
| **Sensitive env vars** | Are API keys baked into `ENV` instructions instead of runtime `--env-file`? |
| **Host volume mounts** | In `docker-compose.yml`, bind mounts like `./.env:/app/.env:ro` — the `:ro` flag prevents container modifications to host files |
| **Platform pin** | `platform: linux/amd64` avoids Apple-Silicon ELF mismatches for native binaries |

#### Layer E — HTTP security headers / web middleware audit

Scan the Express/HTTP app setup for security headers:

```bash
grep -n "res\.set\|res\.header\|app\.disable\|trust proxy\|helmet" src/app.ts src/middleware/ 2>/dev/null
```

Checklist of modern headers (benchmark is OWASP Secure Headers Project):
| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | Nonce-based script-src, `'self'` defaults | Blocks XSS and inline injection |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type confusion |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Referrer-Policy` | `same-origin` or `strict-origin-when-cross-origin` | Prevents referer leakage |
| `Permissions-Policy` | Restrict camera/geo/mic to `()` | Opt-in feature permissions |
| `Cross-Origin-Opener-Policy` | `same-origin` | COOP isolation (Spectre mitigation) |
| `Cross-Origin-Resource-Policy` | `same-origin` | CORP isolation |
| `Strict-Transport-Security` | `max-age=31536000` | HSTS (only if served over HTTPS) |
| `X-Powered-By` | Disabled (`app.disable('x-powered-by')`) | Prevents server fingerprinting |
| `X-XSS-Protection` | `0` | Disables the legacy XSS auditor (modern CSP replaces it) |

Also check for:
- **CORS origin allowlisting** — app should have an explicit origin whitelist or loopback-only, not `Access-Control-Allow-Origin: *`
- **Rate limiting** on mutation endpoints (`POST`, `PUT`, `DELETE`)
- **Body size limit** — `express.json({ limit: '32kb' })` prevents oversized payload attacks
- **Input validation** — schema-based (Zod, Joi) on all API inputs
- **SSRF protection** — URL fetch guard blocking private IPs, cloud metadata endpoints (`169.254.169.254`), and loopback
- **Path traversal guard** — output path validation that blocks `../` escapes
- **Log redaction** — functions that scrub `key=value` secret patterns from crash/log output
- **Local-only admin** — admin/mutation endpoints restricted to loopback, with an `ALLOW_UNSAFE_*` opt-out flag for development

**Code architecture** — read `src/lib/net-safety.ts`, `src/middleware/local-only.ts`, and any `security.ts` / `capabilities.ts` modules. These are the places where defense-in-depth lives. A project with SSRF guards + path traversal checks + CSP nonces + secret redaction + local-only admin is already ahead of 90% of open-source projects this size.

No single finding is a vulnerability on its own — but a project that lacks ALL of these should be flagged for a security hardening pass.

#### Layer F — GitHub CodeQL alert remediation (taint-aware, not cosmetic)

When `gh` shows CodeQL `js/*` alerts (log-injection, request-forgery, http/file-access, path-injection, loop-bound-injection, polynomial-redos, file-system-race), fix them with **taint-aware sanitization at the sink** — CodeQL's dataflow engine only "sees" a sanitizer if it is a recognized pattern applied directly to the tainted value at the point it reaches the dangerous sink. Wrappers and helpers are NOT trusted.

- **`js/log-injection` / `js/incomplete-sanitization`** — strip newlines AT the sink with the literal regex `/[\r\n]/g`. A custom `safeLog(s)` wrapper function is NOT recognized; a broader control-char class like `/[\x00-\x1F\x7F]/g` is flagged as `incomplete-sanitization`. The narrow `[\r\n]` pattern is the one CodeQL accepts. NOTE the conflict: ESLint's `no-control-regex` rule flags `/[\r\n]/g` as an error (CI lint fails). Resolve by adding `/* eslint-disable no-control-regex -- intentional log sanitization */` at the top of the file (the rule only inspects regex *literals*, not `new RegExp` strings). See `references/codeql-sanitizer-patterns.md`.
- **`js/request-forgery` / `js/http-to-file-access` / `js/file-access-to-http`** — validate the URL with a recognized scheme+host guard at the sink BEFORE the request (e.g. the existing `isSafeUrl()` SSRF guard: scheme allow-list + block private/loopback/cloud-metadata `169.254.169.254`). Custom boolean guards are sometimes untrusted by CodeQL — keep the check as close to the `axios.get`/`fetch` call as possible.
- **`js/path-injection`** — reject NUL + `..` AND `path.resolve` + assert the resolved path stays inside an allowed root (confinement is the recognized fix).
- **`js/file-system-race`** — open the fd first, then `fstat` it (kills the stat→open TOCTOU). Don't `existsSync` then `writeFileSync` with a check-then-write window.
- **`js/polynomial-redos`** — replace nested `.*?` across a line with a bounded class (e.g. `[^\]]*`).
- **`js/loop-bound-injection`** — cap a loop bounded by external input (e.g. hash the first N chars).
- **`js/unused-local-variable`** is NOISY (false-positive-prone) and is NOT the CI gate (ESLint's `no-unused-vars` is — and `--quiet` showed 0 errors here). Before deleting a "unused" symbol CodeQL flags: grep it; if it appears more than once (declaration + a real use), it is genuinely used — deleting it breaks the build. CodeQL's heuristic misses cross-file / dynamic usage. Only delete symbols confirmed unused by `grep` + a full `tsc --noEmit`.

**CI reality:** a CodeQL "success" run means the *workflow ran*, NOT that alerts are zero. Alerts only block merge if branch protection requires the CodeQL check to pass. Treat a re-scan after push as the source of truth — the alert count updates only after the new scan completes.

#### Full report format

After all five layers, produce a summary:

```
## Security Audit Report — <project>

### npm Dependencies: 🟢 0 vulns
### Secrets in Source: 🟢 None found
### Git History: 🟢 Clean
### Docker: 🟢 Non-root user, healthcheck, pinned base
### HTTP Headers: 🟢 CSP + COOP + CORP + XFO + Referrer-Policy all set

### ⚠️ Minor observations (not vulnerabilities)
- <finding>: <why it's acceptable or what to watch>
```

### 2. Dead-code removal sequence (when dropping a dep/feature)
Remove ALL of these or typecheck cascades:
- function/definition bodies
- every caller site
- type-union string literals (e.g. `'gtts-fallback'`)
- the `import` line (and any now-unused imports)
- stale doc-comment references
Then re-run typecheck — partial edits leave errors like `}/` → `};`, a lost `return {` brace, or leftover caller refs.

### 3. Repo binary hygiene
- Find byte-identical duplicates: `md5sum file1 file2 file3` — identical hashes = redundant copies.
- **On Windows/MSYS, git symlinks are disabled** (`git config core.symlinks` → `false`) and a static server (e.g. Express `express.static('public')`) cannot reach `../assets`. So:
  - Prefer **gitignoring regenerable build artifacts** over symlinks.
  - A file served from `public/` MUST stay in `public/`; a build artifact regenerated by a script (e.g. `tray-icon.png`, `icon.ico` from a `create-icons` script) can be `git rm --cached` + added to `.gitignore`. Verify the generator still works: `node scripts/create-icons.cjs assets/logo-automation.png`.

### 4. Test coverage — fast integration smoke test
- A true end-to-end render needs ffmpeg + Remotion + network → too heavy/flaky for CI.
- Add a **deterministic integration test** exercising real pipeline pieces without rendering: script parsing (with `[Visual:]` director tags), input-validation guards, workspace creation, id sanitization. Use `node:test` + `tsx --test`.
- Mirror existing `*.test.ts` style (dependency injection / mocks where the real path needs external services).

### 5. Docs — kill placeholder comments
- `grep -n "PLACEHOLDER" README.md`. Replace with **real existing assets** (verify via `ls` first); don't reference files that don't exist (e.g. a missing `hero-banner.png`).
### 6. Build new features as isolated sub-modules, verify, THEN merge

When the user wants a brand-new capability added without destabilizing the repo
(e.g. "build it in a separate folder, verify it works, then connect to main"):
- Create a sibling folder with its **own package.json + tsconfig** + offline
  test suite. Keep the heavy SDK (e.g. `googleapis`) as a **lazy `await import`**
  so dry-run/sandbox modes need zero external deps and are fully verifiable.
- **Lazy-import from the package root** (`import('googleapis')`), never a deep
  internal path (`googleapis/build/src/...`) — the deep path breaks `tsc`
  (TS2307) even though tsx runs it.
- Document an explicit merge plan in the sub-module README (target paths, env
  flag, route guard) so wiring in later is mechanical.
- See `references/isolated-module-build.md` for the full recipe + the
  `buildAuthUrl` async-signature repair and MSYS `/tmp` gotcha.

#### Backward-compatible shim pattern (for replacing existing functionality)

When a new module REPLACES the logic of an existing one (e.g. a new music system
replaces an old `free-music.ts`), **never modify the old code**. Apply the
shim pattern:

1. **Build the new module standalone** in its own directory with its own
   interface (e.g. `src/music-system/` with `MusicEngine` class).
2. **Zero changes to old code.** The old file stays exactly as-is — every
   existing caller continues compiling and running without any edits.
3. **Rewrite the old file as a backward-compatible shim** — its public API
   (exported function signatures, types, class names) stays IDENTICAL, but the
   implementation delegates to the new module internally. Use an internal
   singleton of the new engine so initialization happens once.
4. **All existing callers import unchanged.** They see the same exports with
   the same types — only the implementation behind the scenes switched to the
   new architecture.
5. **Test both paths:** the old callers (via the shim) AND standalone usage
   of the new module. Typecheck must pass with zero errors.

Example structure from a real migration:
```
src/
  lib/free-music.ts          ← WAS: original implementation (rewritten as shim)
                                 NOW: delegates to MusicEngine internally
  music-system/              ← NEW: standalone module
    index.ts                 ← new public API (MusicEngine, etc.)
    types.ts
    engine.ts
    providers/
      registry.ts
      ccmixter.ts
      procedural.ts
      ...
```

This pattern satisfies the user's strong standing preference: **never delete or
modify old code**, build alongside it, and ensure every call site keeps working
without changes.

#### Provider registry pattern (for extensible system architecture)

When a module needs to support multiple interchangeable backends, use the
registry pattern:

1. Define a **Provider interface** (e.g. `MusicProvider` with `search()` +
   `download()` methods).
2. Create a **Registry singleton** that stores provider instances keyed by name
   and sorted by priority.
3. Each provider is its own file implementing the interface.
4. A **registration function** (`registerDefaultProviders()`) instantiates and
   registers all built-in providers in priority order.
5. The **Engine class** delegates to the registry — it queries ALL providers in
   parallel, selects the best result (highest priority with results), and
   processes it.
6. External code can register custom providers at runtime without touching
   built-in code.

See `references/provider-registry-pattern.md` for the full example with the
music-system architecture this pattern was proved against.

## Post-edit verification gate (mandatory on this host)
After ANY code-edit batch, the agent is re-prompted for "fresh passing
verification evidence". Satisfy it with real commands, don't assert success:
- Re-run the test suite + typecheck that were green at baseline.
- Partial edits from dep/feature removal commonly leave: `}/` -> `};`
  brace breakage, a lost `return {` in a removed branch, or leftover caller
  refs. `tsc` surfaces these precisely — fix, re-run, confirm clean.
- When you change a method signature (e.g. `: string` -> `: Promise<string>`),
  grep ALL call sites (unit test, CLI, live branch) and update each, or the
  build breaks at runtime, not at typecheck-of-the-definition.

## Pitfalls

- **`read_file` can render backtick template literals misleadingly.** When a line contains `` `Bearer ${apiKey}` ``, `read_file` may render the backticks as `***` in the displayed output — e.g. `Authorization: *** ${apiKey}`. This looks like broken code (a literal `***` in the authorization header) but is actually correct. **Always verify suspicious lines with `xxd`** via terminal: `sed -n 'LINEp' src/file.ts | xxd | head -5`. The hex dump shows the real characters — `` 60 `` (backtick), not `*`. This is a display artifact, not a code defect.
- **Patch tool Windows path doubling** (this host): `patch`/`write_file` mis-resolve MSYS paths `/c/one/...` to `C:\c\one\...` and error `OUTSIDE the active workspace`. **Fix: pass native Windows paths (`C:\one\...`) to patch/write_file on this Windows/MSYS machine.** Terminal/bash commands may still use `/c/one/...`.
- `npm audit fix` alone almost never clears transitive criticals — the win is removing the single direct dep that drags them in.
- Don't `git commit` for the user; leave edits unstaged so they can review.
- **"Lint" CI job is NOT just eslint.** It usually also runs `prettier --check` (`npm run format:check`). Getting `eslint` to 0 errors leaves the job RED if files aren't prettier-formatted. **Always verify with BOTH `npm run lint` AND `npm run format:check`**; if format fails, run `npm run format` (prettier --write, whitespace-only, safe) and commit. A repo can sit red on every push purely from unformatted files while eslint is clean — that's a pre-existing break, fix by formatting.
- **Diagnosing a CI failure with no `gh` and no token:** see `references/ci-failure-no-token.md` — unauthenticated REST calls to list which jobs failed (job names + conclusions). You can't fetch the raw error text without a PAT; ask the user to paste it or supply `actions:read`.

- **Testing fs-guarded functions (closures/CLI wrappers):** when a function early-returns `{ok:false}` on `!fs.existsSync(input)` and you want to unit-test its LOGIC with an injected mock runner, create a real temp file (`fs.writeFileSync(os.tmpdir()+'/x.tmp', Buffer.from([0]))`) so the guard passes, then let the injected mock drive the logic. Without the real file the test only ever exercises the guard branch. Also: pure helpers (e.g. parse a probe/JSON blob) belong in their own exported function so they're testable without the binary at all. Repo test runner is `node --test` via `tsx --test` — NOT jest; use `import { test, describe } from 'node:test'` + `node:assert/strict`.

- **`ctx.skip()` in node:test does NOT stop execution.** On Node 20/22 the implementation does NOT throw — the test body continues. `ctx.skip()` followed by `return;` (or `throw new Error(...)` — node:test treats the skip as authoritative and ignores subsequent errors) is the safe pattern: `ctx.skip('reason'); return;`. Do NOT rely on an implicit throw.

- `references/isolated-module-build.md` for the full isolated-sub-module
  recipe (lazy SDK import, async-signature repair, MSYS /tmp gotcha, merge plan).
- `references/codeql-sanitizer-patterns.md` — verified before/after recipes that
  actually clear CodeQL `js/*` alerts (log-injection sink pattern, SSRF guard,
  path-injection confinement, TOCTOU fix, redos, unused-var false-positives).

### 7. CI reliability — network-flaky test guard pattern

External-provider tests (Wikimedia, Archive.org, NASA, MetMuseum) that timeout
(~52s) when the API is unreachable break CI spuriously. Pattern with
double-layer defense:

```ts
const axios = require('axios');
async function skipIfUnreachable(url: string, ctx: any, timeoutMs = 3000): Promise<void> {
    // CI environments often block/rate-limit external hosts — skip proactively
    if (process.env.CI === 'true') {
        ctx.skip(`CI env: skipping test for ${url}`);
        return; // ctx.skip() does NOT stop execution — must return/throw
    }
    try {
        await axios.head(url, { timeout: timeoutMs });
    } catch {
        ctx.skip(`host unreachable: ${url}`);
        return;
    }
}

test('MyProvider returns results', async (t) => {
    await skipIfUnreachable('https://the-api-host.com', t);
    const results = await provider.search(...);
});
```

- The 3s HEAD probe is fast enough that skipped tests add negligible time.
- The CI guard prevents the HEAD-success/GET-timeout failure pattern
  (archive.org specific).
- `ctx.skip()` does NOT internally throw — always return or throw after it.
- Use a **separate** `skipIfUnreachable` call per distinct API host.

See `references/network-flaky-test-guard.md` for full pattern + CI env guard
details.

### 8. Windows ENAMETOOLONG — arg-length limit mitigation

On Windows `child_process.spawn` rejects with `ENAMETOOLONG` when a single
command-line argument exceeds ~8KB. In ffmpeg pipelines this is hit when
**word-level caption segments** generate one `drawtext` filter per word →
15 words × 200 chars each × 7 scenes = 21K chars in one `-filter_complex` arg.

**Fixes:**
1. **Merge word-level caption segments into line-level** (group consecutive
   words into ≤7-word lines). Drops drawtext filter count from ~105 to ~14.
2. **Default to segmented rendering** (per-scene small ffmpeg subprocesses).
   Provides per-segment retry isolation in addition to arg-length safety.
3. For single-pass path: use `-filter_complex_script` if the ffmpeg build
   supports it (most ffmpeg-static Windows builds do NOT).

### 9. Placeholder-as-unset — graceful opt-out for disposable config values

When a repo `.env` ships a placeholder (e.g.
`VOICEBOX_PROFILE_ID=<your-voicebox-profile-id-here>`), a naive
`if (process.env.VOICEBOX_PROFILE_ID)` treats it as "configured" and blocks
for 40s+ retries. **Pattern:** check for the placeholder string:

```ts
const raw = process.env.VOICEBOX_PROFILE_ID;
if (!raw || raw.includes('your-voicebox-profile-id')) {
    return false;  // not configured — skip silently
}
```

Apply at TWO layers: service gateway (prevent spawn) + consumer (fast fallback).

### 10. Systematic multi-issue fix campaign (fix-all-bugs mode)

When the user says "fix all the bugs one by one and verify everything", run a
**multi-dimensional audit → prioritized fix → per-step verify** campaign:

#### Phase 1: Multi-dimension audit (before touching code)

Search ALL of these dimensions across `src/` (excluding `node_modules`):

```bash
# 1. Explicit bug markers
grep -rn "FIXME\|TODO\|BUG\|HACK\|WORKAROUND" src/ --include='*.ts' | grep -v node_modules
grep -rn "console.log" src/ --include='*.ts' | grep -v node_modules | grep -v '.test.'
grep -rn "console.error\|console.warn" src/ --include='*.ts' | grep -v node_modules | grep -v '.test.'

# 2. Type-safety escapes
grep -rn "@ts-ignore\|@ts-expect-error" src/ --include='*.ts' | grep -v node_modules
grep -rn "eslint-disable\|eslint-disable-next-line" src/ --include='*.ts' | grep -v node_modules

# 3. Loose typing
grep -rn ": any" src/ --include='*.ts' | grep -v node_modules | grep -v '.d.ts' | grep -v '.test.'
grep -rn "as any" src/ --include='*.ts' | grep -v node_modules | grep -v '.d.ts'

# 4. Known gate/check failures (from test output)
# e.g. X10 black frames, broken provider 404s, timing issues

# 5. Dead / unused test infrastructure
find . -name '*.test.ts' 2>/dev/null | sort
# If zero test files exist, note it as a priority item
```

#### Phase 2: Priority-ordered fix queue

Rank by **impact on every run** (Tier 1) → **offline reliability** (Tier 2) →
**quality/warnings** (Tier 3) → **documentation/cosmetic** (Tier 4):

| Tier | Example Items | Verification Gate |
|------|--------------|------------------|
| 1 – Production impact | Broken providers (404 on every request), missing offline fallbacks, pipeline failures | Full pipeline test |
| 2 – Reliability | No tests, cache bloat, timeout bugs, silent fallbacks | `npm run test:unit` + typecheck |
| 3 – Quality warnings | Gate X failures (black frames, aspect ratio), procedural fallback quality | Typecheck + subjective |
| 4 – Docs / config | Stale `.env.example`, placeholder keys, missing comments | Review |

#### Phase 3: One-by-one execution (never batch commits)

For each item in the queue:
1. **Understand the root cause** — read the file, trace the data flow, identify
   the exact line / function / API call that's wrong.
2. **Fix with minimal change** — never rewrite the module. Targeted patch.
3. **Verify with real commands:**
   ```bash
   npm run typecheck --noEmit     # must be 0 errors
   npm run test:unit              # failing tests must DECREASE (or stay same for network reasons)
   ```
4. **Verify the specific fix:**
   - For a provider fix: run a one-off test that exercises that provider
   - For a pipeline fix: run the full pipeline and verify the output
5. **Commit with descriptive message** — mention the tier and what changed.
6. **Re-run typecheck + tests** after each commit to confirm nothing regressed.

#### Phase 4: Final verification

At campaign end:
- `npm run typecheck` → 0 errors
- `npm run test:unit` → same or fewer failures than baseline
- All committed on `main`, ready for user approval

#### Pitfalls

- **Never treat `verify_evidence` harness output as gospel.** It can report
  "passed" when the command had errors. Always parse raw output:
  `tsc output | grep -c "error TS"` → 0 = pass.
- **Test count may increase** (adding new tests) but failures must not increase
  from the baseline (except pre-existing network-dependent failures).
- **Don't fix source-code `any` when eslint disables the rule.** Check
  `.eslintrc.json` — if `@typescript-eslint/no-explicit-any: "off"`, fixing
  `any` improves type safety but doesn't change lint results and can break
  compilation. Only touch `any` when `noImplicitAny: true` in tsconfig.
- **Don't conflate "audit found N items" with "all N must be fixed."**
  Legacy modules (`src/legacy/`) often have 80%+ of the `any`/`@ts-ignore`
  annotations. Fixing them is high-risk low-return — defer or cancel with
  a note, don't fabricate fixes.
- **A provider whose upstream deleted all assets cannot be "fixed."**
  Check the upstream repo before debugging — `git clone --depth 1` or
  GitHub API count of relevant files. If 0 audio files for an audio provider,
  remove it from registry and document the reason, don't hunt for a
  non-existent fix.
- **When changing output format (e.g. WAV → MP3), the processing pipeline's
  intermediate steps may force a codec** (`-c:a pcm_s16le`). Check every
  processing step (trim, fade, normalize, loop) and update all codec args
  that hardcode the intermediate format.
- **When adding an auto-trim for X10 gate failures** (black frame detection),
  the fix belongs at the DOWNLOAD stage (trim source clips) not at the gate
  (which is read-only). But verify the trim doesn't break downstream
  duration-sensitive operations.

### 11. Parallel subagent debugging for CI-only failures

For CI-only test failures (e.g. 1 of 411 tests failing), dispatch **multiple
parallel subagents** via `delegate_task`:

| Subagent | Goal | Tools |
|---|---|---|
| CI log investigator | `gh run view --log` to extract test name + error message | `gh` CLI |
| Local CI simulator | Run suite with `env -u` to strip local env vars, try `CI=true` | terminal |
| Targeted fix | Apply the fix based on findings | read_file, patch, terminal |

Practical workflow from a real CI-only failure (archive.org 30s timeout):
1. Subagent A extracted the failing test name + timeout error from CI logs
2. Subagent B confirmed with `CI=true` the failure disappears (399 pass, 0 fail)
3. The fix: `skipIfUnreachable` now includes `process.env.CI === 'true'` guard
4. All three ran in parallel, completing in ~52s + 39min (the batch-10 video
   sweep ran concurrently)

Bounded by `delegation.max_concurrent_children` (default 3 on this host).
When the pool is at capacity subsequent delegations run synchronously and
return inline.

Also useful for: reproducing flaky CI failures, running batch verification
sweeps (e.g. 10-video generation) in parallel with test investigation.

## References
- `references/windows-audit-workflow.md` — exact command chain + the patch-path pitfall transcript + git-symlink note.
- `references/avg-hardening-claims.md` — verify handed-over audit claims (false-claim table), fail-closed AI verification pattern, ffmpeg-runner consolidation, bounded-wave execution log. Pairs with `remotion-ffmpeg-video`'s `avg-production-sweeps.md`.
