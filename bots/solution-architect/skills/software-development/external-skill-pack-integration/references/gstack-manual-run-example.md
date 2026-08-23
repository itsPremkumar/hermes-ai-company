# gstack Manual Run Example — `/cso` + `/health` on Automated-Video-Generator

Verified, real execution (2026-07-16) proving the "reference library" integration
strategy (Pitfall 2) actually produces findings. Use this as the template for auditing
any of our repos when gstack skills are read as methodology, not loaded as skills.

## Target
- Repo: `C:\one\Automated-Video-Generator` (Remotion + Edge-TTS + stock media, TS/Node, MIT)
- Version: v5.0.0
- Tooling present: node v22.23.1, bun 1.3.9, npm 10.9.8

## `/health` equivalent (code-quality dashboard)
Ran native equivalents of gstack's `/health` skill:

```bash
cd /c/one/Automated-Video-Generator
npm run typecheck      # tsc -p tsconfig.json --noEmit  → EXIT 0, 0 errors
npm run lint           # eslint                          → 59 errors, 618 warnings
npm run test:unit      # node test runner               → 168 pass / 0 fail / 1 skipped (of 169)
npm audit --omit=dev   # dependency audit               → 0 vulnerabilities
```

Key reads:
- Typecheck: GREEN.
- Tests: GREEN (an earlier "1 fail" was a flaky/transient run; re-run fully green).
- Lint: 56 of 59 "errors" are ESLint *Parsing* errors (config/parser setup issue, not
  code bugs) + `prefer-nullish-coalescing` + unused-var warnings (e.g. `escapeHtml`
  imported-but-unused in `job-status.view.ts`). The lint GATE is red — blocks clean CI.
- Deps: 0 vulns.

## `/cso` equivalent (OWASP Top 10 + STRIDE)
Ran native equivalents of gstack's `/cso` skill (secrets archaeology → supply chain →
code patterns → MCP/web surface):

```bash
# 1. Secrets archaeology
grep -rniE "(api[_-]?key|secret|token|password|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,})" \
  --include=*.ts --include=*.js --include=*.json --include=*.env* . | grep -v node_modules | grep -v '\.git/'
# → .env keys EMPTY; CI uses secrets.*; NO live leaked credentials (clean)

# 2. Supply chain
npm audit --omit=dev          # → 0 vulnerabilities

# 3. OWASP code patterns (injection / traversal / eval)
grep -rniE "(eval\(|execSync|spawn\(|child_process|innerHTML\s*=|\.\./)" --include=*.ts --include=*.js .
# → no command-injection / eval / child_process / traversal in SOURCE
#   (only bin/mcp.js uses spawn with fixed internal paths + shell:true, no user input)

# 4. Web/Electron XSS surface
grep -rnE "innerHTML|dangerouslySet|escapeHtml" src/views/
# → most views ESCAPE user input via escapeHtml(); BUT browser.ts inserts unescaped data
```

### FINDING (real, actionable, low-severity)
`src/views/home/scripts/browser.ts:103` — DOM XSS sink:
```js
drivesList.innerHTML = drivesJson.data.map(d =>
  '<div class="sidebar-item" data-path="' + d + '">' + d + ' Drive</div>'
).join('');
```
`drivesJson.data` (drive letters from `/api/fs/drives`) is inserted raw into `innerHTML`
without escaping. The sibling `quickAccessList` (line 94) is hardcoded and safe. Fix:
wrap `d` in an escape helper (or use `textContent`). Low exploitability (server-constrains
drive letters) but exactly the class of issue `/cso` flags and `/review` would auto-fix.

## Lessons for future runs
1. gstack skills read as methodology = fully executable with native Hermes tools. The
   preamble's `~/.claude/...` bin calls are skippable version checks.
2. `npm run lint` on this repo is SLOW (~60s+) and emits "Parsing" errors — bound it with
   `timeout` and don't treat parse errors as code defects.
3. `npm run test:unit` takes ~52s; save output to a file (`> /tmp/avg_test.log`) and grep
   the saved file rather than re-running repeatedly on a low-RAM box.
4. The high-value, low-cost gstack audits for our repos: `/cso` (security), `/health`
   (typecheck/lint/test), `/qa-only` (visual, needs Chromium — use sparingly). All
   report-only = safe for unattended cron under the autonomy caveat (Pitfall 3).
