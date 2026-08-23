# Recipe: Route `os.tmpdir()` / system-TEMP leaks into a project-local `workspace/tmp`

## Why this matters HERE
The agent host's Windows username is `PREM KUMAR` (has a **space**). System TEMP
resolves to `C:\Users\PREM KUMAR\AppData\Local\Temp`. Two consequences:
- Tools/code that don't quote the TEMP path, or assume a no-space path, break.
- Any `os.tmpdir()` / `process.env.TMP` use in a long-running pipeline slowly
  fills that shared folder (the 7.4 GB junk that had to be cleaned). AVS already
  special-cases this for Remotion: `src/render.ts` sets
  `process.env.REMOTION_TMPDIR = resolveWorkspacePath('tmp','remotion')` to dodge
  the space. Follow that pattern for EVERY other temp write.

## The fix shape (backward-compatible — add, don't delete)
1. Add two helpers to the project's path module (e.g.
   `src/shared/runtime/paths.ts`):

```ts
export function resolveWorkspaceTempPath(...segments: string[]): string {
  return resolveWorkspacePath('tmp', ...normalizeRelativeSegments(segments));
}
export function makeWorkspaceTempDir(prefix: string, sub = 'tests'): string {
  const base = resolveWorkspaceTempPath(sub);
  fs.mkdirSync(base, { recursive: true });
  return fs.mkdtempSync(path.join(base, prefix));
}
```

2. Production leak — replace the `os.tmpdir()` write. Example from
   `src/agentic/orchestrator/artifacts.ts` (contact-sheet frames were landing in
   system TEMP):
```ts
// BEFORE
const frame = `${os.tmpdir()}/cs_frame_${jobId}_${sceneIndex}.png`;
// AFTER
const tmpDir = resolveWorkspaceTempPath('contact-sheet');
fs.mkdirSync(tmpDir, { recursive: true });
const frame = `${tmpDir}/cs_frame_${jobId}_${sceneIndex}.png`;
```

3. Test leaks — route every `fs.mkdtempSync(path.join(os.tmpdir(), P))` to
   `makeWorkspaceTempDir(P)`, and module-level `path.join(os.tmpdir(), x)` refs to
   `path.join(__WS_TEST_TMP__, x)` where
   `const __WS_TEST_TMP__ = resolveWorkspaceTempPath('tests');`.

## Transform-script pattern (bulk-fix many test files)
Write a `.cjs` script that, per file: adds the helper import (compute the
relative path from the file dir to `src/shared/runtime/paths.ts`, append `.js`),
rewrites `fs.mkdtempSync(path.join(os.tmpdir(), P))` -> `makeWorkspaceTempDir(P)`,
rewrites `path.join(os.tmpdir(), x)` -> `path.join(__WS_TEST_TMP__, x)`, then drops
now-unused `import * as os from 'os'` / `const os = require('os')`.

### PITFALL — multiline `import {` blocks break the "insert after last import" regex
A naive `src.replace(/^(\s*import[^\n]*\n)+/m, m[0] + insert)` matches ONLY
single-line imports and will insert the new import LINE MID-STATEMENT when the
file starts with a multiline `import {\n  a,\n  b,\n} from '...'`. Symptom:
`error TS1003: Identifier expected` at the injected line, and a corrupted
`import {\nimport { makeWorkspaceTempDir...`. FIX: detect the multiline block —
insert AFTER the closing `}` of the import, not after the first `import` token.
Verify with `npm run typecheck` (exit 0) before declaring done.

## Verification (prove it, don't assert)
- `npm run typecheck` -> exit 0 (full project — catches the import corruption).
- Run a sample of the patched tests with `node --import tsx --test "src/lib/x.test.ts" ...`.
- `du -sh workspace/tmp` should GROW during the run; the leaked patterns
  (`vf-est-*`, `capside-*`, `cs_frame_*`, `agentic-render-*`) should be **zero**
  in `C:\Users\PREM KUMAR\AppData\Local\Temp`.
- `du -sh output` must be UNCHANGED — final videos were never touched.

## GOTCHA — VERIFY the resolved path actually lands under workspace (not system TEMP)
`fs.mkdtempSync(prefix)` interprets `prefix` as the *full* template path and
creates the dir at the parent of `prefix`, appending 6 random chars. So
`fs.mkdtempSync(path.join(base, prefix))` is correct ONLY if `base` already
exists on disk. If `base` does not exist, Node still creates the dir — but it
does so under the OS default temp root, NOT `base` (the helper silently writes
to `C:\Users\PREM KUMAR\AppData\Local\Temp` while LOOKING like it worked).
- **Always `fs.mkdirSync(base, { recursive: true })` BEFORE `mkdtempSync`.**
- **Probe it live after editing** (don't trust a green typecheck — typecheck
  can't see the runtime path):
  ```bash
  node --import tsx -e "const {makeWorkspaceTempDir}=require('./src/shared/runtime/paths.ts'); \
    const d=makeWorkspaceTempDir('probe-'); \
    console.log('under workspace?:', d.includes('Automated-Video-Generator'+require('path').sep+'workspace'));"
  ```
  Must print `under workspace?: true`. (A `false` here means `base` wasn't
  created first — fix the helper, not the caller.)

## Stale-leak sweep (after patching, system TEMP still shows the patterns)
After fixing the source, a fresh sweep of system TEMP will STILL list the leaked
patterns (`agentic-render-*`, `avg-batch-*`, `ac-test-*`, `av-remotion-*`,
`agentic-vis-*`, `agentic-tts-*`, `capside-*`, `vf-est-*`, `cs_frame_*`,
`ops-test-*`, `pub-test-*`, `loc-test-*`, `avg_test_*`, `avt_*`,
`ffmpeg-smoke-*`, `ffprobe-smoke-*`, `enh_*`, `rt_*`, `voice-test-*`,
`cleaner-test-*`, `cap-*`). These are **pre-fix leftovers**, not new leaks.
Discriminate before deleting:
- **New-leak check**: `find "$LOCALAPPDATA/Temp" -maxdepth 1 <patterns> -mmin -15`
  → must be **0** after a fresh test/pipeline run (this proves the fix holds).
- **Bulk delete leftovers** (safe — all are pipeline scratch from before the fix):
  ```bash
  find "$LOCALAPPDATA/Temp" -maxdepth 1 -regextype posix-extended \
    -regex '.*/(agentic-|avg-|ac-|capside-|vf-est-|cs_frame_|ops-test-|av-remotion-|acq-|voice-test-|pub-test-|loc-test-|avt_|ffmpeg-smoke-|ffprobe-smoke-|enh_|rt_|scene-edit-|va-ts-|va-blk-|restitch)' \
    -exec rm -rf {} + 2>/dev/null
  find "$LOCALAPPDATA/Temp" -maxdepth 1 \( -name 'agentic_vo_*' -o -name '_ops-test-*' -o -name 'agentic-sfx-cache' \) -exec rm -rf {} + 2>/dev/null
  ```
- **Final proof**: `ls "$LOCALAPPDATA/Temp" | grep -iE "agentic|avg-|acq|capside|vf-est|cs_frame" | wc -l` → **0**.

## End-to-end containment proof (the bar for "everything is project-contained")
Run BOTH a real pipeline smoke AND the full test suite, then assert zero
outside-project files:
1. Live run: `tsx src/adapters/cli/agentic-modular.ts plan|visuals|voice --file input/scripts/agentic-scripts.json`
2. Full suite: `npm test` (typecheck + unit). Expect ~514/525 pass; the only
   failures are the Python voice-backend env issue (`fastapi` not installed) —
   NOT a file-location problem.
3. Assert: count of AVS-named files in `C:\Users\PREM KUMAR\AppData\Local\Temp`
   and under `LOCALAPPDATA\Automated Video Generator` is **0**.
4. Assert `git status --short` shows ONLY `M` (modified) entries — no deletions
   of old code, proving backward-compatibility.
5. Assert `du -sh output` and `du -sh workspace/jobs` are intact (final videos /
   job assets never touched).

## Out of scope
The Electron desktop app runtime resolves temp via its own `dataRoot`
(`LOCALAPPDATA/Automated Video Generator`) — a different code path; its
`agentic_ph_*.png` in system TEMP is NOT the same leak and wasn't part of this fix.
