# Media / ffmpeg-pipeline hardening checklist

Used during a gstack production-grade pass on a video/asset-generation TS/Node
project. Each item is a defect class found and fixed in a real AVS (Automated
Video Generator) hardening session.

## 1. Swallowed ffmpeg errors
**Symptom:** output file is empty/broken but no error surfaced.
**Cause:** `execFileSync(ff, args, { stdio: 'ignore' })` discards stderr; the
catch block is empty or only `console.warn`s without the real cause.
**Fix (graceful-degradation preserve):**
- Prefer routing through a centralized safe runner:
  `runFfmpeg(args, {timeoutMs})` that rejects with a typed `FfmpegError`
  carrying `args` + captured `stderr` + exit code, and `SIGKILL`s the child on
  stall.
- If the call MUST fall back (never hard-fail offline), keep the fallback but
  log the cause: `catch (e: any) { console.warn(\`…failed: ${String(e?.stderr ?? e?.message).slice(0,200)}\`); }`
- A bare `catch {}` with no body is a silent failure — always surface `e?.stderr`.

**Repro / scan:**
```
grep -rnE "execFileSync\(\s*ff\(|execFileSync\(\s*FFMPEG|execFileSync\(\s*ffmpeg" src --include=*.ts | grep -v test
# count those using stdio:'ignore'
```

## 2. ffmpeg drawtext caption injection
**Symptom:** a caption containing `'` or `:` breaks the render or injects
filter args; a `'` leaks the rest of the filter as on-screen text.
**Cause:** `text='${userInput}'` interpolated raw into the filtergraph.
**Fix:** one centralized escape helper, used everywhere:
```ts
export function ffmpegDrawtextEscape(t: string): string {
  return String(t)
    .replace(/\\/g, '/')        // backslash first
    .replace(/:/g, '\\:')
    .replace(/'/g, '’')         // typographic quote avoids bare-quote leak
    .replace(/"/g, '\\"')
    .replace(/,/g, '\\,');
}
```
Apply at every `drawtext=text='…'` site (export title cards, brand wordmarks,
captions, kinetic overlays, render.ts). Do NOT keep divergent inline `replace`
chains.

**Regression test pattern** (proves the fix, no ffmpeg needed):
```ts
test('escapes apostrophe so drawtext cannot break out of the quote', () => {
  const out = ffmpegDrawtextEscape("It's a trap");
  assert.ok(!out.includes("'"), 'no bare single quote');
  assert.ok(out.includes('’'), 'typographic quote used');
});
test('captions with special chars wrap safely in a drawtext filter', () => {
  const filter = `drawtext=text='${ffmpegDrawtextEscape(`Bob's "hot:take", 2026`)}':fontcolor=white`;
  const quoteCount = (filter.match(/'/g) || []).length;
  assert.equal(quoteCount, 2, 'single quoted span');
});
```

## 3. Process / resource leaks
**Symptom:** spawned ffmpeg/python processes accumulate; RAM climbs between
jobs; a hung spawn blocks the pipeline.
**Fix:**
- Every `spawn()` that isn't already guarded needs a `setTimeout` →
  `child.kill('SIGKILL')` on stall, and `child.on('error'/'close')` handlers.
- `detached` child (Python TTS backend) on Windows: a bare `SIGTERM` kills only
  the parent shell, not the interpreter. Tear down the tree:
  ```ts
  if (process.platform === 'win32' && pid) {
    spawn('taskkill', ['/T', '/F', '/PID', String(pid)], { stdio: 'ignore', windowsHide: true });
  } else { backendProc.kill('SIGTERM'); }
  ```
**Scan:** `grep -rnE "spawn\(|spawnSync\(" src --include=*.ts | grep -v test`

## 4. CI gate
- Confirm `.github/workflows/ci.yml` (or equivalent) runs `typecheck` + `lint`
  (errors only — warnings non-blocking) + `test:unit`.
- A red CI blocks the `ship` gate. Fix lint ERRORS (not warnings) and real test
  failures first.
- Optional hardening: add a coverage threshold and an end-to-end `compose` smoke
  assertion so the empirical-proof bar is enforced in CI, not just manually.
