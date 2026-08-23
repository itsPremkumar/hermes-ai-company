---
name: codeql-ts-remediation
description: Fix CodeQL js/* security alerts in TS/Next.js repos.
category: github
---

# CodeQL TS/Next.js Remediation

## When to use
A `gh api repos/.../code-scanning/alerts?state=open` shows `js/*` alerts, or the user says "fix the CodeQL alerts", "resolve the security scan". Applies to any TS/Next.js repo with GitHub code-scanning enabled.

## GOTCHA 1 — log-injection needs the sanitizer AT THE SINK, literal `[\r\n]`
CodeQL's `js/log-injection` (and `js/incomplete-sanitization`) only trusts a control-character strip applied DIRECTLY to the logged string via a regex literal containing `\r`/`\n`. A custom wrapper (e.g. `safeLog(s)`) is NOT recognized as a sanitizer → alert persists.
- ✅ `console.error(('[ffmpeg] ' + x).replace(/[\r\n]/g, ' '))`
- ❌ `console.error(safeLog('[ffmpeg] ' + x))`  // wrapper not trusted
- ❌ `replace(/[\x00-\x1F\x7F]/g, ' ')` → fires `js/incomplete-sanitization` even though it also strips \r\n. Use EXACTLY `[\r\n]`.
- Conflict: ESLint `no-control-regex` (often enabled in CI lint) FORBIDS `[\r\n]` literals → would fail lint. Fix: `/* eslint-disable no-control-regex -- log-injection defense */` at file top (only blocks regex *literals*; `new RegExp('...')` strings aren't flagged).

## GOTCHA 2 — custom guards are NOT sanitizers
- `js/request-forgery`, `js/http-to-file-access`, `js/file-access-to-http`: a custom `isSafeUrl()` / `safeCacheFile()` helper is NOT a recognized sanitizer. Validate INLINE where taint flows: before `axios.get(url)` call `isSafeUrl(url)` (scheme allow-list + block private/loopback/metadata hosts); before writing, confine with `path.resolve(p)` + `startsWith(allowedRoot)` prefix check INLINE.
- SSRF guard must reject `file://`, `http://169.254.169.254`, `localhost`, `127.x`, `10.x`, `192.168.x`, `172.16-31.x`.

## GOTCHA 3 — file-system-race (TOCTOU)
`js/file-system-race` flags `existsSync` → `openSync`/`readFileSync`/`writeFileSync` windows.
- Read: open the fd FIRST, then `fstat(fd)` — never `statSync` then open.
- Write: drop the `!existsSync(dest)` pre-check before `writeFileSync` (write is idempotent; the check IS the race).

## GOTCHA 4 — path-injection
Reject NUL (`\0`) + `..` segments AND confine with `path.resolve(p)` + `startsWith(root)` prefix check. Don't rely on a `..` substring check alone.

## GOTCHA 5 — polynomial-redos
`/\[Visual:?\s*.*?\]/gis` (nested `.*?` across a line) is ReDoS-prone. Replace `.*?` with a bounded class like `[^\]]*`.

## GOTCHA 6 — loop-bound-injection
`for (let i=0; i<text.length; i++)` bounded by external input reads as DoS. Bound the work (hash first N chars) or it stays flagged.

## GOTCHA 7 — unused-local-variable is NOISY / often false-positive
`js/unused-local-variable` frequently flags symbols that ARE used (grep count > 1 incl. import). Before deleting, confirm with `grep -c` the symbol appears ONLY at its declaration. If ESLint `--quiet` already reports 0 errors for the file, deleting will BREAK the build. Leave genuine false-positives; only remove verified-unused symbols.

## Verification loop (the part people skip)
1. Fix → `npm run typecheck` + `eslint <files> --quiet` (0 errors) + run the relevant unit test.
2. Commit + `git push origin main`.
3. **CodeQL re-scan takes minutes** — wait for the run, then `gh api repos/.../code-scanning/alerts?state=open` to confirm the count dropped.
4. NOTE: CI "success" ≠ alerts cleared. CodeQL is a check; unless branch protection requires it, the push succeeds regardless. Always re-query the API to prove the fix worked (don't claim done on green CI alone).

Full sanitizer-pattern cheat-sheet + verification commands: `references/codeql-sanitizers.md`.
