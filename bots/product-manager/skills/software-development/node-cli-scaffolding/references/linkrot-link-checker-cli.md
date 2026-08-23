# linkrot — markdown/HTML broken-link checker CLI (build notes)

Session detail for `C:\one\linkrot` (2026-08-01): a zero-dependency TypeScript
CLI that scans markdown/HTML for broken local-file references and remote URLs.
31/31 tests green, committed locally. Use as a recipe for docs-QA / link-audit
CLIs, and for any CLI whose demo needs a live local HTTP server.

## Structure

- `package.json`: `type: module`, `bin: { linkrot: "dist/src/cli.js" }`,
  `engines: node >=18`, zero runtime deps; test script is
  `npm run build && node --test dist/test/extract.test.js dist/test/classify.test.js dist/test/check.test.js dist/test/cli.test.js`
  (EXPLICIT files — `node --test dist/test/` with a trailing slash fails on
  Windows).
- `tsconfig.json`: ES2022, module/moduleResolution NodeNext, `rootDir: "."`,
  `outDir: dist`, strict, `include: ["src/**/*", "test/**/*"]` → tests compile
  to `dist/test/*.test.js`, source to `dist/src/*.js`.

## Extraction (markdown + HTML)

- **Code-fence masking preserves line numbers**: split content on `/\r?\n/`,
  blank every line inside ` ``` ` / `~~~` fences (markers included), rejoin
  with `'\n'`, then run regexes on the masked string. Line number for a match
  at index i = `masked.slice(0, i).split('\n').length`.
- Regexes as `new RegExp('...', 'g')` template strings with double backslashes
  (never regex literals with `\\` — TS1508 / transport mangling).
- **Inline markdown link** (matches image links `![alt](url)` too — treated as
  links):
  `'\\[([^\\]]*)\\]\\(\\s*([^)\\s]+?(?:\\([^)\\s]*\\))*[^()\\s]*)(?:\\s+["\'][^"\']*["\'])?\\s*\\)'`
  — the URL core is LAZY with an optional balanced-parens group and a
  paren-excluding tail. Greedy `[^)\s]+` eats `a_(b` and the `(b)` never gets
  matched (first real failure this session, fixed exactly this way).
- **Angle brackets**: `'<([a-zA-Z][a-zA-Z0-9+.-]*:[^\\s<>]+)>'` — any
  `scheme:...` form (http, https, mailto, ftp…); mailto is skipped later by the
  classifier.
- **HTML href/src**: `'<[a-zA-Z][^>]*?\\shref\\s*=\\s*(?:"([^"]*)"|\'([^\']*)\'|([^\\s>]+))'`
  — the `\s` BEFORE the attribute name is what stops `href` matching inside
  another attribute's quoted value. Same regex with `src`.
- Post-process each URL: trim, decode `&amp;`/`&lt;`/`&gt;`/`&quot;`/`&#39;`,
  strip surrounding `<>` (markdown destinations may be `<...>`-wrapped), then
  `stripFragment` (split at first `#`). Dedupe on `(url, line)` — overlapping
  patterns (e.g. `<https://…>` in a markdown destination) would double-count.

## Classification

- remote: `^https?:\/\/` OR protocol-relative `^\/\/`; skip: `#`-anchors,
  `mailto|tel|data|javascript|ftp|ftps|file|irc|sms|geo|callto|news:`, empty;
  everything else local.
- Windows-absolute detection: `new RegExp('^[a-zA-Z]:[\\\\/]')`; POSIX-absolute
  `^\/`. Local resolve = `path.resolve(path.dirname(sourceFile), url)`.

## Remote checking (global fetch, no deps)

- HEAD first → fall back to GET only on 405/403/501. 200-399 → ok; 404/410 →
  broken; EVERYTHING else (5xx, other 4xx) → unreachable (a warning, not
  fatal). Network error / timeout → unreachable.
- Timeout: AbortController + setTimeout, `clearTimeout` in `finally`.
- **DOMException is NOT `instanceof Error`** — a fetch abort surfaces as
  `DOMException` named `'AbortError'`. Detect via
  `(err as { name?: string }).name === 'AbortError'` (also check
  `err instanceof Error ? err.message : String(err)` for the message).
- After reading status, `await res.body?.cancel()` (guarded) so undici
  keep-alive sockets don't pin the test runner; server test hook must call
  `server.closeAllConnections()` + `close()`.
- Concurrency pool: shared shift-queue + `n = clamp(concurrency, 1, items.length)`
  worker loops, `Promise.all`. Verified max-in-flight == limit in a test.

## CLI shape (testable)

- Pure `parseArgs(argv): ParseResult` discriminated union (`help|version|error|run`),
  no process.exit inside — every branch unit-testable. `main(argv, io)` returns
  the exit code; `io = { out, err }` injectable (tests capture lines).
- Entry guard: `path.resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()`
  — runnable via `node dist/src/cli.js` AND importable by tests.
- Exit codes: 0 clean (unreachable-only is a warning → 0), 1 broken
  (`broken` + local `not_found`), 2 usage. Local missing file status is
  `not_found`, counted in `broken`.
- ANSI via `String.fromCharCode(27)` (never `'\x1b'` literals); color only the
  leading status token so padding can't misalign (existing skill pitfall).
- LinkCheck carries optional `file`/`line` fields the CLI fills in — spec
  fields stay intact, JSON report becomes CI-usable.

## Tests

- check.test.ts: real `node:http` server on port 0 inside the test file
  (routes: /ok 200, /missing 404, /boom 500, /fallback 405-on-HEAD→200-on-GET,
  /slow 3s delay with tracked timer cleared in after-hook). Assert mapping
  200→ok, 404→broken, 500→unreachable, timeout→unreachable.
- cli.test.ts: temp fixture dir + same-process server; assert `main()` returns
  1, stdout contains the broken URLs, `--json` parses to
  `{checked: 4, broken: 2, results:[…]}` with per-result file/line.

## Live demo pattern (server + CLI in ONE foreground command)

Demo script creates a fixture site in `os.tmpdir()`, starts a server on port 0,
runs the built CLI against it, prints output + exit code, cleans up. TWO traps:

1. **`spawnSync` BLOCKS the parent event loop** — the in-process server cannot
   accept/respond to the child's requests, so every remote check times out
   (UNREACHABLE, `timeout after 5000ms`) while local checks pass; child exits 1
   with EMPTY stdout and empty stderr, which misreads as "CLI broken". Fix:
   async `spawn` wrapped in a Promise, awaited from the `listen` callback, so
   the server keeps serving during the child's run.
2. **Repo-path resolution**: a demo script placed OUTSIDE the repo that derives
   the repo dir via `path.dirname(fileURLToPath(import.meta.url))` points one
   level too high → child fails with MODULE_NOT_FOUND (`C:\one\dist\src\cli.js`
   instead of `C:\one\linkrot\dist\src\cli.js`). Join the repo name explicitly
   (`path.join(dirname(...), 'linkrot')`) or keep the script inside the repo.

## Demo evidence (real output)

```
linkrot v1.0.0 — 2 file(s) scanned   links checked: 4   broken: 2   unreachable: 0

  OK  ...\site\index.md:3  about.md
  NOT_FOUND  ...\site\index.md:3  missing.md  (does not exist: ...\missing.md)
  OK  ...\site\index.md:4  http://127.0.0.1:49237/ok
  BROKEN  ...\site\index.md:4  http://127.0.0.1:49237/missing  (HTTP 404)
exit code: 1
```

Fixture: index.md → about.md (exists), missing.md (broken local), 200 URL,
404 URL; a `[fake](...)` link inside a ``` code fence correctly ignored.
