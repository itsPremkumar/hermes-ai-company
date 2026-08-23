# CodeQL taint-sanitizer pitfall (AVS)

CodeQL's security queries (`js/log-injection`, `js/request-forgery`,
`js/http-to-file-access`, `js/file-access-to-http`, `js/path-injection`,
`js/incomplete-sanitization`) track TAINT from a source to a sink. They only
recognize sanitization that is a KNOWN PATTERN applied AT THE SINK. A custom
helper (e.g. `safeLog(s)`) that strips control chars is **not** modeled as a
sanitizer — the alert stays open even though the code is "fixed".

## What works
- **log-injection (`console.*` with tainted text):** inline
  `.replace(/[\r\n]/g, ' ')` directly on the argument at the sink. CodeQL
  recognizes the `\r\n` char-class strip. A broader `/[\x00-\x1F\x7F]/g`
  was flagged as `js/incomplete-sanitization` — use the exact `[\r\n]` pattern.
- **request-forgery / SSRF (`axios.get(url)`):** validate the URL with a
  recognized guard BEFORE the call (`isSafeUrl()` in `src/lib/net-safety.ts`
  does scheme allow-list + private/loopback/metadata host block). Call it
  inside the function that issues the request.
- **path-injection:** reject NUL + `..` AND confine with `path.resolve(...)`
  + a startsWith(prefix) check — CodeQL recognizes resolve+prefix confinement.
- **file-system race (TOCTOU):** open the fd first (`fs.openSync`), then
  `fs.fstat(fd)`; don't `fs.statSync` then open. For write-then-check, drop
  the existence check and write directly.
- **polynomial-redos:** replace nested `.*?` with a bounded class like `[^\]]*`.
- **loop-bound-injection:** cap loop bounds derived from external input.

## ESLint conflict
`/[\r\n]/g` triggers ESLint `no-control-regex` (CI lint fails on ERRORS).
Resolve by adding `/* eslint-disable no-control-regex -- intentional ... */`
at the TOP of the file that uses the pattern (one disable covers the file).

## Verification
A CodeQL alert staying open after a "fix" does NOT mean CI failed — CodeQL is
an informational check here (workflow shows `success` even with open alerts).
Re-scan takes ~2.5 min per push. To truly clear: use the recognized patterns
above and confirm the alert count drops on the next scan
(`gh api repos/.../code-scanning/alerts?state=open`).

## Gotcha from the 2026-08-03 session
First attempt wrapped stripping in `safeLog()` → alerts unchanged. Second
attempt used `/[\x00-\x1F\x7F]/g` inline → new `incomplete-sanitization`
alert. Third (correct): `/[\r\n]/g` at the sink + `eslint-disable`.
