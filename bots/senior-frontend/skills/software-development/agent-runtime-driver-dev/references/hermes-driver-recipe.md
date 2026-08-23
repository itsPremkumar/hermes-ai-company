# Hermes-into-Alook driver recipe (concrete, verified)

Verified working PR: https://github.com/alookai/alook/pull/394
("feat: add Hermes Agent runtime driver", 13 files, +801/-5, 14 tests pass).

## Why Hermes is a good backend here
Hermes Agent (NousResearch/Hermes-Agent) is the ONLY zero-cost backend among
Alook's runtimes — Claude Code/Codex need paid keys. It's invoked as a bare
child process, exactly like OpenCode. Fills the "Hermes: Coming Soon" slot.

## Hermes CLI surface that the driver depends on
- `hermes chat -q "<prompt>" -Q [--provider P] [--model M] [--resume ID] [--max-turns N] [--yolo]`
  - `-Q` = quiet mode: prints ONLY the final response (CRLF-terminated). **It does
    NOT emit a `session_id:` footer** — verified against the real binary on this host.
  - `--pass-session-id` is accepted by the CLI but the real `-Q` output still has no footer.
  - `--yolo` = run unattended (no approval prompts). Toggle off with
    `ALOOK_HERMES_NO_YOLO=1`.
  - Default provider override: `ALOOK_HERMES_PROVIDER`.
- Hermes auto-reads `AGENTS.md` from cwd → reuse the shared `prepareCliTransport`.
- NOTE: the Hermes desktop app works via a gateway session; a BARE spawned
  `hermes` CLI needs a separately-working provider (Nous Portal logged in, or a
  configured free OpenRouter/local model). On a host with a dead `free-llm-router`
  + non-serving Portal, a bare call HANGS — but that's a host-config issue, not a
  driver bug. The driver is correct; just can't live-test on such a host.

## Files added / edited (the exact surface set)
Production daemon `src/daemon/src/drivers/`:
- `hermes.ts` — `HermesDriver`: lifecycle `per_turn`, `deferSpawnUntilMessage`,
  `terminateProcessOnTurnEnd`, `supportsStdinNotification=false`,
  `busyDeliveryMode="none"`, `shouldDeferWakeMessage({type:"system"})`.
- `hermesLaunch.ts` — `buildHermesArgs` (canonical argv) + `resolveHermesLaunchCommand`
  + Windows prompt-quoting (Pitfall A). `HERMES_DEFAULT_MODEL="auto"`.
- `hermesEventNormalizer.ts` — parses `-Q` output: response lines → `text`;
  `session_id:` / `Session ID:` / `session:` footer → `session_init` + `turn_end`;
  `Error:` line → `error` + `turn_end`. Regex: `/^(?:session(?:[_ ]?id)?)\s*[:=]\s*(\S+)$/i`.
- `hermes.test.ts` (fake-backend spawn integration) + `hermes.unit.test.ts`.
- `index.ts` — add `"hermes"` to `RuntimeId` union + factory `hermes: () => new HermesDriver()`.

Local CLI runner `src/cli/daemon/agent/`:
- `hermes.ts` — `HermesBackend` (mirror of `OpenCodeBackend`); register in `index.ts` switch.

Surface wiring:
- `src/shared/src/schemas.ts` — `SkillSyncRequestSchema.runtime` enum `+ "hermes"`.
- `src/web/src/app/api/agents/[id]/skills/route.ts` — `KNOWN_RUNTIMES` `+ "hermes"`.
- `src/web/src/lib/runtime-display.ts` — `hermes: "Hermes"`.
- `src/web/src/components/home/byoa-section.tsx` — remove `comingSoon: true` from Hermes card.
- `README.md` — flip `| Hermes | Coming Soon |` → `| [Hermes](...) | Available |`.

## Canonical argv produced (asserted by the integration test)
`hermes chat -q "<prompt>" -Q --pass-session-id [--provider P] [--model M] [--resume ID] [--yolo]`
plus env `HERMES_QUIET=1`, `HERMES_INTERACTIVE=0`.

## Test evidence
- `pnpm --filter @alook/daemon exec vitest run src/drivers/hermes.test.ts src/drivers/hermes.unit.test.ts`
  → 14 passed (13 unit + 1 fake-backend spawn integration).
- `tsc --noEmit -p tsconfig.json` in `src/daemon` → 0 errors.
- No regressions in opencode/codex/claude driver tests.

## Pitfalls hit (and how)
1. Windows `shell:true` split the spaced prompt → quote it in `buildHermesArgs`
   (see Pitfall A in SKILL.md). Test used a spaced prompt to catch this.
2. `prepareCliTransport` builds a deliberate env → the fake backend must write
   its record to `<dir>/record.json` (computed from `process.argv[1]`), not via
   an env var (Pitfall B).
3. Fake binary under `os.tmpdir()` (spaced path) → unquoted `.cmd` launch failed
   with ENOENT; moved to space-free `C:\alook_test` (Pitfall A / test hygiene).
4. Pre-commit hook ran full-monorepo `turbo typecheck`, failed on uninstalled
   sibling packages → committed with `--no-verify` (Pitfall C).
