# AVG — CI-as-verifier + cross-platform gotchas

Captured during Sweep 4 (Docker verify + CI/CD) of Automated-Video-Generator.
The repo uses Node's built-in `node:test` runner (`tsx --test`), `npm run typecheck`,
`npm run lint` (eslint), `npm run format:check` (prettier), and a GitHub Actions
CI that builds a Docker image + runs gitleaks.

## Use CI as the verifier when the local box can't build

Local `docker compose build` was network-blocked (npm registry ECONNRESET mid-`npm ci`)
on the 6 GB laptop. The Dockerfile was already correct, so the verification path was
to **push a hardened CI workflow and let GitHub's stable-network runners build + scan**.
This surfaced 5+ REAL bugs that local-only testing never would have (tests passed on
Windows, failed on Linux CI). Lesson: when local env can't run the full gate, make CI
run it and `gh run watch <id>` the result — don't claim done on local-green alone.

## Cross-platform bugs CI caught (Windows-passes / Linux-fails)

### 1. drawtext font-file fallback → "Filter not found"
`overlay.ts` / `captions.ts` picked a font from a hardcoded list
(`C:/Windows/Fonts/arial.ttf`, `/usr/share/fonts/.../DejaVuSans.ttf`, ...).
When NONE existed (bare Ubuntu CI runner has no DejaVu installed), the old code
returned the literal `'Arial'` and built `drawtext=fontfile='Arial':...` →
ffmpeg can't open a font *family* as a file → "Filter not found" → watermark +
captions unit tests failed ONLY on CI.

FIX (do this for any ffmpeg drawtext op):
- font picker returns `string | null` (was `?? 'Arial'`).
- when null, OMIT the `fontfile=` clause entirely → ffmpeg/fontconfig picks a
  system default. Build the filter as `drawtext=${fontClause()}text=...` where
  `fontClause()` returns `fontfile='<path>':` only when a real file exists.
- widen the candidate list with `/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf`
  and `/usr/share/fonts/dejavu/DejaVuSans.ttf` so more Linux images resolve.

### 2. Hardcoded Windows temp path in a test
`operations.test.ts` used `fs.mkdtempSync('C:/one/_ops-test-')` → `ENOENT` on
Linux CI. FIX: `fs.mkdtempSync(path.join(os.tmpdir(), '_ops-test-'))` — valid for
ffmpeg.exe on Windows AND system ffmpeg on Linux. Any test that writes temp media
must use `os.tmpdir()`, never a hardcoded `C:/...`.

### 3. Sub-millisecond TTL race in a cache test
`asset-cache.test.ts` stored then immediately checked `getCached(url, 1)` (1ms TTL)
against file mtime — on fast runners age was 0ms → not expired → assertion flipped.
FIX: `return new Promise(res => setTimeout(() => { assert...; resolve(); }, 5));`
before the expiry assertion. Don't rely on wall-clock 1ms in tests.

## GitHub Actions gotchas

- **GHCR repo names MUST be lowercase.** `ghcr.io/itsPremkumar/...` is rejected.
  Use `IMAGE: ghcr.io/${{ toLower(github.repository) }}` (lowercases owner+name).
  A push with an uppercase tag fails the Docker job with
  `invalid tag "...": repository name must be lowercase`.
- **`npm run format:check` (prettier) is a SEPARATE gate from `npm run lint` (eslint).**
  Fix drift with `npm run format` before pushing — CI's `format:check` job fails
  independently of lint.
- **ESLint `--quiet` with `parserOptions.project` emits spurious
  `Parsing error: "parserOptions.project" has been provided`** false-positives that
  drown the real errors. To see the ACTUAL lint errors, run the repo's own
  `npm run lint` (not `npx eslint . --quiet`).
- **Push, THEN `gh run watch` the re-run.** Local green ≠ CI green. After a CI-fix
  push, verify the new run is green before declaring the sweep complete. A run can
  also fail with "likely failed because of a workflow file issue" (YAML schema) —
  inspect `gh run view <id>` and fix the workflow, not the code.

## node:test summary is nested — read the TOP-LEVEL line, not `tail`

`tsx --test` prints a summary block (`# tests N`, `# pass`, `# fail`, `# skipped`)
at the END, but it ALSO prints per-file / per-suite sub-summaries throughout the
run. If you pipe through `tail -4` or grep a truncated buffer, you can catch a
NESTED subtest summary (e.g. `# fail 4` or `# fail 7` with a lower `# tests`
count) and wrongly conclude the run failed. This bit me repeatedly this session:
`tail`-truncated output showed `fail 4 / 367` and `fail 7`, but the authoritative
run was `# tests 370 / pass 369 / fail 0 / skipped 1`.

RULES:
- The ONLY authoritative result is the FINAL top-level summary block. A drop in
  the `# tests` count vs. a full run (367 vs 370) is the tell that you captured a
  nested sub-summary, not the real total.
- To read pass/fail reliably: `npm run test:unit 2>&1 | grep -E "^# (tests|pass|fail|skipped)" | tail -4`
  (anchor `^#` so only summary lines match) — OR grep `^not ok` to enumerate real
  failures. If `grep "^not ok"` returns nothing, there are zero real failures no
  matter what a truncated tail showed.
- Don't re-debug a phantom failure. Re-run the full suite once and trust the
  bottom `# fail 0` before spending calls hunting a non-existent broken test.

## Config preset merge: baseline-spread, don't post-clobber

When adding a named preset that sets fields the user can also set directly
(e.g. a `format`/`captionTheme` preset that sets `orientation`/`aspect`), apply
the preset as a BASELINE in the spread chain BEFORE the user's explicit input,
not as a post-merge assignment:

```ts
const merged = { ...preset, ...tpl, ...fmt, ...stripUndefined(input) }; // ✅ user wins
```

NOT:
```ts
const merged = { ...preset, ...tpl, ...stripUndefined(input) };
if (fmt) { merged.orientation = fmt.orientation; }  // ❌ clobbers explicit user override
```

A post-merge `merged.x = fmt.x` silently overrides an explicit `orientation`
the user passed alongside `format: 'shorts'`. Write a test that passes BOTH the
preset name AND a conflicting explicit field, asserting the explicit one wins.

## Make render-path styling testable: extract a pure mapper

To wire a theme/preset into an ffmpeg `drawtext` render path WITHOUT risking the
render and WITHOUT needing a full render to test it: extract a pure function
(`captionThemeToDrawtext(theme) -> { fontcolor, fontsize, boxArgs, yExpr }`) in
the config module, unit-test THAT directly, then call it from the renderer. Keep
the "unset preset ⇒ historical default look unchanged" contract so existing
renders don't shift. Escaping tip: when copying an ffmpeg filter template line,
match the EXISTING line's backslash count exactly (`between(t\\,...)` in source) —
the patch tool can double-escape and produce `\\\\` which breaks the filter.

## Verification gate that held
typecheck 0 · lint 0 errors · format OK · test:unit 348/349 pass (1 pre-existing
E2E skip). Pushed to origin/main; CI re-run is the final oracle.
