# Agentic Pipeline Hardening — reusable patterns

Captured while hardening the 6-stage agentic pipeline
(plan → acquire → verify → decide → gate → render) on branch
`improvement/pipeline-hardening` (worktree `C:/one/avs-improvements`, base
commit `fe22038`). Durable techniques + a verified real bug, not
environment noise.

## 1. Git worktree isolation + node_modules symlink (Windows/MSYS gotcha)

When another process/model is editing `main`, do pipeline work in an isolated
worktree so commits never collide:

```bash
cd /c/one/Automated-Video-Generator
git worktree add -b improvement/pipeline-hardening C:/one/avs-improvements <base_commit>
```

The worktree has NO `node_modules` (gitignored). Symlink the main repo's
node_modules so `tsx` resolves deps WITHOUT a reinstall (saves RAM + time):

```bash
cd /c/one/avs-improvements
cmd /c "mklink /D node_modules C:\one\Automated-Video-Generator\node_modules"
```

PITFALL: `mklink /D node_modules /c/one/...` (unix-style) produces a BROKEN
symlink resolving to `/c/C:/one/...` and `axios`/tsx fail with
MODULE_NOT_FOUND. ALWAYS pass a Windows-style absolute path to mklink
(`C:\one\...`, backslashes). Verify with `ls -la | grep node_modules` and
confirm it points at `C:\one\...`, not `/c/C:/...`.

## 2. Offline stage tests (inject fakes, no live backend)

Each stage module (acquire/verify/gateway/gate) accepts a `deps` object of
injectable functions. Unit-test by passing fakes — NO network, NO torch/kokoro:

```ts
const deps = {
  fetchVisual: async (k, kind) => [{ url: 'u', localPath: '', source: 'pexels' }],
  download: async (u, d, f) => { const p = path.join(d, f); fs.mkdirSync(d, {recursive:true}); fs.writeFileSync(p,'x'); return p; },
  fetchMusic: async () => [],
  verifyImage: async () => ({ passes: true, confidence: 8, reason: 'ok' }),
  verifyVideo: async () => ({ passes: true, confidence: 8, reason: 'ok' }),
  decide: async () => ({ decision: 'approved', rationale: 'good' }),
} as any;
const { decisions, manifest } = await runGateway(plan, candidates, deps);
```

Run single worktree suite: `npx tsx --test "src/agentic/**/*.test.ts"`.
(Use `npx tsx` when bare `node --import tsx --test` errors with
"Cannot find package 'tsx'".)

verifyAll SKIP NOTE: it calls `fs.existsSync(c.localPath)` first and SKIPS
calling verifyImage for missing files. A fake candidate pointing at
`/tmp/MISSING.jpg` yields 0 verifyImage calls — don't assert the call fired
for it. Make real temp files via `makeWorkspaceTempDir('tag-')` instead.

## 3. Gateway retry bug (verified real) — PITFALL

`gateway.ts` originally had:

```ts
for (let attempt = 0; attempt < maxRetries && !replaced; attempt++) {
  replaced = await reAcquireScene(...);
  if (replaced) {
    const rv = (await verifyAll([replaced], ws, deps))[0];
    const r2 = await deps.decide(replaced, {...});
    if (r2.decision === 'approved') { ...; break; }
  }
}
if (!replaced) decisions.push(mkDecision(c, 'rejected', ...));
```

BUG: the `&& !replaced` loop condition stops the loop as soon as
`reAcquireScene` returns ANY candidate — even if the subsequent re-verify
REJECTS it. A bad asset could slip through as "approved" on a rejected retry.
FIX: retry up to `maxRetries` regardless; only mark `rejected` if no
replacement was approved:

```ts
let replacedApproved = false;
for (let attempt = 0; attempt < maxRetries; attempt++) {
  replaced = await reAcquireScene(...);
  if (!replaced) break;
  const rv = (await verifyAll([replaced], ws, deps))[0];
  const r2 = await deps.decide(replaced, {...});
  if (r2.decision === 'approved') { candidates.push(replaced); decisions.push(mkDecision(replaced,'approved',...)); replacedApproved = true; break; }
}
if (!replacedApproved) decisions.push(mkDecision(c, 'rejected', ...));
```

## 4. Voice integration test — skip, don't fail, when backend absent

`voice-controller.test.ts` is a LIVE-backend test (needs torch/kokoro venv).
Make it skip cleanly so the suite stays green offline:

```ts
import { ensureBackend, killBackend } from '../../lib/speech-backend.js';
test('runVoiceStage ...', { timeout: 240_000 }, async (t) => {
  if (!(await ensureBackend())) {
    t.skip('voicebox backend unavailable (set VOICEBOX_PYTHON to a torch/kokoro venv)');
    return;
  }
  // ... real assertions ...
});
```

The backend resolves python via `VOICEBOX_PYTHON` or `venv/Scripts/python.exe`
(cwd-relative). `src/speech/` is the vendored backend — runs as
`python -m speech.main` with `cwd=src/`. Do NOT install torch/kokoro in a
RAM-starved box just to flip this test from skip→pass; the skip is correct
offline behavior.

## 5. Modular CLI voice stage parity — PITFALL

`agentic-modular.ts` `voice` subcommand must build a FULL `AgenticWorkspace`
(incl `audioDir`) — not a partial `{ root }`. Without `audioDir` the Kokoro
backend can't resolve its output dir. Also generate `syllableWordTimings()`
caption segments so the modular path produces real word-timed captions like
the orchestrator.

## 6. Structured logging (console.log → logInfo)

Infra: `src/shared/logging/runtime-logging.ts` exports `logInfo/logWarn/logError`
(already MCP-aware — routes to stderr in MCP runtime). Convert production
`console.log` calls. Path depth: from `src/agentic/orchestrator/*.ts` import is
`'../../shared/logging/runtime-logging.js'`; from `src/agentic/plugins/color/`
and `src/agentic/plugins/core/` it's `'../../../shared/logging/runtime-logging.js'`;
from `src/agentic/plugins/integration-example.ts` (plugins root) it's
`'../../shared/logging/runtime-logging.js'`.

Plugin files that declare "zero deps on main codebase" may instead define a
local shim (as `voice-controller.ts` does):

```ts
const console = { log: (...a) => logInfo('[VOICE-CTRL]', ...a), warn: (...a) => logWarn('[VOICE-CTRL]', ...a), error: (...a) => logError('[VOICE-CTRL]', ...a) };
```

## 7. Workspace prune default — RAM discipline

`pipeline.ts` used `?? 25` for `AGENTIC_KEEP_WORKSPACES`; `config.ts` documents
`2`. Align to `?? 2` (RAM-starved box, ~800MB free). Don't let a stale number
silently keep 25 workspaces and exhaust disk/RAM.
