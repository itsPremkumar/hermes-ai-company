# envguard — zero-dep .env validator CLI (session detail, 2026-08-01)

Built `C:\one\envguard` v1.0.0: validates `.env` against `.env.example` (missing/extra keys +
type mismatches). 37/37 tests green, committed `a3953da` on `main`. Reuse the shape for any
config/secret-file validation CLI.

## Tool shape
- `src/types.ts` (EnvKey/ValidationIssue/ValidationResult), `src/parser.ts` (example parsing),
  `src/envfile.ts` (real .env parsing), `src/validator.ts` (pure check), `src/cli.ts` (flags,
  table/JSON render, --fix, exit codes). Tests in `test/*.test.ts` → `dist/test/*.test.js`.
- tsconfig: rootDir `.`, outDir `dist`, NodeNext; bin = `dist/src/cli.js`; shebang preserved by tsc.

## .env.example parsing rules (durable spec)
- Split lines on `/\r?\n/` (CRLF-safe). Skip blank lines. Lines starting with `#` skipped.
- `# type: <hint>` sets a PENDING hint for the next key. Blank lines between hint and key are OK;
  any OTHER comment line CLEARS the pending hint (predictable "directly above" semantics).
- `KEY=VALUE` splits on the FIRST `=` (values may contain `=`). Surrounding quotes stripped
  (`KEY="a=b"` → `a=b`). After unquoting: empty value → REQUIRED (`hasDefault:false`),
  non-empty → OPTIONAL.
- `readEnvFile` (real .env): same rules, plus optional `export ` prefix ignored; returns
  `Map<string,string>`; `KEY=` stores `''` (presence matters, not just truthiness).

## Type-hint regexes (new RegExp string form — double backslashes)
- number: `^-?\d+(\.\d+)?$`
- boolean: `^(true|false|1|0|yes|no)$` (i)
- url: `^https?://` (i)
- email: `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- port: `^\d{1,5}$`
- Empty value is an explicit mismatch for EVERY non-string hint (checked before the regex; valid
  for `string` and for untyped keys).

## Exit codes / strict layering
- 0 ok; 1 errors (missing required, type mismatch, or --strict extras); 2 usage (bad flag,
  empty/unreadable .env.example).
- Extras are warnings by default: keep the pure `validate(exampleKeys, envValues)` two-arg
  signature honest (`ok` stays true with extras); the CLI layer counts extras as errors under
  `--strict`. Keeps the validator pure and unit-testable.
- Missing `.env` file → treat as empty env (all required keys reported missing). Missing/empty
  `.env.example` → usage error, exit 2.

## --fix design (consent + honest revalidation)
- Appends missing REQUIRED keys as `KEY=` lines. Prints exactly what will be added FIRST (that's
  the consent), then writes, then RE-VALIDATES and reports the post-fix state: an appended empty
  value for a typed key becomes a NEW type mismatch (exit 1); untyped/string keys pass (exit 0).
  Document this in the README so the fix-then-fill loop is expected behavior.

## Testable CLI pattern (reuse verbatim)
- `main(argv, {stdout, stderr, cwd})` returns the exit code; NEVER `process.exit` inside.
- Boot guard at module bottom: `resolve(process.argv[1]).toLowerCase() ===
  fileURLToPath(import.meta.url).toLowerCase()` — runs only when executed directly.
- `class Capture extends Writable` collects output in-process; fixtures via
  `os.tmpdir()` + `mkdtemp` + `try/finally rm(dir, {recursive:true, force:true})`.
- `isTTY` via cast: `Boolean((stdout as { isTTY?: boolean }).isTTY)`.
- Table alignment: pad the status cell BEFORE wrapping in ANSI colors (escape codes break padEnd).

## Invocation gotcha (verified live)
`node dist/src/cli.js --env /other/dir/.env` from a foreign cwd with a RELATIVE cli path fails
the entry guard silently (no output, exit 0). Run demos from the repo root or pass an absolute
path to `dist/src/cli.js`.

## Live demo evidence (all exit codes exercised)
- Broken .env (2 missing, 1 type mismatch, 1 extra): table shows MISSING/TYPE/EXTRA rows →
  `envguard: 3 error(s), 1 warning(s)`, exit 1.
- `--fix`: prints `appending 2 missing required key(s)` + `API_BASE_URL=` / `WEBHOOK_URL=` lines,
  appends, re-validates (empty typed keys → TYPE errors, exit 1).
- Healthy .env: `envguard: all checks passed ✓ (10 keys checked)`, exit 0. `--json`: structured
  payload with `ok/exitCode/issues/extras/keys`, exit 0. Empty example: usage error, exit 2.
- Demo dir in `C:\one\envguard-demo`, removed after capture; repo committed clean.
