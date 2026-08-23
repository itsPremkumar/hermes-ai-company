# AVG Lint Gate — what's intentional vs what to fix

Condensed knowledge for running gstack `/health` or a lint cleanup against
`itsPremkumar/Automated-Video-Generator` (TS/Node, Remotion + ffmpeg-static +
Edge-TTS). Captured after a real /cso + /health pass (2026-07-16) that took the
gate from 73 errors -> 0.

## Bottom line
Lint is GREEN at **0 errors / ~770 warnings**. The warnings are the author's
deliberate style choices (set to `warn`), NOT bugs. Do NOT churn them into errors
or rewrite 700+ lines -- that risks breaking the working pipeline and gstack itself
warns against treating config-strictness as code defects.

## Rules that MUST stay as-is
| Rule | Setting | Why |
|------|---------|-----|
| `@typescript-eslint/no-require-imports` | `warn` | `ffmpeg-static`, `ffprobe-static`, `edge-tts` have no ESM default export / type decls. Loaded via `require()`; `.path` is the binary. `import` -> runtime break. |
| `@typescript-eslint/no-var-requires` | `warn` | Same reason as above. |
| `eqeqeq` | `smart` | Allows idiomatic `== null` / `!= null` null-checks. `always` would flag legit code. |
| `no-explicit-any` | `warn` | Author uses `any` liberally in the legacy pipeline. |
| `prefer-nullish-coalescing` | `warn` | Author uses `||` for defaults throughout. |

## Real fixes that legitimately improve the gate (safe, done)
- `prefer-const` (error): destructure only the reassigned binding as `let`
  (e.g. `const { startMs, text } = m; let { endMs } = m;`).
- `no-var` (error): trivial.
- `no-self-assign` (error): a dead `x = x;` line in `src/agentic/gateway.ts`
  was a real (if harmless) no-op -- remove it.
- DOM-XSS (`innerHTML` unescaped): in `src/views/home/scripts/browser.ts` the
  drive-list and error sinks interpolated server data into `innerHTML`. Rewrote
  to `document.createElement` + `dataset` + `appendChild(document.createTextNode(...))`
  (same safe pattern already used by `loadPath`). Low exploitability (server
  constrains drive letters) but exactly the class `/cso` flags.

## Verification commands (run in the SAME turn you edit)
```bash
cd /c/one/Automated-Video-Generator
npx tsc -p tsconfig.json --noEmit   # 0 errors expected
npx eslint src/                     # 0 errors, ~770 warnings expected
timeout 320 npx tsx --test "src/**/*.test.ts"   # 193 pass / 0 fail (1 skipped)
npm audit --omit=dev                # 0 vulnerabilities
```
eslint is slow (~60s) and emits "Parsing" noise on this repo -- bound with
`timeout` and treat parse lines as non-defects. The AVG suite takes ~50s; capture
to a file and grep rather than re-running on a low-RAM box.

## Do NOT do
- Convert `require('ffmpeg-static')` to `import ffmpeg from 'ffmpeg-static'` -- the
  default export is undefined; `.path` lookup fails and renders break.
- Flip the `warn` rules above to `error` to "force a stricter gate" -- you'll get
  80+ fake failures on intentional code.
- Rewrite `any`/`||` usages repo-wide -- massive churn, collision risk with other
  workstreams, zero functional gain.
