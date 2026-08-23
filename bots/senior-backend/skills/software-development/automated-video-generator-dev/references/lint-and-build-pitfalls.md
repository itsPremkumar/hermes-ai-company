# AVS Lint & Build Pitfalls (2026-08-01 maintenance pass)

## 1. `no-misleading-character-class` in render.ts (REAL BUILD-BLOCKING BUG)
`src/agentic/orchestrator/render.ts` defines `CJK_RE` and `INDIC_ARABIC_RE` to pick
font fallbacks for multilingual captions (Devanagari/Tamil/Arabic/CJK).

**Wrong:** literal Unicode code-point ranges inside a character class:
`const INDIC_ARABIC_RE = /[஀-௿ก-๛ༀ-༏က-ၿ]/;` → ESLint error
`no-misleading-character-class` (exit non-zero, blocks `npm run lint`).

**Right:** pure `\uXXXX` escapes + `u` flag + disable comment (ranges are tested
and working — `re.test('ம்')` → `true`):
```ts
// eslint-disable-next-line no-misleading-character-class -- Unicode code-point ranges for Indic/Arabic scripts; tested and working
const INDIC_ARABIC_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0E00-\u0E7F\u0E80-\u0EFF\u1000-\u109F]/u;
const CJK_RE = /[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u2F00-\u2FDF\u3000-\u303F\uFF00-\uFFEF]/u;
```

## 2. `patch` tool double-escapes `\u`
`patch` mangles `\uXXXX` → `\\uXXXX` (literal backslash+u in file), re-triggering the
ESLint error. **Fix:** write the line with a Python heredoc using raw strings so the
backslash is emitted verbatim:
```python
python << 'PYEOF'
path = 'src/agentic/orchestrator/render.ts'
lines = open(path, 'r', encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if l.strip().startswith('const INDIC_ARABIC_RE'):
        lines[i] = r'    const INDIC_ARABIC_RE = /[\u0600-\u06FF...]/u;'
open(path, 'w', encoding='utf-8').write('\n'.join(lines))
PYEOF
```
Or just add the `eslint-disable-next-line` comment — it suppresses the error even if
the regex is written with escapes.

## 3. `npm install` OOM on the 6 GB RAM box
Full install (Remotion 8-pkg bump) gets **Killed (exit 137)** at ~4–9 min (6 GB RAM).
After a kill, `node_modules` is inconsistent:
- `.bin/eslint` symlink missing → `npm run lint` fails "eslint not recognized".
  Recreate BOTH on Windows:
  ```bash
  cat > node_modules/.bin/eslint <<'EOF'
  #!/bin/sh
  basedir=$(dirname "$0")
  exec node "$basedir/../eslint/bin/eslint.js" "$@"
  EOF
  chmod +x node_modules/.bin/eslint
  cat > node_modules/.bin/eslint.cmd <<'EOF'
  @ECHO OFF
  SETLOCAL
  SET "PATH=%~dp0;%PATH%"
  node "%~dp0\..\eslint\bin\eslint.js" %*
  ENDLOCAL
  EOF
  ```
- Missing transitive dep (e.g. `escape-string-regexp`) → often lands anyway on
  timeout; re-run `npm install <pkg> --no-save` only if `node node_modules/<pkg>`
  truly 404s.
- `package.json` is NOT updated when install is killed — bump ranges manually with
  `sed -i` after `npm ls <pkg>` confirms the new version is in node_modules.

## 4. `@ts-ignore` → `@ts-expect-error` on static binaries
`ffmpeg-static` / `ffprobe-static` have no type declarations. Replace `// @ts-ignore`
with `// @ts-expect-error` (future unnecessary suppression → hard error). EXCEPTION:
if the import resolves with no type error, `@ts-expect-error` errors "unused
directive" — keep `// @ts-ignore` there (the `ffmpeg-static` import case).

## 5. Lint posture (current)
`eslint.config.mjs` treats `no-explicit-any` (807 occurrences), `prefer-nullish-
coalescing` (hundreds), and `no-unused-vars` as **warn**, not error. `npm run lint`
gate = 0 errors. Do NOT try to zero-out the ~2400 warnings — that's a refactor, not
production-readiness. `eqeqeq: smart`, `prefer-const`, `no-var` ARE errors.

## 6. Dep update command (safe minor/patch)
```bash
npm install @remotion/cli@4.0.503 @remotion/renderer@4.0.503 @remotion/captions@4.0.503 \
  @remotion/media-utils@4.0.503 @remotion/motion-blur@4.0.503 @remotion/paths@4.0.503 \
  @remotion/shapes@4.0.503 @remotion/transitions@4.0.503 \
  @modelcontextprotocol/sdk@1.30.0 axios@1.19.0 eslint@9.39.5 @eslint/js@9.39.5 --no-audit --no-fund
```
Then `sed -i` the version ranges in package.json to match.
