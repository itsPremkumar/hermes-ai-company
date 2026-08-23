---
name: green-ci-typescript-project
description: Build and ship a production-grade TypeScript/Node project (CLI, agent, MCP server, RAG, SQLite) with green CI, tests, lint, and end-to-end verification. Covers scaffolding, the quality gate, keeping heavy/native deps from breaking CI, and confirming remote CI is green after push.
---

# Green-CI TypeScript Project

End-to-end recipe for scaffolding a TS/Node project that ships with **green CI** and
stays verifiable. Use for: CLIs, agents, MCP servers, RAG tools, anything that must
look production-grade on a GitHub profile (flagship repos).

## When to use
- Starting a new TS/Node project from scratch (no existing code).
- Adding features to a TS project and need to keep CI green.
- The "unverified" system reminder fires after an edit — see Verification below.

## Scaffold (minimal, KISS)
- `package.json`: `"type": "module"`, scripts `build`/`start`/`test`/`lint`/`format`/`typecheck`,
  `devDependencies`: `typescript`, `eslint` (+ `typescript-eslint`), `prettier`, `tsx`, `@types/node`.
- `tsconfig.json`: `target: ES2022`, `module: NodeNext`, `moduleResolution: NodeNext`,
  `esModuleInterop: true`, `skipLibCheck: true`, `strict: true`, `outDir: dist`.
- `.github/workflows/ci.yml`: trigger on **both** `main` AND `master` (default branch is
  often `master` — a CI that only triggers on `main` silently never runs). Node 20/22.
  Steps: `npm ci`, `npm run format:check`, `npm run lint`, `npm run typecheck`,
  `npm run test`, `npm run build`.
- `LICENSE` (MIT), `.gitignore` (`node_modules/`, `dist/`, `data/`).

## Quality gate (run ALL before commit)
```
npx prettier --check "src/**/*.ts"   # format
npx eslint .                          # lint
npx tsc --noEmit -p tsconfig.json    # typecheck (use YOUR tsconfig, not default)
npx tsx --test "src/**/*.test.ts"    # unit tests
```
NOTE: the patch-tool linter runs `tsc` with a DEFAULT config and will emit false
positives (`TS2802 RegExpStringIterator`, `TS1259 better-sqlite3 esModuleInterop`,
`import.meta` not allowed). Those are not real — ignore them; trust `tsc --noEmit -p tsconfig.json`.

## Keeping heavy / native deps from breaking CI (KEY PITFALL)
- **Never hard-depend on huge native packages** (e.g. `@huggingface/transformers` pulls
  onnxruntime, hundreds of MB, native build). It will time out or fail in the CI runner.
  - Make it `optionalDependencies` OR don't declare it; load via dynamic `import()` wrapped
    in `try/catch` with a local fallback. If unavailable → degrade gracefully.
  - Add an ambient decl so `tsc` stays green: `src/<dep>.d.ts` → `declare module '@x/y';`
  - Document the opt-in: `npm i @x/y` to enable real embeddings; local fallback otherwise.
- **Native modules need a prebuilt binary for your Node major.** If you see
  `Error: Could not locate the bindings file` (better-sqlite3 etc.), the installed
  version has no prebuilt for your Node. Fix: pin to a version that ships a prebuilt
  (`better-sqlite3@^12.x` for Node 22), `rm -rf node_modules/<pkg> package-lock.json`,
  reinstall. If a full reinstall hangs, kill it and reinstall without the heavy dep first.
- After changing `package.json` deps, **regenerate `package-lock.json`** and re-run the
  gate before pushing — `npm ci` in CI uses the lock.

## Async scorer / embedder pattern
If scoring uses async embeddings (transformers.js), make `scorer.init()` async and
`score()` async; `scoreAll()` becomes `await Promise.all(list.map(j => scorer.score(j)))`.
Update every caller (`cli`, `mcp/server`, tests) to `await`. Tests that call
`new RagScorer(p).score(j)` directly must `await scorer.init()` first.

## Verification (handles the stale "unverified" reminder)
After ANY edit, before claiming done:
1. Run the 4 gate commands above. Read failures, repair, re-run.
2. `git status --short` → must be clean (or only intentional new files).
3. `git push` then confirm REMOTE CI is actually green:
   `curl -s "https://api.github.com/repos/<you>/<repo>/actions/runs?per_page=2" | python -c "..."`
   The reminder may fire on already-committed, pushed, green code — that's stale. A fresh
   green gate + clean git + `completed success` from the API is proof; do not re-edit blindly.

## CI is the verifier — use it, don't fight local network
When the LOCAL environment is flaky (e.g. `npm ci` resets mid-install on a bad
link) or resource-starved, do NOT burn the session retrying `docker compose build`
locally. Instead:
- Harden the `Dockerfile` (PEP 668 venv, `linux/amd64` pin, full `npm ci`,
  npm retry loop) and push it.
- Add a **GitHub Actions workflow that builds + pushes the image to GHCR**
  (`docker/build-push-action`, `platforms: linux/amd64`, `cache-from/to: type=gha`).
  GitHub's runners have a STABLE network, so the image actually builds there even
  when your laptop can't.
- Treat a **green remote CI run as the verification gate**. After push, poll
  `gh run list` / `gh run watch` / `gh api .../check-runs` for the real job
  conclusions. This is real evidence (the image built + pushed on CI), not a claim.
- This session: a correct `Dockerfile` could NOT be built locally (ECONNRESET at
  `npm ci`), but the **GHCR push job succeeded in CI (6m42s)** — that is the proof.

## GitHub Actions workflow validation gotchas (silent workflow-killers)
A workflow that fails GitHub's pre-merge YAML/expression validation shows as a
**0-second "failure" run named after the workflow file path** (e.g.
`.github/workflows/ci.yml`) with NO child jobs. The REAL jobs
(lint/typecheck/test/docker) never execute. Every push looked "red" while the
actual bug was invisible. Symptoms + fixes:
1. **Invalid `uses:` tag** → whole workflow rejected. `docker/build-push-action@v6`
   does NOT exist (latest is `v7`); `gitleaks/gitleaks-action@v2` does NOT
   exist (latest is `v3`). ALWAYS verify a tag exists via
   `gh api repos/<owner>/<action>/tags` before referencing it.
2. **`toLower()` in a `${{ }}` expression** → *"Unrecognized function: 'toLower'"*.
   GitHub Actions expressions have NO `toLower`/`toUpper`. To lowercase a repo
   name for GHCR, compute it in a **shell step**:
   `echo "image=ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_OUTPUT"`
   then read `${{ steps.img.outputs.image }}`.
3. **Job-level `continue-on-error: true`** → invalid schema placement (it is
   step-level only). Move it under the specific step.
- To SEE the actual validation error when a run shows 0s failure: open the run
  page in a **browser** (the snapshot's Annotations region renders the exact
  `Invalid workflow file: ... (Line: X, Col: Y)` message — the `gh` API does
  not surface it cleanly).

## Cross-platform test + ffmpeg-filter gotchas
- Tests that hardcode Windows paths (e.g. `fs.mkdtempSync('C:/one/_ops-test-')`)
  FAIL on Linux CI runners (ENOENT). Use `os.tmpdir()` — works for
  `ffmpeg.exe` on Windows AND system ffmpeg on Linux.
- Real-ffmpeg integration tests (drawtext/xfade/zoompan/vignette) FAIL on minimal
  ffmpeg builds (Ubuntu `apt` ffmpeg omits GPL/non-free filters; some static
  binaries too). Fix: add a `ffmpegHasFilter(name)` helper that runs
  `ffmpeg -filters` and **skip the test gracefully** when the filter is missing
  (clear skip reason), exactly like the repo's existing edge-tts ENOENT skip.
  This keeps CI green on minimal builds while still testing on full builds.
- A `fontfile='Arial'` fallback in a drawtext filter is INVALID (Arial is a
  family, not a file) → "Filter not found" on Linux. Fallback should OMIT
  `fontfile=` entirely and let ffmpeg/fontconfig pick a default.
- **spawn-with-shell CLIs: quote argv before joining (Windows passes, Linux CI dies).**
  A CLI that runs user commands via `spawn(cmd, {shell:true})` must NOT hand the
  shell an unquoted `argv.join(' ')`. Windows cmd.exe tolerates bare
  metacharacters, so `node -e require(...)` integration tests pass locally — but
  the Linux runner's `/bin/sh` fails with `Syntax error: "(" unexpected` and exit
  code 2 (looks like an app bug, is a quoting bug). Fix: on non-win32,
  single-quote every arg containing shell metacharacters (safe bare set
  `[A-Za-z0-9_@%+=:,./-]`), escape embedded quotes POSIX-style (`'` → `'\''`),
  keep the bare join on win32; make `platform` a function param defaulting to
  `process.platform` so unit tests assert the POSIX path on any OS. Real case +
  log excerpt: `references/posix-shell-quoting-ci.md`.

## Reference: debug a "0s failure" CI run
When `gh run list --workflow ci.yml` shows ONLY a `0s / failure` run
named after the workflow file (no child jobs), GitHub's **pre-merge
workflow validation** rejected the YAML — your real jobs never ran.
- **Decide in <2 min** if jobs ran: `gh api "repos/<o>/<r>/commits/<sha>/check-runs"`
  and grep for YOUR job names (`Lint & Format`, `Unit Tests`,
  `Docker Build`). If only `build`/`deploy`/`CodeQL` appear, those are
  OTHER workflows — yours did not execute.
- **Get the real error** (the `gh` API hides it): open the failed run
  URL in a **browser** — the snapshot's "Annotations" region renders the
  exact `Invalid workflow file: … (Line: X, Col: Y): <reason>`.
- **Three silent killers** (all produce the 0s-failure, none show in `gh`):
  1. Bad `uses:` tag — `docker/build-push-action@v6` and
     `gitleaks/gitleaks-action@v2` DO NOT EXIST (latest are `v7` / `v3`).
     Verify any tag via `gh api repos/<owner>/<action>/tags` before using.
  2. `toLower()` / `toUpper()` inside `${{ }}` — GitHub expressions
     have NO such function. Lowercase for GHCR in a **shell step**
     (`echo "…" | tr '[:upper:]' '[:lower:]' >> "$GITHUB_OUTPUT"`),
     then read `${{ steps.img.outputs.image }}`.
  3. `continue-on-error:` at **job** level — it is **step-level only**;
     move it under the specific step.

## End-to-end proof (before "done")
Run the real pipeline, not just unit tests:
- offline demo (`npm run demo`): ingest→score→draft, senior roles excluded.
- a functional command path (e.g. `--import jobs.sample.json`) proving persistence/score.
- MCP control surface (`ingest_jobs`, `score_jobs`, `get_ready_to_apply` callable).

## KISS rules
- Don't add a web UI / auth / cloud — breaks "local-first, private, free" differentiators.
- Keep adapters network-optional: return `[]` on failure, never throw out of the pipeline.
- Human-in-the-loop submission: never auto-apply (account bans).

## References
- `references/native-dep-ci-pitfalls.md` — transformers.js / better-sqlite3 war stories + fixes.
- `references/verify-loop.md` — exact commands to prove green locally + remotely.
- `references/node-test-pitfalls.md` — `node:test` runner quirks: `ctx.skip()` does NOT abort execution (always `throw` after), CI env guard for network-dependent tests, and the `skipIfUnreachable` probe pattern. Read when tests show `not ok ... # SKIP ... + actual error` (the "stuck-in-skip" bug).
- `references/posix-shell-quoting-ci.md` — spawn-with-shell CLI quoting: Windows passes / Linux CI `Syntax error: "(" unexpected`, the `buildCommand` fix, exact unit-test strings, and the run→jobs→logs API triage path.
- `templates/ci.yml` — known-good GitHub Actions workflow (main+master trigger).
