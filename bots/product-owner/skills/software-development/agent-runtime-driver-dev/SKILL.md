---
name: agent-runtime-driver-dev
description: Add a backend agent-runtime driver/adapter (Claude Code, Codex, OpenCode, Hermes, Gemini, Cursor, ...) to an agent-orchestration platform that drives agents as spawned child processes (Alook-style), by mirroring an existing driver — and VERIFY it without a live inference backend / paid API key. Use when filling a "Coming Soon" runtime slot, contributing a new backend to an "AI workforce" framework, or writing subprocess-spawn integration tests for code that shells out to an external CLI.
---

# agent-runtime-driver-dev

## When to use
- You're adding a new backend agent runtime to an orchestration platform whose
  agents run as **spawned child processes** (Alook, similar "AI workforce"
  frameworks). The platform already has 2+ working drivers and a "Coming Soon"
  slot you're filling.
- You must verify the new driver **without a live inference backend** (no paid
  key, no network) — also the situation upstream CI is in.
- More generally: you need a **fake-backend integration test** for any code that
  shells out to an external CLI you can't call for real.

## Core pattern: mirror an existing driver, do NOT invent
These platforms define one `Driver` (or `AgentBackend`) interface; every backend
is a thin adapter over shared plumbing. Reuse it:
- **Shared spawn/kill:** `spawnAgentProcess` / `killProcessTree`.
- **Shared transport:** `prepareCliTransport` writes `AGENTS.md` (the standing
  prompt) into the workdir; most coding CLIs auto-read it from cwd → no bespoke
  delivery channel needed.
- **Shared probe:** `probeCliRuntime(binary)` checks PATH + `--version`.
- **Shared cross-platform resolve:** `resolveSpawnSpec` (Windows `.cmd` shim →
  `shell:true`).
- **Shared normalizer target:** `ParsedEvent` (`text` / `thinking` / `tool_call`
  / `turn_end` / `session_init` / `error`).
- **Registration:** a `RuntimeId` union + factory map in `index.ts`, plus surface
  allowlists (web `KNOWN_RUNTIMES`, shared schema enums, display-name map, README
  "Coming Soon" table).

## Lifecycle choice — copy the closest existing one
- `persistent` (Claude): one long-lived process, gated stdin steering.
- `per_turn` (OpenCode): one process per turn, `--resume <id>` for continuity,
  defer system-only wakes, terminate on turn end. **Most new CLIs fit here.**

## Verify WITHOUT a live backend (the key technique)
Write a **fake-backend spawn integration test** — don't require a real inference
call:
1. In the test, drop a stand-in executable (`.cmd` on Windows, `.sh` on POSIX)
   that (a) records the exact `argv` + relevant env to a file the test can locate,
   and (b) emits a realistic stdout transcript (response lines + a session-id
   footer).
2. Point the driver's `agentCliPath` at the fake binary; call `spawn()`; assert
   the recorded argv matches the canonical invocation shape.
3. Feed the fake transcript line-by-line through `parseLine`/`normalizeLine`;
   assert it collapses into `text` + `turn_end` + `session_init`.

Copy-paste scaffold: `templates/fake-backend-spawn-test.ts`.

### Pitfall A — Windows `shell:true` does NOT re-quote spaced args
`child_process.spawn(cmd, args, { shell: true })` on Windows does **not** wrap
args containing spaces in quotes, so `cmd.exe`'s `%*` splits `"Fix the bug"` into
4 tokens — the child gets a broken prompt.
- **Fix:** quote any positional arg with a space yourself on Windows, e.g.
  `if (process.platform === "win32" && prompt.includes(" ")) args[i] = '"' + prompt + '"'`.
  (The `src/cli` OpenCode backend does this via `quoteWinArg`/`quoteWinArgs`; the
  daemon's `spawnAgentProcess` does NOT, so the driver must.)
- **Also:** put the fake binary in a **space-free** temp dir (e.g. `C:\alook_test`),
  because the `.cmd` path itself can't be unquoted by `cmd /c` either. Use a
  `mkTmp()` that writes under a no-space base, NOT `os.tmpdir()` (which is
  `C:\Users\PREM KUMAR\...` on this box — has a space).

### Pitfall B — spawned child may not inherit arbitrary `process.env`
`prepareCliTransport`-style helpers build a *deliberate* env (layered, no raw
`process.env` passthrough) for zero-trust reasons. A test that sets
`process.env.SOME_VAR` and expects the child to see it will fail.
- **Fix:** have the fake binary write its record to a path it computes from its
  own location (`path.dirname(process.argv[1]) + '/record.json'`), which the test
  already knows because it created the dir. Don't pass the record path via env.

### Pitfall C — pre-commit hook runs the WHOLE monorepo
A `simple-git-hooks` pre-commit = `pnpm typecheck && lint && test && ...` via
`turbo` typechecks **every** package. If you only `pnpm install --filter
@scope/<yours>...`, sibling packages (email-worker, wake-worker, ...) fail
typecheck because their deps aren't installed → the commit is aborted.
- **Fix:** for a fork PR this is fine (upstream CI re-runs everything). Confirm
  YOUR packages typecheck clean (`tsc --noEmit -p tsconfig.json` → 0 errors) and
  your tests pass, then `git commit --no-verify` and note it in the commit body.

## Contribution flow (fork PR)
- `gh repo fork <upstream> --clone=false` (idempotent if the fork exists).
- Add fork remote, push feature branch, `gh pr create --head <you>:<branch>
  --base main`.
- Extend **every** surface the existing drivers touch (driver registry + web
  allowlist + shared schema enums + README table + BYOA marketing card) so the
  new runtime shows end-to-end, not just in the daemon.

## Concrete known-good example
`references/hermes-driver-recipe.md` — the exact Hermes-into-Alook driver (argv
shape, normalizer, registration edits, test results) as a reusable template.
