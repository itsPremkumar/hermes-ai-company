# CodeQL TS/Next.js sanitizer cheat-sheet

## log-injection (js/log-injection, js/incomplete-sanitization)
```ts
// At the sink — CodeQL trusts this exact pattern:
console.error(('[ffmpeg] ' + x).replace(/[\r\n]/g, ' '));
// If ESLint no-control-regex fires, disable it for the file:
/* eslint-disable no-control-regex -- log-injection defense */
```
Never hide the strip in a helper (`safeLog`). `[\x00-\x1F\x7F]` also strips \r\n but trips `incomplete-sanitization`.

## request-forgery / http-to-file-access / file-access-to-http (SSRF)
```ts
if (!isSafeUrl(url)) throw new Error('blocked');   // scheme allow-list + block 127/10/192.168/172.16-31/169.254.169.254/file:
const res = await axios.get(url, {...});
```
`isSafeUrl` must be called INLINE before the request; a custom fn used elsewhere is not a sanitizer.

## path-injection
```ts
if (p.includes('\0') || p.includes('..')) return false;
const resolved = path.resolve(p);
if (!resolved.startsWith(allowedRoot)) return false;
```

## file-system-race (TOCTOU)
```ts
// read: open first, then fstat
const fd = fs.openSync(p, 'r'); const st = fs.fstatSync(fd);
// write: don't pre-check existsSync — just write (idempotent)
fs.writeFileSync(dest, buf);
```

## polynomial-redos
Replace `.*?` across a line with `[^\]]*` (or other bounded class).

## loop-bound-injection
Bound the loop: `const t = text.slice(0, 4096);` before iterating.

## Verify
```bash
npm run typecheck
npx eslint <files> --quiet            # 0 errors
git push origin main
# wait ~2-3 min for CodeQL re-scan, then:
gh api repos/<owner>/<repo>/code-scanning/alerts?state=open \
  --jq 'group_by(.rule.id) | map({rule: .[0].rule.id, n: length})'
```
CI "success" does NOT mean alerts cleared — re-query the API to prove it.
