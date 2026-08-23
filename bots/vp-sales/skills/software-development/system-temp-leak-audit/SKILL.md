---
name: system-temp-leak-audit
description: Trace, fix, and PROVE elimination of files a codebase writes to the system TEMP directory (os.tmpdir() / process.env.TMP / AppData Local Temp) instead of project-local paths. Use when a user demands "all generated files must stay inside the project", a disk fills with pipeline/test scratch, or code review flags temp leakage. Covers the fs.mkdtempSync path-anchor pitfall, the mass-rewrite transformer pattern, and the live before/after sweep that turns "I fixed it" into verifiable proof.
---

# System TEMP Leak Audit

## When to use
- User rule: "everything the tool generates must live in the project workspace, nothing in system TEMP."
- Disk fills with `<prefix>-*` scratch dirs in `C:\Users\<user>\AppData\Local\Temp` (or `/tmp`).
- You must both **fix** the leak and **prove** containment with a live sweep (not a claim).

## The leak signature
Files end up in system TEMP when code calls:
- `fs.mkdtempSync(path.join(os.tmpdir(), prefix))`
- `path.join(os.tmpdir(), 'foo')` for temp file paths
- `process.env.TMP || 'C:/tmp'` fallbacks
- `require('os').tmpdir()` directly

## Fix pattern (backward-compatible, no old code deleted)
1. **Add helpers** in a central paths module (e.g. `src/shared/runtime/paths.ts`):
   ```ts
   export function resolveWorkspaceTempPath(...segments: string[]): string {
     return resolveWorkspacePath('workspace', 'tmp', ...normalizeRelativeSegments(segments));
   }
   export function makeWorkspaceTempDir(prefix: string, sub = 'tests'): string {
     const base = resolveWorkspaceTempPath(sub);
     fs.mkdirSync(base, { recursive: true });
     return fs.mkdtempSync(path.join(base, prefix)); // path.join => anchors under base
   }
   ```
2. **Rewrite production leaks**: `os.tmpdir()` → `resolveWorkspaceTempPath('contact-sheet')` etc.
3. **Rewrite test leaks** (often 20+ files): `fs.mkdtempSync(path.join(os.tmpdir(), 'X-'))` → `makeWorkspaceTempDir('X-')`; module-level `path.join(os.tmpdir(), y)` → `path.join(__WS_TEST_TMP__, y)` where `const __WS_TEST_TMP__ = resolveWorkspaceTempPath('tests');`.

## CRITICAL PITFALL — fs.mkdtempSync anchoring
`fs.mkdtempSync(prefix)` treats `prefix` as the **full template path** and creates the dir
*there* (appending 6 random chars). Passing `fs.mkdtempSync(base, prefix)` (two-arg form) does
NOT use `base` as parent — it still creates under the OS temp root. You MUST pass
`fs.mkdtempSync(path.join(base, prefix))`. Verify with a live probe:
```js
const d = makeWorkspaceTempDir('probe-');
console.log(d.includes('workspace' + require('path').sep + 'tmp')); // MUST be true
```
A false result means the dir landed in system TEMP — the helper is broken.

## Mass-rewrite transformer (safe, reviewable)
For many test files, a one-shot Node script is faster than 26 manual patches. See
`references/transformer.cjs`. It: adds the workspace-temp import, rewrites the two `os.tmpdir`
forms, injects the `__WS_TEST_TMP__` const, and drops now-unused `os` imports.
**Always re-read files afterward** — the naive regex `^(\s*import[^\n]*\n)+` can mis-anchor when a
file opens with a **multiline `import {` block** (it inserts the new import *inside* the block).
Manual fix: move the injected `import { makeWorkspaceTempDir... }` + const to the top, remove the
duplicate line it created.

## Verification — the part that proves it
1. `rg -n "os\.tmpdir|process\.env\.TMP" src tests remotion --glob '!paths.ts'` → expect **0** real hits.
2. `npm run typecheck` → exit 0.
3. **Live before/after sweep** (the proof):
   ```bash
   # snapshot leak count in system TEMP
   find "$LOCALAPPDATA/Temp" -maxdepth 1 \( -name 'agentic-*' -o -name 'avg-*' -o -name 'ac-*' ... \) | wc -l
   # run the real pipeline / the patched tests
   node --import tsx --test "tests/..."   # or: npm run generate:agentic ...
   # re-sweep — want 0 NEW (use -mmin -15 to confirm no fresh leak)
   find "$LOCALAPPDATA/Temp" -maxdepth 1 -name 'agentic-*' -mmin -15 | wc -l   # want 0
   ```
4. Delete stale pre-fix leftovers, then re-sweep to confirm **0** total.

## Gotchas
- `search_files`/`rg` on Windows MSYS may fail on `/c/one/...` paths; use `terminal` + bare `rg`
  (ripgrep works) instead of the search_files tool for deep scans.
- False-negative "leak" in sweep: the Electron build resolves `dataRoot` to `LOCALAPPDATA\AppData\Local\Automated Video Generator` (separate runtime) — in CLI mode that folder does not exist, so nothing writes there. Confirm mode before chasing it.
- Stale leftovers from BEFORE the fix will still sit in system TEMP; a post-fix sweep counts them.
  Distinguish new (mtime window) vs old before claiming "still leaking".
- Don't touch installed-tool caches (npm cache, ffmpeg-static binary, Python venv) — those are
  dependencies, not files the app *generates*.
